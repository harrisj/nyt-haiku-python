from tortoise import Tortoise, run_async, fields
from tortoise.models import Model


class Article(Model):
    id = fields.IntField(pk=True)
    parsed = fields.BooleanField(null=False, default=False)
    url = fields.CharField(max_length=1024, unique=True, null=False)
    nyt_uri = fields.TextField(null=True)
    title = fields.TextField(null=True)
    published_at = fields.DatetimeField(null=True)
    description = fields.TextField(null=True)
    byline = fields.TextField(null=True)
    section = fields.CharField(max_length=32, null=True)
    keyword = fields.TextField(null=True)
    sensitive = fields.BooleanField(null=False, default=False)
    tiny_url = fields.TextField(null=True)


class Haiku(Model):
    id = fields.IntField(pk=True)
    hash = fields.CharField(max_length=255, unique=True, null=False)
    article = fields.ForeignKeyField('models.Article', related_name='haiku')
    sentence = fields.TextField()
    line0 = fields.TextField()
    line1 = fields.TextField()
    line2 = fields.TextField()
    tweet = fields.TextField(null=True)
    tweet_id = fields.TextField(null=True)
    tweeted_at = fields.DatetimeField(null=True)
    retweet_count = fields.IntField(null=False, default=0)
    favorite_count = fields.IntField(null=False, default=0)


async def init(path):
    # Here we connect to a SQLite DB file.
    # also specify the app name of "models"
    # which contain models from "app.models"
    await Tortoise.init(
        db_url=f'sqlite://{path}',
        modules={'models': ['nyt_haiku.models']}
    )


async def setup_db():
    await Tortoise.generate_schemas()


async def close_db():
    await Tortoise.close_connections()
