import base64
import hashlib


def get_md5_str_of_str(input_string: str) -> str:
    byte_string = input_string.encode()
    md5_hash = hashlib.md5()
    md5_hash.update(byte_string)
    return md5_hash.hexdigest()


# powered by Google Gemini
# cuz idk why urlsafe_b64encode doesn't work


def encodeb64_safe(data: str) -> str:
    """
    Encodes a string into a URL- and filename-safe Base64 format.

    Replaces standard Base64 '+' with '-' and '/' with '_', and removes
    the '=' padding for a cleaner, safer result.

    Args:
        data: The input string to be encoded.

    Returns:
        The filename-safe Base64 encoded string.
    """
    # 1. Encode the string to bytes using UTF-8
    data_bytes = data.encode("utf-8")

    # 2. Use the URL-safe Base64 encoder
    encoded_bytes_with_padding = base64.urlsafe_b64encode(data_bytes)

    # 3. Remove the trailing '=' padding to make it truly filename-safe
    encoded_bytes_no_padding = encoded_bytes_with_padding.rstrip(b"=")

    # 4. Decode the result back to a standard string
    return encoded_bytes_no_padding.decode("utf-8")


def decodeb64_safe(encoded_data: str) -> str:
    """
    Decodes a string from its URL- and filename-safe Base64 format back
    to the original string.

    It automatically adds back the necessary '=' padding before decoding.

    Args:
        encoded_data: The filename-safe Base64 encoded string.

    Returns:
        The original decoded string.
    """
    # 1. Encode the string to bytes
    encoded_bytes = encoded_data.encode("utf-8")

    # 2. Calculate and re-apply padding (Base64 length must be a multiple of 4)
    # The length must be calculated modulo 4. If the remainder is 2 or 3,
    # padding is needed to make it a multiple of 4 (e.g., 2 or 1 '=' signs).
    missing_padding = len(encoded_bytes) % 4
    if missing_padding:
        encoded_bytes += b"=" * (4 - missing_padding)

    # 3. Use the URL-safe Base64 decoder
    original_bytes = base64.urlsafe_b64decode(encoded_bytes)

    # 4. Decode the result back to a standard string
    return original_bytes.decode("utf-8")
