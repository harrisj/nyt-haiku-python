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
    "Mr. Raffensperger responded quickly in a statement of his own.",
    "She retired to Boca Raton, Fla. last year.",
    "Arthur D. Lastname.",
    "Another day at I.B.M. for us.",
    "CAIRO - The sun?",
    "The nameless narrator in Yishai Sarid’s",
    "’s priorities the necessary step to",
    "— I hiked them one after the other on",
    "-aware this is the end",
    ", among other things",
    'It is not over," she said.',
    "After four years, she said to me, ‘Calvin, ",
    "Are these qualities carried in our genes, or does the life we live —",
    "He already had a pair of Crocs, he said, “but these were Bad Bunny",
    "probably revenge for a joke Michael",
    "At his expense, he said",
    "“— and make sure that we invest in the people who in fact need the help.",
    "invest in the people who in fact need the help.“",
    "The end;",
    "The end-",
    "The end)",
    "By Jacob Harris",
    "From match.com",
    "And that is why I have only one answer to every question now:",
    "Michaela Coel] is such a good writer.",
    "Michaela Coel) is such a good writer.",
    "But (Michaela Coel is such a good writer.",
    "But [Michaela Coel is such a good writer.",
    "He gave way to a lefty, Tim Hill, with two outs in the second, and",
    "He gave way to a lefty, Tim Hill, with two outs in the second, or",
    "He gave way to a lefty, Tim Hill, with two outs in the second, but",
    "Jacob Harris for the New York Times?",
    "He contacted The Times for correction!",
    "Photograph by Jacob Harris.",
    "Illustration by Jacob Harris.",
    "Cost was $83 total.",
    "Down 86th Street we strolled.",
    "Stock of AT&T declined."])
def test_is_awkward_text(mod, text):
    assert mod.is_awkward(text)

@pytest.mark.parametrize('text', [
    "My friend Dr Watson.",
    "There are 43 lights.",
    "I won't do it!",
    "Her name is Rio and she dances on the sand!",
    "Her vocal authority and pop fame?",
    "Self-aware this is the end.",
    "Michaela Coel is such an [expletive] good writer!",
    "This is by us!",
    "How many hours of creative work do you think you do in a day?",
    "It didn’t matter how big the pool was, if there was a pool I’d jump in."])
def test_is_not_awkward(mod, text):
    assert not mod.is_awkward(text)
