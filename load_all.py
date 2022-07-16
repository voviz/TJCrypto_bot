from datetime import timedelta, timezone, datetime

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from DataBase import DataBase

import logging

from config import *


# Log initialization
logging.basicConfig(level=logging.DEBUG)

# bot initialization
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# database
db_file = 'database.db'
db = DataBase(db_file)

fee_rate = 1.3

