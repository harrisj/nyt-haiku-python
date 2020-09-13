#!/usr/bin/env python3
import os

import asyncio
import aiohttp
import logging
import logging.config
from dotenv import load_dotenv
from nyt_haiku import models, nyt, twitter

load_dotenv()

logger = logging.getLogger()
logging.config.fileConfig('logconfig.ini')

async def main():
    logger.info("Starting run...")
    db_path = os.getenv("DB_PATH")
    await models.init(db_path)

    connector = aiohttp.TCPConnector(limit_per_host=15)
    async with aiohttp.ClientSession(connector=connector) as session:
        await nyt.check_sections(session, logger)
        await nyt.fetch_articles(session, logger)
        if os.getenv("DISABLE_TWITTER") != 'true':
            await twitter.tweet(session, logger)
            
    await models.close_db()
    logger.info("Ending run...")

asyncio.run(main())
