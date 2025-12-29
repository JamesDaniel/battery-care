
import asyncio
from tapo import ApiClient
import time
import psutil
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

async def main():


    username = os.environ.get("API_USERNAME")
    password = os.environ.get("API_PASSWORD")
    device_ip = os.environ.get("DEVICE_IP_ADDRESS")

    if not username or not password or not device_ip:
        print("API_USERNAME, API_PASSWORD, and DEVICE_IP_ADDRESS must be set in the .env file.")
        return

    while True:
        print('start of loop')
        time.sleep(30)
        client = ApiClient(username, password)
        device = await client.p110(device_ip)
        device_info = await device.get_device_info()
        device_on = device_info.device_on
        battery = psutil.sensors_battery()

        if not battery:
            print('No battery detected. Ending this script.')
            break

        battery_percent = battery.percent
        print(f'battery percent {battery_percent}')
        if device_on and battery_percent >= 80:
            print('device on and battery greater than 80. Turning Off.')
            await device.off()
        elif not device_on and battery_percent <= 30:
            print('device off and battery less than 30. Turning on.')
            await device.on()

if __name__ == "__main__":
    asyncio.run(main())
