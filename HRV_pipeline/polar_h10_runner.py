import asyncio

from read_polarH10 import readPolarH10

class PolarH10Runner:

    def __init__(self, output_file: str):

        self.output_file = output_file

        self.recorder = readPolarH10(output_file=self.output_file)

    async def run(self):

        try:

            print("Verbinde mit Polar H10...")

            await self.recorder.start_recording()

            print("Recording gestartet.")

            print(f"Speichere nach: {self.output_file}")

            print("Aufnahme läuft. Stoppe die Session mit Ctrl+C / Control+C.")

            while True:

                await asyncio.sleep(1)

        except KeyboardInterrupt:

            print("\nKeyboardInterrupt erkannt. Session wird gestoppt...")

        finally:

            print("Stoppe Recording...")

            await self.recorder.stop_recording()

            print("Recording beendet und Datei gespeichert.")