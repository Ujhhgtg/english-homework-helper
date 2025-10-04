def parse_int(string: str) -> int | None:
    try:
        return int(string)
    except ValueError:
        return None


def mask_string_middle(input_string: str) -> str:
    """
    Converts a string into a censored format by keeping the first 3 and
    last 3 characters, replacing the middle section with asterisks (*).

    The resulting string maintains the original length.

    Args:
        input_string: The string to be masked (e.g., 'secret_password').

    Returns:
        The masked string (e.g., 'sec***********ord').
        If the string is 6 characters or less, it returns the original string.
    """

    REVEAL_COUNT = 3

    string_length = len(input_string)

    if string_length <= 2 * REVEAL_COUNT:
        return input_string

    start_revealed = input_string[:REVEAL_COUNT]

    end_revealed = input_string[-REVEAL_COUNT:]

    censored_length = string_length - (2 * REVEAL_COUNT)

    middle_stars = "*" * censored_length

    masked_string = start_revealed + middle_stars + end_revealed

    return masked_string
