import os

import asyncio
from tortoise import Tortoise
from peony import PeonyClient
from dateutil import parser

from nyt_haiku import models

def tweet_from_haiku(haiku: models.Haiku):
    return f"{haiku.line0}\n{haiku.line1}\n{haiku.line2}\n\n{haiku.article.url}"


def change_in_counts(haiku: models.Haiku, favorite_count: int, retweet_count: int) -> bool:
    return haiku.favorite_count is None or haiku.retweet_count is None or favorite_count > haiku.favorite_count or retweet_count > haiku.retweet_count


async def tweet(session):
    twitter_client = PeonyClient(consumer_key=os.getenv("TWITTER_CONSUMER_KEY"),
                                 consumer_secret=os.getenv("TWITTER_CONSUMER_SECRET"),
                                 access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
                                 access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
                                 session=session)

    # Need to do a manual connection to order by random
    conn = Tortoise.get_connection("default")
    haiku_rows = await conn.execute_query_dict("select id from haiku where tweet_id IS NULL order by RANDOM() limit 1")

    if len(haiku_rows) > 0:
        haiku = await models.Haiku.filter(id=haiku_rows[0]["id"]).first()
        await haiku.fetch_related('article')
        haiku.tweet = tweet_from_haiku(haiku)
        print("TWEET:", haiku.tweet)
        
        response = await twitter_client.api.statuses.update.post(status=haiku.tweet, trim_user=True)
        haiku.tweet_id = response['id_str']
        haiku.tweeted_at = parser.parse(response['created_at'])
        await haiku.save()

    print("Updating tweet statistics...")
    response = await twitter_client.api.statuses.user_timeline.get(screen_name=os.getenv("TWITTER_USERNAME"), trim_user=True)
    for t in response:
        haiku = await models.Haiku.filter(tweet_id=t['id_str']).first()
        if haiku:
            favorite_count = t['favorite_count']
            retweet_count = t['retweet_count']

            if change_in_counts(haiku, favorite_count, retweet_count):
                print(f"{t['id_str']} FAVES: {haiku.favorite_count} -> {favorite_count} RT: {haiku.retweet_count} -> {retweet_count}")
                haiku.favorite_count = favorite_count
                haiku.retweet_count = retweet_count
                await haiku.save()
