from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
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


def goto_hw_original_page(index: int, record: HomeworkRecord) -> bool:
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
        return False

    globalvars.driver.find_element(By.CSS_SELECTOR, button_selector).click()

    toast_wait = WebDriverWait(globalvars.driver, 1.5)
    try:
        toast_elem = toast_wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, TOAST_SELECTOR))
        )
        toast_text = toast_elem.text
        print(f"<error> website sends toast message: {toast_text}")
        return False

    except TimeoutException:
        ...

    print("<info> opened hw original page")
    return True


def goto_hw_completed_page(index: int, record: HomeworkRecord):
    if record.status != HomeworkStatus.COMPLETED:
        raise ValueError("homework status invalid: homework is not completed")

    row_selector_nth = f"{HOMEWORK_TABLE_SELECTOR}:nth-child({index + 1})"
    globalvars.driver.find_element(
        By.CSS_SELECTOR, f"{row_selector_nth} > {VIEW_COMPLETED_BUTTON_SELECTOR}"
    ).click()
    globalvars.wait.until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, DIALOG_VIEW_COMPLETED_BUTTON_SELECTOR)
        )
    ).click()
    globalvars.wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ANSWER_ROWS_SELECTOR))
    )
    print("<info> opened hw completed page")


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
        if not goto_hw_original_page(index, record):
            print("<error> failed to navigate to hw original page; aborting...")
            return

        globalvars.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "el-dialog__body"))
        )

        # audio_element = globalvars.wait.until(
        #     EC.presence_of_element_located((By.TAG_NAME, "audio"))
        # )
        audio_element = globalvars.driver.safe_find_element(By.TAG_NAME, "audio")
        if not audio_element:
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

    if not goto_hw_original_page(index, record):
        print("<error> failed to navigate to hw original page; aborting...")
        return None

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
def fill_in_answers(index: int, record: HomeworkRecord, answers: dict) -> None:
    print(f"--- step: fill in answers for index {index} ---")

    if not goto_hw_original_page(index, record):
        print("<error> failed to navigate to hw original page; aborting...")
        return

    quiz_container_id = "taskContent"

    interactive_elements_xpath = (
        f"//div[@id='{quiz_container_id}']//input[@type='radio' or @type='text']"
    )

    all_inputs = globalvars.driver.find_elements(By.XPATH, interactive_elements_xpath)

    questions = {}

    for element in all_inputs:
        input_type = element.get_attribute("type")
        q_id = element.get_attribute("name")

        if input_type == "radio":
            if q_id and q_id not in questions:
                questions[q_id] = {"type": "radio", "name": q_id}

        elif input_type == "text":
            if q_id and q_id not in questions:
                questions[q_id] = {"type": "text", "element": element}

    ordered_q_ids = list(questions.keys())

    print(f"<info> found {len(ordered_q_ids)} questions to answer")

    if len(answers) < len(ordered_q_ids):
        print(
            f"<warning> only {len(answers)} answers provided for {len(ordered_q_ids)} questions"
        )
        ordered_q_ids = ordered_q_ids[: len(answers)]

    for q_num, (q_id, answer) in enumerate(zip(ordered_q_ids, answers), 1):

        question_info = questions[q_id]

        try:
            time.sleep(0.5)
            answer_types = answer["type"].split("|")

            if question_info["type"] == "radio":
                if "choice" not in answer_types:
                    print(
                        f"<error> question type and answer type mismatch for question {q_id}; aborting..."
                    )
                    return

                answer_letter = answer["content"]

                xpath = (
                    f"//div[@id='{quiz_container_id}']"
                    f"//input[@type='radio' and @name='{q_id}' and @value='{answer_letter}']"
                )

                globalvars.wait.until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                ).click()
                print(
                    f"<success> ✅ question {q_num} (choice): selected option {answer_letter}"
                )

            elif question_info["type"] == "text":
                if "fill-in-blanks" not in answer_types:
                    print(
                        f"<error> question type and answer type mismatch for question {q_id}; aborting..."
                    )
                    return

                answer_text = answer["content"]

                text_input_element = question_info["element"]

                text_input_element.clear()
                text_input_element.send_keys(answer_text)

                print(
                    f"<success> ✅ question {q_num} (FIB): filled text '{answer_text}'"
                )

        except Exception as e:
            print(
                f"<error> ❌ could not set answer '{answer}' for question {q_num} ({question_info['type']}): {e}"
            )

    print("\n<info> all answers filled in; please review and submit manually")


def get_answers(index: int, record: HomeworkRecord) -> list[dict]:
    print(f"--- step: retrieve answers for index {index}: {record.title}")

    if record.status != HomeworkStatus.COMPLETED:
        goto_hw_list_page()
        print("<error> homework item is not completed; returning empty list")
        return []

    goto_hw_completed_page(index, record)

    elements = globalvars.driver.find_elements(By.CSS_SELECTOR, ANSWER_ROWS_SELECTOR)
    if len(elements) <= 0:
        goto_hw_list_page()
        print("<warning> no answers are found; returning empty list")
        return []

    answers_list = []
    for index, element in enumerate(elements):
        element = element.find_element(By.CSS_SELECTOR, ANSWER_TEXT_SELECTOR)

        answer_type = "unknown"
        answer_text = element.text

        # FIXME: cannot identify fill-in-blanks questions that require entering letters
        # NOTE: the questions' types might change
        if len(answer_text) >= 2:
            answer_type = "fill-in-blanks"
        elif len(answer_text) <= 0:
            print("<warning> answer is blank")
        elif "A" <= answer_text.upper() <= "D":
            answer_type = "choice|fill-in-blanks"
        elif "E" <= answer_text.upper() <= "Z":
            answer_type = "fill-in-blanks"
        else:
            print("<warning> ???")

        answers_list.append(
            {"index": index + 1, "type": answer_type, "content": answer_text}
        )

    goto_hw_list_page()
    return answers_list


def generate_answers(
    index: int, record: HomeworkRecord, client: AIClient
) -> dict | None:
    print(f"--- step: generate answers for index {index}: {record.title} ---")

    if not goto_hw_original_page(index, record):
        print("<error> failed to navigate to hw original page; aborting...")
        return None

    audio_wait = WebDriverWait(globalvars.driver, 1.5)
    try:
        audio_wait.until(EC.presence_of_element_located((By.TAG_NAME, "audio")))
        has_audio = True
    except TimeoutException:
        has_audio = False

    # has_audio = globalvars.driver.safe_find_element(By.TAG_NAME, "audio") is not None
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
            model=client.selected_model(),
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
    goto_hw_list_page()

    try:
        answers = json.loads(raw_data)
        print(
            f"<success> model result is valid; totalling {len(raw_data)} chars in length"
        )

        print("<info> post-processing model result...")
        post_process_count = 0
        for answer in answers:
            if len(answer["content"]) >= 2:
                if answer["type"] != "fill-in-blanks":
                    post_process_count += 1
                    answer["type"] = "fill-in-blanks"
            elif "A" <= answer["content"].upper() <= "D":
                post_process_count += 1
                answer["type"] = "choice|fill-in-blanks"
            elif "E" <= answer["content"].upper() <= "Z":
                post_process_count += 1
                answer["type"] = "fill-in-blanks"

        print(f"<info> post-processed model result for {post_process_count} times")
        return answers

    except json.JSONDecodeError:
        print(f"<error> model result is not valid json")
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
