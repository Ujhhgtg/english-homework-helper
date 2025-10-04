URL_LOGIN = "https://admin.jeedu.net/login"
URL_HOMEWORK_LIST = "https://admin.jeedu.net/exam/studentTaskList"

SCHOOL_SELECTOR = ".el-select > div:nth-child(1) > input:nth-child(1)"
SCHOOL_ITEM_SELECTOR = ".el-select-dropdown__item > span:nth-child(1)"
ACCOUNT_SELECTOR = (
    "div:nth-child(2) > div:nth-child(1) > div:nth-child(1) > input:nth-child(1)"
)
PASSWORD_SELECTOR = (
    "div:nth-child(3) > div:nth-child(1) > div:nth-child(1) > input:nth-child(1)"
)
SLIDER_HANDLE_SELECTOR = ".el-icon-d-arrow-right"
LOGIN_BUTTON_SELECTOR = "div.el-form-item:nth-child(7) > div:nth-child(1) > button:nth-child(1) > span:nth-child(1) > span:nth-child(1)"

ACCOUNT_DROPDOWN_SELECTOR = ".avatar-container"
LOGOUT_BUTTON_SELECTOR = ".el-dropdown-menu__item--divided"

LOGOUT_DIALOG_PRIMARY_BUTTON_SELECTOR = "button.el-button--default:nth-child(2)"
# SECURITY_DIALOG_SECONDARY_BUTTON_SELECTOR = "span.dialog-footer > button:nth-child(1)"

HOMEWORK_TABLE_SELECTOR = "tr.el-table__row"
START_TIME_SELECTOR = "td:nth-child(1) > div:nth-child(1) > span:nth-child(1)"
END_TIME_SELECTOR = "td:nth-child(2) > div:nth-child(1) > span:nth-child(1)"
TITLE_SELECTOR = "td:nth-child(3) > div:nth-child(1) > span:nth-child(1)"
TEACHER_SELECTOR = "td:nth-child(4) > div:nth-child(1)"
PASS_SCORE_SELECTOR = "td:nth-child(5) > div:nth-child(1) > span:nth-child(1)"
CURRENT_SCORE_SELECTOR = (
    "td:nth-child(6) > div:nth-child(1) > span:nth-child(1) > span:nth-child(1)"
)
TOTAL_SCORE_SELECTOR = (
    "td:nth-child(6) > div:nth-child(1) > span:nth-child(1) > span:nth-child(2)"
)
IS_PASS_SELECTOR = "td:nth-child(7) > div:nth-child(1) > span:nth-child(1)"
TEACHER_WORDS_SELECTOR = "td:nth-child(9) > div:nth-child(1)"
STATUS_SELECTOR = (
    "td:nth-child(11) > div:nth-child(1) > button:nth-child(1) > span:nth-child(1)"
)
VIEW_COMPLETED_BUTTON_SELECTOR = (
    "td:nth-child(12) > div:nth-child(1) > div:nth-child(1) > button:nth-child(1)"
)
VIEW_ORIGINAL_BUTTON_SELECTOR = (
    "td:nth-child(12) > div:nth-child(1) > div:nth-child(1) > button:nth-child(2)"
)
NEXT_PAGE_BUTTON_SELECTOR = ".btn-next"

PAPER_SELECTOR = ".el-dialog__body"

DRAG_DISTANCE_PIXELS = 300

COMPLETION_WORD_MAP = {
    (): ["list", "audio", "text", "answers", "help", "account", "ai", "config", "exit"],
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
    ("answers",): ["download", "fill_in", "generate"],
    ("answers", "download"): [],
    ("answers", "fill_in"): [],
    ("answers", "generate"): [],
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
    ("ai",): ["select_api"],
    (
        "ai",
        "select_api",
    ): [],
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
Complete the following listening comprehension.

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
        "option": "A"
    },
    # other answers
]
```

Output requirements:
1. NO MARKDOWN, NO COMMENTS, ONLY PURE JSON
2. For the vocabulary part that lets you fill words into the blanks inside a whole passage: (1) treat them as "fill-in-blanks" questions, but fill in the letters that represents the words instead of the words themselves. (2) you must not use words repeatedly. one word can be used only 0~1 times.
3. There are only two types: "choice" and "fill-in-blanks". Treat translations as "fill-in-blanks" questions.
"""

GENERATE_ANSWERS_PROMPT = """
Questions:
```
{questions}
```

Output format (index starts at 1):
```
[
    {
        "number": 1,
        "type": "choice",
        "option": "A"
    },
    {
        "index": 2,
        "type": "fill-in-blanks",
        "option": "answer to the question"
    },
    # other answers
]
```

Output requirements:
1. NO MARKDOWN, NO COMMENTS, ONLY PURE JSON
2. For the vocabulary part that lets you fill words into the blanks inside a whole passage, treat them as "fill-in-blanks" questions, but fill in the letters that represents the words instead of the words themselves.
3. There are only two types: "choice" and "fill-in-blanks". Treat translations as "fill-in-blanks" questions.
"""
