from prompt_toolkit.completion import Completer, Completion


class LastWordCompleter(Completer):
    def __init__(self, word_map: dict, case_insensitive=False) -> None:
        super().__init__()
        self.word_map = word_map
        self.case_insensitive = case_insensitive

    def get_completions(self, document, complete_event):
        # DON'T strip — keep original spacing semantics
        text_before_cursor = document.text_before_cursor
        words = tuple(text_before_cursor.split())

        # Find the longest prefix (from the start) that exists in word_map
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
