import pandas as pd
import numpy as np
import re
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo

# Study runs in a physical lab at KIT (Karlsruhe, Germany) -- D16. The experimenter reads
# and types wall-clock time off a clock in the room, so all human-facing input/output here
# is Europe/Berlin local time. Internally, everything is compared in UTC because the
# recorder (read_polarH10.py) timestamps in UTC to align with oTree's own timestamps.
LOCAL_TZ = ZoneInfo("Europe/Berlin")


class HRVAnalyzer:

    def __init__(self, csv_file: str):
        self.csv_file = csv_file
        self.df = None
        self._load_csv()

    def _load_csv(self):
        self.df = pd.read_csv(self.csv_file)
        # utc=True: the recorder writes UTC ISO timestamps (e.g. "...+00:00"); this parses
        # them as UTC-aware. NOTE: CSVs recorded before the UTC switch contain naive LOCAL
        # time and must not be reloaded here without manually converting them first --
        # utc=True would otherwise silently misinterpret them as UTC.
        self.df["timestamp"] = pd.to_datetime(self.df["timestamp"], utc=True)
        self.df = self.df.sort_values("timestamp").reset_index(drop=True)
        first_local = self.df["timestamp"].iloc[0].tz_convert(LOCAL_TZ)
        last_local = self.df["timestamp"].iloc[-1].tz_convert(LOCAL_TZ)
        print(f"CSV geladen: {len(self.df)} RR-Werte von "
              f"{first_local.strftime('%Y-%m-%d %H:%M:%S')} bis {last_local.strftime('%Y-%m-%d %H:%M:%S')} (lokale Zeit)")

    # Erkennt reine Uhrzeit-Strings wie "14:32", "14:32:00" oder "14:32:00.500"
    _TIME_ONLY_PATTERN = re.compile(r"^\d{1,2}:\d{2}(:\d{2}(\.\d+)?)?$")

    def _parse_time(self, time_str: str) -> pd.Timestamp:
        """
        Parst einen Zeitstring als lokale Uhrzeit (Europe/Berlin) und wandelt ihn zum
        Vergleich mit self.df["timestamp"] in UTC um. Falls nur HH:MM:SS angegeben wird,
        wird das Datum aus dem ersten CSV-Zeitstempel (lokal) übernommen.
        """
        time_str = time_str.strip()

        if self._TIME_ONLY_PATTERN.match(time_str):
            # Nur Uhrzeit angegeben → lokales Kalenderdatum aus den CSV-Daten nehmen
            date = self.df["timestamp"].iloc[0].tz_convert(LOCAL_TZ).date()
            ts = pd.Timestamp(f"{date}T{time_str}")
        else:
            # Vollständiger Datetime-String (enthält Datum)
            ts = pd.Timestamp(time_str)

        return self._to_utc(ts)

    @staticmethod
    def _to_utc(ts: pd.Timestamp) -> pd.Timestamp:
        """Interpret a naive Timestamp as Europe/Berlin wall-clock time and convert to UTC;
        pass an already-tz-aware Timestamp straight through (unambiguous as given)."""
        if ts.tzinfo is None:
            ts = ts.tz_localize(LOCAL_TZ)
        return ts.tz_convert(timezone.utc)


    def _calculate_rmssd(self, rr_values: list) -> float | None:
        """
        Formel: sqrt( mean( (RR[i+1] - RR[i])^2 ) )
        """
        if len(rr_values) < 2:
            return None

        rr = np.array(rr_values)
        successive_diffs = np.diff(rr)       # Aufeinanderfolgende Differenzen
        squared_diffs = successive_diffs ** 2
        rmssd = np.sqrt(np.mean(squared_diffs))

        return round(rmssd, 2)

    def baseline_rmssd(self, start_time: str) -> float | None:
        """
        Berechnet den RMSSD für ein festes 5-Minuten-Baseline-Fenster.

        """
        start = self._parse_time(start_time)
        end = start + timedelta(minutes=5)

        mask = (self.df["timestamp"] >= start) & (self.df["timestamp"] < end)
        rr_values = self.df[mask]["rr_ms"].tolist()

        if len(rr_values) < 2:
            print(f"Zu wenige Datenpunkte im Baseline-Fenster: nur {len(rr_values)} RR-Werte gefunden.")
            return None

        rmssd = self._calculate_rmssd(rr_values)

        start_local = start.tz_convert(LOCAL_TZ)
        end_local = end.tz_convert(LOCAL_TZ)
        print(f"\n── Baseline ──────────────────────────────────")
        print(f"   Zeitfenster : {start_local.strftime('%H:%M:%S')} – {end_local.strftime('%H:%M:%S')} (lokale Zeit)")
        print(f"   RR-Werte    : {len(rr_values)}")
        print(f"   RMSSD       : {rmssd} ms")
        print(f"──────────────────────────────────────────────\n")

        return rmssd

    def rolling_rmssd(
        self,
        start_time: str,
        end_time: str,
        window_minutes: float = 1,
        step_seconds: int = 30
    ) -> list[dict]:
        start = self._parse_time(start_time)
        end = self._parse_time(end_time)

        window = timedelta(minutes=window_minutes)
        step = timedelta(seconds=step_seconds)

        if window <= timedelta(0):
            raise ValueError("window_minutes muss größer als 0 sein.")
        if step <= timedelta(0):
            raise ValueError("step_seconds muss größer als 0 sein.")

        results = []
        current = start

        print(f"\n── Rolling RMSSD (Fenster: {window_minutes} min, Schritt: {step_seconds}s) ──")

        while current + window <= end:
            window_end = current + window

            mask = (self.df["timestamp"] >= current) & (self.df["timestamp"] < window_end)
            rr_values = self.df[mask]["rr_ms"].tolist()

            rmssd = self._calculate_rmssd(rr_values)

            results.append({
                "window_start": current,
                "window_end":   window_end,
                "rmssd_ms":     rmssd,
                "n_rr":         len(rr_values)
            })

            rmssd_str = f"{rmssd} ms" if rmssd is not None else "–– (zu wenig Daten)"
            print(f"   {current.tz_convert(LOCAL_TZ).strftime('%H:%M:%S')} – "
                  f"{window_end.tz_convert(LOCAL_TZ).strftime('%H:%M:%S')} | "
                  f"RMSSD: {rmssd_str:>10} | n={len(rr_values)}")

            current += step

        print(f"──────────────────────────────────────────────\n")

        return results
       
       
        

       