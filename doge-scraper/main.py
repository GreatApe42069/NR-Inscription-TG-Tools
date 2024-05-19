import json
import logging
from io import BytesIO

import requests
from telegram import Update
from telegram.ext import CallbackContext, Updater, CommandHandler, MessageHandler, Filters

from controllers.collection_stat import CollectionController
from utils.constants import BOT_TOKEN, BASE_URL

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

collection_stat = CollectionController()


def authorized_user(func):
    def wrapper(update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        print(f"User ID: {user_id}, Chat ID: {chat_id}")
        # Allow anyone to use the bot, no restriction on user IDs
        return func(update, context)

    return wrapper


def start(update: Update, context: CallbackContext):
    help_message = f"""
    Hi {update.effective_user.first_name}!,\n
🚀 Welcome to The Node Runners Inscription Tool Bot!\nHere are the commands you can use:\n
1. /inscription <address> <filter_id> - Get all the inscriptions for the given address.
Optionally, you can provide a filter id to get inscriptions from that id onwards.

2. /list <collection_name> <skip> <limit> - Get all the inscriptions for the given collection name.\n
skip -> Number of inscriptions to be skipped from start
limit -> Max number of inscription data per command, max allowed is 2000 to avoid timeout.
    """
    update.message.reply_text(help_message)


def unknown_command(update: Update, context: CallbackContext):
    update.message.reply_text("Sorry, I didn't understand that command., please use /help to get a list of commands.")


def get_user_id(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(f"Your user ID is: {update.effective_user.id}")

def get_ordinals_wallet_inscriptions(update: Update, context: CallbackContext) -> None:
    if not context.args:
        update.message.reply_text("Please provide the address")
        return

    address = context.args[0]
    filter_id = context.args[1] if len(context.args) > 1 else None
    print(f"Addresses: {address}")

    update.message.reply_text(f"Scraping IDs for address {address}...")
    api_url = f"{BASE_URL}/wallet/{address}/inscriptions"
    response = requests.get(api_url, params={})
    print(response)
    if response.status_code != 200:
        update.message.reply_text(f"Please enter a valid address.")
        return

    inscriptions = [{
        "id": inscription["id"],
        "meta": {
            "name": str(idx),
            "attributes": []
        }
    } for idx, inscription in enumerate(response.json(), start=1)]

    # filter the inscriptions if filter ID is provided
    for idx, inscription in enumerate(inscriptions):
        if filter_id and inscription["id"] == filter_id:
            inscriptions = inscriptions[idx:]
            break

    json_response = json.dumps(inscriptions)
    file_bytes = BytesIO(json_response.encode('utf-8'))
    with open(f'{address}.json', 'w') as f:
        f.write(json_response)
    # Send the file
    context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=file_bytes,
        filename=f'{address}.json'
    )


def __get_query_filters(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("Please provide the collection name")
        raise Exception("Invalid Args")

    default_limit = 2000
    default_skip = 0

    if len(context.args) == 3:
        return context.args
    elif len(context.args) == 2:
        return context.args + [default_limit]
    elif len(context.args) == 1:
        return context.args + [default_skip, default_limit]
    else:
        update.message.reply_text(f"Too many args passed, please use this format: <slug> <skip> <limit>")
        raise Exception("Invalid Args")

def list_collection(update: Update, context: CallbackContext) -> None:
    try:
        collection_name, skip, limit = __get_query_filters(update, context)
    except Exception:
        return
    update.message.reply_text(f"Fetching inscriptions data for {collection_name}... Skip: {skip}, Limit: {limit}")
    response = collection_stat.get_collection_data(collection_name, skip=int(skip), limit=int(limit))
    json_response = json.dumps(response, indent=4)
    file_bytes = BytesIO(json_response.encode('utf-8'))
    context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=file_bytes,
        filename=f'{collection_name}_({skip}-{limit}).json'
    )


def main() -> None:
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    # Add handlers for commands and messages
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('list', list_collection))
    dispatcher.add_handler(CommandHandler('inscription', get_ordinals_wallet_inscriptions))
    dispatcher.add_handler(CommandHandler('help', start))
    dispatcher.add_handler(MessageHandler(Filters.command, unknown_command))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
