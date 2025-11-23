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

# install pytorch with cuda 12.6 support
install-torch-cu126:
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
    @echo "installed torch with CUDA 12.6 support"

# install pytorch with cuda 12.8 support
install-torch-cu128:8
    pip install torch torchvision
    @echo "installed torch with CUDA 12.8 support"

# install pytorch with cuda 13.0 support
install-torch-cu130:
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu129
    @echo "installed torch with CUDA 13.0 support"

# install pytorch with rocm 6.4 support
install-torch-rocm64:
    pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm6.4
    @echo "installed torch with ROCm 6.4 support"
