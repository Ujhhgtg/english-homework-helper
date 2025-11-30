#!/usr/bin/env python
# -*- coding: utf-8 -*-


import json
import shlex
import atexit
from pathlib import Path
from typing import Optional

from rich import traceback
from prompt_toolkit.shortcuts import choice
from prompt_toolkit import PromptSession

from .models.homework_record import HomeworkRecord
from .models.ai_client import AIClient
from .models.credentials import Credentials
from .utils.browser.constants import *
from .utils.logging import print, print_and_copy_path, patch_whisper_transcribe_progress
from .utils.convert import try_parse_int
from .utils.crypto import encodeb64_safe
from .utils.prompt import ReplCompleter
from .utils.config import load_config, save_config, migrate_config_if_needed
from .utils.context.impl.browser_context import BrowserContext
from .utils.context.impl.console_messenger import ConsoleMessenger
from .utils.fs import CACHE_DIR
from .tasks_browser import *
from . import globalvars


def _at_exit():
    global driver
    if globalvars.context.driver is not None:
        try:
            globalvars.context.driver.current_url
            globalvars.context.driver.quit()
            print("<info> atexit: browser closed automatically")
        except:
            print(f"<error> critical error during exit:")
            globalvars.context.messenger.send_exception(exc)


def main():
    globalvars.context = BrowserContext(messenger=ConsoleMessenger())

    print("--- english homework helper ---")
    print("--- by: ujhhgtg ---")
    print("--- github: https://github.com/Ujhhgtg/english-homework-helper ---")

    print("--- step: initialize ---")
    traceback.install()
    print("<info> rich traceback installed")
    atexit.register(_at_exit)
    print("<info> registered atexit handler")
    migrate_config_if_needed()
    globalvars.context.config = load_config()
    print("<info> loaded config file")
    patch_whisper_transcribe_progress()
    print("<info> patched whisper.transcribe to use rich console")

    match globalvars.context.config.browser.type:
        case "chrome":
            from selenium.webdriver.chrome.options import (
                Options as WebDriverOptions,
            )
            from selenium.webdriver.chrome.webdriver import (
                WebDriver,
            )

        case "firefox":
            from selenium.webdriver.firefox.options import (
                Options as WebDriverOptions,
            )
            from selenium.webdriver.firefox.webdriver import (
                WebDriver,
            )
        case "edge":
            from selenium.webdriver.edge.options import (
                Options as WebDriverOptions,
            )
            from selenium.webdriver.edge.webdriver import (
                WebDriver,
            )
        case "safari":
            from selenium.webdriver.safari.options import (
                Options as WebDriverOptions,
            )
            from selenium.webdriver.safari.webdriver import (
                WebDriver,
            )
        case _:
            print(
                f"<error> unsupported browser type: {globalvars.context.config.browser.type}; aborting..."
            )
            return
    driver_options = WebDriverOptions()
    if globalvars.context.config.browser.type != "safari":
        driver_options.binary_location = globalvars.context.config.browser.binary_path  # type: ignore
    else:
        if globalvars.context.config.browser.binary_path != "":
            print(
                "<warning> safari browser binary path is ignored; using system default"
            )
    if globalvars.context.config.browser.headless:
        driver_options.add_argument("--headless")
    globalvars.context.init_driver(WebDriver(options=driver_options))  # type: ignore
    print(
        f"<info> started browser {globalvars.context.config.browser.type}{" in headless mode" if globalvars.context.config.browser.headless else ""}"
    )

    ai_client: Optional[AIClient] = None
    if globalvars.context.config.ai_client.selected is not None:
        sel_index = globalvars.context.config.ai_client.selected
        if 0 <= sel_index < len(globalvars.context.config.ai_client.all):
            ai_client = AIClient.from_dict(
                globalvars.context.config.ai_client.all[sel_index]
            )
            print(f"<info> using default AI client at index {sel_index}")
        else:
            print(
                f"<warning> default AI client index {sel_index} out of range; falling back to no AI client"
            )

    hw_list: list[HomeworkRecord] = []
    session: PromptSession = PromptSession()

    if globalvars.context.config.credentials.selected is not None:
        sel_index = globalvars.context.config.credentials.selected
        if 0 <= sel_index < len(globalvars.context.config.credentials.all):
            cred = Credentials.from_dict(
                globalvars.context.config.credentials.all[sel_index]
            )
            login(cred)
            print(
                f"<info> using default credentials at index {sel_index}: {cred.describe()}"
            )
            goto_hw_list_page()
            hw_list = get_hw_list()
            print_hw_list(hw_list)
        else:
            print(
                f"<warning> default credentials index {sel_index} out of range; not logging in"
            )
    else:
        print(f"<warning> no default credentials provided; not logging in")

    print("--- entering interactive mode ---")

    # with patch_stdout():
    while True:
        user_input = (
            session.prompt(
                "ehh> ",
                completer=ReplCompleter(COMPLETION_WORD_MAP),
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
                    print("  ai - select AI client & model")
                    print("  config - reload/save configuration")
                    print(
                        "  rescue - try to recover from an unexpected error by returning to homework list page"
                    )
                    print("  exit - exit the program")

                case "list":
                    hw_list = get_hw_list()
                    print_hw_list(hw_list)

                case "audio":
                    if len(input_parts) < 3:
                        print("<error> argument not enough")
                        continue
                    index = try_parse_int(input_parts[2])
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
                            audio_file = (
                                CACHE_DIR
                                / f"homework_{encodeb64_safe(hw_list[index].title)}_audio.mp3"
                            )
                            if not audio_file.is_file():
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
                    index = try_parse_int(input_parts[2])
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
                    index = try_parse_int(input_parts[2])
                    if index is None:
                        print("<error> argument invalid")
                        continue
                    if index < 0 or index >= len(hw_list):
                        print(f"<error> index out of range: {index}")
                        continue

                    match input_parts[1]:
                        case "fill_in":
                            answers_input = session.prompt("answers: ").strip()
                            with open(answers_input, "rt", encoding="utf-8") as f:
                                answers = json.load(f)
                            fill_in_answers(index, hw_list[index], answers)

                        case "download":
                            answers = get_answers(index, hw_list[index])
                            if len(answers) == 0:
                                print(
                                    "<error> no answers retrieved; cannot save to file"
                                )
                                continue

                            answers_file = (
                                CACHE_DIR
                                / f"homework_{encodeb64_safe(hw_list[index].title)}_answers.json"
                            )
                            with open(answers_file, "wt", encoding="utf-8") as f:
                                f.write(
                                    json.dumps(answers, indent=4, ensure_ascii=False)
                                )
                            print_and_copy_path(answers_file)

                        case "generate":
                            if ai_client is None:
                                print("<error> no ai client selected")
                                continue
                            answers = generate_answers(index, hw_list[index], ai_client)
                            if answers is None:
                                print("<error> failed to generate answers")
                                continue

                            answers_file = (
                                CACHE_DIR
                                / f"homework_{encodeb64_safe(hw_list[index].title)}_answers_gen.json"
                            )
                            with open(answers_file, "wt", encoding="utf-8") as f:
                                f.write(
                                    json.dumps(answers, indent=4, ensure_ascii=False)
                                )
                            print_and_copy_path(answers_file)

                        case "download_from_paper":
                            raise NotImplementedError

                        case "submit":
                            raise NotImplementedError

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
                                            globalvars.context.config.credentials.all,
                                        )
                                    ),
                                )
                            )  # type: ignore
                            default = 0
                            if isinstance(
                                globalvars.context.config.credentials.selected, int
                            ):
                                default = globalvars.context.config.credentials.selected
                            cred_choice = choice(
                                "select credentials to use:",
                                options=options,
                                default=default,
                            )
                            cred = Credentials.from_dict(
                                globalvars.context.config.credentials.all[cred_choice]
                            )
                            logout()
                            login(cred)
                            goto_hw_list_page()
                            hw_list = get_hw_list()
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
                                            globalvars.context.config.credentials.all,
                                        )
                                    ),
                                )  # type: ignore
                            )
                            default = "none"
                            if isinstance(
                                globalvars.context.config.credentials.selected, int
                            ):
                                default = globalvars.context.config.credentials.selected
                            cred_choice = choice(
                                "select default credentials to use:",
                                options=options,
                                default=default,
                            )
                            if cred_choice == "none":
                                globalvars.context.config.credentials.selected = None
                                print("<info> disabled auto login")
                                continue

                            globalvars.context.config.credentials.selected = cred_choice
                            cred = Credentials.from_dict(
                                globalvars.context.config.credentials.all[cred_choice]
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
                                            globalvars.context.config.ai_client.all,
                                        )
                                    ),
                                )  # type: ignore
                            )
                            default = "none"
                            if isinstance(
                                globalvars.context.config.ai_client.selected, int
                            ):
                                default = globalvars.context.config.ai_client.selected
                            client_choice = choice(
                                "select AI client to use:",
                                options=options,
                                default=default,
                            )
                            if client_choice == "none":
                                ai_client = None
                                globalvars.context.config.ai_client.selected = None
                                print("<info> AI features disabled")
                                continue

                            ai_client_conf = globalvars.context.config.ai_client.all[
                                client_choice
                            ]
                            ai_client = AIClient.from_dict(ai_client_conf)
                            globalvars.context.config.ai_client.selected = client_choice
                            print(f"<info> selected AI client: {ai_client.describe()}")
                        case "select_model":
                            if ai_client is None:
                                print("<error> no ai client selected")
                                continue

                            options = list(enumerate(ai_client.models))
                            model_choice = choice(
                                "select AI model to use:",
                                options=options,
                                default=ai_client.selected_model_index,
                            )

                            ai_client_conf = next(
                                c
                                for c in globalvars.context.config.ai_client.all
                                if c.api_url == ai_client.api_url
                                and c.api_key == ai_client.api_key
                            )
                            ai_client_conf.model.selected = model_choice
                            ai_client.selected_model_index = model_choice
                            print(
                                f"<info> selected AI model: {ai_client.selected_model}"
                            )
                        case _:
                            print("<error> argument invalid")

                case "config":
                    if len(input_parts) < 2:
                        print("<error> argument not enough")
                        continue

                    match input_parts[1]:
                        case "reload":
                            globalvars.context.config = load_config()
                            print("<info> reloaded config file")
                            print("<info> note: current states are not changed")
                        case "save":
                            save_config(globalvars.context.config)
                            print("<info> saved config to file")
                        case _:
                            print("<error> argument invalid")

                case "rescue":
                    goto_hw_list_page()

                case "exit":
                    print("<info> exiting...")
                    save_config(globalvars.context.config)
                    print("<info> saved config to file")
                    break

                case _:
                    print(f"<error> unrecognized command: '{user_input}'")

        except NotImplementedError:
            print("<error> feature not yet implemented")

        except KeyboardInterrupt:
            print("<warning> interrupted")


if __name__ == "__main__":
    main()
