import logging

logger = logging.getLogger(__name__)


def decode(content, encoding="utf-8"):
    try:
        content = content.decode(encoding)
    except AttributeError:
        return content
    return content


def encode(content, encoding="utf-8"):
    """
    No python 3, converte string para bytes
    No python 2, converte unicode para string
    """
    try:
        _content = content.encode(encoding)
    except AttributeError:
        return content
    except UnicodeEncodeError:
        _content = content.encode(encoding, "xmlcharrefreplace")
    return _content
