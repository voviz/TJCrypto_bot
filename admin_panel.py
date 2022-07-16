from aiogram import types

import re

from config import ADMIN_IDS
from load_all import dp, bot, db, fee_rate
from aiogram.dispatcher import FSMContext
from converter import get_coin_to_usd, get_currency_to_usd
from states import CardAdd, CardEdit

cancel_card_add_btn = types.InlineKeyboardButton(text='🚫Отменить добавление карты', callback_data='cancel_add_button')
cancel_card_add_markup = types.InlineKeyboardMarkup().add(cancel_card_add_btn)


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
                                                     f'пополнения: <b>{db.get_sum_to_pay(client_id)}</b>\n\nНа карту:'
                                                     f' {db.get}',
                                                parse_mode='html',
                                                reply_markup=confirm_payment_markup)
    db.set_admin_message_order(unique_id, message_order.message_id)
    await state.finish()


# Подтверждение оплаты заказа
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


# Подтверждение отправки битка
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
                                text=f'✅Заказ Q{unique_id} выполнен!\n\nСумма '
                                     f'{float(db.get_active_sum_btc(unique_id)) * get_coin_to_usd("btc") * get_currency_to_usd("tjs") * fee_rate:.0f} сом.')

    db.change_status(unique_id, 'completed')


# Обработка добавления карты
@dp.message_handler(lambda message: message.from_user.id in ADMIN_IDS, commands=['add_card', 'cards'])
async def handle_add_card(message: types.Message, state: FSMContext):
    # Добавление новой карты
    if message.text == '/add_card':
        edit_message = await bot.send_message(message.from_user.id, text='Отправь боту название карты',
                                              reply_markup=cancel_card_add_markup)
        await CardAdd.EnterCardName.set()
        await state.update_data(edit_message_id=edit_message.message_id, edit_message_text=edit_message.text)

    # Список карт
    if message.text == '/cards':
        cards = db.get_cards()
        cards_list_markup = types.InlineKeyboardMarkup()
        for card in cards:
            cards_list_markup.add(
                types.InlineKeyboardButton(text=card[0] + f' ({card[2]} сом.)', callback_data=card[1] + 'C'))

        await bot.send_message(message.from_user.id, text=f'Список карт', reply_markup=cards_list_markup)


# Нажатие на кнопку карты для ее изменения
@dp.callback_query_handler(lambda call: call.from_user.id in ADMIN_IDS and call.data in [card[1] + 'C' for card in db.get_cards()])
async def handle_card_edit(call: types.callback_query):
    cards = db.get_cards()
    for card in cards:
        if card[1] + 'C' == call.data:
            card_number = db.get_card_number(card[1])
            change_card_markup = types.InlineKeyboardMarkup() \
                .add(types.InlineKeyboardButton(text='Изменить название', callback_data='change_card_name')) \
                .add(types.InlineKeyboardButton(text='Изменить лимит переводов', callback_data='change_card_limit')) \
                .add(types.InlineKeyboardButton(text='🗑Удалить карту', callback_data='delete_card'))

            await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id,
                                        text=f'Карта {card[1]}\n\nНазвание: {card[0]}\n\nРеквизиты: {card_number}'
                                             f'\n\nЛимит переводов: {card[2]} сом.', reply_markup=change_card_markup)


# Изменение карты
@dp.callback_query_handler(lambda call: call.from_user.id in ADMIN_IDS and call.data in ['change_card_name',
                                                                                         'change_card_limit',
                                                                                         'delete_card',
                                                                                         'confirm_delete',
                                                                                         'cancel_delete'])
async def edit_card(call: types.callback_query, state: FSMContext):
    card_id = get_card_id_from_message(call.message.text)
    card_number = db.get_card_number(card_id)
    if call.data == 'change_card_name':
        await bot.send_message(chat_id=call.from_user.id, text=f'Отправь новое название для карты {card_number}')
        await CardEdit.ChangeCardName.set()
        await state.update_data(card_id=card_id)

    if call.data == 'change_card_limit':
        await bot.send_message(call.from_user.id, text=f'Отправь новый лимит для карты {card_number}')
        await CardEdit.ChangeCardLimit.set()
        await state.update_data(card_id=card_id)


    if call.data == 'delete_card':
        confirm_delete_markup = types.InlineKeyboardMarkup()\
            .add(types.InlineKeyboardButton(text='🗑Подтвердить удаление', callback_data='confirm_delete'))\
            .add(types.InlineKeyboardButton(text='🚫Отменить удаление', callback_data='cancel_delete'))
        await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id,
                                    text=f'Карта {card_id}\n\nХочешь удалить карту {card_number} ?',
                                    reply_markup=confirm_delete_markup)

    if call.data == 'confirm_delete':
        db.delete_card(card_id)
        await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id,
                              text=f'Карта {card_number} удалена!')

    if call.data == 'cancel_delete':
        await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id,
                              text=f'Действие отменено.')


# Изменение названия карты
@dp.message_handler(lambda message: message.from_user.id in ADMIN_IDS, state=CardEdit.ChangeCardName)
async def handle_card_name(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    card_id = user_data['card_id']
    db.change_card_name(card_id, message.text)
    card_number = db.get_card_number(card_id)
    await bot.send_message(message.from_user.id, f'Название карты {card_number} изменено на\n\n{message.text}')
    await state.finish()


# Изменение лимита
@dp.message_handler(lambda message: message.from_user.id in ADMIN_IDS, state=CardEdit.ChangeCardLimit)
async def handle_card_limit(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    card_id = user_data['card_id']
    try:
        limit = int(message.text)
    except ValueError:
        await bot.send_message(message.from_user.id, f'{message.text} не является числом!')
        return
    db.change_card_limit(card_id, limit)
    card_number = db.get_card_number(card_id)
    await bot.send_message(message.from_user.id, f'Лимит переводов карты {card_number} изменен на\n\n{limit} сом.')
    await state.finish()

# Обработка названия карты при добавлении
@dp.message_handler(lambda message: message.from_user.id in ADMIN_IDS, state=CardAdd.EnterCardName)
async def handle_card_name(message: types.Message, state: FSMContext):
    await state.update_data(card_name=message.text.upper())

    user_data = await state.get_data()
    edit_message_id = user_data['edit_message_id']
    edit_message_text = user_data['edit_message_text']
    await bot.edit_message_text(chat_id=message.from_user.id, message_id=edit_message_id, text=edit_message_text)
    edit_message = await bot.send_message(message.from_user.id,
                                          text=f'Название {message.text} сохранено.\n\nВведи номер'
                                               f' карты без пробелов.', reply_markup=cancel_card_add_markup)

    await CardAdd.Credentials.set()
    await state.update_data(edit_message_id=edit_message.message_id, edit_message_text=edit_message.text)


# Обработка номера карты
@dp.message_handler(lambda message: message.from_user.id in ADMIN_IDS, state=CardAdd.Credentials)
async def handle_credentials(message: types.Message, state: FSMContext):
    try:
        int(message.text)
    except ValueError:
        await bot.send_message(message.from_user.id, f'{message.text} не является числом!')
        return
    if len(message.text) != 16:
        await bot.send_message(message.from_user.id, text='Карта состоит не из 16 чисел')
        return
    await state.update_data(card_number=message.text)
    user_data = await state.get_data()
    edit_message_id = user_data['edit_message_id']
    edit_message_text = user_data['edit_message_text']
    await bot.edit_message_text(chat_id=message.from_user.id, message_id=edit_message_id, text=edit_message_text)
    edit_message = await bot.send_message(message.from_user.id,
                                          text=f'Номер {message.text} сохранен.\n\nВведи лимит переводов на карту'
                                               f'(в сомоли).', reply_markup=cancel_card_add_markup)

    await CardAdd.SetLimit.set()
    await state.update_data(edit_message_id=edit_message.message_id, edit_message_text=edit_message.text)


# Обработка установки лимита
@dp.message_handler(lambda message: message.from_user.id in ADMIN_IDS, state=CardAdd.SetLimit)
async def handle_set_limit(message: types.Message, state: FSMContext):
    try:
        limit = int(message.text)
    except ValueError:
        await bot.send_message(message.from_user.id, f'{message.text} не является числом!')
        return
    await state.update_data(card_limit=limit)

    user_data = await state.get_data()
    card_name = user_data['card_name']
    card_number = user_data['card_number']
    edit_message_id = user_data['edit_message_id']
    edit_message_text = user_data['edit_message_text']

    await bot.edit_message_text(chat_id=message.from_user.id, message_id=edit_message_id, text=edit_message_text)
    confirm_add_card_markup = types.InlineKeyboardMarkup() \
        .add(types.InlineKeyboardButton(text="✅Добавить", callback_data='confirm_add_card')) \
        .add(cancel_card_add_btn)
    edit_message = await bot.send_message(message.from_user.id,
                                          text=f'Добавить карту: {card_name}\n\nНомер: {card_number}\n\nЛимит '
                                               f'переводов: {limit}', reply_markup=confirm_add_card_markup)

    await CardAdd.ConfirmAddCard.set()
    await state.update_data(edit_message_id=edit_message.message_id, edit_message_text=edit_message.text)


# Обработка подтверждения добавления карты
@dp.callback_query_handler(lambda call: call.from_user.id in ADMIN_IDS and call.data == 'confirm_add_card',
                           state=CardAdd.ConfirmAddCard)
async def handle_confirm_card_add(call: types.callback_query, state: FSMContext):
    user_data = await state.get_data()
    card_name = user_data['card_name']
    card_number = user_data['card_number']
    card_limit = user_data['card_limit']
    edit_message_id = user_data['edit_message_id']
    edit_message_text = user_data['edit_message_text']
    db.add_card(card_number, card_limit, card_name)
    await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id,
                                text=f'Карта {card_name} добавлена!\n\nНомер: {card_number}\n\nЛимит переводов:'
                                     f' {card_limit}')
    await state.finish()


# Отмена добавления карты
@dp.callback_query_handler(lambda call: call.from_user.id in ADMIN_IDS and call.data == 'cancel_add_button',
                           state=[CardAdd.ConfirmAddCard, CardAdd.SetLimit, CardAdd.Credentials, CardAdd.EnterCardName])
async def handle_cancel_card_add(call: types.callback_query, state: FSMContext):
    await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id,
                                text=f'Добавление карты прекращено.')
    await state.finish()


def get_id_from_message(message):
    return re.search(r'(?<=N)\d+', message).group(0)


def get_unique_id_from_message(message):
    return re.search(r'(?<=Q)\d+', message).group(0)


def get_card_id_from_message(message):
    return re.search(r'(?<=Карта )\w+-\d+', message).group(0)