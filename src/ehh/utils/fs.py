def read_file_text(path: str) -> str:
    with open(path, "rt", encoding="utf-8") as f:
        return f.read()
