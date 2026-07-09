import asyncio

from polar_h10_runner import PolarH10Runner

async def main():

    participant_id = input("Participant ID eingeben: ").strip()
    output_file = f"participant_{participant_id}_hrv_raw.csv"

    runner = PolarH10Runner(output_file=output_file)

    await runner.run()

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        print("\nProgramm wurde mit Ctrl+C / Control+C beendet.")