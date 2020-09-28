import os
import sys
import pytest
from dateutil import parser
import logging

from nyt_haiku import nyt, haiku

logger = logging.getLogger(__name__)
logger.setLevel(logging.NOTSET)


def test_normalize_url():
    assert nyt.normalize_url('http://www.foo.com/') == "http://www.foo.com/"
    assert nyt.normalize_url('http://www.foo.com/bar?baz=quux') == "http://www.foo.com/bar"


def test_parse_article():
    path = os.path.join(os.path.dirname(__file__), 'samples', 'article.html')
    html = ''

    with open(path) as file:
        html = file.read()

    meta, body = nyt.parse_article(logger, 'http://nytimes.com/', html)

    assert body is not None
    assert not meta['sensitive']
    assert meta['parsed']
    assert meta['title'] == "How to Negotiate With Your Landlord"
    assert meta['nyt_uri'] == 'nyt://article/41bdb446-cd51-57ad-9d24-a78f587d42e1'
    assert meta["published_at"] == parser.parse('2020-09-25T13:00:08.000Z')
    assert meta['byline'] == 'By Ronda Kaysen'
    assert meta['description'] == 'It’s a renter’s market. Here are some tips to help you take advantage of your power as a tenant.'
    assert meta['keywords'] == 'Real Estate, Housing,Rent,Landlord,Service Content,Shelter-in-Place (Lifestyle);Social Distancing,Brooklyn,Manhattan,Queens'
    assert meta['section'] == 'Real Estate'
    assert meta['tags'] == 'Real Estate and Housing (Residential);Renting and Leasing (Real Estate);Landlords;Content Type: Service;Quarantine (Life and Culture);Brooklyn (NYC);Manhattan (NYC);Queens (NYC)'



def test_parse_blog():
    path = os.path.join(os.path.dirname(__file__), 'samples', 'live_blog.html')
    html = ''

    with open(path) as file:
        html = file.read()

    meta, body = nyt.parse_article(logger, 'http://nytimes.com/', html)

    assert body is not None
    assert not meta['sensitive']
    assert meta['parsed']
    assert meta['title'] == 'Tech Stocks Lead Wall Street Higher: Live Business Briefing'
    assert meta['nyt_uri'] == 'nyt://legacycollection/19601213-5afe-5bb1-9b8d-4b0b416356be'
    assert meta['published_at'] == parser.parse('2020-09-25T10:28:45.000Z')
    assert meta['byline'] == 'By Kevin Granville and Mohammed Hadi'
    assert meta['description'] == ''
    assert meta['keywords'] == 'null'
    assert meta['section'] == 'Business'
