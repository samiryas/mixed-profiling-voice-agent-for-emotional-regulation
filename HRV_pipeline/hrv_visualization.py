import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from hrv_analyzer import HRVAnalyzer


class HRVVisualizer:

    def __init__(self, csv_file: str):
        self.analyzer = HRVAnalyzer(csv_file)

    def plot_rolling_rmssd(
        self,
        start_time: str,
        end_time: str,
        window_minutes: float = 1,
        step_seconds: int = 30
    ):
        results = self.analyzer.rolling_rmssd(
            start_time=start_time,
            end_time=end_time,
            window_minutes=window_minutes,
            step_seconds=step_seconds
        )

        # Nur Fenster mit gültigem RMSSD-Wert plotten (zu wenig Daten -> None wird übersprungen)
        timestamps = [r["window_end"] for r in results if r["rmssd_ms"] is not None]
        rmssd_values = [r["rmssd_ms"] for r in results if r["rmssd_ms"] is not None]

        if not rmssd_values:
            print("Keine gültigen RMSSD-Werte im gewählten Zeitraum gefunden.")
            return

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(timestamps, rmssd_values, marker="o", linestyle="-")

        ax.set_title(
            f"RMSSD über die Zeit (Fenster: {window_minutes} min, "
            f"Schritt: {step_seconds}s, Phase: {start_time} – {end_time})"
        )
        ax.set_xlabel("Uhrzeit")
        ax.set_ylabel("RMSSD (ms)")
        ax.grid(True)

        # Wichtig: Matplotlib zeigt Datetime-Werte sonst manchmal mit Datum/Tag-Offset an.
        # Dadurch wird auf der Achse nur HH:MM:SS angezeigt.
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.get_xaxis().get_offset_text().set_visible(False)
        fig.autofmt_xdate()

        plt.tight_layout()
        plt.show()
