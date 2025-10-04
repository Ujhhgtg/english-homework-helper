# 📚 English Homework Helper

A powerful command-line tool designed to automate login, homework list parsing, and content extraction (including audio downloading and transcription) from the [简练英语平台](https://admin.jeedu.net) platform using Selenium and OpenAI's Whisper.

## ✨ Features

- Homework List Parsing: Scrapes and presents a structured list of all pending and completed homework, including scores and status.

- Retrieve the complete text content of a homework assignment.

- Download embedded audio files for listening or transcription.

- Utilizes Whisper model for English transcription of downloaded homework audio.

- Provides an interactive command-line interface powered by prompt-toolkit.

## 🚀 Setup & Installation

### Prerequisites

You need to have Python 3.9+ and Firefox installed on your system.

### 1. Clone repo & Install deps

Clone the repository and install the required Python packages:

```bash
git clone https://github.com/Ujhhgtg/english-homework-helper.git
cd english-homework-helper

# Install PyTorch for GPU-accelerated Whisper audio transcription
# Choose one of the following based on your device
# Skip this step to fallback to CPU
# CUDA 12.6
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu126
# CUDA 12.8
pip3 install torch torchvision
# CUDA 12.9
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu129
# ROCm 6.4
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/rocm6.4

pip install -r requirements.txt
```

### 2. Configure credentials

Rename `local/credentials.py.example` to `local/credentials.py` and fill in your own credentials.

### 3. Configure OpenAI API (Optional)

> [!NOTE]
> This step is optional. However, if you don't configure this, you would not be able to use AI-based features.

Rename `local/ai_clients.py.example` to `local/ai_clients.py` and fill in your api urls & keys.

### 4. Configure Telegram Bot (Optional)

> [!NOTE]
> This step is optional. However, if you don't configure this, you would not be able to run the Telegram Bot.

> [!WARNING]
> The bot is currently under development, its features are incomplete and is not available for use (you can find it in the comments though).

Rename `local/telegram_bot_token.py.example` to `local/telegram_bot_token.py` and fill in your token.

## 💻 Usage

Run the main script:

```bash
python main.py
```

## 🤝 Contributing

This project is a personal utility. If you find it useful or have suggestions for improvement, feel free to open an issue or submit a pull request!
