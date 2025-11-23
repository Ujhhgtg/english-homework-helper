default:
    just --list

alias b := build

# build wheel
build:
    python -m build
    @echo "build complete. distribution files are in dist/ dir."

alias i := install

# install package (-f to force reinstall)
install force='':
    pip install {{ if force == "-f" { "--force-reinstall" } else { "" } }} ./dist/*.tar.gz
    @echo "installation complete."

alias r := run-api

# run cli (api version)
run-api:
    @echo "running ehh cli (api version)."
    python -m ehh.cli_api

# run cli (browser version)
run-browser:
    @echo "running ehh cli (browser version)."
    python -m ehh.cli_browser

# run tui
run-tui:
    @echo "running ehh tui."
    python -m ehh.tui

# run telegram bot
run-bot:
    @echo "running ehh telegram bot."
    python -m ehh.telegram_bot

# run custom
run NAME:
    @echo "running ehh {{NAME}}."
    python -m ehh.{{NAME}}
