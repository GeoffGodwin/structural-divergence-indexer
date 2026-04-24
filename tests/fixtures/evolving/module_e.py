import asyncio


async def fetch(url: str) -> str:
    await asyncio.sleep(0)
    return url


async def process(data: str) -> str:
    await asyncio.sleep(0)
    return data.strip() if data else ""
