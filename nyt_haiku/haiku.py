import re
import spacy
import syllapy
import hashlib

from nyt_haiku.errors import LineMismatchError

nlp = spacy.load("en_core_web_sm")

def sentences_from_article(text):
    doc = nlp(text)
    return [s.text.rstrip() for s in doc.sents]


def skip_sentence(sentence_text):
    # Skip month abbreviations
    if re.search(r'(Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|Mr|Mrs|Dr)\.', sentence_text):
        return True

    if re.search(r'["“”0-9\n]', sentence_text):
        return True

    if re.search(r'[A-Z]\.[A-Z].', sentence_text):
        return True

    if re.match(r'^\(.+[^\)]$', sentence_text):
        return True

    if re.search(r'(^By )|(photograph by)|(for the New York Times)|(illustration by)', sentence_text, flags=re.IGNORECASE):
        return True

    return False

def terms_from_sentence(text):
    cleaned_text = text.strip(r'[ \n\t"“”]')
    return [(t, syllapy.count(t)) for t in cleaned_text.split(' ')]


def seek_line(lines, max_syllables, terms):
    '''These arguments are passed by reference and altered'''
    syllable_count = 0
    line = []

    while syllable_count < max_syllables:
        if not terms:
            raise LineMismatchError("Line is too short")

        term, syllables = terms.pop(0)
        syllable_count += syllables
        line.append(term)

    if syllable_count > max_syllables:
        raise LineMismatchError("Line is too long")

    lines.append(' '.join(line))


def seek_eol(terms):
    if terms:
        raise LineMismatchError("Line is too long")


def find_haiku(sentence_text):
    if skip_sentence(sentence_text):
        return None

    terms = terms_from_sentence(sentence_text)

    lines = []

    try:
        seek_line(lines, 5, terms)
        seek_line(lines, 7, terms)
        seek_line(lines, 5, terms)
        seek_eol(terms)

        return {"lines": lines, "sentence": sentence_text, "hash": hashlib.md5(sentence_text.encode('utf-8')).hexdigest()}

    except LineMismatchError:
        return None


def find_haikus_in_article(body_text):
    haikus = []

    for sent in sentences_from_article(body_text):
        haiku = find_haiku(sent)
        if haiku:
            haikus.append(haiku)

    return haikus
