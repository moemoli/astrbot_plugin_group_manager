import aiohttp


async def fetch_url(url: str,headers:dict | None = None) -> dict:
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as response:
            return await response.json()
