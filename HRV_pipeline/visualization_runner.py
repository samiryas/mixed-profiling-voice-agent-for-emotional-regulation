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


if __name__ == "__main__":
    runner = HRVVisualizationRunner(csv_file="messung_proband1.csv")
    runner.run_rolling_visualization(
        start_time="19:40:39",
        end_time="19:42:39",
        window_minutes=1,
        step_seconds=20
    )