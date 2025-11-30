WHISPER: bool = True
PYPERCLIP: bool = True
SELENIUM: bool = True

try:
    import whisper  # type: ignore
except ImportError:
    WHISPER = False

try:
    import pyperclip  # type: ignore
except ImportError:
    PYPERCLIP = False

try:
    import selenium  # type: ignore
except ImportError:
    SELENIUM = False
