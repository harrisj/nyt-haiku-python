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

SPECIAL_PUNCTUATION_BREAKS = ['-', '—']


def clean_term(term):
    return unidecode(term).strip().lower().strip(punctuation)


def is_special_punctuation(term):
    return term in SPECIAL_PUNCTUATION_BREAKS


def has_syllable_exception(term):
    return term in syllapy.WORD_DICT


class HaikuFinder():
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")

        # Load additional syllable definitions beyond syllapy
        syllable_file_path = os.path.join(os.path.dirname(__file__), 'data', 'syllable_counts.csv')
        with open(syllable_file_path, newline='') as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) == 2:
                    word = row[0].lower()
                    count = int(row[1])
                    syllapy.WORD_DICT[word] = count

    def sentences_from_article(self, text):
        if not text:
            return []

        doc = self.nlp(text)
        return [s.text.rstrip() for s in doc.sents]

    def syllables_for_term(self, term):
        if is_special_punctuation(term):
            return 0

        # Some things to do before stripping the term
        # Disney+, Apple+, etc.
        r = re.match('(.+)\+$', term)
        if r:
            return self.syllables_for_term(r.group(1)) + 1

        stripped_term = clean_term(term)
        try:
            if has_syllable_exception(stripped_term):
                return syllapy.count(stripped_term)

            r = re.match("(.+)'s$", stripped_term)
            if r:
                # Most possessive's don't add syllables
                return syllapy.count(r.group(1))

            r = re.match('([0-9]{4})s?$', stripped_term)
            if r:
                terms = num2words(r.group(1), to='year').split()
                return reduce(operator.add, [self.syllables_for_term(term) for term in terms])

            if re.match('[0-9,]+$', stripped_term):
                terms = num2words(int(stripped_term.replace(',', ''))).split()
                return reduce(operator.add, [self.syllables_for_term(term) for term in terms])

            r = re.match('([0-9]+)-([0-9]+)$', stripped_term)
            if r:
                s1 = self.syllables_for_term(r.group(1))
                s2 = self.syllables_for_term(r.group(2))
                if s1 and s2:
                    return s1 + s2 + 1
                else:
                    return 0

            r = re.match('([^-]+)[-/](.+)$', stripped_term)
            if r:
                s1 = self.syllables_for_term(r.group(1))
                s2 = self.syllables_for_term(r.group(2))

                if s1 and s2:
                    return s1 + s2
                else:
                    return 0

            c = syllapy.count(stripped_term)
            return c

        except RuntimeError as err:
            raise SyllableCountError("Unable to count syllables for term")

    def terms_from_sentence(self, text):
        cleaned_text = text.strip("[ \r\n\t\"“”'’\\(\\)\\[\\];]")
        return [(t, self.syllables_for_term(t)) for t in cleaned_text.split()]

    def seek_line(self, lines, max_syllables, terms):
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

    def seek_eol(self, terms):
        if terms:
            raise LineMismatchError("Line is too long")

    def find_haiku(self, sentence_text):
        try:
            terms = self.terms_from_sentence(sentence_text)
        except SyllableCountError:
            return None
    
        lines = []

        try:
            self.seek_line(lines, 5, terms)
            self.seek_line(lines, 7, terms)
            self.seek_line(lines, 5, terms)
            self.seek_eol(terms)

            return {"lines": lines, "sentence": sentence_text, "hash": hashlib.md5(sentence_text.encode('utf-8')).hexdigest()}

        except LineMismatchError:
            return None

    def find_haikus_in_article(self, body_text):
        haikus = []

        for sent in self.sentences_from_article(body_text):
            haiku = self.find_haiku(sent)
            if haiku:
                haikus.append(haiku)

        return haikus
