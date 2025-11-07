#!/usr/bin/env python
# -*- coding: utf-8 -*-

import atexit
import json
import shlex
from pathlib import Path

from selenium.webdriver.firefox.options import (
    Options as FirefoxOptions,
)
from selenium.webdriver.support.ui import WebDriverWait

from textual.app import App, ComposeResult
from textual.widgets import (
    Header,
    Footer,
    Input,
    Log,
    ListView,
    ListItem,
    Label,
    Static,
)
from textual.containers import Container, Vertical
from textual.binding import Binding
from textual.message import Message

from models.homework_record import HomeworkRecord
from models.ai_client import AIClient
from models.credentials import Credentials
from utils.webdriver import FirefoxDriver
from utils.convert import parse_int
from utils.crypto import encodeb64_safe
from utils.config import load_config, save_config
from utils.logging import print
from utils.context.context import Context
from utils.context.messenger import TextualMessenger
from tasks import *  # login, goto_hw_list_page, get_list, download_audio, transcribe_audio, get_text, download_text, get_answers, generate_answers, fill_in_answers, logout
import globalvars  # Assuming this module still manages global state like driver, wait, config


class HomeworkRecordItem(ListItem):
    """A custom list item to display a single HomeworkRecord."""

    def __init__(self, record: HomeworkRecord, index: int) -> None:
        super().__init__()
        self.record = record
        self.index = index

    def compose(self) -> ComposeResult:
        # Display the index and the homework title
        yield Label(f"[{self.index}] {self.record.title}", classes="list-label")


class HomeworkApp(App):
    """The main Textual application for the English Homework Helper."""

    CSS = """
    #app-grid {
        grid-size: 3 1; /* Three columns: List, Main, Command */
        grid-columns: 1fr 3fr; /* Sidebar for list, main area */
    }
    #hw-list {
        dock: left;
        width: 30;
        border-right: thick $secondary 50%;
        padding: 0;
    }
    #main-area {
        height: 100%;
        padding: 1;
    }
    #output-log {
        height: 100%;
    }
    #command-input {
        dock: bottom;
        border-top: heavy $secondary 50%;
        height: 3;
    }
    .list-label {
        width: 100%;
        overflow: ellipsis;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=False, priority=True),
    ]

    hw_list: list[HomeworkRecord] = []
    ai_client: AIClient | None = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        globalvars.context = Context(messenger=TextualMessenger(self, "#output-log"))

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        yield ListView(id="hw-list", classes="box")

        with Container(id="main-area"):
            yield Log(id="output-log", classes="box")
            yield Input(
                placeholder="Enter command (e.g., list, help, exit)", id="command-input"
            )

    def on_mount(self) -> None:
        print("--- english homework helper ---")
        print("--- by: ujhhgtg ---")
        print("--- github: https://github.com/Ujhhgtg/english-homework-helper ---")
        print("--- step: initialize ---")

        atexit.register(self._at_exit)
        print("[i] registered atexit handler")
        Path("./cache/").mkdir(parents=True, exist_ok=True)
        print("[i] created cache directory")
        globalvars.config = load_config()
        print("[i] loaded config file")

        driver_options = FirefoxOptions()
        if globalvars.config.browser.headless:
            driver_options.add_argument("--headless")

        try:
            globalvars.driver = FirefoxDriver(options=driver_options)
            globalvars.wait = WebDriverWait(globalvars.driver, 15)
            print(
                f"[i] started browser{' in headless mode' if globalvars.config.browser.headless else ''}"
            )
        except Exception as e:
            print(f"[error] failed to start browser: {e}")

        if globalvars.config.ai_client.selected is not None:
            sel_index = globalvars.config.ai_client.selected
            if 0 <= sel_index < len(globalvars.config.ai_client.all):
                self.ai_client = AIClient.from_dict(
                    globalvars.config.ai_client.all[sel_index]
                )
                print(f"[i] using default AI client at index {sel_index}")
            else:
                print(
                    f"[warning] default AI client index {sel_index} out of range; falling back to no AI client"
                )

        if globalvars.config.credentials.selected is not None:
            sel_index = globalvars.config.credentials.selected
            if 0 <= sel_index < len(globalvars.config.credentials.all):
                cred = Credentials.from_dict(
                    globalvars.config.credentials.all[sel_index]
                )
                try:
                    login(cred)
                    goto_hw_list_page()
                    self.hw_list = get_list()
                    self._update_homework_list_view()
                    print(
                        f"[i] using default credentials at index {sel_index}: {cred.describe()}"
                    )
                except Exception as e:
                    print(f"[error] automatic login failed: {e}")
            else:
                print(
                    f"[warning] default credentials index {sel_index} out of range; not logging in"
                )
        else:
            print(f"[warning] no default credentials provided; not logging in")

        print("--- entering interactive mode ---")
        self.query_one("#command-input").focus()

    def _at_exit(self):
        if globalvars.driver is not None:
            try:
                globalvars.driver.current_url
                globalvars.driver.quit()
                print("[i] atexit: browser closed automatically")
                save_config(globalvars.config)
                print("[i] saved config to file")
            except Exception as e:
                print(f"[error] error occured at exit: {e}")

    def _update_homework_list_view(self) -> None:
        hw_list_view = self.query_one("#hw-list", ListView)
        hw_list_view.clear()
        for index, record in enumerate(self.hw_list):
            hw_list_view.append(HomeworkRecordItem(record, index))

    def on_input_submitted(self, message: Input.Submitted) -> None:
        user_input = message.value.strip().lower()
        self.query_one(Input).value = ""  # Clear the input box
        if not user_input:
            return

        print(f"ehh> {user_input}")

        try:
            input_parts = shlex.split(user_input)
            if not input_parts:
                return

            command = input_parts[0]
            args = input_parts[1:]

            self._execute_command(command, args)

        except Exception as e:
            print(f"[error] an unexpected error occurred: {e}")
            try:
                goto_hw_list_page()
            except Exception:
                ...

    def _execute_command(self, command: str, args: list[str]) -> None:

        match command:
            case "help":
                print("[i] available commands:")
                print("  audio [download|transcribe] <index>")
                print("  text [display|download] <index>")
                print("  answers [fill_in|download|generate] <index>")
                print("  list - list all homework items")
                print("  account [login|logout|select_default]")
                print("  ai [select_api|select_model]")
                print("  config [reload|save]")
                print("  exit - exit the program")

            case "list":
                self.hw_list = get_list()
                self._update_homework_list_view()
                print("[i] homework list updated.")

            case "audio":
                if len(args) < 2:
                    print(
                        "[error] argument not enough. Usage: audio [download|transcribe] <index>"
                    )
                    return
                subcommand = args[0]
                index = parse_int(args[1])
                if index is None or not (0 <= index < len(self.hw_list)):
                    print(f"[error] invalid or out of range index: {args[1]}")
                    return

                record = self.hw_list[index]
                if subcommand == "download":
                    download_audio(index, record)
                elif subcommand == "transcribe":
                    audio_file = (
                        f"cache/homework_{encodeb64_safe(record.title)}_audio.mp3"
                    )
                    if not Path(audio_file).is_file():
                        print(
                            f"[error] audio file for index {index} not found; please download it first"
                        )
                        return
                    transcribe_audio(index, record)
                else:
                    print("[error] argument invalid")

            case "text":
                if len(args) < 2:
                    print(
                        "[error] argument not enough. Usage: text [display|download] <index>"
                    )
                    return
                subcommand = args[0]
                index = parse_int(args[1])
                if index is None or not (0 <= index < len(self.hw_list)):
                    print(f"[error] invalid or out of range index: {args[1]}")
                    return

                record = self.hw_list[index]
                if subcommand == "display":
                    print(get_text(index, record))
                elif subcommand == "download":
                    download_text(index, record)
                else:
                    print("[error] argument invalid")

            case "answers":
                if len(args) < 2:
                    print(
                        "[error] argument not enough. Usage: answers [fill_in|download|generate] <index>"
                    )
                    return
                subcommand = args[0]
                index = parse_int(args[1])
                if index is None or not (0 <= index < len(self.hw_list)):
                    print(f"[error] invalid or out of range index: {args[1]}")
                    return

                record = self.hw_list[index]

                if subcommand == "fill_in":
                    print(
                        "[warning] For 'fill_in', you need a separate command to submit JSON data. This feature requires a custom input screen in Textual."
                    )
                    if len(args) < 3:
                        print(
                            '[error] Not enough arguments for fill_in. Usage: answers fill_in <index> <\'{"key": "value"}\'>'
                        )
                        return

                    try:
                        answers_input = args[2]
                        answers = json.loads(answers_input)
                        fill_in_answers(index, record, answers)
                        print("[success] Answers filled in successfully.")
                    except json.JSONDecodeError:
                        print("[error] Invalid JSON format for answers.")
                    except Exception as e:
                        print(f"[error] Failed to fill in answers: {e}")

                elif subcommand == "download":
                    answers = get_answers(index, record)
                    if not answers:
                        print("[error] no answers retrieved; cannot save to file")
                        return

                    answers_file = (
                        f"cache/homework_{encodeb64_safe(record.title)}_answers.json"
                    )
                    with open(answers_file, "wt", encoding="utf-8") as f:
                        f.write(json.dumps(answers, indent=4, ensure_ascii=False))
                    print(f"[success] saved to file {answers_file}")

                elif subcommand == "generate":
                    if self.ai_client is None:
                        print("[error] no ai client selected")
                        return
                    answers = generate_answers(index, record, self.ai_client)
                    if answers is None:
                        print("[error] failed to generate answers")
                        return

                    answers_file = f"cache/homework_{encodeb64_safe(record.title)}_answers_gen.json"
                    with open(answers_file, "wt", encoding="utf-8") as f:
                        f.write(json.dumps(answers, indent=4, ensure_ascii=False))
                    print(f"[success] saved to file {answers_file}")

                else:
                    print("[error] argument invalid")

            case "account":
                if len(args) < 1:
                    print(
                        "[error] argument not enough. Usage: account [login|logout|select_default]"
                    )
                    return
                subcommand = args[0]

                if subcommand == "login":
                    print(
                        "[warning] 'account login' requires a selection. Please use 'account login <index>'"
                    )
                    if len(args) < 2:
                        print("[error] Missing credentials index. Available accounts:")
                        for idx, cred_dict in enumerate(
                            globalvars.config.credentials.all
                        ):
                            cred = Credentials.from_dict(cred_dict)
                            print(f"  [{idx}] {cred.describe()}")
                        return

                    index_str = args[1]
                    try:
                        cred_choice = int(index_str)
                    except ValueError:
                        print("[error] Invalid index.")
                        return

                    if 0 <= cred_choice < len(globalvars.config.credentials.all):
                        cred = Credentials.from_dict(
                            globalvars.config.credentials.all[cred_choice]
                        )
                        logout()
                        login(cred)
                        goto_hw_list_page()
                        self.hw_list = get_list()
                        self._update_homework_list_view()
                        print(
                            f"[success] Logged in with credentials: {cred.describe()}"
                        )
                    else:
                        print("[error] Credentials index out of range.")
                        return

                elif subcommand == "logout":
                    logout()
                    print("[success] Logged out.")

                elif subcommand == "select_default":
                    print(
                        "[warning] 'select_default' requires an index or 'none'. Usage: account select_default <index|none>"
                    )
                    if len(args) < 2:
                        print(
                            "[error] Missing credentials index. Available accounts (use 'none' to disable auto-login):"
                        )
                        print("  [none] disable auto login")
                        for idx, cred_dict in enumerate(
                            globalvars.config.credentials.all
                        ):
                            cred = Credentials.from_dict(cred_dict)
                            print(f"  [{idx}] {cred.describe()}")
                        return

                    choice_str = args[1].lower()
                    if choice_str == "none":
                        globalvars.config.credentials.selected = None
                        print("[i] disabled auto login")
                    else:
                        try:
                            cred_choice = int(choice_str)
                        except ValueError:
                            print("[error] Invalid index or command.")
                            return

                        if 0 <= cred_choice < len(globalvars.config.credentials.all):
                            globalvars.config.credentials.selected = cred_choice
                            cred = Credentials.from_dict(
                                globalvars.config.credentials.all[cred_choice]
                            )
                            print(
                                f"[i] selected default credentials: {cred.describe()}"
                            )
                        else:
                            print("[error] Credentials index out of range.")
                else:
                    print("[error] argument invalid")

            case "ai":
                if len(args) < 1:
                    print(
                        "[error] argument not enough. Usage: ai [select_api|select_model]"
                    )
                    return
                subcommand = args[0]

                if subcommand == "select_api":
                    print(
                        "[warning] 'select_api' requires an index or 'none'. Usage: ai select_api <index|none>"
                    )
                    if len(args) < 2:
                        print(
                            "[error] Missing AI client index. Available clients (use 'none' to disable AI):"
                        )
                        print("  [none] disable AI features")
                        for idx, client_dict in enumerate(
                            globalvars.config.ai_client.all
                        ):
                            client = AIClient.from_dict(client_dict)
                            print(f"  [{idx}] {client.describe()}")
                        return

                    choice_str = args[1].lower()
                    if choice_str == "none":
                        self.ai_client = None
                        globalvars.config.ai_client.selected = None
                        print("[i] AI features disabled")
                    else:
                        try:
                            client_choice = int(choice_str)
                        except ValueError:
                            print("[error] Invalid index or command.")
                            return

                        if 0 <= client_choice < len(globalvars.config.ai_client.all):
                            ai_client_conf = globalvars.config.ai_client.all[
                                client_choice
                            ]
                            self.ai_client = AIClient.from_dict(ai_client_conf)
                            globalvars.config.ai_client.selected = client_choice
                            print(
                                f"[i] selected AI client: {self.ai_client.describe()}"
                            )
                        else:
                            print("[error] AI client index out of range.")

                elif subcommand == "select_model":
                    if self.ai_client is None:
                        print("[error] no ai client selected")
                        return

                    print(
                        "[warning] 'select_model' requires an index. Usage: ai select_model <index>"
                    )
                    if len(args) < 2:
                        print(
                            f"[error] Missing model index. Available models for {self.ai_client.describe()}:"
                        )
                        for idx, model_name in enumerate(self.ai_client.models):
                            print(
                                f"  [{idx}] {model_name}{' (default)' if idx == self.ai_client.selected_model_index else ''}"
                            )
                        return

                    try:
                        model_choice = int(args[1])
                    except ValueError:
                        print("[error] Invalid index.")
                        return

                    if 0 <= model_choice < len(self.ai_client.models):
                        # Find and update the config for the currently used client
                        for client_conf in globalvars.config.ai_client.all:
                            if (
                                client_conf.api_url == self.ai_client.api_url
                                and client_conf.api_key == self.ai_client.api_key
                            ):
                                client_conf.model.selected = model_choice
                                self.ai_client.selected_model_index = model_choice
                                print(
                                    f"[i] selected AI model: {self.ai_client.selected_model()}"
                                )
                                break
                    else:
                        print("[error] Model index out of range.")

                else:
                    print("[error] argument invalid")

            case "config":
                if len(args) < 1:
                    print("[error] argument not enough. Usage: config [reload|save]")
                    return
                subcommand = args[0]
                if subcommand == "reload":
                    globalvars.config = load_config()
                    print("[i] reloaded config file")
                    print(
                        "[i] note: current states (browser, ai client) are not changed"
                    )
                elif subcommand == "save":
                    save_config(globalvars.config)
                    print("[i] saved config to file")
                else:
                    print("[error] argument invalid")

            case "exit":
                ...

            case _:
                print(f"[error] unrecognized command: '{command}'")

    async def action_quit(self) -> None:
        """Called when the user issues the 'quit' action (e.g., 'exit' command or Ctrl+C)."""
        print("[i] exiting...")
        # The _at_exit handler will call save_config and quit the driver
        await super().action_quit()


if __name__ == "__main__":
    # Remove the original main() wrapper and run the Textual App
    app = HomeworkApp()
    app.run()
