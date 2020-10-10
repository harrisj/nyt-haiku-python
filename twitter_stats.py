import os

import asyncio
import logging
import logging.config
from peony import PeonyClient
from dotenv import load_dotenv
from nyt_haiku import models
from nyt_haiku.models import Haiku

load_dotenv()

logger = logging.getLogger()
logging.config.fileConfig('logconfig.ini')

loop = asyncio.get_event_loop()

twitter_client = PeonyClient(consumer_key=os.getenv("TWITTER_CONSUMER_KEY_V2"),
                             consumer_secret=os.getenv("TWITTER_CONSUMER_SECRET_V2"),
                             access_token=os.getenv("TWITTER_ACCESS_TOKEN_V2"),
                             access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET_V2"),
                             api_version="2",
                             suffix="")

async def count_records():
    count = await Haiku.filter(tweet_id__not_isnull=True).count()
    logger.info(f"{count} records in DB...")
    return count


async def fetch_records(offset, limit):
    return await Haiku.filter(tweet_id__not_isnull=True).order_by('id').offset(offset).limit(limit)


def change_in_statistics(record, tweet):
    return record.retweet_count != tweet["public_metrics"]["retweet_count"] or record.favorite_count != tweet["public_metrics"]["like_count"] or record.quote_count != tweet["public_metrics"]["quote_count"]


async def update_tweet_stats(records):
    records_by_id = {}
    for r in records:
        records_by_id[r.tweet_id] = r

    logger.debug(records_by_id)

    tweet_ids = [r.tweet_id for r in records]

    dotted_parameters = {"tweet.fields": "public_metrics"}
    response = await twitter_client.api.tweets.get(
        ids=','.join(tweet_ids),
        **dotted_parameters)

    logger.debug(response)

    for t in response['data']:
        record = records_by_id[t.get("id")]
        if change_in_statistics(record, t):
            tweet_stats = t["public_metrics"]
            logger.info(f"TWEET {t.id} FAVES: {record.favorite_count} -> {tweet_stats['like_count']} RT: {record.retweet_count} -> {tweet_stats['retweet_count']} QT: {record.quote_count} -> {tweet_stats['quote_count']}")

            record.favorite_count = tweet_stats['like_count']
            record.retweet_count = tweet_stats['retweet_count']
            record.quote_count = tweet_stats['quote_count']
            await record.save()


async def fetch_and_update(offset, limit):
    logger.info(f"OFFSET: {offset}")

    records = await fetch_records(offset, limit)
    logger.info(f"Fetched {len(records)} records")
    await update_tweet_stats(records)


async def main():
    logger.info("Starting run...")
    db_path = os.getenv("DB_PATH")
    await models.init(db_path)

    count = await count_records()
    offset = 0
    limit = 100

    while offset < count:
        await fetch_and_update(offset, limit)
        offset += limit

    await models.close_db()


loop.run_until_complete(main())
