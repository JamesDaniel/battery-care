import psutil
import asyncio
import os
import datetime

from tapo_client import TapoDevice

LAST_DEEP_CHARGE_FILE = "last_deep_charge_date.txt"
upper_battery_threshold = 80
lower_battery_threshold = 30


class LaptopBattery:

    def initialize(self):
        self.battery = psutil.sensors_battery()
        if not self.battery:
            print('No battery detected. Ending this script.')
            raise Exception('No battery detected.')

    def get_percent(self) -> float:
        self.battery = psutil.sensors_battery()
        return self.battery.percent

    async def charge(self, plug: TapoDevice, target_percent=upper_battery_threshold):
        print(f'Charging to {target_percent}%')
        await plug.on()
        battery_percent = self.get_percent()
        while battery_percent < target_percent:
            print(f'Charging. Current battery level: {self.get_percent()}%')
            await asyncio.sleep(30)
            if self.get_percent() < battery_percent:
                # Laptop plug automation set in Tapo app:
                #   When plug turned on, turn it off after 1 hour.
                print('Battery level dropped during charge cycle. Turning on plug.')
                await plug.on()
            battery_percent = self.get_percent()
        print('Charging complete.')

    async def discharge(self, plug: TapoDevice, target_percent=lower_battery_threshold):
        print(f'Discharging to {target_percent}%')
        await plug.off()
        battery_percent = self.get_percent()
        while battery_percent > target_percent:
            print(f'Discharging. Current battery level: {self.get_percent()}%')
            await asyncio.sleep(30)
            if self.get_percent() > battery_percent:
                print('Battery level increased during discharge cycle. Turning off plug.')
                await plug.off()
            battery_percent = self.get_percent()
        print('Discharging complete.')


class LaptopClient:
    def __init__(self):
        self.last_deep_cycle_date: datetime.datetime | None = None

    def initialize(self):
        self.last_deep_cycle_date = self.load_last_deep_cycle_date()

    def create_battery(self):
        battery = LaptopBattery()
        battery.initialize()
        return battery

    def load_last_deep_cycle_date(self) -> datetime.datetime:
        """Load the last discharge date from file."""
        if os.path.exists(LAST_DEEP_CHARGE_FILE):
            try:
                with open(LAST_DEEP_CHARGE_FILE, 'r') as f:
                    date_str = f.read().strip()
                    return datetime.datetime.fromisoformat(date_str)
            except (ValueError, IOError):
                return None
        return None

    def save_last_deep_cycle_date(self, date: datetime.datetime):
        """Save the last discharge date to file."""
        try:
            with open(LAST_DEEP_CHARGE_FILE, 'w') as f:
                f.write(date.isoformat())
        except IOError as e:
            print(f"Warning: Could not save last discharge date: {e}")

    def should_deep_cycle(self) -> bool:
        now = datetime.datetime.now()

        # Check if it hasn't been done in more than 61 days
        if self.last_deep_cycle_date is None or (now - self.last_deep_cycle_date).days > 61:
            return True

        # Every second month
        is_odd_month = now.month % 2 == 1
        is_between_9am_and_noon = 9 <= now.hour < 12

        if is_odd_month and is_between_9am_and_noon:
            # Only return True if we haven't done it this month yet
            if (self.last_deep_cycle_date.month != now.month or
                    self.last_deep_cycle_date.year != now.year):
                return True

        return False

    async def deep_cycle(self, device: TapoDevice, battery: LaptopBattery):
        print(f'Deep Cycle. Waiting for battery to discharge to 5%. Current level: {battery.get_percent()}%')
        await battery.discharge(device, target_percent=5)

        print(f'Deep Cycle. Waiting for battery to charge to 100%. Current level: {battery.get_percent()}%')
        await battery.charge(device, target_percent=100)

        print('Deep cycle complete.')
        self.last_deep_cycle_date = datetime.datetime.now()
        self.save_last_deep_cycle_date(self.last_deep_cycle_date)
