import asyncio
import tracemalloc
from main import main

async def run_main():
    return await main()

if __name__ == "__main__":
    tracemalloc.start()
    asyncio.run(run_main())
