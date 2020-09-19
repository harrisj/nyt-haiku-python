import pytest
import collections

from nyt_haiku import haiku


def test_sentences_from_article():
    para = "It was the puzzle’s creator, an unassuming Hungarian architecture professor named Erno Rubik. When he invented the cube in 1974, he wasn’t sure it could ever be solved. Mathematicians later calculated that there are 43,252,003,274,489,856,000 ways to arrange the squares, but just one of those combinations is correct."

    sentences = haiku.sentences_from_article(para)
    assert isinstance(sentences, collections.Sequence)
    assert len(sentences) > 1

    sentences = haiku.sentences_from_article("")
    assert isinstance(sentences, collections.Sequence)
    assert len(sentences) == 0

    sentences = haiku.sentences_from_article(None)
    assert isinstance(sentences, collections.Sequence)
    assert len(sentences) == 0


def test_terms_from_sentence():
    sentence = "It was the puzzle’s creator, an unassuming architecture professor named Erno Rubik."
    terms = haiku.terms_from_sentence(sentence)

    assert terms == [("It", 1), ("was", 1), ("the", 1), ("puzzle’s", 2), ("creator,", 3),
                     ("an", 1), ("unassuming", 4), ("architecture", 4),
                     ("professor", 3), ("named", 1), ("Erno", 2), ("Rubik.", 2)]


def test_load_syllables_override():
    sentence = "an inspired foil"
    terms = haiku.terms_from_sentence(sentence)
    assert terms == [("an", 1), ("inspired", 3), ("foil", 2)]


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
def test_terms_from_sentence_strip(ldelim, rdelim):
    sentence = f"{ldelim}Passersby were astonished by the amount of fudge{rdelim}"
    print(sentence)
    terms = haiku.terms_from_sentence(sentence)
    assert len(terms) > 0
    assert terms[0] == ("Passersby", 3)
    assert terms[-1] == ("fudge", 1)


@pytest.mark.parametrize("term,expected", [
    ("apple", 2),
    ("57", 4),
    ("1,435", 10),
    ("1954", 5),
    ("4-year-old", 3),
    ("self-aware", 3),
    ("-carry", 2)])
def test_syllables_for_term(term, expected):
    assert haiku.syllables_for_term(term) == expected
