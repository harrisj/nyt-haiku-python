import os
import re

class ArticleModerator:
    def __init__(self):
        self.init_sensitive_tags()
        self.init_sensitive_terms()

    def init_sensitive_tags(self):
        self.sensitive_tags = set()

        with open(os.path.join(os.path.dirname(__file__), 'data', 'sensitive_tags.txt')) as fp:
            self.sensitive_tags = set(line for line in (l.strip() for l in fp) if line)

        # print(f"SENSITIVE TAGS: {len(self.sensitive_tags)} loaded")

    def init_sensitive_terms(self):
        self.sensitive_terms = set()

        with open(os.path.join(os.path.dirname(__file__), 'data', 'sensitive_terms.txt')) as fp:
            self.sensitive_terms = set(line for line in (l.strip() for l in fp) if line)

        # print(f"SENSITIVE TERMS: {len(self.sensitive_terms)} loaded")

        sensitive_regex_string = '|'.join([f"({t})" for t in self.sensitive_terms])
        self.sensitive_term_regex = re.compile(f"\b{sensitive_regex_string}\b", re.IGNORECASE)

    def is_sensitive_tag(self, tag):
        return tag in self.sensitive_tags

    def contains_sensitive_term(self, text):
        return self.sensitive_term_regex.search(text)
