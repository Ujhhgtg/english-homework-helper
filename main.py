#!/usr/bin/env python
# -*- coding: utf-8 -*-

from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import (
    Options as FirefoxOptions,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
import openai
import time
import atexit
from prompt_toolkit import PromptSession

# from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import choice
import urllib.request
import threading
import whisper
from pathlib import Path

# import telegram
# from telegram import Update, ForceReply
# from telegram.ext import (
#     Application,
#     CommandHandler,
#     MessageHandler,
#     filters,
#     ContextTypes,
#     ConversationHandler,
# )
import json
import shlex
from munch import Munch, munchify

from utils.constants import *
from models.homework_record import HomeworkRecord
from models.homework_status import HomeworkStatus
from models.ai_client import AIClient
from utils.webdriver import FirefoxDriver
from utils.logging import print
from utils.convert import parse_int, mask_string_middle
from utils.crypto import encodeb64_safe
from utils.prompt import LastWordCompleter


driver: FirefoxDriver = None  # type: ignore
wait: WebDriverWait = None  # type: ignore
whisper_model: whisper.model.Whisper | None = None
config: Munch = None  # type: ignore
session: PromptSession = PromptSession()


def _at_exit():
    global driver
    if driver is not None:
        try:
            driver.current_url
            driver.quit()
            print("<info> atexit: browser closed automatically")
        except Exception as e:
            print(f"<error> error occured at exit: {e}")


def _safe_get_text(element, selector: str):
    """Safely finds and returns the text of a child element, returns None on failure."""
    try:
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


def _read_file_string(path: str) -> str:
    with open(path, "rt", encoding="utf-8") as f:
        return f.read()


def goto_hw_list_page(driver: FirefoxDriver):
    driver.get(URL_HOMEWORK_LIST)
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, HOMEWORK_TABLE_SELECTOR))
    )
    print(f"<info> navigated to: {URL_HOMEWORK_LIST}")


def goto_hw_details_page(index: int, record: HomeworkRecord):
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
        return

    button_element = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, button_selector))
    )
    button_element.click()
    print("<info> opened hw details page")


def login(driver: FirefoxDriver, credentials: Munch):
    global config

    print("--- step: login ---")
    driver.get(URL_LOGIN)
    print(f"<info> navigated to: {URL_LOGIN}")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, LOGIN_BUTTON_SELECTOR)))

    school_string = credentials.school
    school_field = driver.find_element(By.CSS_SELECTOR, SCHOOL_SELECTOR)
    # school_field.click()
    school_field.send_keys(school_string)
    print(f"<info> entered '{school_string}' into school field")
    # input()
    wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, SCHOOL_ITEM_SELECTOR))
    ).click()
    print(f"<info> selected school item")

    account_string = credentials.username
    driver.find_element(By.CSS_SELECTOR, ACCOUNT_SELECTOR).send_keys(account_string)
    print(f"<info> entered '{account_string}' into account field")

    password_string = credentials.password
    driver.find_element(By.CSS_SELECTOR, PASSWORD_SELECTOR).send_keys(password_string)
    print(f"<info> entered '{mask_string_middle(password_string)}' into password field")

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

    driver.find_element(By.CSS_SELECTOR, LOGIN_BUTTON_SELECTOR).click()
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ACCOUNT_DROPDOWN_SELECTOR))
    )
    driver.find_element(By.TAG_NAME, "body").send_keys(
        Keys.ESCAPE
    )  # close "set security questions" dialog
    print("<success> logged in")


def logout(driver: FirefoxDriver) -> None:
    print("--- step: logout ---")

    account_dropdown = driver.safe_find_element(
        By.CSS_SELECTOR, ACCOUNT_DROPDOWN_SELECTOR
    )
    if account_dropdown is None:
        print("<warning> cannot find account dropdown; seems to be already logged out")
        return

    account_dropdown.click()
    driver.find_element(By.CSS_SELECTOR, LOGOUT_BUTTON_SELECTOR).click()
    driver.find_element(By.CSS_SELECTOR, LOGOUT_DIALOG_PRIMARY_BUTTON_SELECTOR).click()
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, LOGIN_BUTTON_SELECTOR)))
    print("<success> logged out")


def get_list(driver: FirefoxDriver) -> list[HomeworkRecord]:
    """Finds and extracts data from all homework rows on the current page (table structure)."""

    print("--- step: retrieve homework list ---")
    homework_records: list[HomeworkRecord] = []

    try:
        while True:
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, HOMEWORK_TABLE_SELECTOR)
                )
            )
            homework_rows = driver.find_elements(
                By.CSS_SELECTOR, HOMEWORK_TABLE_SELECTOR
            )

            if not homework_rows:
                print(
                    f"<warning> no homework items found using selector: {HOMEWORK_TABLE_SELECTOR}"
                )
                break

            print(f"<info> found {len(homework_rows)} homework items to parse")

            for i, row in enumerate(homework_rows):
                title = row.find_element(By.CSS_SELECTOR, TITLE_SELECTOR).text
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
                    f"<success> extracted {i}: Title='{title}', Status='{status_enum} ({status_text})', Score='{current_score}/{total_score}'"
                )

            next_page_button = driver.find_element(
                By.CSS_SELECTOR, NEXT_PAGE_BUTTON_SELECTOR
            )
            if not next_page_button.get_attribute("disabled"):
                next_page_button.click()
            else:
                break

        return homework_records

    except Exception as e:
        print(
            f"<error> critical error during homework table parsing: {e}; returning empty list"
        )
        return []


def download_audio(driver: FirefoxDriver, index: int, record: HomeworkRecord):
    print(f"--- step: download audio of index {index} ---")

    try:
        goto_hw_details_page(index, record)

        audio_element = driver.safe_find_element(By.TAG_NAME, "audio")
        if audio_element is None:
            print(f"<error> audio element not found")
            goto_hw_list_page(driver)
            return
        audio_url = audio_element.get_attribute("src")

        if not audio_url:
            print("<error> audio source url not found on the task page")
            goto_hw_list_page(driver)
            return

        filename = f"cache/homework_{encodeb64_safe(record.title)}_audio.mp3"
        try:
            print(f"<info> downloading audio from: {audio_url}")
            urllib.request.urlretrieve(audio_url, filename)
            print(f"<success> file saved as '{filename}'")
        except Exception as download_e:
            print(
                f"<error> failed to download audio using urllib.request: {download_e}"
            )

        goto_hw_list_page(driver)

    except Exception as e:
        print(f"<error> critical error during audio download: {e}")


def transcribe_audio(index: int, record: HomeworkRecord):
    global whisper_model, config

    print(f"--- step: transcribe audio of index {index} ---")

    audio_file = f"cache/homework_{encodeb64_safe(record.title)}_audio.mp3"

    # global whisper_model
    # if whisper_model is None:
    #     print("<info> loading Whisper model (this may take a while)...")
    #     whisper_model = faster_whisper.WhisperModel(
    #         config.whisper.model, device="cuda", compute_type="float16"
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

    # print(f"<success> transcription saved to '{transcription_file}'")

    if whisper_model is None:
        print(
            f"<info> loading Whisper model{" into memory" if config.whisper.in_memory else ""} (this may take a while)..."
        )
        whisper_device = None
        if config.whisper.device == "cuda":
            whisper_device = "cuda"
        elif config.whisper.device == "cpu":
            whisper_device = "cpu"
        elif config.whisper.device != "auto":
            print(
                f"<warning> unrecognized whisper device '{config.whisper.device}'; falling back to 'auto'"
            )
        whisper_model = whisper.load_model(
            config.whisper.model,
            device=whisper_device,
            in_memory=config.whisper.in_memory,
        )
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
            print(
                f"<success> transcription saved to '{transcription_file}'; totalling {len(transcription)} chars in length"
            )
        if isinstance(transcription, list):
            trans_str = "\n".join(transcription)
            f.write(trans_str)
            print(
                f"<success> transcription saved to '{transcription_file}'; totallin {len(trans_str)} chars in length"
            )


def get_text(driver: FirefoxDriver, index: int, record: HomeworkRecord) -> str | None:
    print(f"--- step: retreive text content of index {index} ---")

    goto_hw_details_page(index, record)

    print(f"<info> scraping text content using selector: {PAPER_SELECTOR}")
    paper_element = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, PAPER_SELECTOR))
    )
    homework_text = paper_element.text

    goto_hw_list_page(driver)

    return homework_text


def download_text(driver: FirefoxDriver, index: int, record: HomeworkRecord):
    print(f"--- step: download text content of index {index} ---")

    homework_text = get_text(driver, index, record)
    if homework_text is None:
        print(f"<error> failed to retrieve text content for index {index}")
        return

    text_file = f"cache/homework_{encodeb64_safe(record.title)}_text.txt"
    with open(text_file, "w", encoding="utf-8") as f:
        f.write(homework_text)
    print(
        f"<info> text content saved to '{text_file}'; totalling {len(homework_text)} chars in length"
    )


# TODO: fill-in-the-blanks questions
def fill_answers(
    driver: FirefoxDriver, index: int, record: HomeworkRecord, answers: list[str]
) -> None:
    print(f"--- step: fill in answers for index {index} ---")

    goto_hw_details_page(index, record)

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
            wait.until(EC.element_to_be_clickable((By.XPATH, xpath))).click()
            print(f"<success> ✅ question {q_num}: selected option {answer_letter}")

        except Exception as e:
            print(
                f"<error> ❌ could not select answer {answer_letter} for question {q_num}: {e}"
            )

    print("<info> all answers filled in; please review and submit manually")


def generate_answers(
    driver: FirefoxDriver, index: int, record: HomeworkRecord, client: AIClient
) -> dict | None:
    print(f"--- step: generate answers for index {index} ---")

    goto_hw_details_page(index, record)

    has_audio = driver.safe_find_element(By.TAG_NAME, "audio") is not None
    transcription_file = f"cache/homework_{encodeb64_safe(record.title)}_audio.mp3.txt"
    if has_audio:
        if not Path(transcription_file).is_file():
            print(
                "<error> transcription does not exist; please transcribe the audio first"
            )
            return None
    else:
        print("<info> homework item seems not to have listening part; skipping that")

    text_file = f"cache/homework_{encodeb64_safe(record.title)}_text.txt"
    if not Path(text_file).is_file():
        print("<error> text content does not exist; please download it first")
        return None

    if has_audio:
        prompt = GENERATE_ANSWERS_WITH_LISTENING_PROMPT.replace(
            "{transcription}", _read_file_string(transcription_file)
        ).replace("{questions}", _read_file_string(text_file))
    else:
        prompt = GENERATE_ANSWERS_PROMPT.replace(
            "{questions}", _read_file_string(text_file)
        )

    print("<info> requesting model for a response (this may take a while)...")
    try:
        response = client.client.chat.completions.create(
            model=client.model,
            messages=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": "You are a professional English teacher.",
                        }
                    ],
                },
                {"role": "user", "content": [{"type": "text", "text": prompt}]},
            ],
        )
    except openai.APIError as e:
        print(f"<error> api returned error: {e}")
        goto_hw_list_page(driver)
        return None

    raw_data = response.choices[0].message.content
    if raw_data is None:
        print("<error> model returned null")
        goto_hw_list_page(driver)
        return None
    print(f"<success> model result is valid")
    goto_hw_list_page(driver)

    try:
        return json.loads(raw_data)
    except json.JSONDecodeError as e:
        print(f"<error> critical error during json decode of model result: {e}")
        return None


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


def _load_config(path: str = "local/config.json") -> Munch:
    with open(path, "rt", encoding="utf-8") as f:
        return munchify(json.load(f))  # type: ignore


def _save_config(config: Munch, path: str = "local/config.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(config, indent=4, ensure_ascii=False))


def main():
    global config, driver, wait

    print("--- english homework helper ---")
    print("--- by: ujhhgtg ---")
    print("--- github: https://github.com/Ujhhgtg/english-homework-helper ---")

    # print("--- step: start telegram bot ---")
    # application = Application.builder().token(config.telegram_bot_token).build()

    # application.add_handler(CommandHandler("list", command_list))
    # application.add_handler(CommandHandler("download_audio", command_download_audio))

    print("--- step: initialize ---")
    atexit.register(_at_exit)
    print("<info> registered atexit handler")
    Path("./cache/").mkdir(parents=True, exist_ok=True)
    print("<info> created cache directory")
    config = _load_config()
    print("<info> loaded config file")

    driver_options = FirefoxOptions()
    if config.browser.headless:
        driver_options.add_argument("--headless")
    driver = FirefoxDriver(options=driver_options)
    wait = WebDriverWait(driver, 15)
    print(
        f"<info> started browser{" in headless mode" if config.browser.headless else ""}"
    )

    ai_client: AIClient | None = None
    if config.ai_client.default is not None:
        default_index = config.ai_client.default
        if 0 <= default_index < len(config.ai_client.all):
            ai_client_conf = config.ai_client.all[default_index]
            ai_client = AIClient(
                ai_client_conf.api_url, ai_client_conf.api_key, ai_client_conf.model
            )
            print(f"<info> using default AI client at index {default_index}")
        else:
            print(
                f"<warning> default AI client index {default_index} out of range; falling back to no AI client"
            )

    hw_list: list[HomeworkRecord] = []

    credentials = None
    if config.credentials.default is not None:
        default_index = config.credentials.default
        if 0 <= default_index < len(config.credentials.all):
            credentials = config.credentials.all[default_index]
            login(driver, credentials)
            goto_hw_list_page(driver)
            hw_list = get_list(driver)
            print(f"<info> using default credentials at index {default_index}")
        else:
            print(
                f"<warning> default credentials index {default_index} out of range; not logging in"
            )
    else:
        print(f"<info> no default credentials provided; not logging in")
    # if credentials is None:
    #     credentials_choice = choice(
    #         "select credentials to use:",
    #         options=list(
    #             map(
    #                 lambda c: (
    #                     c.username,
    #                     f"{c.school} / {c.username} / {mask_string_middle(c.password)}",
    #                 ),
    #                 config.credentials.all,
    #             )
    #         ),
    #     )
    #     credentials = next(
    #         c for c in config.credentials.all if c.username == credentials_choice
    #     )

    # application.run_polling(allowed_updates=Update.ALL_TYPES)

    print("--- entering interactive mode ---")

    # with patch_stdout():
    while True:
        user_input = (
            session.prompt(
                "ehh> ",
                completer=LastWordCompleter(COMPLETION_WORD_MAP),
            )
            .strip()
            .lower()
        )
        input_parts = shlex.split(user_input)
        if len(input_parts) <= 0:
            continue

        try:
            match input_parts[0]:
                case "help":
                    print("available commands:")
                    print("  audio - download/transcribe audio of a homework item")
                    print("  text - display/download text content of a homework item")
                    print(
                        "  answers - fill in/download/generate answers for a homework item"
                    )
                    print("  help - show this help message")
                    print("  list - list all homework items")
                    print("  account - login/logout/select default account")
                    print("  ai - select AI client")
                    print("  config - reload/save configuration")
                    print("  exit - exit the program")

                case "list":
                    hw_list = get_list(driver)

                case "audio":
                    if len(input_parts) < 3:
                        print("<error> argument not enough")
                        continue
                    index = parse_int(input_parts[2])
                    if index is None:
                        print("<error> argument invalid")
                        continue

                    if index < 0 or index >= len(hw_list):
                        print(f"<error> index out of range: {index}")
                        continue

                    match input_parts[1]:
                        case "download":
                            download_audio(driver, index, hw_list[index])
                        case "transcribe":
                            audio_file = f"cache/homework_{encodeb64_safe(hw_list[index].title)}_audio.mp3"
                            if not Path(audio_file).is_file():
                                print(
                                    f"<error> audio file for index {index} not found; please download it first"
                                )
                                continue
                            transcribe_audio(index, hw_list[index])
                        case _:
                            print("<error> argument invalid")

                case "text":
                    if len(input_parts) < 3:
                        print("<error> argument not enough")
                        continue
                    index = parse_int(input_parts[2])
                    if index is None:
                        print("<error> argument invalid")
                        continue
                    if index < 0 or index >= len(hw_list):
                        print(f"<error> index out of range: {index}")
                        continue

                    match input_parts[1]:
                        case "display":
                            print(get_text(driver, index, hw_list[index]))
                        case "download":
                            download_text(driver, index, hw_list[index])
                        case _:
                            print("<error> argument invalid")

                case "answers":
                    if len(input_parts) < 3:
                        print("<error> argument not enough")
                        continue
                    index = parse_int(input_parts[2])
                    if index is None:
                        print("<error> argument invalid")
                        continue
                    if index < 0 or index >= len(hw_list):
                        print(f"<error> index out of range: {index}")
                        continue

                    match input_parts[1]:
                        case "fill_in":
                            answers_input = (
                                session.prompt("answers (e.g. A B C D A): ")
                                .strip()
                                .upper()
                            )
                            answers = answers_input.split()
                            if not answers or any(
                                a not in ["A", "B", "C", "D"] for a in answers
                            ):
                                print(
                                    f"<error> invalid answers format: '{answers_input}'"
                                )
                                continue
                            fill_answers(driver, index, hw_list[index], answers)
                        case "download":
                            raise NotImplementedError()
                        case "generate":
                            if ai_client is None:
                                print("<error> no ai client selected")
                                continue
                            answers = generate_answers(
                                driver, index, hw_list[index], ai_client
                            )
                            print(answers)

                        case _:
                            print("<error> argument invalid")

                case "account":
                    if len(input_parts) < 2:
                        print("<error> argument not enough")
                        continue

                    match input_parts[1]:
                        case "login":
                            options = list(
                                map(
                                    lambda c: (
                                        c[0],
                                        f"{c[1].school} / {c[1].username} / {mask_string_middle(c[1].password)}",
                                    ),
                                    enumerate(config.credentials.all),
                                )
                            )  # type: ignore
                            default = 0
                            if isinstance(config.credentials.default, int):
                                default = config.credentials.default
                            cred_choice = choice(
                                "select credentials to use:",
                                options=options,
                                default=default,
                            )
                            credentials = config.credentials.all[cred_choice]
                            logout(driver)
                            login(driver, credentials)
                            goto_hw_list_page(driver)
                            hw_list = get_list(driver)
                            print(
                                f"<success> logged in with credentials: {credentials.school} / {credentials.username} / {mask_string_middle(credentials.password)}"
                            )
                        case "logout":
                            logout(driver)
                        case "select_default":
                            options = [("none", "disable auto login")]
                            options.extend(
                                map(
                                    lambda c: (
                                        c[0],
                                        f"{c[1].school} / {c[1].username} / {mask_string_middle(c[1].password)}",
                                    ),
                                    enumerate(config.credentials.all),
                                )  # type: ignore
                            )
                            default = "none"
                            if isinstance(config.credentials.default, int):
                                default = config.credentials.default
                            cred_choice = choice(
                                "select default credentials to use:",
                                options=options,
                                default=default,
                            )
                            if cred_choice == "none":
                                config.credentials.default = None
                                print("<info> cleared default credentials")
                                continue

                            config.credentials.default = cred_choice
                            cred = config.credentials.all[cred_choice]
                            print(
                                f"<info> selected default credentials: {cred.school} / {cred.username} / {mask_string_middle(cred.password)}"
                            )
                        case _:
                            print("<error> argument invalid")

                case "ai":
                    if len(input_parts) < 2:
                        print("<error> argument not enough")
                        continue

                    match input_parts[1]:
                        case "select_api":
                            options = [("none", "disable AI features")]
                            options.extend(
                                map(
                                    lambda c: (
                                        c[0],
                                        f"{c[1].api_url} / {mask_string_middle(c[1].api_key)} / {c[1].model}",
                                    ),
                                    enumerate(config.ai_client.all),
                                )  # type: ignore
                            )
                            default = "none"
                            if isinstance(config.ai_client.default, int):
                                default = config.ai_client.default
                            cred_choice = choice(
                                "select AI client to use:",
                                options=options,
                                default=default,
                            )
                            if cred_choice == "none":
                                ai_client = None
                                config.ai_client.default = None
                                print("<info> AI features disabled")
                                continue

                            ai_client_conf = config.ai_client.all[cred_choice]
                            ai_client = AIClient(
                                ai_client_conf.api_url,
                                ai_client_conf.api_key,
                                ai_client_conf.model,
                            )
                            config.ai_client.default = cred_choice
                            print(
                                f"<info> selected AI client: {ai_client.api_url} / {mask_string_middle(ai_client.api_key)} / {ai_client.model}"
                            )
                        case _:
                            print("<error> argument invalid")

                case "config":
                    if len(input_parts) < 2:
                        print("<error> argument not enough")
                        continue

                    match input_parts[1]:
                        case "reload":
                            config = _load_config()
                            print("<info> reloaded config file")
                            print("<info> note: current states are not changed")
                        case "save":
                            _save_config(config)
                            print("<info> saved config to file")
                        case _:
                            print("<error> argument invalid")

                case "exit":
                    print("<info> exiting...")
                    _save_config(config)
                    print("<info> saved config to file")
                    break

                case _:
                    print(f"<error> unrecognized command: '{user_input}'")
        except NotImplementedError:
            print("<error> feature not yet implemented")

        except KeyboardInterrupt:
            print("<warning> interrupted")
            continue


if __name__ == "__main__":
    main()
