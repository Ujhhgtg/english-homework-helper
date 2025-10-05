#!/usr/bin/env python
# -*- coding: utf-8 -*-

from selenium.webdriver.firefox.options import (
    Options as FirefoxOptions,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import atexit
from prompt_toolkit.shortcuts import choice
from pathlib import Path
import shlex
from prompt_toolkit import PromptSession

from models.homework_record import HomeworkRecord
from models.ai_client import AIClient
from models.credentials import Credentials
from utils.constants import *
from utils.webdriver import FirefoxDriver
from utils.logging import print
from utils.convert import parse_int
from utils.crypto import encodeb64_safe
from utils.prompt import LastWordCompleter
from utils.config import load_config, save_config
from tasks import *
import globalvars

# driver: FirefoxDriver = None  # type: ignore
# wait: WebDriverWait = None  # type: ignore
# whisper_model: whisper.model.Whisper | None = None
# config: Munch = None  # type: ignore
# session: PromptSession = PromptSession()


def _at_exit():
    global driver
    if globalvars.driver is not None:
        try:
            globalvars.driver.current_url
            globalvars.driver.quit()
            print("<info> atexit: browser closed automatically")
        except Exception as e:
            print(f"<error> error occured at exit: {e}")


def main():
    print("--- english homework helper ---")
    print("--- by: ujhhgtg ---")
    print("--- github: https://github.com/Ujhhgtg/english-homework-helper ---")

    print("--- step: initialize ---")
    atexit.register(_at_exit)
    print("<info> registered atexit handler")
    Path("./cache/").mkdir(parents=True, exist_ok=True)
    print("<info> created cache directory")
    globalvars.config = load_config()
    print("<info> loaded config file")

    driver_options = FirefoxOptions()
    if globalvars.config.browser.headless:
        driver_options.add_argument("--headless")
    globalvars.driver = FirefoxDriver(options=driver_options)
    globalvars.wait = WebDriverWait(globalvars.driver, 15)
    print(
        f"<info> started browser{" in headless mode" if globalvars.config.browser.headless else ""}"
    )

    ai_client: AIClient | None = None
    if globalvars.config.ai_client.default is not None:
        default_index = globalvars.config.ai_client.default
        if 0 <= default_index < len(globalvars.config.ai_client.all):
            ai_client_conf = globalvars.config.ai_client.all[default_index]
            ai_client = AIClient.from_dict(ai_client_conf)
            print(f"<info> using default AI client at index {default_index}")
        else:
            print(
                f"<warning> default AI client index {default_index} out of range; falling back to no AI client"
            )

    hw_list: list[HomeworkRecord] = []
    session: PromptSession = PromptSession()

    if globalvars.config.credentials.default is not None:
        default_index = globalvars.config.credentials.default
        if 0 <= default_index < len(globalvars.config.credentials.all):
            cred = Credentials.from_dict(
                globalvars.config.credentials.all[default_index]
            )
            login(cred)
            goto_hw_list_page()
            hw_list = get_list()
            print(
                f"<info> using default credentials at index {default_index}: {cred.describe()}"
            )
        else:
            print(
                f"<warning> default credentials index {default_index} out of range; not logging in"
            )
    else:
        print(f"<warning> no default credentials provided; not logging in")

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
                    hw_list = get_list()

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
                            download_audio(index, hw_list[index])
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
                            print(get_text(index, hw_list[index]))
                        case "download":
                            download_text(index, hw_list[index])
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
                            fill_in_answers(index, hw_list[index], answers)

                        case "download":
                            answers = get_answers(index, hw_list[index])
                            if len(answers) == 0:
                                print(
                                    "<error> no answers retrieved; cannot save to file"
                                )
                                continue

                            answers_file = f"cache/homework_{encodeb64_safe(hw_list[index].title)}_answers.json"
                            with open(answers_file, "wt", encoding="utf-8") as f:
                                f.write(
                                    json.dumps(answers, indent=4, ensure_ascii=False)
                                )
                            print(f"<success> saved to file {answers_file}")

                        case "generate":
                            if ai_client is None:
                                print("<error> no ai client selected")
                                continue
                            answers = generate_answers(index, hw_list[index], ai_client)

                            answers_file = f"cache/homework_{encodeb64_safe(hw_list[index].title)}_answers_gen.json"
                            with open(answers_file, "wt", encoding="utf-8") as f:
                                f.write(
                                    json.dumps(answers, indent=4, ensure_ascii=False)
                                )
                            print(f"<success> saved to file {answers_file}")

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
                                        c[1].describe(),
                                    ),
                                    enumerate(
                                        map(
                                            lambda c: Credentials.from_dict(c),
                                            globalvars.config.credentials.all,
                                        )
                                    ),
                                )
                            )  # type: ignore
                            default = 0
                            if isinstance(globalvars.config.credentials.default, int):
                                default = globalvars.config.credentials.default
                            cred_choice = choice(
                                "select credentials to use:",
                                options=options,
                                default=default,
                            )
                            cred = Credentials.from_dict(
                                globalvars.config.credentials.all[cred_choice]
                            )
                            logout()
                            login(cred)
                            goto_hw_list_page()
                            hw_list = get_list()
                            print(
                                f"<success> logged in with credentials: {cred.describe()}"
                            )
                        case "logout":
                            logout()
                        case "select_default":
                            options = [("none", "disable auto login")]
                            options.extend(
                                map(
                                    lambda c: (
                                        c[0],
                                        c[1].describe(),
                                    ),
                                    enumerate(
                                        map(
                                            lambda c: Credentials.from_dict(c),
                                            globalvars.config.credentials.all,
                                        )
                                    ),
                                )  # type: ignore
                            )
                            default = "none"
                            if isinstance(globalvars.config.credentials.default, int):
                                default = globalvars.config.credentials.default
                            cred_choice = choice(
                                "select default credentials to use:",
                                options=options,
                                default=default,
                            )
                            if cred_choice == "none":
                                globalvars.config.credentials.default = None
                                print("<info> disabled auto login")
                                continue

                            globalvars.config.credentials.default = cred_choice
                            cred = Credentials.from_dict(
                                globalvars.config.credentials.all[cred_choice]
                            )
                            print(
                                f"<info> selected default credentials: {cred.describe()}"
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
                                        c[1].describe(),
                                    ),
                                    enumerate(
                                        map(
                                            lambda c: AIClient.from_dict(c),
                                            globalvars.config.ai_client.all,
                                        )
                                    ),
                                )  # type: ignore
                            )
                            default = "none"
                            if isinstance(globalvars.config.ai_client.default, int):
                                default = globalvars.config.ai_client.default
                            cred_choice = choice(
                                "select AI client to use:",
                                options=options,
                                default=default,
                            )
                            if cred_choice == "none":
                                ai_client = None
                                globalvars.config.ai_client.default = None
                                print("<info> AI features disabled")
                                continue

                            ai_client_conf = globalvars.config.ai_client.all[
                                cred_choice
                            ]
                            ai_client = AIClient.from_dict(ai_client_conf)
                            globalvars.config.ai_client.default = cred_choice
                            print(f"<info> selected AI client: {ai_client.describe()}")
                        case _:
                            print("<error> argument invalid")

                case "config":
                    if len(input_parts) < 2:
                        print("<error> argument not enough")
                        continue

                    match input_parts[1]:
                        case "reload":
                            globalvars.config = load_config()
                            print("<info> reloaded config file")
                            print("<info> note: current states are not changed")
                        case "save":
                            save_config(globalvars.config)
                            print("<info> saved config to file")
                        case _:
                            print("<error> argument invalid")

                case "exit":
                    print("<info> exiting...")
                    save_config(globalvars.config)
                    print("<info> saved config to file")
                    break

                case _:
                    print(f"<error> unrecognized command: '{user_input}'")

        except NotImplementedError:
            print("<error> feature not yet implemented")

        except KeyboardInterrupt:
            print("<warning> interrupted")

        # except Exception as e:
        #     print(
        #         f"<error> unexpected error during task execution: {e}; trying to recover..."
        #     )
        #     goto_hw_list_page()


if __name__ == "__main__":
    main()
