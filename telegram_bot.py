from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from models.homework_record import HomeworkRecord
from models.homework_status import HomeworkStatus
from tasks import *

hw_list: list[HomeworkRecord] = []


async def command_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global hw_list

    hw_list = get_list()
    if not hw_list:
        # Simple message for no homework, no special formatting needed
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="No homework items found \\(Phew\\!\\)",  # Escaping the parentheses in MarkdownV2
        )
        return

    # --- Formatting the Homework List with MarkdownV2 ---

    # Header: Bold and use an emoji
    message_lines = ["*📚 Homework List 📋*"]

    for i, hw in enumerate(hw_list):
        # Determine status color/emoji
        status_text = hw.status.value if hw.status else "Unknown"
        if hw.status == HomeworkStatus.COMPLETED:
            status_emoji = "✅"
        elif (
            hw.status == HomeworkStatus.NOT_COMPLETED
            or hw.status == HomeworkStatus.MAKE_UP
            or hw.status == HomeworkStatus.IN_PROGRESS
        ):
            status_emoji = "⏳"
        else:
            status_emoji = "❓"

        # Use 'monospace' for scores/status to align them and make them stand out
        status_score_info = (
            f"Status: `{status_text}` \\| Score: `{hw.current_score}/{hw.total_score}`"
        )

        # Combine: 1. Title - Status: ... | Score: ...
        message_lines.append(
            f"{i+1}\\. {status_emoji} `{hw.title.replace("-", "\\-")}`\n    {status_score_info}"
        )

    # Join lines, ensuring newlines are correctly handled in MarkdownV2
    message = "\n\n".join(message_lines)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        parse_mode="MarkdownV2",  # IMPORTANT: Specify the parsing mode
    )


async def command_download_audio(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    global hw_list

    chat_id = update.effective_chat.id

    if not context.args:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Please provide a URL after the command, e.g., `/download_audio <url>`.",
        )
        return

    index = context.args[0]
    try:
        index = int(index)
    except ValueError:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Invalid index. Please provide a valid homework index.",
        )
        return

    print(index)

    if index < 0 or index >= len(hw_list):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Index out of range: {index}",
        )
        return

    download_audio(index, hw_list[index])

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Audio for homework index {index} downloaded successfully.",
    )
    await context.bot.send_audio(
        chat_id=update.effective_chat.id,
        audio=open(f"cache/homework_{index}_audio.mp3", "rb"),
        caption=f"Here is the audio for homework index {index}.",
    )


def main():
    print("--- step: start telegram bot ---")
    application = Application.builder().token(config.telegram_bot_token).build()

    application.add_handler(CommandHandler("list", command_list))
    application.add_handler(CommandHandler("download_audio", command_download_audio))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
