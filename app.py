import asyncio


from aiogram import executor
from load_all import bot


async def on_shutdown(dp):
    await bot.close()


async def on_startup(func):
    asyncio.create_task(schedule_delete_orders())


if __name__ == "__main__":
    from admin_panel import dp
    from handlers import dp
    from scheduler import schedule_delete_orders

    executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown)
