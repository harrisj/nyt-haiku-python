import pytest
import collections.abc
import syllapy

from nyt_haiku import haiku
from nyt_haiku.haiku import HaikuFinder


@pytest.fixture(scope="module")
def haiku_finder():
    return HaikuFinder()


def test_sentences_from_article(haiku_finder):
    para = "It was the puzzle’s creator, an unassuming Hungarian architecture professor named Erno Rubik. When he invented the cube in 1974, he wasn’t sure it could ever be solved. Mathematicians later calculated that there are 43,252,003,274,489,856,000 ways to arrange the squares, but just one of those combinations is correct."

    sentences = haiku_finder.sentences_from_article(para)
    assert isinstance(sentences, collections.abc.Sequence)
    assert len(sentences) > 1

    sentences = haiku_finder.sentences_from_article("")
    assert isinstance(sentences, collections.abc.Sequence)
    assert len(sentences) == 0

    sentences = haiku_finder.sentences_from_article(None)
    assert isinstance(sentences, collections.abc.Sequence)
    assert len(sentences) == 0


def test_terms_from_sentence(haiku_finder):
    sentence = "It was the puzzle’s creator — an unassuming architecture professor named Erno Rubik."
    terms = haiku_finder.terms_from_sentence(sentence)

    assert terms == [("It", 1), ("was", 1), ("the", 1), ("puzzle’s", 2), ("creator", 3), ("—", 0),
                     ("an", 1), ("unassuming", 4), ("architecture", 4),
                     ("professor", 3), ("named", 1), ("Erno", 2), ("Rubik.", 2)]


def test_load_syllables_override(haiku_finder):
    sentence = "he debates all"
    terms = haiku_finder.terms_from_sentence(sentence)
    assert terms == [("he", 1), ("debates", 2), ("all", 1)]


@pytest.mark.parametrize("ldelim, rdelim", [
    (" ", "\n"),
    ("\t", "\r\n"),
    ("(", ")"),
    ("[", "]"),
    ('"', '"'),
    ('“', '”'),
    ("'", "'"),
    ("’", "’"),
    ("", ";")
])
def test_terms_from_sentence_strip(haiku_finder, ldelim, rdelim):
    sentence = f"{ldelim}Passersby were astonished by the amount of fudge{rdelim}"
    print(sentence)
    terms = haiku_finder.terms_from_sentence(sentence)
    assert len(terms) > 0
    assert terms[0] == ("Passersby", 3)
    assert terms[-1] == ("fudge", 1)


@pytest.mark.parametrize("term,expected", [
    ("apple", 2),
    ("scene's", 1),
    ("France's", 2),
    ("Disney+", 3),
    ("57", 4),
    ("1,235", 10),
    ("1952", 5),
    ("1920s", 4),
    ("buyer/seller", 4),
    ("old-fashioned", 3),
    ("2-year-old", 3),
    ("self-aware", 3),
    ("16-10", 4),
    ("-carry", 2)])
def test_syllables_for_term(haiku_finder, term, expected):
    assert haiku_finder.syllables_for_term(term) == expected


@pytest.mark.parametrize("term,expected", [
    ("weren’t", 1)])
def test_overrides_for_term(haiku_finder, term, expected):
    stripped_term = haiku.clean_term(term)
    assert stripped_term in syllapy.WORD_DICT
    assert haiku_finder.syllables_for_term(term) == expected
