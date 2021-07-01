from uuid import uuid4
import json
import logging
import re
import time, datetime
import urllib.parse

import requests as req
from lxml import etree
from telegram import InlineQueryResultArticle, ParseMode, InputTextMessageContent, Update
from telegram.ext import Updater, InlineQueryHandler, CommandHandler, CallbackContext
from telegram.utils.helpers import escape_markdown


# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def command_start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    update.message.reply_text(
        'Bem-vindo! '
        'Para saber a idade actual de vacinação, escreva /idade. '
        'Para receber notificação quando a idade baixar, subscreva '
        'o canal @idadevacinas.'
    )


def command_help(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text(
        'Para saber a idade actual de vacinação, escreva /idade. '
        'Para receber notificação quando a idade baixar, subscreva '
        'o canal @idadevacinas.'
    )

def command_idade(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    global current_age
    update.message.reply_text(
        f'A idade mínima de vacinação é {current_age} '
        f'(última verificação às {last_checked.strftime("%H:%M")}).'
    )

def inlinequery(update: Update, context: CallbackContext) -> None:
    """Handle the inline query."""
    pass


class Bot:
    def __init__(self, token: str):
        self.token = token
        self.url = f'https://api.telegram.org/bot{token}'

    def get_updates(self):
        url = f'{self.url}/getUpdates'
        r = req.get(url)
        updates = json.loads(r.text)
        return updates

    def send_text(self, id: int, text: str):
        url_template = f'{self.url}/sendMessage?chat_id={id}&text={text}'
        encoded_text = urllib.parse.quote(text)
        url = url_template.format(text=encoded_text) 
        r = req.post(url)


def get_age(session: req.Session) -> int:
    """Access site to extract relevant information."""
    url = 'https://covid19.min-saude.pt/pedido-de-agendamento/'
    response = session.get(url)
    response.status_code

    title_path = "//div[@id = 'pedido_content']/h3/strong"
    html = etree.HTML(response.text)
    title = html.xpath(title_path)[0]

    title_template = r'Tem (\d+) ou mais anos'
    match = re.match(title_template, title.text)
    age = int(match.groups()[0])

    global last_checked
    last_checked = datetime.datetime.now()

    return age



current_age = 30
last_checked = None
def main():
    token = ''  # Insert Telegram Bot token
    channel_id = -1  # Insert Telegram Channel Id to send updates
    test_channel_id = -2  # Test Channel Id
    global current_age


    ## Create responsive bot
    ## Source: github.com/python-telegram-bot/python-telegram-bot/blob/master/examples/inlinebot.py

    # Create the Updater and pass it your bot's token.
    updater = Updater(token)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", command_start))
    dispatcher.add_handler(CommandHandler("help", command_help))
    dispatcher.add_handler(CommandHandler("idade", command_idade))

    # on non command i.e message - echo the message on Telegram
    dispatcher.add_handler(InlineQueryHandler(inlinequery))

    # Start the Bot
    updater.start_polling()

    # Block until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    # updater.idle()




    ## Start periodic checker

    bot = Bot(token)

    with req.Session() as session:
        age = get_age(session)

        # Starting bot message
        text = f"Bot iniciado. A idade de vacinação neste momento é {age}."
        bot.send_text(id=test_channel_id, text=text)

        # text = f"A idade de vacinação neste momento é {age}."
        # bot.send_text(id=channel_id, text=text)

        # Keep checking
        while True:
            age = get_age(session)

            if age < current_age:
                text = (
                    f"A idade de vacinação baixou para {age}. "
                    "Inscrição em: "
                    "https://covid19.min-saude.pt/pedido-de-agendamento/."
                )
                bot.send_text(id=channel_id, text=text)
                current_age = age

            time.sleep(60)


        text = f"Bot terminado. A idade de vacinação neste momento é {age}."
        bot.send_text(id=test_channel_id, text=text)




if __name__ == '__main__':
    main()