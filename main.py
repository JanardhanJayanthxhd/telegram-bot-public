import logging
import re
import datetime as dt
import asyncio
from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PollAnswerHandler,
    filters,
)


TOKEN = 'YOUR_BOT_TOKEN'
BOT_USERNAME = '@YOUR_BOT_NAME'

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# total number of voters
TOTAL_VOTER_COUNT = 6


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inform user about what this bot can do"""
    await update.message.reply_text("Greetings, START_TEXT")


async def gears(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List of possessions"""
    await update.message.reply_text("YOUR_GEARS", parse_mode='HTML')


# Responses
def handle_response(text: str, update: Update) -> str:
    processed_text = text.lower()
    if processed_text in ['hi', 'hello']:
        return f'Hey there! {extract_names(update.effective_user.mention_html())}'
    return 'I cannot what you just wrote...'


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type
    text: str = update.message.text

    print(f'User {update.message.chat.id} in {message_type} : {text}')

    if message_type == 'group' or message_type == 'supergroup':
        if BOT_USERNAME in text:
            processed_text = text.replace(BOT_USERNAME, '').strip()
            response: str = handle_response(processed_text, update)
    else:
        response: str = handle_response(text, update)

    print(f'BOT : {response}')

    await update.message.reply_text(response)


# Poll
async def poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a predefined poll"""
    if update.effective_user.id == 1301038543:
        questions = ["In", "Maybe", "Out"]
        message = await context.bot.send_poll(
            update.effective_chat.id,
            "Badminton, are you in?",
            questions,
            is_anonymous=False,
            open_period=599, 
        )
        # Save some info about the poll the bot_data for later use in receive_poll_answer
        payload = {
            message.poll.id: {
                "questions": questions,
                "message_id": message.message_id,
                "chat_id": update.effective_chat.id,
                "answers": 0,
                "open_for": 599,
                "open_time": dt.datetime.now()
            }
        }
        context.bot_data.update(payload)
    else:
        await update.message.reply_text('Unavailable')


def extract_names(html_string):
    """returns the name from html tag using regular expression"""
    # Regular expression pattern to match the names within the <a> tag
    pattern = r'<a href="tg://user\?id=\d+">([^<]+)</a>'
    # Use re.search to find the match
    match = re.search(pattern, html_string)
    if match:
        # Extract the full name
        full_name = match.group(1)
        return f'{full_name}'
    else:
        return None


async def receive_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Summarize a users poll vote, works once per voting"""
    answer = update.poll_answer
    answered_poll = context.bot_data[answer.poll_id]

    try:
        questions = answered_poll["questions"]
    # this means this poll answer update is from an old poll, we can't do our answering then
    except KeyError:
        return

    selected_options = answer.option_ids
    answer_string = ""

    for question_id in selected_options:
        answer_string += questions[question_id]

    user_name = extract_names(update.effective_user.mention_html())

    # selecting the last element of the bot_data dictionary - last element.
    poll_data = list(context.bot_data.items())[-1][1]
    print(f'poll data : {poll_data}')
    poll_open_duration = poll_data['open_for']
    poll_open_time = poll_data['open_time']
    poll_close_time = (poll_open_time + dt.timedelta(seconds=poll_open_duration)).time()

    # Close poll if the open_duration is over or after six participants voted
    while True:
        time_now = dt.datetime.now().time()

        if time_now >= poll_close_time or answered_poll["answers"] == TOTAL_VOTER_COUNT:
            # posting poll results before closing.
            await context.bot.send_message(
                answered_poll["chat_id"],
                f"{user_name} : <b>{answer_string}</b>",
                parse_mode=ParseMode.HTML,
            )
            answered_poll["answers"] += 1
            try:
                await context.bot.stop_poll(answered_poll["chat_id"], answered_poll["message_id"])
            except BadRequest:
                break
        else:
            await asyncio.sleep(1)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display a help message"""
    await update.message.reply_text("HELP_TEXT")


def main() -> None:
    """Run bot."""
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("poll", poll))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler('gear', gears))
    app.add_handler(PollAnswerHandler(receive_poll_answer))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    # bot
    app.run_polling()


if __name__ == "__main__":
    main()
