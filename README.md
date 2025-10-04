# 📚 English Homework Helper

A powerful command-line tool designed to automate login, homework list parsing, and content extraction (including audio downloading and transcription) from the [简练英语平台](https://admin.jeedu.net) platform using Selenium and OpenAI's Whisper.

## ✨ Features

- Structured Homework Overview: Scrapes and presents a clear, structured list of all pending and completed homework, including scores and completion status.

- Content Retrieval: Easily retrieve the complete text content of any homework assignment.

- Audio Management: Download embedded audio files for self-study or automated transcription.

- Accurate Transcription: Utilizes the powerful Whisper model for highly accurate English transcription of downloaded homework audio.

- AI-Powered Answers: Generates potential answers using any OpenAI-compatible LLM to assist with your assignments.

- Interactive Interface: Provides a dynamic, user-friendly command-line interface powered by `prompt-toolkit`.

## 🚀 Setup & Installation

### Prerequisites

You need to have Python 3.9+ and Firefox installed on your system.

### 1. Clone repo & Install deps

Clone the repository and install the required Python packages:

```bash
git clone https://github.com/Ujhhgtg/english-homework-helper.git
cd english-homework-helper

# Install PyTorch for GPU-accelerated Whisper audio transcription (highly recommended)
# Choose the correct command based on your device/CUDA version (skip to fallback to CPU)
# CUDA 12.6
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
# CUDA 12.8 (Common for many systems)
pip install torch torchvision
# CUDA 12.9
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu129
# ROCm 6.4 (For some AMD GPUs)
pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm6.4

pip install -r requirements.txt

```

### 2. Configure Settings

> [!NOTE]
> Some configuration options are optional, however you won't be able to access advanced features if you skip them.

Rename `local/config.json.example` to `local/config.json` and fill it in.

## 🔑 Guide: How to use LLMs for free

To use the AI-powered features, you'll need an API key from an LLM provider. This tool is compatible with OpenAI (e.g., ChatGPT models) and other OpenAI-compatible models including Google's Gemini (via its API endpoint) and Ollama.

### Google Gemini (Cloud)

> [!NOTE]
> The Gemini API has a free tier, but usage is subject to limits and billing.

1. Go to [Google AI Studio](https://aistudio.google.com/app/api-keys).

2. Sign in with your Google account.

3. Click `Create API key`. You may need to select or create a Google Cloud Project.

4. Copy the generated key and keep it secure.

5. Add the following in `local/config.json`:

    ```json
    {
        ...
        "ai_client": {
            "default": 0,
            "all": [
                {
                    "api_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
                    "api_key": "YOUR API KEY HERE",
                    "model": "find one in https://ai.google.dev/gemini-api/docs/models"
                }
            ]
        },
        ...
    }
    ```

### Ollama (Local)

> [!NOTE]
> Although Ollama can be run locally, the quality is often worse since most setups can only run highly-distilled models.

1. Install Ollama: Follow the instructions for your operating system on the [Ollama website](https://ollama.com/download).

2. Run the server:

    ```bash
    ollama serve
    ```

3. Pull a model. You can find models on the [Ollama Library](https://ollama.com/library).

    ```bash
    ollama pull model-name
    ```

4. Add the following in `local/config.json`. Ollama's server typically runs on `http://localhost:11434`.

    ```json
    {
        ...
        "ai_client": {
            "default": 0,
            "all": [
                {
                    "api_url": "http://localhost:11434/v1/",
                    "api_key": "ollama",
                    "model": "model-name"
                }
            ]
        },
        ...
    }
    ```

## 💻 Usage

Run the main script:

```bash
python main.py
```

## 🤝 Contributing

This project is a personal utility. If you find it useful or have suggestions for improvement, feel free to open an issue or submit a pull request!
