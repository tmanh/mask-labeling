__appname__ = "Labeling App - TMA"

__version__ = "0.1.0"


def fmtShortcut(text):
    mod, key = text.split("+", 1)
    return "<b>%s</b>+<b>%s</b>" % (mod, key)