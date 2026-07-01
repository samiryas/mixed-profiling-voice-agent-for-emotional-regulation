import matplotlib.pyplot as plt
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

        plt.figure(figsize=(12, 6))
        plt.plot(timestamps, rmssd_values, marker='o', linestyle='-')
        plt.title(
            f"RMSSD über die Zeit (Fenster: {window_minutes} min, "
            f"Schritt: {step_seconds}s, Phase: {start_time} – {end_time})"
        )
        plt.xlabel("Zeit")
        plt.ylabel("RMSSD (ms)")
        plt.grid()
        plt.show()