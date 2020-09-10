import asyncio

from nyt_haiku import models, nyt


async def main():
    await models.init('haiku.db')
    await nyt.check_sections()
    await nyt.fetch_articles()


asyncio.run(main())
print("All Done")
