import re
import sqlite3
import tortoise
import asyncio
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, NavigableString, Comment
from datetime import datetime
from dateutil import parser
import operator
from functools import reduce

from nyt_haiku.moderator import ArticleModerator
from nyt_haiku.models import Article, Haiku

ARTICLE_MODERATOR = ArticleModerator()

NYT_SECTION_PATTERN = '^https?://www.nytimes.com/(interactive/)?202'

NYT_SECTION_URLS = ['https://www.nytimes.com/',
                    'https://www.nytimes.com/pages/world/',
                    'https://www.nytimes.com/pages/national/',
                    'https://www.nytimes.com/pages/todayspaper/',
                    'https://www.nytimes.com/pages/politics/',
                    'https://www.nytimes.com/pages/nyregion/',
                    'https://www.nytimes.com/pages/business/',
                    'https://www.nytimes.com/pages/technology/',
                    'https://www.nytimes.com/pages/sports/',
                    'https://dealbook.nytimes.com/',
                    'https://www.nytimes.com/pages/science/',
                    'https://www.nytimes.com/pages/health/',
                    'https://www.nytimes.com/pages/arts/',
                    'https://www.nytimes.com/pages/style/',
                    'https://www.nytimes.com/pages/opinion/',
                    'https://www.nytimes.com/pages/automobiles/',
                    'https://www.nytimes.com/pages/books/',
                    'https://www.nytimes.com/crosswords/',
                    'https://www.nytimes.com/pages/dining/',
                    'https://www.nytimes.com/pages/education/',
                    'https://www.nytimes.com/pages/fashion/',
                    'https://www.nytimes.com/pages/garden/',
                    'https://www.nytimes.com/pages/magazine/',
                    'https://www.nytimes.com/pages/business/media/',
                    'https://www.nytimes.com/pages/movies/',
                    'https://www.nytimes.com/pages/arts/music/',
                    'https://www.nytimes.com/pages/obituaries/',
# #                           'http://www.nytimes.com/pages/realestate/',
                    'https://www.nytimes.com/pages/t-magazine/',
                    'https://www.nytimes.com/pages/arts/television/',
                    'https://www.nytimes.com/pages/theater/',
                    'https://www.nytimes.com/pages/travel/',
                    'https://www.nytimes.com/pages/fashion/weddings/',
                    ]


def normalize_url(url:str) -> str:
    return urljoin(url, urlparse(url).path)


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
    article_urls = set([normalize_url(url) for url in article_urls if re.search(NYT_SECTION_PATTERN, url)])

    for url in article_urls:
        try:
            exists = await Article.get_or_create(url=url)
            logger.debug(f"EXISTS {url}")
            if not exists:
                logger.debug(f"CREATE ARTICLE {url}")
                await Article.create(url=url)
        except (tortoise.exceptions.IntegrityError, sqlite3.IntegrityError):
            pass


async def check_sections(session, logger):
    logger.info("SECTIONS start...")
    await asyncio.gather(*[asyncio.create_task(section_callback(session, logger, url)) for url in NYT_SECTION_URLS], return_exceptions=True)
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
    meta['byline'] = soup.find('meta', attrs={'name':'byl'}).get("content", None)
    meta['description'] = soup.find('meta', attrs={'name':'description'}).get("content", None)
    meta['keywords'] = soup.find('meta', attrs={'name':'news_keywords'}).get("content", None)
    meta['section'] = soup.find('meta', property='article:section').get("content", None)

    if ARTICLE_MODERATOR.is_sensitive_section(meta['section']):
        logger.debug(f"SENSITIVE SECTION: {meta['section']} in {url}")
        meta['sensitive'] = True

    title_tag = soup.find('meta', property='twitter:title')
    if title_tag:
        meta['title'] = title_tag.get('content', None)
    else:
        meta['title'] = soup.title

    if ARTICLE_MODERATOR.contains_sensitive_term(meta['title']):
        logger.debug(f"SENSITIVE TITLE: {meta['title']} IN {url}")
        meta['sensitive'] = True

    published_tag = soup.find('meta', property='article:published')
    if published_tag:
        meta['published_at'] = parser.parse(published_tag.get("content", None))
    else:
        meta['published_at'] = datetime.now()

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


async def save_haikus(logger, haiku_finder, article_id, url: str, body: str):
    haikus = haiku_finder.find_haikus_in_article(body)
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


async def article_callback(session, logger, haiku_finder, article: Article):
    article.sensitive = False
    text = None
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}

    async with session.get(article.url, headers=headers) as response:
        text = await response.text()

    meta, body = parse_article(logger, article.url, text)

    if meta['sensitive']:
        logger.info(f"SKIP    {article.url} SENSITIVE")
    else:
        haiku_count = await save_haikus(logger, haiku_finder, article.id, article.url, body)
        logger.info(f"FOUND {haiku_count} {article.url}")

    article.parsed = True
    article.sensitive = meta['sensitive']
    article.title = meta['title']
    article.nyt_uri = meta['nyt_uri']
    article.published_at = meta['published_at']
    article.byline = meta['byline']
    article.description = meta['description']
    article.keywords = meta['keywords']
    article.tags = meta['tags']
    article.section = meta['section']

    await article.save()


async def fetch_articles(session, logger, haiku_finder):
    logger.info("ARTICLES start...")
    unfetched_articles = await Article.filter(parsed=False).all()
    await asyncio.gather(*[asyncio.create_task(article_callback(session, logger, haiku_finder, article)) for article in unfetched_articles], return_exceptions=True)
    logger.info("ARTICLES done")
