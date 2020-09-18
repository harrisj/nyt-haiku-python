import re
import os
import csv
import spacy
import syllapy
import hashlib
from num2words import num2words
from string import punctuation

from nyt_haiku.errors import LineMismatchError, SyllableCountError

nlp = spacy.load("en_core_web_sm")

# Load additional syllable definitions beyond syllapy
syllable_file_path = os.path.join(os.path.dirname(__file__), 'data', 'syllable_counts.csv')
with open(syllable_file_path, newline='') as file:
    reader = csv.reader(file)
    for row in reader:
        if len(row) == 2:
            word = row[0].lower()
            count = int(row[1])
            syllapy.WORD_DICT[word] = count


def sentences_from_article(text):
    if not text:
        return []

    doc = nlp(text)
    return [s.text.rstrip() for s in doc.sents]


def syllables_for_term(term):
    stripped_term = term.strip().lower().strip(punctuation)

    try:
        if re.match('[0-9,]+$', stripped_term):
            return syllapy.count(num2words(int(stripped_term.replace(',', ''))))

        r = re.match('([^-]+)-([^-]+)$', stripped_term)
        if r:
            return syllapy.count(r.group(1)) + syllapy.count(r.group(2))

        return syllapy.count(term)

    except Exception:
        raise SyllableCountError("Unable to count syllables for term")


def terms_from_sentence(text):
    cleaned_text = text.strip("[ \r\n\t\"“”'’\\(\\)\\[\\];]")
    return [(t, syllables_for_term(t)) for t in cleaned_text.split(' ')]


def seek_line(lines, max_syllables, terms):
    '''These arguments are passed by reference and altered'''
    syllable_count = 0
    line = []

    while syllable_count < max_syllables:
        if not terms:
            raise LineMismatchError("Line is too short")

        term, syllables = terms.pop(0)

        if syllables == 0:
            raise LineMismatchError("Syllable count missing for term")
        
        syllable_count += syllables
        line.append(term)

    if syllable_count > max_syllables:
        raise LineMismatchError("Line is too long")

    lines.append(' '.join(line))


def seek_eol(terms):
    if terms:
        raise LineMismatchError("Line is too long")


def find_haiku(sentence_text):
    try:
        terms = terms_from_sentence(sentence_text)
    except SyllableCountError:
        return None

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
