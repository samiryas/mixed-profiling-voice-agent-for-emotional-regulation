from hrv_visualization import HRVVisualizer

class HRVVisualizationRunner:

    def __init__(self, csv_file: str):
        self.visualizer = HRVVisualizer(csv_file)

    def run_baseline_visualization(self, start_time: str):
        self.visualizer.plot_baseline_rmssd(start_time)

    def run_rolling_visualization(
        self,
        start_time: str,
        end_time: str,
        window_minutes: float = 1,
        step_seconds: int = 30
    ):
        self.visualizer.plot_rolling_rmssd(
            start_time=start_time,
            end_time=end_time,
            window_minutes=window_minutes,
            step_seconds=step_seconds
        )

def main():
    csv_file = input(
        "CSV-Datei eingeben [messung_proband1.csv]: "
    ).strip() or "messung_proband1.csv"

    runner = HRVVisualizationRunner(csv_file=csv_file)

    baseline_start = input(
        "Startzeit der 5-Minuten-Baseline eingeben "
        "(z. B. 19:40:39): "
    ).strip()

    if not baseline_start:
        print("Keine Baseline-Startzeit eingegeben. Programm wird beendet.")
        return

    try:
        runner.run_baseline_calculation(start_time=baseline_start)
    except (ValueError, TypeError) as error:
        print(f"Ungültige Baseline-Startzeit: {error}")


if __name__ == "__main__":
    main()
