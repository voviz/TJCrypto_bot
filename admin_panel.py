from aiogram import types

import re

from config import ADMIN_IDS
from load_all import dp, bot, db
from aiogram.dispatcher import FSMContext
from converter import get_coin_to_usd


@dp.callback_query_handler(lambda call: call.from_user.id in ADMIN_IDS and call.data == 'start_execution', state="*")
async def handle_start_exec(call: types.CallbackQuery, state: FSMContext):
    client_id = get_id_from_message(call.message.text)
    unique_id = get_unique_id_from_message(call.message.text)

    # Если время заказ кончилось
    if db.get_status(unique_id) != 'payment':
        await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id,
                                    text="Заказ уже принят в обработку или время истекло.")

        await state.finish()
        return

    # Если кто-то взял этот заказ то не надо ничего делать
    if db.get_executor(unique_id):
        await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id,
                                    text="Заказ уже приня"
                                         "т в обработку. Или время истекло.")
        await state.finish()
        return

    # Взял заказ в обработку
    confirm_payment_markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('Подтвердить зачисление',
                                                                                         callback_data='confirm_payment'))
    db.set_executor(unique_id, call.from_user.id)
    message_order = await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id,
                                                text=f'Вы приняли в обработку заказ Q{unique_id} пользователя N'
                                                     f'{client_id}\n\nОжидайте '
                                                     f'пополнения: <b>{db.get_sum_to_pay(client_id)}</b>',
                                                parse_mode='html',
                                                reply_markup=confirm_payment_markup)
    db.set_admin_message_order(unique_id, message_order.message_id)
    await state.finish()


@dp.callback_query_handler(lambda call: call.from_user.id in ADMIN_IDS and call.data == 'confirm_payment', state='*')
async def handle_confirm_payment(call: types.CallbackQuery, state: FSMContext):
    client_id = get_id_from_message(call.message.text)
    unique_id = get_unique_id_from_message(call.message.text)

    await bot.delete_message(chat_id=client_id, message_id=db.get_user_message_order(unique_id))
    await bot.delete_message(chat_id=client_id, message_id=db.get_user_message_card(unique_id))
    await bot.send_message(chat_id=client_id, text=f"Внесена сумма {db.get_sum_to_pay(client_id)} сом.")
    await state.storage.reset_state(chat=client_id)

    sent_btc = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Отправил BTC", callback_data='sent_btc'))
    await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id,
                                text=f'Вы подтвердили зачисление сомоли у заказа Q{unique_id} пользователя N{client_id}.'
                                     f'\n\nОтправь {db.get_sum_btc(client_id)} BTC на кошелек:', reply_markup=sent_btc)
    message_wallet = await bot.send_message(chat_id=call.from_user.id, text=f'{db.get_wallet(client_id)}')
    message_sum = await bot.send_message(chat_id=call.from_user.id, text=f'{db.get_sum_btc(client_id)}')

    db.set_admin_messages_to_delete(unique_id, message_wallet.message_id, message_sum.message_id)

    # Изменение статуса у заказа
    db.change_status(unique_id, 'payment_approved')


@dp.callback_query_handler(lambda call: call.from_user.id in ADMIN_IDS and call.data == 'sent_btc', state='*')
async def handle_sent_btc(call: types.CallbackQuery):
    client_id = get_id_from_message(call.message.text)
    unique_id = get_unique_id_from_message(call.message.text)

    await bot.send_message(chat_id=client_id, text=f'Ваша заявка №{unique_id} исполнена!\n\nНа Ваш кошелек: <code>'
                                                   f'{db.get_active_wallet(unique_id)}</code>\n\nОтправлена сумма:'
                                                   f' {db.get_active_sum_btc(unique_id)} BTC.\n\nВсе обмены зачисляются после'
                                                   f' 1-6 подтверждений от сети, всё зависит от вашего сервиса, '
                                                   f'на котором расположен кошелёк.\n\nВремя зачисления BTC при обычной'
                                                   f' загруженности в среднем занимает <b>от 20 до 40 мин.</b>\n\n'
                                                   f'В случаях же, когда сеть перегружена транзакцими, подтверждение '
                                                   f'может занимать до нескольких часов.\n\nПроцедура подтверждения '
                                                   f'<b>НЕ ЗАВИСИТ</b> от нас и определяется исключительно скоростью'
                                                   f' обработки транзакций криптовалютными сетями.', parse_mode='html')

    await bot.delete_message(chat_id=call.from_user.id, message_id=db.get_admin_message_sum(unique_id))
    await bot.delete_message(chat_id=call.from_user.id, message_id=db.get_admin_message_wallet(unique_id))
    await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id,
                                text=f'✅Заказ Q{unique_id} выполнен!\n\nСумма {db.get_active_sum_btc(unique_id) * get}')

    db.change_status(unique_id, 'completed')


def get_id_from_message(message):
    return re.search(r'(?<=N)\d+', message).group(0)


def get_unique_id_from_message(message):
    return re.search(r'(?<=Q)\d+', message).group(0)
