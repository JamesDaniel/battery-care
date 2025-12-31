
import asyncio
from tapo import ApiClient
import psutil
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

lower_battery_threshold = 30
upper_battery_threshold = 80

LAST_DEEP_CHARGE_FILE = "last_deep_charge_date.txt"


def load_last_deep_cycle_date():
    """Load the last discharge date from file."""
    if os.path.exists(LAST_DEEP_CHARGE_FILE):
        try:
            with open(LAST_DEEP_CHARGE_FILE, 'r') as f:
                date_str = f.read().strip()
                return datetime.fromisoformat(date_str)
        except (ValueError, IOError):
            return None
    return None


def save_last_deep_cycle_date(date):
    """Save the last discharge date to file."""
    try:
        with open(LAST_DEEP_CHARGE_FILE, 'w') as f:
            f.write(date.isoformat())
    except IOError as e:
        print(f"Warning: Could not save last discharge date: {e}")


last_deep_cycle_date = load_last_deep_cycle_date()


def should_deep_cycle():
    now = datetime.now()

    # Check if it hasn't been done in more than 61 days
    if last_deep_cycle_date is None or (now - last_deep_cycle_date).days > 61:
        return True

    # Every second month
    is_odd_month = now.month % 2 == 1
    is_between_9am_and_noon = 9 <= now.hour < 12

    if is_odd_month and is_between_9am_and_noon:
        # Only return True if we haven't done it this month yet
        if (last_deep_cycle_date.month != now.month or
                last_deep_cycle_date.year != now.year):
            return True

    return False


async def deep_cycle(username, password, device_ip):
    global last_deep_cycle_date

    client = ApiClient(username, password)
    device = await client.p110(device_ip)
    await device.off()

    battery = psutil.sensors_battery()
    battery_percent = battery.percent
    while battery_percent > 5:
        await device.refresh_session()

        print(f'Deep Cycle. Waiting for battery to discharge to 5%. Current level: {battery_percent}%')
        await asyncio.sleep(60)
        battery = psutil.sensors_battery()
        battery_percent = battery.percent

    await device.on()

    while battery_percent < 99:
        await device.refresh_session()

        print(f'Deep Cycle. Waiting for battery to charge to 99%. Current level: {battery_percent}%')
        await asyncio.sleep(60)
        battery = psutil.sensors_battery()
        battery_percent = battery.percent

    await device.off()

    print('Deep cycle complete.')
    last_deep_cycle_date = datetime.now()
    save_last_deep_cycle_date(last_deep_cycle_date)


async def main():
    username = os.environ.get("API_USERNAME")
    password = os.environ.get("API_PASSWORD")
    device_ip = os.environ.get("DEVICE_IP_ADDRESS")

    if not username or not password or not device_ip:
        msg = "API_USERNAME, API_PASSWORD, and DEVICE_IP_ADDRESS"
        print(f"{msg} must be set in the .env file.")
        return

    while True:
        client = ApiClient(username, password)
        device = await client.p110(device_ip)
        device_info = await device.get_device_info()
        device_on = device_info.device_on
        battery = psutil.sensors_battery()

        if not battery:
            print('No battery detected. Ending this script.')
            break

        battery_percent = battery.percent
        charging = 'Charging' if battery.power_plugged else 'Discharging'
        print(f'Battery percent {battery_percent}, {charging}.')
        if device_on and battery_percent >= upper_battery_threshold:
            print(f'Device On and battery greater than {upper_battery_threshold}. Turning Off.')
            await device.off()
        elif not device_on and battery_percent <= lower_battery_threshold:
            print(f'Device Off and battery less than {lower_battery_threshold}. Turning On.')
            await device.on()

        if should_deep_cycle():
            await deep_cycle(username, password, device_ip)

        await asyncio.sleep(30)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        print("Program interrupted by user. Exiting...")