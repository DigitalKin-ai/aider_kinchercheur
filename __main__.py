import asyncio
import tracemalloc
import traceback
from aider.main import main
from aider.gui import gui_main

async def async_main():
    try:
        tracemalloc.start()
        return await gui_main()
    except Exception as e:
        print(f"An error occurred: {e}")
        print(f"Error details: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    asyncio.run(async_main())
