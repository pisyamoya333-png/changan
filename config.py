import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from os import getenv
from dotenv import find_dotenv, load_dotenv


load_dotenv(find_dotenv())


bot = Bot(token=getenv('TOKEN'), default=DefaultBotProperties(parse_mode='HTML', link_preview_is_disabled=True))
payment_api_token = getenv("PAYMENT_API_TOKEN")

bot_username = getenv('BOT_USERNAME')
bot_name = getenv('BOT_NAME')
helper_username = getenv('HELPER_USERNAME')
payfrom_channel_id = getenv('PAYFROM_CHANNEL_ID')

payment_url = getenv("PAYMENT_URL")
sqlalchemy_url = getenv('SQLALCHEMY_URL')

required_channel_id = getenv("REQUIRED_CHANNEL_ID")
owner_required_channel_id = getenv("OWNER_REQUIRED_CHANNEL_ID")


logging.basicConfig(
    level=logging.ERROR,
    filename='logs.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)
