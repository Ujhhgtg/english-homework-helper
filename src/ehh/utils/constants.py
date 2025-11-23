COMPLETION_WORD_MAP = {
    (): [
        "list",
        "audio",
        "text",
        "answers",
        "help",
        "account",
        "ai",
        "config",
        "exit",
    ],
    ("list",): [],
    ("audio",): ["download", "transcribe"],
    (
        "audio",
        "download",
    ): [],
    (
        "audio",
        "transcribe",
    ): [],
    ("text",): ["display", "download"],
    (
        "text",
        "display",
    ): [],
    (
        "text",
        "download",
    ): [],
    ("answers",): ["download", "fill_in", "generate", "download_from_paper", "submit"],
    ("answers", "download"): [],
    ("answers", "fill_in"): [],
    ("answers", "generate"): [],
    ("answers", "download_from_paper"): [],
    ("answers", "submit"): [],
    ("help",): [],
    ("account",): ["login", "logout", "select_default"],
    (
        "account",
        "login",
    ): [],
    (
        "account",
        "logout",
    ): [],
    (
        "account",
        "select_default",
    ): [],
    ("ai",): ["select_api", "select_model"],
    ("ai", "select_api"): [],
    ("ai", "select_model"): [],
    ("config",): ["reload", "save"],
    (
        "config",
        "reload",
    ): [],
    (
        "config",
        "save",
    ): [],
    ("exit",): [],
}


GENERATE_ANSWERS_WITH_LISTENING_PROMPT = """
Complete the following questions.

Listening audio transcription:
```
{transcription}
```

Questions:
```
{questions}
```

Output format (index starts at 1): 
```
[
    {
        "index": 1,
        "type": "choice",
        "content": "A"
    },
    # other answers
]
```

Output requirements:
1. NO MARKDOWN, NO COMMENTS, ONLY PURE JSON
2. For the groups of questions that lets you fill words/sentences into the blanks inside a whole passage: (1) treat them as "fill-in-blanks" questions, but fill in the letters that represents the words instead of the words themselves. (2) you must not use words/sentences repeatedly. one word/sentence can be used only 0~1 times.
3. There are only two types: "choice" and "fill-in-blanks". Treat translations as "fill-in-blanks" questions.
"""

GENERATE_ANSWERS_PROMPT = """
Complete the following questions.

Questions:
```
{questions}
```

Output format (index starts at 1):
```
[
    {
        "index": 1,
        "type": "choice",
        "content": "A"
    },
    {
        "index": 2,
        "type": "fill-in-blanks",
        "content": "answer to the question"
    },
    # other answers
]
```

Output requirements:
1. NO MARKDOWN, NO COMMENTS, ONLY PURE JSON
2. For the vocabulary part that lets you fill words into the blanks inside a whole passage, treat them as "fill-in-blanks" questions, but fill in the letters that represents the words instead of the words themselves.
3. There are only two types: "choice" and "fill-in-blanks". Treat translations as "fill-in-blanks" questions.
"""
