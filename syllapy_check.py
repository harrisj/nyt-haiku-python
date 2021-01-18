import sys
import requests
from nyt_haiku import nyt, haiku
from nyt_haiku.moderator import ArticleModerator
from nyt_haiku.haiku import HaikuFinder, clean_term
from string import punctuation
import logging
words = {}

logger = logging.getLogger(__name__)

def fetch_article(url):
    r = requests.get(url)
    assert r.status_code == 200

    meta, body = nyt.parse_article(logger, url, r.text, True)
    return body

if __name__ == "__main__":
    url = sys.argv[1]
    body = fetch_article(url)
    haiku = HaikuFinder()
    sentences = haiku.sentences_from_article(body)
    moderator = ArticleModerator()

    for sent in sentences:
        print(sent)

        terms = haiku.terms_from_sentence(sent)
        for (term, count) in terms:
            term = clean_term(term)
            words[term] = count

    haikus = haiku.find_haikus_in_article(body)

    print("\n\nTERMS")
    for word in sorted(words.keys()):
        print(f"{word}: {words[word]}")

    print("\n\nHAIKU")
    for haiku in haikus:
        if not moderator.is_awkward(haiku["sentence"]):
            print(f'{haiku["lines"][0]}\n{haiku["lines"][1]}\n{haiku["lines"][2]}\n')
