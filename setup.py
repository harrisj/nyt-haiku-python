#!/usr/bin/env python3
import os

import asyncio
from dotenv import load_dotenv

from nyt_haiku import models

# settings.py
load_dotenv()

async def main():
    db_path = os.getenv("DB_PATH")
    await models.init(db_path)
    await models.setup_db()
    await models.close_db()


asyncio.run(main())
