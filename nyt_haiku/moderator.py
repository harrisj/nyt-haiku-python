import os
import re

class ArticleModerator:
    def __init__(self):
        self.init_sensitive_tags()
        self.init_sensitive_terms()
        self.init_sensitive_sections()
        self.init_awkward_abbreviations()

    def init_sensitive_tags(self):
        with open(os.path.join(os.path.dirname(__file__), 'data', 'sensitive_tags.txt')) as fp:
            self.sensitive_tags = set(line for line in (l.strip() for l in fp) if line)

        # print(f"SENSITIVE TAGS: {len(self.sensitive_tags)} loaded")

    def init_sensitive_terms(self):
        with open(os.path.join(os.path.dirname(__file__), 'data', 'sensitive_terms.txt')) as fp:
            self.sensitive_terms = set(line for line in (l.strip() for l in fp) if line)

        # print(f"SENSITIVE TERMS: {len(self.sensitive_terms)} loaded")

        sensitive_regex_string = '|'.join([f"({t})" for t in self.sensitive_terms])
        self.sensitive_term_regex = re.compile(f"\b{sensitive_regex_string}\b", re.IGNORECASE)

    def init_awkward_abbreviations(self):
        with open(os.path.join(os.path.dirname(__file__), 'data', 'bad_abbreviations.txt')) as fp:
            self.awkward_abbreviations = set(line for line in (l.strip() for l in fp) if line)

        awkward_regex_string = '|'.join([f"({t})" for t in self.awkward_abbreviations]).replace(".", "\\.")
        self.awkward_abbreviation_regex = re.compile(awkward_regex_string)

    def init_sensitive_sections(self):
        with open(os.path.join(os.path.dirname(__file__), 'data', 'sensitive_sections.txt')) as fp:
            self.sensitive_sections = set(line for line in (l.strip() for l in fp) if line)

    def is_sensitive_tag(self, tag):
        return tag in self.sensitive_tags

    def is_sensitive_section(self, tag):
        return tag in self.sensitive_sections

    def contains_sensitive_term(self, text):
        return self.sensitive_term_regex.search(text)

    def is_awkward(self, text):
        if self.awkward_abbreviation_regex.search(text):
            return True

        # if not re.search(r'[.?!;]([‘“"\)])?$', text):
        #     return True

        # Multi-character abbreviations
        if re.search('[A-Z]\\.[A-Z]\\.', text):
            return True

        # Single initials
        if re.search(r'\b[A-Z]\. ', text):
            return True

        # Multiple capitalized letters in a row (suggests a dateline)
        if re.search(r'[A-Z][A-Z]+', text):
            return True

        # Ordinals
        if re.search(r'[0-9]+(nd|st|th)', text):
            return True

        # Websites
        if re.search(r'([A-Za-z0-9]+)\.(com|org|net|ly|io)', text):
            return True

        # Bad starters
        if re.fullmatch(r"^[—\-\('’,;a-z].*", text):
            return True

        # No internal quotes
        if re.search(r' [‘“"][A-Za-z]', text) or re.search(r'[”"’] ', text):
            return True

        # Mismatched quotes
        if re.match(r'[‘“"\']', text) and re.search(r'[^‘“"\']$', text):
            return True

        if re.match(r'[^‘“"\']', text) and re.search(r'[‘“"\']$', text):
            return True

        # Mismatched parens
        if re.search(r'\([^\)]+$', text) or re.search(r'\[[^\]]+$', text):
            return True

        if re.match(r'[^\(]+\)', text) or re.match(r'[^\[]+\]', text):
            return True

        if re.search(r'\b(he|she) said', text):
            return True

        # Bad ends
        if re.fullmatch(r".+(([\-\);—:,])|(['’]s)|(\b(and|or|but)))", text):
            return True

        # Bad anywhere
        if re.search(r'[$@%#&\n\t]', text):
            return True

        # NYT Credits
        if re.search(r'(^By )|(photograph by)|(contributed reporting)|(the New York Times)|(The Times)|(illustration by)', text, flags=re.IGNORECASE):
            return True

        return False
