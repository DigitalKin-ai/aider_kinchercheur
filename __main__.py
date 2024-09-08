import asyncio
import tracemalloc
from aider.main import main
from aider.gui import launch_gui

async def async_main():
    try:
        tracemalloc.start()
        return await launch_gui(None)
    except Exception as e:
        print(f"An error occurred: {e}")
        return 1

if __name__ == "__main__":
    asyncio.run(async_main())
