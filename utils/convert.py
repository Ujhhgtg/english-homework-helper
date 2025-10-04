def parse_int(string: str) -> int | None:
    try:
        return int(string)
    except ValueError:
        return None
