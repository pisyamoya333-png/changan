import asyncio
from aiogram import Dispatcher

from config import bot, logger
from app.handlers import router_verification, router, router_admin
from app.database.models import async_main


dp = Dispatcher()


async def main():
    try:
        logger.error("Бот запускается...")
        await async_main()
        dp.include_router(router_verification)
        dp.include_router(router)
        dp.include_router(router_admin)
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Произошла ошибка: {e}", exc_info=True)
    finally:
        logger.error("Бот завершил работу.")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.error("Бот остановлен вручную (KeyboardInterrupt).")
        print('Exit')