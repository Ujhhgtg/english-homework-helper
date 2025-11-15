import globalvars


def print(*args, **kwargs):
    globalvars.context.messenger.send_text(*args, **kwargs)


def download_file_with_progress(progress, url: str, filename: str):
    with globalvars.http_client.stream("GET", url) as response:
        response.raise_for_status()
        total = int(response.headers.get("Content-Length", 0))

        with open(filename, "wb") as f:
            task = progress.add_task("[cyan]Downloading...", total=total)
            for chunk in response.iter_bytes(chunk_size=8192):
                f.write(chunk)
                progress.update(task, advance=len(chunk))
