def parse_int(string: str) -> int | None:
    try:
        return int(string)
    except ValueError:
        return None


def mask_string_middle(input_string: str) -> str:
    REVEAL_COUNT = 3

    string_length = len(input_string)

    if string_length <= 2 * REVEAL_COUNT:
        return string_length * "*"

    start_revealed = input_string[:REVEAL_COUNT]
    end_revealed = input_string[-REVEAL_COUNT:]
    middle_stars = "*" * 3
    masked_string = start_revealed + middle_stars + end_revealed

    return masked_string
