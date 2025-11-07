import globalvars


def print(*args, **kwargs):
    globalvars.context.messenger.send_text(*args, **kwargs)
