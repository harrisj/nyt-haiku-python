import re
import os
import csv
import spacy
import syllapy
import hashlib
from num2words import num2words
from unidecode import unidecode
from string import punctuation

from functools import reduce
import operator

from nyt_haiku.errors import LineMismatchError, SyllableCountError

nlp = spacy.load("en_core_web_sm")

SPECIAL_PUNCTUATION_BREAKS = ['-', '—']

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


def clean_term(term):
    return unidecode(term).strip().lower().strip(punctuation)


def is_special_punctuation(term):
    return term in SPECIAL_PUNCTUATION_BREAKS;


def syllables_for_term(term):
    if is_special_punctuation(term):
        return 0

    stripped_term = clean_term(term)
    try:
        r = re.match('([0-9]{4})s?$', stripped_term)
        if r:
            terms = num2words(r.group(1), to='year').split()
            return reduce(operator.add, [syllables_for_term(term) for term in terms])

        if re.match('[0-9,]+$', stripped_term):
            terms = num2words(int(stripped_term.replace(',', ''))).split()
            return reduce(operator.add, [syllables_for_term(term) for term in terms])

        r = re.match('([0-9]+)-([0-9]+)$', stripped_term)
        if r:
            s1 = syllables_for_term(r.group(1))
            s2 = syllables_for_term(r.group(2))
            return s1 + s2 + 1

        r = re.match('([^-]+)[-/](.+)$', stripped_term)
        if r:
            s1 = syllables_for_term(r.group(1))
            s2 = syllables_for_term(r.group(2))

            if s1 == 0 or s2 == 0:
                return 0
            else:
                return s1 + s2

        c = syllapy.count(term)
        return c

    except Exception as err:
        raise SyllableCountError("Unable to count syllables for term")


def terms_from_sentence(text):
    cleaned_text = text.strip("[ \r\n\t\"“”'’\\(\\)\\[\\];]")
    return [(t, syllables_for_term(t)) for t in cleaned_text.split()]


def seek_line(lines, max_syllables, terms):
    '''These arguments are passed by reference and altered'''
    syllable_count = 0
    line = []

    while syllable_count < max_syllables:
        if not terms:
            raise LineMismatchError("Line is too short")

        term, syllables = terms.pop(0)

        if syllables == 0 and not is_special_punctuation(term):
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
