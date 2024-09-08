import asyncio
import tracemalloc
from aider.main import main

async def run_main():
    return await main()

if __name__ == "__main__":
    tracemalloc.start()
    asyncio.get_event_loop().run_until_complete(run_main())
