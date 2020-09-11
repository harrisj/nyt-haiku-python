import asyncio

from nyt_haiku import models, nyt

loop = asyncio.get_event_loop()
loop.run_until_complete(models.init('haiku.db'))
loop.run_until_complete(nyt.check_sections())
# Zero-sleep to allow underlying connections to close
loop.run_until_complete(asyncio.sleep(0))
loop.run_until_complete(nyt.fetch_articles())
# Zero-sleep to allow underlying connections to close
loop.run_until_complete(asyncio.sleep(0))
loop.close()

print("All Done")
