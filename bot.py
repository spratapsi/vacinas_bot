import json
import logging
import re
import time, datetime

from lxml import etree
import requests as req
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

## Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


## Get age from website

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


## Telegram bot commands

def start(update, context):
    update.message.reply_text(
        'Bem-vindo! '
        'Para saber a idade actual de vacinação, escreva /idade. '
        'Para receber notificação quando a idade baixar, subscreva '
        'o canal @idadevacinas.'
    )

def help(update, context):
    update.message.reply_text(
        'Para saber a idade actual de vacinação, escreva /idade. '
        'Para receber notificação quando a idade baixar, subscreva '
        'o canal @idadevacinas.'
    )

def idade(update, context):
    """Send a message when the command /help is issued."""
    global current_age, last_checked
    update.message.reply_text(
        f'A idade mínima de vacinação é {current_age} '
        f'(última verificação às {last_checked.strftime("%H:%M")}).'
    )

def reply_to_message(update, context):
    """Default behaviour to reply to messages"""
    pass


def main():
    global current_age, last_checked
    update_frequency = 60  # seconds

    with req.Session() as session:
        age = current_age = get_age(session)
        last_checked = datetime.datetime.now()


    ## Setup bot

    with open('telegram_config.json') as telegram_config_file:
        config = json.load(telegram_config_file)

        bot_token = config["bot_token"]
        channel_id = config["channel_id"]
        test_channel_id = config["test_channel_id"]

    bot = telegram.Bot(token=bot_token)
    updater = Updater(token=bot_token)

    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', help))
    dispatcher.add_handler(CommandHandler('idade', idade))
    dispatcher.add_handler(MessageHandler(Filters.text, reply_to_message))

    updater.start_polling()
    # updater.idle()


    ## Starting bot message
    text = f"Bot iniciado. A idade de vacinação neste momento é {current_age}."
    bot.send_message(chat_id=test_channel_id, text=text)


    ## Start periodic checker

    with req.Session() as session:
        while True:
            if age < current_age:
                text = (
                    f"A idade de vacinação baixou para {age}. "
                    "Inscrição em: "
                    "https://covid19.min-saude.pt/pedido-de-agendamento/."
                )
                bot.send_message(chat_id=channel_id, text=text)
                current_age = age

            time.sleep(update_frequency)
            age = get_age(session)


    ## Shutdown bot message
    text = f"Bot terminado. A idade de vacinação neste momento é {age}."
    bot.send_message(chat_id=test_channel_id, text=text)



if __name__ == '__main__':
    main()
