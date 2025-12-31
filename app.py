import asyncio
from dotenv import load_dotenv
from laptop_client import LaptopBattery, LaptopClient
from tapo_client import TapoClient

load_dotenv()


async def main():
    tapo = TapoClient()
    laptop = LaptopClient()
    laptop.initialize()
    plug = await tapo.create_device()
    battery: LaptopBattery = laptop.create_battery()

    while True:
        if laptop.should_deep_cycle():
            await laptop.deep_cycle(plug, battery)

        await battery.charge(plug)
        await asyncio.sleep(5)
        await battery.discharge(plug)
        await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        print("Program interrupted by user. Exiting...")
