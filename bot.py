import asyncio
import logging
from aiogram import Bot, Dispatcher

import config
import database
from handlers import router

logging.basicConfig(level=logging.INFO)

async def main():
    await database.init_db()
    
    bot = Bot(token=config.BOT_TOKEN)
    
    dp = Dispatcher()
    
    dp.include_router(router)
    
    print("бот успешно запущен!")
    
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("бот остановлен вручную.")
