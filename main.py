#!/usr/bin/env python3
import os

import asyncio
import aiohttp
from dotenv import load_dotenv
from nyt_haiku import models, nyt, twitter

load_dotenv()

async def main():
    db_path = os.getenv("DB_PATH")
    await models.init(db_path)

    connector = aiohttp.TCPConnector(limit_per_host=15)
    async with aiohttp.ClientSession(connector=connector) as session:
        await nyt.check_sections(session)
        await nyt.fetch_articles(session)
        if os.getenv("DISABLE_TWITTER") != 'true':
            await twitter.tweet(session)
            
    await models.close_db()


asyncio.run(main())
print("All Done")
