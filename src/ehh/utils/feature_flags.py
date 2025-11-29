WHISPER: bool = True
PYPERCLIP: bool = True


def init() -> None:
    global WHISPER, PYPERCLIP

    try:
        import whisper  # type: ignore
    except ImportError:
        WHISPER = False

    try:
        import pyperclip  # type: ignore
    except ImportError:
        PYPERCLIP = False
