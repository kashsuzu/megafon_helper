"""
Послание для кодеров: 
Если тебе не нравится качество кода и ты уже успел забрызгать слюнями весь монитор,
то ИДИ НАХУЙ ОТСЮДА

На БЕСПЛАТНЫЙ софт грех что-то пиздеть.
"""

import asyncio
import sys

from dotenv import load_dotenv
from loguru import logger

from src.bot.telegram_bot import start_telegram_bot
from src.database import Database  # noqa: F401
from src.startup import print_startup_message

load_dotenv()  # reads variables from a .env file and sets them in os.environ

logger_format = (
    "<green>{time:DD-MM-YY HH:mm:ss}</green> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{level}</level> | "
    "{extra[account_id]} - <level>{message}</level> "
)

logger.remove()
logger.configure(extra={"account_id": ""})
logger.add(sys.stderr, format=logger_format, colorize=True, enqueue=True)
logger.add("data/logs.log", format=logger_format, colorize=False, enqueue=True)


async def main():
    print_startup_message()
    db = Database()
    await db.create_tables()
    await start_telegram_bot()


if __name__ == "__main__":
    asyncio.run(main())
