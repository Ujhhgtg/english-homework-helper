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

### 1. Project Setup

Clone the repository and install the required Python packages:

```bash
git clone https://github.com/Ujhhgtg/english-homework-helper.git
cd english-homework-helper
pip install -r requirements.txt
```

### 2. Configure Credentials

Rename `local/credentials.py.example` to `local/credentials.py` and fill in your own credentials.

## 💻 Usage

Run the main script:

```bash
python main.py
```

## 🤝 Contributing

This project is a personal utility. If you find it useful or have suggestions for improvement, feel free to open an issue or submit a pull request!
