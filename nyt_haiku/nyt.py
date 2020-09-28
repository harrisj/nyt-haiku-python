import re
import sqlite3
import tortoise
import asyncio

from bs4 import BeautifulSoup, NavigableString, Comment
from dateutil import parser
import operator
from functools import reduce

from nyt_haiku.moderator import ArticleModerator
from nyt_haiku.models import Article, Haiku
from nyt_haiku.haiku import find_haikus_in_article

ARTICLE_MODERATOR = ArticleModerator()

NYT_SECTION_PATTERN = '^https?://www.nytimes.com/(interactive/)?202'

NYT_SECTION_URLS = ['http://www.nytimes.com/',
                    'http://www.nytimes.com/pages/world/',
                    'http://www.nytimes.com/pages/national/',
                    'http://www.nytimes.com/pages/todayspaper/',
                    'http://www.nytimes.com/pages/politics/',
                    'http://www.nytimes.com/pages/nyregion/',
                    'http://www.nytimes.com/pages/business/',
                    'http://www.nytimes.com/pages/technology/',
                    'http://www.nytimes.com/pages/sports/',
                    'http://dealbook.nytimes.com/',
                    'http://www.nytimes.com/pages/science/',
                    'http://www.nytimes.com/pages/health/',
                    'http://www.nytimes.com/pages/arts/',
                    'http://www.nytimes.com/pages/style/',
                    'http://www.nytimes.com/pages/opinion/',
                    'http://www.nytimes.com/pages/automobiles/',
                    'http://www.nytimes.com/pages/books/',
                    'http://www.nytimes.com/crosswords/',
                    'http://www.nytimes.com/pages/dining/',
                    'http://www.nytimes.com/pages/education/',
                    'http://www.nytimes.com/pages/fashion/',
                    'http://www.nytimes.com/pages/garden/',
                    'http://www.nytimes.com/pages/magazine/',
                    'http://www.nytimes.com/pages/business/media/',
                    'http://www.nytimes.com/pages/movies/',
                    'http://www.nytimes.com/pages/arts/music/',
                    'http://www.nytimes.com/pages/obituaries/',
# #                           'http://www.nytimes.com/pages/realestate/',
                    'http://www.nytimes.com/pages/t-magazine/',
                    'http://www.nytimes.com/pages/arts/television/',
                    'http://www.nytimes.com/pages/theater/',
                    'http://www.nytimes.com/pages/travel/',
                    'http://www.nytimes.com/pages/fashion/weddings/',
                    ]


async def section_callback(session, logger, section_url: str):
    """Process a page and add links to the database"""
    logger.debug(f"START SECTION {section_url}")
    soup = None

    async with session.get(section_url) as response:
        soup = BeautifulSoup(await response.text(), 'html.parser')
    article_urls = [a.get('href') or '' for a in soup.find_all('a')]

    # if not http://, prepend domain name
    domain = '/'.join(section_url.split('/')[:3])
    article_urls = [url if '://' in url else operator.concat(domain, url) for url in article_urls]
    article_urls = set([url for url in article_urls if re.search(NYT_SECTION_PATTERN, url)])

    for url in article_urls:
        try:
            exists = await Article.get_or_create(url=url)
            if not exists:
                await Article.create(url=url)
        except (tortoise.exceptions.IntegrityError, sqlite3.IntegrityError):
            pass


async def check_sections(session, logger):
    logger.info("SECTIONS start...")
    await asyncio.gather(*[asyncio.create_task(section_callback(session, logger, url)) for url in NYT_SECTION_URLS])
    logger.info("SECTIONS done")


def parse_article(logger, url: str, body_html:str, parse_sensitive:bool=False):
    '''Returns metadata plus body text'''

    meta = {}
    soup = BeautifulSoup(body_html, 'html.parser')

    # Get rid of comments
    for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
        comment.extract()

    meta['sensitive'] = False
    meta['parsed'] = True
    meta['nyt_uri'] = soup.find('meta', attrs={'name':'nyt_uri'}).get("content", None)
    meta['published_at'] = parser.parse(soup.find('meta', property='article:published').get("content", None))
    meta['byline'] = soup.find('meta', attrs={'name':'byl'}).get("content", None)
    meta['description'] = soup.find('meta', attrs={'name':'description'}).get("content", None)
    meta['keywords'] = soup.find('meta', attrs={'name':'news_keywords'}).get("content", None)
    meta['section'] = soup.find('meta', property='article:section').get("content", None)

    title_tag = soup.find('meta', property='twitter:title')
    if title_tag:
        meta['title'] = title_tag.get('content', None)
    else:
        meta['title'] = soup.title

    if ARTICLE_MODERATOR.contains_sensitive_term(meta['title']):
        logger.debug(f"SENSITIVE TITLE: {meta['title']} IN {url}")
        meta['sensitive'] = True

    a_tags_meta = soup.find_all("meta", attrs={'property':'article:tag'})
    a_tags = [a.get('content') for a in a_tags_meta]
    meta['tags'] = ';'.join(a_tags)

    for tag in a_tags:
        if ARTICLE_MODERATOR.is_sensitive_tag(tag):
            logger.debug(f"SENSITIVE TAG: {tag} IN {url}")
            meta['sensitive'] = True
            break

    if meta['sensitive'] and not parse_sensitive:
        return meta, None

    body_found = False
    try:
        p_tags = list(soup.find("article", {"id": "story"}).find_all('p'))
        body_found = True
    except AttributeError:
        pass

    if not body_found:
        try:
            p_tags = list(soup.find("article", {"id": "interactive"}).find_all('p'))
            body_found = True
        except AttributeError:
            pass

    if not body_found:
        try:
            p_tags = []
            for post in list(soup.find_all("div", {"class": "live-blog-post"})):
                p_tags += post.find_all('p')
            body_found = True
        except AttributeError:
            pass

    if not body_found:
        logger.info(f"ERROR   {url} NO PARAGRAPHS")
        return meta, None

    p_contents = reduce(operator.concat, [p.contents + [NavigableString('\n')] for p in p_tags], [])

    body_strings  = []
    for node in p_contents:
        if type(node) is NavigableString:
            body_strings.append(node)
        else:
            if node.name == 'br':
                body_strings.append(' \n ')
            else:
                try:
                    body_strings.append(node.get_text())
                except:
                    body_strings.append(node)

    body = ''.join(body_strings)
    return meta, body


async def save_haikus(logger, article_id, url: str, body: str):
    haikus = find_haikus_in_article(body)
    haiku_count = 0

    for haiku in haikus:
        sensitive = ARTICLE_MODERATOR.contains_sensitive_term(haiku["sentence"]) or ARTICLE_MODERATOR.is_awkward(haiku["sentence"])
        exists = await Haiku.exists(hash=haiku["hash"])
        if not exists and not sensitive:
            haiku_count += 1
            logger.info(f'HAIKU {haiku["hash"]} {url}: {haiku["lines"][0]} / {haiku["lines"][1]} / {haiku["lines"][2]}')

            try:
                await Haiku.create(
                    hash=haiku["hash"],
                    sentence=haiku["sentence"],
                    line0=haiku["lines"][0],
                    line1=haiku["lines"][1],
                    line2=haiku["lines"][2],
                    article_id=article_id
                )
            except (tortoise.exceptions.IntegrityError, sqlite3.IntegrityError):
                # print(f'HASH COLLISION FOR {haiku["hash"]}')
                pass

    return haiku_count


async def article_callback(session, logger, article: Article):
    article.sensitive = False
    text = None
    async with session.get(article.url) as response:
        text = await response.text()

    meta, body = parse_article(logger, article.url, text)

    if meta['sensitive']:
        logger.info(f"SKIP    {article.url} SENSITIVE")
    else:
        haiku_count = await save_haikus(logger, article.id, article.url, body)
        logger.info(f"FOUND {haiku_count} {article.url}")

    article.parsed = True
    article.title = meta['title']
    article.nyt_uri = meta['nyt_uri']
    article.published_at = meta['published_at']
    article.byline = meta['byline']
    article.description = meta['description']
    article.keywords = meta['keywords']
    article.tags = meta['tags']
    article.section = meta['section']

    await article.save()


async def fetch_articles(session, logger):
    logger.info("ARTICLES start...")
    unfetched_articles = await Article.filter(parsed=False).all()
    await asyncio.gather(*[asyncio.create_task(article_callback(session, logger, article)) for article in unfetched_articles])
    logger.info("ARTICLES done")
