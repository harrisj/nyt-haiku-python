import pytest

from nyt_haiku.article_moderator import ArticleModerator

def test_sensitive_tags():
    a = ArticleModerator()

    assert a.is_sensitive_tag("Looting")
    assert not a.is_sensitive_tag("Arts and Entertainment")


def test_sensitive_terms():
    a = ArticleModerator()

    assert a.contains_sensitive_term("Area man murdered by angry goose")
    assert not a.contains_sensitive_term("Area man given ice cream by friendly goose")
