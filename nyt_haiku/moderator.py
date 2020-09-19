import os
import re

class ArticleModerator:
    def __init__(self):
        self.init_sensitive_tags()
        self.init_sensitive_terms()
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
        self.awkward_abbreviation_regex = re.compile(f"\b{awkward_regex_string}")

    def is_sensitive_tag(self, tag):
        return tag in self.sensitive_tags

    def contains_sensitive_term(self, text):
        return self.sensitive_term_regex.search(text)

    def is_awkward(self, text):
        if self.awkward_abbreviation_regex.search(text):
            return True

        # Multi-character abbreviations
        if re.search(r'[A-Z]\.[A-Z]\.', text):
            return True

        # Multiple capitalized letters in a row (suggests a dateline)
        if re.search(r'[A-Z][A-Z]+', text):
            return True

        # Ordinals
        if re.search(r'[0-9]+(nd|st|th)', text):
            return True

        # Websites
        if re.search('([A-Za-z0-9]+)\.(com|org|net|ly|io)', text):
            return True

        # Bad starters
        if re.fullmatch(r"^[—\-\('’].*", text):
            return True

        # Bad ends
        if re.fullmatch(r".+(([\-\);])|(['’]s))$", text):
            return True

        # Bad anywhere
        if re.search(r'["“”$@#&\n\t]', text):
            return True

        # NYT Credits
        if re.search(r'(^By )|(photograph by)|(for the New York Times)|(illustration by)', text, flags=re.IGNORECASE):
            return True

        return False
