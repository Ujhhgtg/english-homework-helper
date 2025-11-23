from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.validation import Validator, ValidationError


class LastWordCompleter(Completer):
    def __init__(self, word_map: dict, case_insensitive=False) -> None:
        super().__init__()
        self.word_map = word_map
        self.case_insensitive = case_insensitive

    def get_completions(self, document, complete_event):
        text_before_cursor = document.text_before_cursor
        words = tuple(text_before_cursor.split())

        options = []
        for length in range(len(words), -1, -1):
            prefix = words[:length] if length else ()
            if prefix in self.word_map:
                options = self.word_map[prefix]
                break

        current = document.get_word_under_cursor()
        cur_check = current.lower() if self.case_insensitive else current
        for opt in options:
            opt_check = opt.lower() if self.case_insensitive else opt
            if opt_check.startswith(cur_check):
                yield Completion(opt, start_position=-len(current))


class YesNoValidator(Validator):
    def validate(self, document):
        text = document.text.lower().strip()
        yes_variations = ("y", "yes")
        no_variations = ("n", "no")

        if text in yes_variations:
            document.text = "yes"  # type: ignore
        elif text in no_variations:
            document.text = "no"  # type: ignore
        else:
            raise ValidationError(
                message="invalid input",
                cursor_position=len(document.text),
            )


def prompt_for_yn(session: PromptSession, message: str) -> bool:
    while True:
        response = session.prompt(message, validator=YesNoValidator())

        if response == "yes":
            return True
        elif response == "no":
            return False
