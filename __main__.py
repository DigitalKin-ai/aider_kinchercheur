import asyncio
import tracemalloc
from aider.main import main
from aider.gui import launch_gui

async def run_main():
    return await main()

if __name__ == "__main__":
    tracemalloc.start()
    asyncio.run(launch_gui(None))
