import pytest
from nyt_haiku.moderator import ArticleModerator

a = ArticleModerator()

@pytest.fixture(scope="module")
def mod():
    a = ArticleModerator()
    return a

def test_sensitive_tags(mod):
    assert mod.is_sensitive_tag("Looting")
    assert not mod.is_sensitive_tag("Arts and Entertainment")


def test_sensitive_terms(mod):
    assert mod.contains_sensitive_term("Area man murdered by angry goose")
    assert not mod.contains_sensitive_term("Area man given ice cream by friendly goose")


@pytest.mark.parametrize('text', [
    "My friend Dr. Watson",
    "She retired to Boca Raton, Fla.",
    "Another day at I.B.M. for us",
    "CAIRO - The sun",
    "the nameless narrator in Yishai Sarid’s",
    "’s priorities the necessary step to",
    "— I hiked them one after the other on",
    "-aware this is the end",
    'It is not over," she said.',
    "The end;",
    "The end-",
    "The end)",
    "By Jacob Harris",
    "From match.com",
    "Jacob Harris for the New York Times",
    "photograph by Jacob Harris",
    "illustration by Jacob Harris",
    "Cost was $83 total",
    "Down 86th Street",
    "Stock of AT&T"])
def test_is_awkward_text(mod, text):
    assert mod.is_awkward(text)

@pytest.mark.parametrize('text', [
    "My friend Dr Watson",
    "self-aware this is the end",
    "This is by us",
    "How many hours of creative work do you think you do in a day?",
    "It didn’t matter how big the pool was, if there was a pool I’d jump in."])
def test_is_not_awkward(mod, text):
    assert not mod.is_awkward(text)
