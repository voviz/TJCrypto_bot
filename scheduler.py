from load_all import db, bot, dp
import aioschedule
import asyncio
import datetime


async def schedule_delete_orders():
    aioschedule.every(60).seconds.do(clear_orders)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def clear_orders():
    for order_id in db.get_order_ids_waiting_payment():
        unique_id = order_id[0]
        creation_date = db.get_creation_date(unique_id)
        if (datetime.datetime.now() - datetime.datetime.strptime(creation_date,
                                                                 '%Y-%m-%d %H:%M:%S')).total_seconds() >= 900:
            client_id = db.get_client_id(unique_id)

            db.increase_card_limit(db.get_chosen_card_id(client_id), db.get_sum_to_pay(client_id))
            db.expire_order(unique_id)
            await bot.send_message(client_id, text=f'Ваш заказ №{unique_id} удален, потому что он не оплачен.\n\nПосле '
                                                   f'удаления заказа реквезиты недействительны!')
            await bot.delete_message(client_id, db.get_user_message_order(unique_id))
            await bot.delete_message(client_id, db.get_user_message_card(unique_id))
            if db.get_executor(unique_id):
                await bot.edit_message_text(chat_id=db.get_executor(unique_id),
                                            message_id=db.get_admin_message_order(unique_id),
                                            text=f'Заказ {unique_id} у пользователя {client_id} не был оплачен.')

            await dp.storage.finish(chat=client_id)
