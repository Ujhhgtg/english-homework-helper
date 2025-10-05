from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import json
import urllib.request
import openai
import time
import whisper
from pathlib import Path

from models.homework_status import HomeworkStatus
from models.homework_record import HomeworkRecord
from models.ai_client import AIClient
from models.credentials import Credentials
from utils.constants import *
from utils.crypto import encodeb64_safe
from utils.fs import read_file_text
from utils.convert import mask_string_middle
from utils.logging import print
import globalvars


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


def goto_hw_list_page():
    globalvars.driver.get(URL_HOMEWORK_LIST)
    globalvars.wait.until(
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

    button_element = globalvars.wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, button_selector))
    )
    button_element.click()
    print("<info> opened hw details page")


def logout() -> None:
    print("--- step: logout ---")

    account_dropdown = globalvars.driver.safe_find_element(
        By.CSS_SELECTOR, ACCOUNT_DROPDOWN_SELECTOR
    )
    if account_dropdown is None:
        print("<warning> cannot find account dropdown; seems to be already logged out")
        return

    account_dropdown.click()
    globalvars.driver.find_element(By.CSS_SELECTOR, LOGOUT_BUTTON_SELECTOR).click()
    globalvars.driver.find_element(
        By.CSS_SELECTOR, LOGOUT_DIALOG_PRIMARY_BUTTON_SELECTOR
    ).click()
    globalvars.wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, LOGIN_BUTTON_SELECTOR))
    )
    print("<success> logged out")


def get_list() -> list[HomeworkRecord]:
    """Finds and extracts data from all homework rows on the current page (table structure)."""
    print("--- step: retrieve homework list ---")
    homework_records: list[HomeworkRecord] = []

    try:
        while True:
            globalvars.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, HOMEWORK_TABLE_SELECTOR)
                )
            )
            homework_rows = globalvars.driver.find_elements(
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

            next_page_button = globalvars.driver.find_element(
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


def download_audio(index: int, record: HomeworkRecord):
    print(f"--- step: download audio of index {index} ---")

    try:
        goto_hw_details_page(index, record)

        audio_element = globalvars.driver.safe_find_element(By.TAG_NAME, "audio")
        if audio_element is None:
            print(f"<error> audio element not found")
            goto_hw_list_page()
            return
        audio_url = audio_element.get_attribute("src")

        if not audio_url:
            print("<error> audio source url not found on the task page")
            goto_hw_list_page()
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

        goto_hw_list_page()

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

    if globalvars.whisper_model is None:
        print(
            f"<info> loading Whisper model{" into memory" if globalvars.config.whisper.in_memory else ""} (this may take a while)..."
        )
        whisper_device = None
        if globalvars.config.whisper.device == "cuda":
            whisper_device = "cuda"
        elif globalvars.config.whisper.device == "cpu":
            whisper_device = "cpu"
        elif globalvars.config.whisper.device != "auto":
            print(
                f"<warning> unrecognized whisper device '{globalvars.config.whisper.device}'; falling back to 'auto'"
            )
        whisper_model = whisper.load_model(
            globalvars.config.whisper.model,
            device=whisper_device,
            in_memory=globalvars.config.whisper.in_memory,
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


def get_text(index: int, record: HomeworkRecord) -> str | None:
    print(f"--- step: retreive text content of index {index} ---")

    goto_hw_details_page(index, record)

    print(f"<info> scraping text content using selector: {PAPER_SELECTOR}")
    paper_element = globalvars.wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, PAPER_SELECTOR))
    )
    homework_text = paper_element.text

    goto_hw_list_page()

    return homework_text


def download_text(index: int, record: HomeworkRecord):
    print(f"--- step: download text content of index {index} ---")

    homework_text = get_text(index, record)
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
def fill_answers(index: int, record: HomeworkRecord, answers: list[str]) -> None:
    print(f"--- step: fill in answers for index {index} ---")

    goto_hw_details_page(index, record)

    quiz_container_id = "content1"

    question_inputs = globalvars.driver.find_elements(
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
            globalvars.wait.until(EC.element_to_be_clickable((By.XPATH, xpath))).click()
            print(f"<success> ✅ question {q_num}: selected option {answer_letter}")

        except Exception as e:
            print(
                f"<error> ❌ could not select answer {answer_letter} for question {q_num}: {e}"
            )

    print("<info> all answers filled in; please review and submit manually")


def generate_answers(
    index: int, record: HomeworkRecord, client: AIClient
) -> dict | None:
    print(f"--- step: generate answers for index {index} ---")

    goto_hw_details_page(index, record)

    has_audio = globalvars.driver.safe_find_element(By.TAG_NAME, "audio") is not None
    transcription_file = f"cache/homework_{encodeb64_safe(record.title)}_audio.mp3.txt"
    if has_audio:
        if not Path(transcription_file).is_file():
            print(
                "<error> transcription does not exist; please transcribe the audio first"
            )
            return None
    else:
        print("<warning> homework item seems not to have listening part; skipping that")

    text_file = f"cache/homework_{encodeb64_safe(record.title)}_text.txt"
    if not Path(text_file).is_file():
        print("<error> text content does not exist; please download it first")
        return None

    if has_audio:
        prompt = GENERATE_ANSWERS_WITH_LISTENING_PROMPT.replace(
            "{transcription}", read_file_text(transcription_file)
        ).replace("{questions}", read_file_text(text_file))
    else:
        prompt = GENERATE_ANSWERS_PROMPT.replace(
            "{questions}", read_file_text(text_file)
        )

    print(f"<info> current AI client: {client.describe()}")
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
        goto_hw_list_page()
        return None

    raw_data = response.choices[0].message.content
    if raw_data is None:
        print("<error> model returned null")
        goto_hw_list_page()
        return None
    print(f"<success> model result is valid")
    goto_hw_list_page()

    try:
        return json.loads(raw_data)
    except json.JSONDecodeError as e:
        print(f"<error> critical error during json decode of model result: {e}")
        return None


def login(credentials: Credentials):
    print("--- step: login ---")
    globalvars.driver.get(URL_LOGIN)
    print(f"<info> navigated to: {URL_LOGIN}")
    globalvars.wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, LOGIN_BUTTON_SELECTOR))
    )

    school_string = credentials.school
    school_field = globalvars.driver.find_element(By.CSS_SELECTOR, SCHOOL_SELECTOR)
    # school_field.click()
    school_field.send_keys(school_string)
    print(f"<info> entered '{school_string}' into school field")
    # input()
    globalvars.wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, SCHOOL_ITEM_SELECTOR))
    ).click()
    print(f"<info> selected school item")

    account_string = credentials.username
    globalvars.driver.find_element(By.CSS_SELECTOR, ACCOUNT_SELECTOR).send_keys(
        account_string
    )
    print(f"<info> entered '{account_string}' into account field")

    password_string = credentials.password
    globalvars.driver.find_element(By.CSS_SELECTOR, PASSWORD_SELECTOR).send_keys(
        password_string
    )
    print(f"<info> entered '{mask_string_middle(password_string)}' into password field")

    slider_handle = globalvars.wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, SLIDER_HANDLE_SELECTOR))
    )
    actions = ActionChains(globalvars.driver)
    actions.click_and_hold(slider_handle).move_by_offset(
        DRAG_DISTANCE_PIXELS, 0
    ).release().perform()
    print(
        f"<info> dragged slider {DRAG_DISTANCE_PIXELS} pixels to the right (x-offset)"
    )

    globalvars.driver.find_element(By.CSS_SELECTOR, LOGIN_BUTTON_SELECTOR).click()
    globalvars.wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ACCOUNT_DROPDOWN_SELECTOR))
    )
    globalvars.driver.find_element(By.TAG_NAME, "body").send_keys(
        Keys.ESCAPE
    )  # close "set security questions" dialog
    print("<success> logged in")
