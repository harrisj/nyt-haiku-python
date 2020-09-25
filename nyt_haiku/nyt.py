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

NYT_SECTION_PATTERN = '^https?://www.nytimes.com/202'

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

# Borrowed from nyt-last-word
async def article_callback(session, logger, article: Article):
    soup = None
    article.sensitive = False

    async with session.get(article.url) as response:
        soup = BeautifulSoup(await response.text(), 'html.parser')

    for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
        comment.extract()

    try:
        article.title = soup.find('meta', property='twitter:title', content=True).get("content", None)
        article.nyt_uri = soup.find('meta', attrs={'name':'nyt_uri'}).get("content", None)
        article.published_at = parser.parse(soup.find('meta', property='article:published').get("content", None))
        article.byline = soup.find('meta', attrs={'name':'byl'}).get("content", None)
        article.description = soup.find('meta', attrs={'name':'description'}).get("content", None)
        article.keywords = soup.find('meta', attrs={'name':'news_keywords'}).get("content", None)
        article.section = soup.find('meta', property='article:section').get("content", None)
    except AttributeError as e:
        #print("META MISSING", url, e)
        article.parsed = True
        await article.save()
        return

    if ARTICLE_MODERATOR.contains_sensitive_term(article.title):
        logger.debug(f"SENSITIVE TITLE: {article.title} IN {article.url}")
        article.sensitive = True

    a_tags_meta = soup.find_all("meta", attrs={'property':'article:tag'})
    a_tags = [a.get('content') for a in a_tags_meta]
    article.tags = ';'.join(a_tags)

    for tag in a_tags:
        if ARTICLE_MODERATOR.is_sensitive_tag(tag):
            logger.debug(f"SENSITIVE TAG: {tag} IN {article.url}")
            article.sensitive = True
            break

    if article.sensitive:
        logger.info(f"SKIP    {article.url} SENSITIVE")
        article.parsed = True
        await article.save()
        return

    try:
        p_tags = list(soup.find("article", {"id": "story"}).find_all('p'))
    except AttributeError:
        logger.info(f"ERROR   {article.url} NO PARAS")
        article.parsed = True
        await article.save()
        return

    div = soup.find('div', attrs={'class': 'story-addendum story-content theme-correction'})
    if div:
        p_tags += [div]

    footer = soup.find('footer', attrs={'class': 'story-footer story-content'})
    if footer:
        p_tags += list(footer.find_all(lambda x: x.get('class') != 'story-print-citation' and x.name == 'p'))

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

    main_body = ''.join(body_strings)

#        authorids = soup.find('div', attrs={'class':'authorIdentification'})
#        authorid = authorids.getText() if authorids else ''

    top_correction = ' '.join(x.getText() for x in
                              soup.find_all('nyt_correction_top')) or ' '
    bottom_correction = ' '.join(x.getText() for x in
                                 soup.find_all('nyt_correction_bottom')) or ' '

    body = '\n'.join([top_correction,
                      main_body,
#                                   authorid,
                      bottom_correction,])


    haikus = find_haikus_in_article(body)
    haiku_count = 0

    for haiku in haikus:
        sensitive = ARTICLE_MODERATOR.contains_sensitive_term(haiku["sentence"]) or ARTICLE_MODERATOR.is_awkward(haiku["sentence"])
        exists = await Haiku.exists(hash=haiku["hash"])
        if not exists and not sensitive:
            haiku_count += 1
            logger.info(f'HAIKU {haiku["hash"]} {article.url}: {haiku["lines"][0]} / {haiku["lines"][1]} / {haiku["lines"][2]}')

            try:
                await Haiku.create(
                    hash=haiku["hash"],
                    sentence=haiku["sentence"],
                    line0=haiku["lines"][0],
                    line1=haiku["lines"][1],
                    line2=haiku["lines"][2],
                    article_id=article.id
                )
            except (tortoise.exceptions.IntegrityError, sqlite3.IntegrityError):
                # print(f'HASH COLLISION FOR {haiku["hash"]}')
                pass

    article.parsed = True

    logger.info(f"FOUND {haiku_count} {article.url}")
    await article.save()


async def fetch_articles(session, logger):
    logger.info("ARTICLES start...")
    unfetched_articles = await Article.filter(parsed=False).all()
    await asyncio.gather(*[asyncio.create_task(article_callback(session, logger, article)) for article in unfetched_articles])
    logger.info("ARTICLES done")
