#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import (
    Options as FirefoxOptions,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains  # Import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
import time
import atexit
from rich.console import Console
from rich.highlighter import ReprHighlighter
from rich.theme import Theme
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import choice
from prompt_toolkit.completion import WordCompleter
import urllib.request
import threading
import whisper
from pathlib import Path
import telegram
from telegram import Update, ForceReply
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

from constants import *
from models.homework_record import HomeworkRecord
from models.homework_status import HomeworkStatus
from models.ai_client import AIClient
from local.credentials import CREDENTIALS_LIST
from local.ai_clients import AI_CLIENT_LIST
from local.telegram_bot_token import TELEGRAM_BOT_TOKEN


driver_options = FirefoxOptions()
driver_options.binary_location = "/usr/bin/firefox"
driver = webdriver.Firefox(options=driver_options)
wait = WebDriverWait(driver, 15)
whisper_model: whisper.model.Whisper | None = None
session = PromptSession()


_console: Console | None = None


def print(*args, **kwargs):
    global _console
    if not _console:
        highlighter = ReprHighlighter()
        highlighter.highlights.extend(
            [
                r"(?i)(?P<info>info)",
                r"(?i)(?P<warning>warning)",
                r"(?i)(?P<error>error)",
            ]
        )
        theme = Theme(
            {
                "repr.info": "bold green",
                "repr.warning": "bold yellow",
                "repr.error": "bold red",
            }
        )
        _console = Console(highlighter=highlighter, theme=theme)
    _console.print(*args, **kwargs)


def _close_browser_on_exit():
    global driver
    if driver:
        try:
            driver.current_url
            driver.quit()
            print("<info> atexit: browser closed automatically")
        except Exception:
            pass


def _safe_get_text(element, selector: str):
    """Safely finds and returns the text of a child element, returns None on failure."""
    try:
        # Use a dot prefix for relative CSS selectors when using find_element
        # Since the elements are nested within the table row, we use the relative selector
        return element.find_element(By.CSS_SELECTOR, selector).text
    except:
        return None


def _get_status_enum(status_text: str | None) -> HomeworkStatus | None:
    """Converts the scraped status string to the HomeworkStatus Enum."""
    if not status_text:
        return None

    for member in HomeworkStatus:
        if member.value == status_text:
            return member

    return None


def login(driver):
    print("--- step: login ---")

    credentials_choice = choice(
        "select credentials to use:",
        options=list(
            map(
                lambda c: (c.username, f"{c.school} / {c.username} / {c.password}"),
                CREDENTIALS_LIST,
            )
        ),
    )
    credentials = next(c for c in CREDENTIALS_LIST if c.username == credentials_choice)

    school_string = credentials.school
    school_field = driver.find_element(By.CSS_SELECTOR, SCHOOL_SELECTOR)
    # school_field.click()
    school_field.send_keys(school_string)
    print(f"<info> entered '{school_string}' into school field")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, SCHOOL_ITEM_SELECTOR)))
    school_item = driver.find_element(By.CSS_SELECTOR, SCHOOL_ITEM_SELECTOR)
    school_item.click()
    print(f"<info> selected school item")

    account_string = credentials.username
    account_field = driver.find_element(By.CSS_SELECTOR, ACCOUNT_SELECTOR)
    account_field.send_keys(account_string)
    print(f"<info> entered '{account_string}' into account field")

    password_string = credentials.password
    password_field = driver.find_element(By.CSS_SELECTOR, PASSWORD_SELECTOR)
    password_field.send_keys(password_string)
    print(f"<info> entered '{password_string}' into password field")

    slider_handle = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, SLIDER_HANDLE_SELECTOR))
    )
    actions = ActionChains(driver)
    actions.click_and_hold(slider_handle).move_by_offset(
        DRAG_DISTANCE_PIXELS, 0
    ).release().perform()
    print(
        f"<info> dragged slider {DRAG_DISTANCE_PIXELS} pixels to the right (x-offset)"
    )

    login_button = driver.find_element(By.CSS_SELECTOR, LOGIN_BUTTON_SELECTOR)
    login_button.click()


def get_homework_list(driver) -> list[HomeworkRecord]:
    """Finds and extracts data from all homework rows on the current page (table structure)."""

    print("--- step: parse homework list ---")
    homework_records: list[HomeworkRecord] = []

    try:
        wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, HOMEWORK_TABLE_SELECTOR))
        )

        homework_rows = driver.find_elements(By.CSS_SELECTOR, HOMEWORK_TABLE_SELECTOR)

        if not homework_rows:
            print(
                "<warning> no homework items found using selector:",
                HOMEWORK_TABLE_SELECTOR,
            )
            return []

        print(f"<info> found {len(homework_rows)} homework items to parse")

        for i, row in enumerate(homework_rows):
            title = _safe_get_text(row, TITLE_SELECTOR)
            start_time = _safe_get_text(row, START_TIME_SELECTOR)
            end_time = _safe_get_text(row, END_TIME_SELECTOR)
            teacher_name = _safe_get_text(row, TEACHER_SELECTOR)
            pass_score = _safe_get_text(row, PASS_SCORE_SELECTOR)
            current_score = _safe_get_text(row, CURRENT_SCORE_SELECTOR)
            total_score = _safe_get_text(row, TOTAL_SCORE_SELECTOR)
            is_pass = _safe_get_text(row, IS_PASS_SELECTOR)
            teacher_words = _safe_get_text(row, TEACHER_WORDS_SELECTOR)
            status_text = _safe_get_text(row, STATUS_SELECTOR)
            status_enum = _get_status_enum(status_text)

            record = HomeworkRecord(
                title=title,
                start_time=start_time,
                end_time=end_time,
                teacher=teacher_name,
                pass_score=pass_score,
                current_score=current_score,
                total_score=total_score,
                is_pass=is_pass,
                teacher_comment=teacher_words,
                status=status_enum,
            )

            homework_records.append(record)
            print(
                f"<info> extracted {i + 1}: Title='{title}', Status='{status_enum} ({status_text})', Score='{current_score}/{total_score}'"
            )

        return homework_records

    except Exception as e:
        print(
            f"<error> critical error during homework table parsing: {e}; returning empty list"
        )
        return []


def download_audio(driver, index: int, record: HomeworkRecord):
    print(f"--- step: download audio of index {index} ---")

    try:
        row_selector_nth = f"{HOMEWORK_TABLE_SELECTOR}:nth-child({index + 1})"

        if (
            record.status == HomeworkStatus.NOT_COMPLETED
            or record.status == HomeworkStatus.IN_PROGRESS
            or record.status == HomeworkStatus.MAKE_UP
        ):
            button_selector = f"{row_selector_nth} > {STATUS_SELECTOR}"
        elif record.status == HomeworkStatus.COMPLETED:
            button_selector = f"{row_selector_nth} > {VIEW_ORIGINAL_BUTTON_SELECTOR}"
        else:
            print(f"<error> unsupported homework status: {record.status}")
            return None

        button_element = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, button_selector))
        )

        button_element.click()
        print("<info> clicked 'go complete hw' button")

        if (
            record.status == HomeworkStatus.NOT_COMPLETED
            or record.status == HomeworkStatus.IN_PROGRESS
            or record.status == HomeworkStatus.MAKE_UP
        ):
            audio_selector = "#taskContent > p:nth-child(1) > audio:nth-child(1)"
        elif record.status == HomeworkStatus.COMPLETED:
            audio_selector = "#content1 > p:nth-child(1) > audio:nth-child(1)"
        else:
            print(f"<error> unsupported homework status: {record.status}")
            return

        audio_element = driver.find_element(By.CSS_SELECTOR, audio_selector)
        if not audio_element:
            print(f"<error> audio element not found using selector: {audio_selector}")
            driver.get(URL_HOMEWORK_LIST)
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, HOMEWORK_TABLE_SELECTOR)
                )
            )
            return
        audio_url = audio_element.get_attribute("src")

        if not audio_url:
            print("<error> audio source url not found on the task page")
            driver.back()
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, HOMEWORK_TABLE_SELECTOR)
                )
            )
            return

        filename = f"cache/homework_{index}_audio.mp3"
        try:
            print(f"<info> downloading audio from: {audio_url}")
            urllib.request.urlretrieve(audio_url, filename)
            print(f"<info> download successful! file saved as '{filename}'")
        except Exception as download_e:
            print(
                f"<error> failed to download audio using urllib.request: {download_e}"
            )

        driver.get(URL_HOMEWORK_LIST)
        wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, HOMEWORK_TABLE_SELECTOR))
        )
        print("<info> navigated back to homework list page")

    except Exception as e:
        print(f"<error> critical error during audio download: {e}")


def transcribe_audio(index: int):
    print(f"--- step: transcribe audio of index {index} ---")

    audio_file = f"cache/homework_{index}_audio.mp3"

    # global whisper_model
    # if whisper_model is None:
    #     print("<info> loading Whisper model (this may take a while)...")
    #     whisper_model = faster_whisper.WhisperModel(
    #         "large", device="cuda", compute_type="float16"
    #     )
    # else:
    #     print("<info> Whisper model already loaded")

    # print(f"<info> transcribing audio file: {audio_file} (this may take a while)...")
    # segments, info = whisper_model.transcribe(audio_file, language="en", beam_size=5)
    # total_duration = round(info.duration, 2)
    # transcription_file = f"{audio_file}.txt"

    # with open(transcription_file, "w", encoding="utf-8") as f:
    #     with Progress() as progress:
    #         task_id = progress.add_task(
    #             "[bold_cyan]Transcribing...", total=total_duration
    #         )
    #         for segment in segments:
    #             progress.update(task_id, completed=round(segment.end, 2))
    #             f.write(segment.text)

    # print(f"<info> transcription successful! saved to '{transcription_file}'")

    global whisper_model
    if whisper_model is None:
        print("<info> loading Whisper model (this may take a while)...")
        whisper_model = whisper.load_model("large")
    else:
        print("<info> Whisper model already loaded")

    print(f"<info> transcribing audio file: {audio_file} (this may take a while)...")
    result = whisper_model.transcribe(audio_file, language="en", verbose=False)
    transcription = result.get("text", None)
    if transcription is None or (transcription is str and transcription.strip() == ""):
        print(f"<error> transcription failed or returned empty result")
        return

    transcription_file = f"{audio_file}.txt"
    with open(transcription_file, "w", encoding="utf-8") as f:
        if isinstance(transcription, str):
            f.write(transcription)
            print(f"<info> transcription successful! saving to '{transcription_file}'")
        if isinstance(transcription, list):
            f.write("\n".join(transcription))
            print(f"<info> transcription successful! saved to '{transcription_file}'")


def get_text(driver, index: int, record: HomeworkRecord) -> str | None:
    print(f"--- step: retreive text content of index {index}")

    PAPER_SELECTOR = ".el-dialog__body"

    row_selector_nth = f"{HOMEWORK_TABLE_SELECTOR}:nth-child({index + 1})"

    if (
        record.status == HomeworkStatus.NOT_COMPLETED
        or record.status == HomeworkStatus.IN_PROGRESS
        or record.status == HomeworkStatus.MAKE_UP
    ):
        button_selector = f"{row_selector_nth} > {STATUS_SELECTOR}"
    elif record.status == HomeworkStatus.COMPLETED:
        button_selector = f"{row_selector_nth} > {VIEW_ORIGINAL_BUTTON_SELECTOR}"
    else:
        print(f"<error> unsupported homework status: {record.status}")
        return None

    button_element = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, button_selector))
    )

    button_element.click()
    print("<info> clicked 'go complete hw' button")

    print(f"<info> scraping text content using selector: {PAPER_SELECTOR}")
    paper_element = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, PAPER_SELECTOR))
    )
    homework_text = paper_element.text

    driver.get(URL_HOMEWORK_LIST)
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, HOMEWORK_TABLE_SELECTOR))
    )
    print("<info> navigated back to homework list")

    return homework_text


def download_text(driver, index: int, record: HomeworkRecord):
    print(f"--- step: download text content of index {index} ---")

    homework_text = get_text(driver, index, record)
    if homework_text is None:
        print(f"<error> failed to retrieve text content for index {index}")
        return

    text_file = f"cache/homework_{index}_text.txt"
    with open(text_file, "w", encoding="utf-8") as f:
        f.write(homework_text)
    print(f"<info> text content saved to '{text_file}'")


def fill_answers(driver, index: int, record: HomeworkRecord, answers: list[str]):
    print(f"--- step: fill in answers for index {index} ---")

    row_selector_nth = f"{HOMEWORK_TABLE_SELECTOR}:nth-child({index + 1})"
    if (
        record.status == HomeworkStatus.NOT_COMPLETED
        or record.status == HomeworkStatus.IN_PROGRESS
        or record.status == HomeworkStatus.MAKE_UP
    ):
        button_selector = f"{row_selector_nth} > {STATUS_SELECTOR}"
    elif record.status == HomeworkStatus.COMPLETED:
        button_selector = f"{row_selector_nth} > {VIEW_ORIGINAL_BUTTON_SELECTOR}"
    else:
        print(f"<error> unsupported homework status: {record.status}")
        return None

    button_element = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, button_selector))
    )
    button_element.click()
    print("<info> clicked 'go complete hw' button")

    quiz_container_id = "content1"

    question_inputs = driver.find_elements(
        By.XPATH,
        f"//div[@id='{quiz_container_id}']//input[@type='radio' and contains(@class, 'pjAnswer')]",
    )

    question_names = [
        input_element.get_attribute("name") for input_element in question_inputs
    ]

    print(f"<info> found {len(question_names)} questions")

    if len(answers) < len(question_names):
        print(
            f"<warning> only {len(answers)} answers provided for {len(question_names)} questions"
        )
        question_names = question_names[: len(answers)]

    for q_num, (name, answer_letter) in enumerate(zip(question_names, answers), 1):
        print(q_num, name, answer_letter)

        xpath = (
            f"//div[@id='{quiz_container_id}']"
            f"//input[@type='radio' and @name='{name}' and @value='{answer_letter}']"
        )

        try:
            time.sleep(0.5)
            radio_button = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            radio_button.click()
            print(f"<info> ✅ question {q_num}: selected option {answer_letter}")

        except Exception as e:
            print(
                f"<error> ❌ could not select answer {answer_letter} for question {q_num}: {e}"
            )

    print("<info> all answers filled in; please review and submit manually")


# hw_list: list[HomeworkRecord] = []


# async def command_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     global hw_list

#     hw_list = parse_homework_list(driver)
#     if not hw_list:
#         # Simple message for no homework, no special formatting needed
#         await context.bot.send_message(
#             chat_id=update.effective_chat.id,
#             text="No homework items found \\(Phew\\!\\)",  # Escaping the parentheses in MarkdownV2
#         )
#         return

#     # --- Formatting the Homework List with MarkdownV2 ---

#     # Header: Bold and use an emoji
#     message_lines = ["*📚 Homework List 📋*"]

#     for i, hw in enumerate(hw_list):
#         # Determine status color/emoji
#         status_text = hw.status.value if hw.status else "Unknown"
#         if hw.status == HomeworkStatus.COMPLETED:
#             status_emoji = "✅"
#         elif (
#             hw.status == HomeworkStatus.NOT_COMPLETED
#             or hw.status == HomeworkStatus.MAKE_UP
#             or hw.status == HomeworkStatus.IN_PROGRESS
#         ):
#             status_emoji = "⏳"
#         else:
#             status_emoji = "❓"

#         # Use 'monospace' for scores/status to align them and make them stand out
#         status_score_info = (
#             f"Status: `{status_text}` \\| Score: `{hw.current_score}/{hw.total_score}`"
#         )

#         # Combine: 1. Title - Status: ... | Score: ...
#         message_lines.append(
#             f"{i+1}\\. {status_emoji} `{hw.title.replace("-", "\\-")}`\n    {status_score_info}"
#         )

#     # Join lines, ensuring newlines are correctly handled in MarkdownV2
#     message = "\n\n".join(message_lines)

#     await context.bot.send_message(
#         chat_id=update.effective_chat.id,
#         text=message,
#         parse_mode="MarkdownV2",  # IMPORTANT: Specify the parsing mode
#     )


# async def command_download_audio(
#     update: Update, context: ContextTypes.DEFAULT_TYPE
# ) -> None:
#     global hw_list

#     chat_id = update.effective_chat.id

#     if not context.args:
#         await context.bot.send_message(
#             chat_id=chat_id,
#             text="Please provide a URL after the command, e.g., `/download_audio <url>`.",
#         )
#         return

#     index = context.args[0]
#     try:
#         index = int(index)
#     except ValueError:
#         await context.bot.send_message(
#             chat_id=update.effective_chat.id,
#             text="Invalid index. Please provide a valid homework index.",
#         )
#         return

#     print(index)

#     if index < 0 or index >= len(hw_list):
#         await context.bot.send_message(
#             chat_id=update.effective_chat.id,
#             text=f"Index out of range: {index}",
#         )
#         return

#     download_audio(driver, index, hw_list[index])

#     await context.bot.send_message(
#         chat_id=update.effective_chat.id,
#         text=f"Audio for homework index {index} downloaded successfully.",
#     )
#     await context.bot.send_audio(
#         chat_id=update.effective_chat.id,
#         audio=open(f"cache/homework_{index}_audio.mp3", "rb"),
#         caption=f"Here is the audio for homework index {index}.",
#     )


def main():
    print("--- english homework helper ---")
    print("--- by: ujhhgtg ---")
    print("--- github: https://github.com/Ujhhgtg/english-homework-helper ---")

    # print("--- step: start telegram bot ---")
    # application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # application.add_handler(CommandHandler("list", command_list))
    # application.add_handler(CommandHandler("download_audio", command_download_audio))

    print("--- step: initialize ---")
    atexit.register(_close_browser_on_exit)
    print("<info> registered atexit handler to close browser on exit")
    Path("./cache/").mkdir(parents=True, exist_ok=True)
    print("<info> created cache directory")

    driver.get(URL_LOGIN)
    print(f"<info> navigated to: {URL_LOGIN}")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, LOGIN_BUTTON_SELECTOR)))

    login(driver)
    time.sleep(2)

    driver.get(URL_HOMEWORK_LIST)
    print(f"<info> navigated to: {URL_HOMEWORK_LIST}")
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, HOMEWORK_TABLE_SELECTOR))
    )

    hw_list: list[HomeworkRecord] = get_homework_list(driver)
    ai_client: AIClient | None = None

    # application.run_polling(allowed_updates=Update.ALL_TYPES)

    print("--- entering interactive mode ---")

    # with patch_stdout():
    while True:
        user_input = (
            session.prompt(
                "ehh> ",
                completer=WordCompleter(
                    [
                        "download_audio",
                        "transcribe_audio",
                        "get_text",
                        "download_text",
                        "fill_answers",
                        "help",
                        "list",
                        "select_ai_client",
                        "exit",
                    ],
                    ignore_case=True,
                ),
            )
            .strip()
            .lower()
        )
        try:
            match user_input:
                case "help":
                    print("available commands:")
                    print("  download_audio - download audio of a homework item")
                    print(
                        "  transcribe_audio - transcribe downloaded audio using Whisper"
                    )
                    print("  get_text - get text content of a homework item")
                    print("  download_text - download text content of a homework item")
                    print("  fill_answers - fill in answers for a homework item")
                    print("  help - show this help message")
                    print("  list - list all homework items")
                    print("  select_ai_client - select AI client for AI-based features")
                    print("  exit - exit the program")

                case "list":
                    hw_list = get_homework_list(driver)

                case "download_audio":
                    index = int(
                        session.prompt("homework index to download audio: ").strip()
                    )
                    if index < 0 or index >= len(hw_list):
                        print(f"<error> index out of range: {index}")
                        raise KeyboardInterrupt()

                    download_audio(driver, index, hw_list[index])

                case "transcribe_audio":
                    index = int(
                        session.prompt("homework index to transcribe audio: ").strip()
                    )
                    # if index < 0 or index >= len(hw_list):
                    #     print(f"<error> index out of range: {index}")
                    #     raise KeyboardInterrupt()

                    audio_file = f"cache/homework_{index}_audio.mp3"

                    if not Path(audio_file).is_file():
                        print(
                            f"<error> audio file for index {index} not found; please download it first"
                        )
                        raise KeyboardInterrupt()

                    transcribe_audio(index)

                case "get_text":
                    index = int(session.prompt("homework index to get text: ").strip())
                    if index < 0 or index >= len(hw_list):
                        print(f"<error> index out of range: {index}")
                        raise KeyboardInterrupt()

                    get_text(driver, index, hw_list[index])

                case "download_text":
                    index = int(
                        session.prompt("homework index to download text: ").strip()
                    )
                    if index < 0 or index >= len(hw_list):
                        print(f"<error> index out of range: {index}")
                        raise KeyboardInterrupt()

                    download_text(driver, index, hw_list[index])

                case "fill_answers":
                    index = int(
                        session.prompt("homework index to fill in answers: ").strip()
                    )
                    if index < 0 or index >= len(hw_list):
                        print(f"<error> index out of range: {index}")
                        raise KeyboardInterrupt()

                    answers_input = (
                        session.prompt("answers (e.g. A B C D A): ").strip().upper()
                    )
                    answers = answers_input.split()
                    if not answers or any(
                        a not in ["A", "B", "C", "D"] for a in answers
                    ):
                        print(f"<error> invalid answers format: '{answers_input}'")
                        raise KeyboardInterrupt()

                    fill_answers(driver, index, hw_list[index], answers)

                case "select_ai_client":
                    options = [("none", "disable AI features")]
                    options.extend(
                        map(
                            lambda c: (
                                f"{c.api_url}|{c.api_key}",
                                f"{c.api_url} / {c.api_key}",
                            ),
                            AI_CLIENT_LIST,
                        )
                    )
                    ai_choice = choice(
                        "select AI client to use:",
                        options=options,
                    )
                    if ai_choice == "none":
                        ai_client = None
                        print("<info> AI features disabled")
                    else:
                        ai_choice_keys = ai_choice.split("|")
                        ai_client = next(
                            (
                                c
                                for c in AI_CLIENT_LIST
                                if c.api_url == ai_choice_keys[0]
                                and c.api_key == ai_choice_keys[1]
                            ),
                            None,
                        )
                        print(f"<info> selected AI client: {ai_client.api_url} / {ai_client.api_key}")  # type: ignore

                case "exit":
                    print("<info> exiting...")
                    break

                case "":
                    ...

                case _:
                    print(f"<error> unrecognized command: '{user_input}'")
        except KeyboardInterrupt:
            continue


if __name__ == "__main__":
    main()
