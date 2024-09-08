import asyncio
import tracemalloc
from aider.main import main

async def run_main():
    await main()

if __name__ == "__main__":
    tracemalloc.start()
    asyncio.run(run_main())
