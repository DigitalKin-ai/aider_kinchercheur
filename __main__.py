import asyncio
import tracemalloc
from main import main

if __name__ == "__main__":
    tracemalloc.start()
    asyncio.run(main())
