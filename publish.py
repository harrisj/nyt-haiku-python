import csv
import os
import json

import asyncio
import logging
import logging.config
from tortoise import Tortoise
from jinja2 import Environment, FileSystemLoader

from dotenv import load_dotenv
from nyt_haiku import models

load_dotenv()

logger = logging.getLogger()
logging.config.fileConfig('logconfig.ini')

async def publish_csv():
    logger.info("Publishing CSV...")
    headers = ['id', 'tweet_id', 'tweeted_at', 'line0', 'line1', 'line2', 'tweet_url', 'favorite_count', 'retweet_count', 'quote_count', 'nyt_url', 'nyt_title', 'byline', 'published_at', 'section', 'tags']
    haikus = await models.Haiku.filter(tweet_id__not_isnull=True).order_by('id').all().prefetch_related("article")
    csv_path = os.getenv('CSV_OUTPUT_PATH')

    with open(csv_path, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(headers)

        for h in haikus:
            csvwriter.writerow([h.id, h.tweet_id, h.tweeted_at, h.line0, h.line1, h.line2, f"https://twitter.com/nythaikus/status/{h.tweet_id}",
                                h.favorite_count, h.retweet_count, h.quote_count, h.article.url, h.article.title,
                                h.article.byline, h.article.published_at, h.article.section, h.article.tags])

async def publish_html():
    logger.info("Publishing HTML...")

    html_path = os.getenv('HTML_OUTPUT_PATH')
    conn = Tortoise.get_connection("default")
    haikus = await conn.execute_query_dict("select h.tweet_id, h.line0, h.line1, h.line2, h.favorite_count, h.retweet_count, h.quote_count, a.url, a.title from haiku h join article a on a.id = h.article_id where h.tweet_id is NOT NULL order by favorite_count + retweet_count + quote_count DESC limit 50")

    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('index.html')
    output_from_parsed_template = template.render(haikus=haikus)

    # to save the results
    with open(html_path, "w") as fh:
        fh.write(output_from_parsed_template)


async def main():
    db_path = os.getenv("DB_PATH")
    await models.init(db_path)
    await publish_csv()
    await publish_html()
    await models.close_db()

asyncio.run(main())
