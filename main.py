#!/usr/bin/env python3
import os

import asyncio
from dotenv import load_dotenv
from nyt_haiku import models, nyt

load_dotenv()

async def main():
    db_path = os.getenv("DB_PATH")
    await models.init(db_path)
    await nyt.check_sections()
    await nyt.fetch_articles()
    await models.close_db()


asyncio.run(main())
print("All Done")
