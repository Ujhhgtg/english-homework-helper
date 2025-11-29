import inspect
from pathlib import Path

from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn

from .. import globalvars
from . import feature_flags

_original_print = print


def print(*args, **kwargs):
    if not globalvars.context or not globalvars.context.messenger:
        _original_print("(null ctx fallback) ", end="")
        _original_print(*args, **kwargs)
        return

    globalvars.context.messenger.send_text(*args, **kwargs)


def download_file_with_progress(progress, url: str, filename: str):
    with globalvars.context.http_client.stream("GET", url) as response:
        response.raise_for_status()
        total = int(response.headers.get("Content-Length", 0))

        with open(filename, "wb") as f:
            if progress is not None:
                task_id = progress.add_task("[cyan]Downloading...", total=total)
            for chunk in response.iter_bytes(chunk_size=8192):
                f.write(chunk)
                if progress is not None:
                    progress.update(task_id, advance=len(chunk))


def print_and_copy_path(path: str | Path) -> None:
    if isinstance(path, Path):
        path = str(path)

    if feature_flags.PYPERCLIP:
        import pyperclip

        pyperclip.copy(path)

    print(
        f"<success> saved to file '{path}'{" (path copied to clipboard)" if feature_flags.PYPERCLIP else ""}"
    )
    if not feature_flags.PYPERCLIP:
        print("<warning> pyperclip not installed, cannot copy path to clipboard")


def patch_whisper_transcribe_progress():
    if not feature_flags.WHISPER:
        print(
            "<warning> whisper is not installed; not patching whisper transcribe progress"
        )
        return

    import whisper

    original_source = inspect.getsource(whisper.transcribe)

    tqdm_ctx_line = """
    with tqdm.tqdm(
        total=content_frames, unit="frames", disable=verbose is not False
    ) as pbar:
    """

    rich_ctx_line = """
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=globalvars.context.messenger.rich_console,
    ) as progress:
        task_id = progress.add_task("[cyan]Transcribing...", total=content_frames)
    """

    patched_source = original_source.replace(tqdm_ctx_line, rich_ctx_line)

    tqdm_update_line = "pbar.update(min(content_frames, seek) - previous_seek)"
    rich_update_line = (
        "progress.update(task_id, advance=min(content_frames, seek) - previous_seek)"
    )
    patched_source = patched_source.replace(tqdm_update_line, rich_update_line)

    whisper.transcribe  # type: ignore
    execution_scope = whisper.transcribe.__dict__.copy()
    execution_scope.update(whisper.transcribe.__globals__)
    execution_scope.update(whisper.__dict__)
    execution_scope.update(whisper.model.__dict__)
    execution_scope["Progress"] = Progress
    execution_scope["BarColumn"] = BarColumn
    execution_scope["TimeRemainingColumn"] = TimeRemainingColumn
    execution_scope["TextColumn"] = TextColumn
    execution_scope["globalvars"] = globalvars

    exec(patched_source, execution_scope)

    func = execution_scope["transcribe"]
    whisper.model.Whisper.transcribe = func
