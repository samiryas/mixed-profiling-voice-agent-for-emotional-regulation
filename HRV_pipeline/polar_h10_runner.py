import asyncio
import csv
from datetime import datetime, timedelta
from bleak import BleakScanner, BleakClient
from read_polarH10 import readPolarH10
from hrv_analyzer import HRVAnalyzer

class PolarH10runner:

    def __init__(self, output_file: str, duration_minutes: int = 60):
        self.output_file = output_file
        self.duration_minutes = duration_minutes
        # Nimmt Dateiname und Aufnahmedauer entgegen, erstellt intern den Logger
        self.logger = readPolarH10(output_file=self.output_file)

    async def run(self):
        try:
            await self.logger.start_recording()

            print(f"Aufnahme läuft. Automatischer Stop in {self.duration_minutes} Minuten...")
            await asyncio.sleep(self.duration_minutes * 60)

        except asyncio.CancelledError:
            print("Manuell abgebrochen.")

        finally:
            await self.logger.stop_recording()
            print("Datei gespeichert.")
    


if __name__ == "__main__":
    session = PolarH10runner(
        output_file="messung_proband1.csv",
        duration_minutes=2
    )
    asyncio.run(session.run())