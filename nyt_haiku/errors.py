class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class LineMismatchError(Error):
    pass


class SyllableCountError(Error):
    pass
