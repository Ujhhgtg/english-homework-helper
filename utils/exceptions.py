from typing import NoReturn


class BreakMatchCase(Exception):
    pass


def break_match_case() -> NoReturn:
    raise BreakMatchCase()
