import asyncio
import csv
from datetime import datetime, timedelta, timezone
from bleak import BleakScanner, BleakClient


class readPolarH10:
    HEART_RATE_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

    def __init__(self, output_file: str, device_name_contains: str = "Polar H10"):
        self.output_file = output_file
        self.device_name_contains = device_name_contains

        self.device = None
        self.client = None
        self.csv_file = None
        self.csv_writer = None
        self.is_recording = False

        # Wall-clock arrival time of the previous BLE notification. Anchoring every packet to
        # its own real arrival time (instead of summing RR intervals from one fixed
        # session-start anchor) makes beat timestamps self-correct for clock drift and dropped
        # notifications, rather than silently accumulating offset for the rest of the session.
        # See docs/hrv_pipeline_clock_drift.md.
        self._last_arrival = None

        # UTC so beat timestamps align directly with oTree's own timestamps (phase_log,
        # vas_stress_timestamp, HRV baseline/recovery start/end all use datetime.now(utc)).
        # Injectable so tests can control "now" deterministically without real sleeps.
        self._clock = lambda: datetime.now(timezone.utc)

    async def find_device(self, timeout: int = 10):
        print("Suche nach Polar H10...")
        devices = await BleakScanner.discover(timeout=timeout)

        for device in devices:
            print(f"Gefunden: {device.name} - {device.address}")

            if device.name and self.device_name_contains.lower() in device.name.lower():
                self.device = device
                print(f"Polar-Gerät ausgewählt: {device.name} - {device.address}")
                return device

        raise RuntimeError("Kein Polar H10 gefunden. Ist der Gurt angelegt und Bluetooth aktiv?")

    async def connect(self):
        if self.device is None:
            await self.find_device()

        print("Verbinde mit Polar H10...")
        self.client = BleakClient(self.device.address)
        await self.client.connect()

        if not self.client.is_connected:
            raise RuntimeError("Verbindung zum Polar H10 fehlgeschlagen.")

        print("Verbunden.")

    async def start_recording(self):
        if self.client is None or not self.client.is_connected:
            await self.connect()

        self.csv_file = open(self.output_file, mode="w", newline="", encoding="utf-8")
        self.csv_writer = csv.writer(self.csv_file)

        self.csv_writer.writerow([
            "timestamp",
            "rr_ms",
            "hr_bpm",
            "gap_ms",
        ])

        self._last_arrival = None
        self.is_recording = True

        await self.client.start_notify(
            self.HEART_RATE_MEASUREMENT_UUID,
            self.notification_handler
        )

        print(f"Recording gestartet. Speichere nach: {self.output_file}")

    async def stop_recording(self):
        self.is_recording = False

        if self.client and self.client.is_connected:
            await self.client.stop_notify(self.HEART_RATE_MEASUREMENT_UUID)
            await self.client.disconnect()

        if self.csv_file:
            self.csv_file.close()

        print("Recording gestoppt und Datei geschlossen.")

    def notification_handler(self, sender, data: bytearray):
        if not self.is_recording:
            return

        # Wall-clock arrival time of this packet -- the authoritative time source. Using it
        # (rather than summing RR intervals from one fixed session-start anchor) means clock
        # drift and dropped notifications never compound: every packet re-anchors to real time.
        arrival_time = self._clock()
        gap_ms = 0.0
        if self._last_arrival is not None:
            gap_ms = (arrival_time - self._last_arrival).total_seconds() * 1000
        self._last_arrival = arrival_time

        hr_bpm, rr_intervals_ms = self.parse_heart_rate_measurement(data)
        if not rr_intervals_ms:
            return

        # RR intervals within one packet are in chronological order (oldest first, per the
        # Bluetooth HR Measurement spec), and the packet arrives essentially when the last beat
        # in it completes. Distribute them backwards from arrival_time using their own
        # (precise, device-measured) spacing -- only the packet's anchor point comes from the
        # wall clock, so within-packet ordering stays accurate to the millisecond.
        offsets_before_arrival = []
        running = 0.0
        for rr in reversed(rr_intervals_ms):
            offsets_before_arrival.append(running)
            running += rr
        offsets_before_arrival.reverse()

        for rr_ms, offset_ms in zip(rr_intervals_ms, offsets_before_arrival):
            beat_time = arrival_time - timedelta(milliseconds=offset_ms)
            beat_timestamp = beat_time.isoformat(timespec="milliseconds")
            self.write_rr_to_csv(beat_timestamp, rr_ms, hr_bpm, round(gap_ms, 1))
            print(f"{beat_timestamp} | HR: {hr_bpm} | RR: {rr_ms} | gap={gap_ms:.0f}ms")

    def parse_heart_rate_measurement(self, data: bytearray):
        flags = data[0]
        index = 1

        hr_is_16_bit = flags & 0x01

        if hr_is_16_bit:
            hr_bpm = int.from_bytes(data[index:index + 2], byteorder="little")
            index += 2
        else:
            hr_bpm = data[index]
            index += 1

        sensor_contact_present = flags & 0x06
        energy_expended_present = flags & 0x08
        rr_interval_present = flags & 0x10

        if energy_expended_present:
            index += 2

        rr_intervals_ms = []

        if rr_interval_present:
            while index + 1 < len(data):
                rr_raw = int.from_bytes(data[index:index + 2], byteorder="little")
                rr_ms = (rr_raw / 1024) * 1000
                rr_intervals_ms.append(round(rr_ms, 2))
                index += 2

        return hr_bpm, rr_intervals_ms

    def write_rr_to_csv(self, timestamp: str, rr_ms: float, hr_bpm: int, gap_ms: float = 0.0):
        self.csv_writer.writerow([
            timestamp,
            rr_ms,
            hr_bpm,
            gap_ms,
        ])
        self.csv_file.flush()

