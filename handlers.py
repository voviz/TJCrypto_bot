from aiogram import types
from aiogram.dispatcher import FSMContext

from load_all import dp, bot, db
from states import TradeRequest
from config import ADMIN_IDS

from converter import get_coin_to_usd, get_currency_to_usd

main_menu_text = "<b>Бот обменник!</b>\n\nТут ты можешь обменять свои <b>TZS</b> на " \
                 "<b>BTC</b>.\n\nЖми кнопку \"<b>Купить Биткоин</b>\" или просто напиши " \
                 "сумму в <b>TZS</b> или <b>BTC</b>.\n\n<b>Пример:</b> 0.001 или 0,001 " \
                 "или 2070."
buy_btc_text = "Укажите сумму в BTC или же TZS\n\n<code>Пример: 0.001 или 0,001 или 2070</code>"

cancel_button = types.InlineKeyboardButton(text="🚫Отмена", callback_data="cancel")
confirm_button = types.InlineKeyboardButton(text="Согласен✅", callback_data="confirm_trade")
buy_btc_btn = types.InlineKeyboardButton(text="Купить Биткоин", callback_data="buy_btc")
main_menu_markup = types.InlineKeyboardMarkup(inline_keyboard=[[buy_btc_btn]])
confirm_trade_markup = types.InlineKeyboardMarkup(inline_keyboard=[[cancel_button, confirm_button]])

# mega_cancel = types.InlineKeyboardMarkup().add(
#     types.InlineKeyboardButton(text='🚫Отменить заказ', callback_data='mega_cancel'))

start_execution = types.InlineKeyboardMarkup().add(
    types.InlineKeyboardButton(text='Начать выполнение', callback_data='start_execution')
)


# Обработка Старт
@dp.message_handler(commands=['start'])
async def handle_start(message: types.Message):
    await bot.send_message(message.from_user.id, main_menu_text, parse_mode='html', reply_markup=main_menu_markup)
    if not db.user_exists(message.from_user.id):
        db.add_user(message.from_user.id, message.from_user.first_name, message.from_user.last_name,
                    message.from_user.username, message.chat.id)


@dp.callback_query_handler(lambda call: call.data == 'pressed_wallet', state=TradeRequest.EnterWallet)
async def handle_wallet(call: types.CallbackQuery, state: FSMContext):
    if call.data == 'pressed_wallet':
        # Введен кошелек
        await TradeRequest.TradeConfirmation.set()

        sum_to_pay = get_sum_to_pay(call.from_user.id)

        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text=f"Время на оплату заказа <b>15 минут!</b>\n\nИтого к оплате "
                                         f"<b>{sum_to_pay} сом.</b>\n\nПосле оплаты средства"
                                         f" будут переведены на кошелек: <code>{db.get_wallet(call.from_user.id)}"
                                         f"</code>\n\nЕсли у вас есть вопрос, или возникли проблемы с оплатой, "
                                         f"пишите поддержке: @voviz\n\nВы согласны на обмен?",
                                    parse_mode='html', reply_markup=confirm_trade_markup)


@dp.callback_query_handler(lambda callback_query: True, state=TradeRequest.TradeConfirmation)
async def handle_confirm_cancel_trade(call: types.CallbackQuery, state: FSMContext):
    # Заявка подтверждена
    if call.data == 'confirm_trade':
        await TradeRequest.Payment.set()

        sum_to_pay = get_sum_to_pay(call.from_user.id)
        db.set_sum_to_pay(call.from_user.id, sum_to_pay)

        unique_id = db.create_request(call.from_user.id, db.get_wallet(call.from_user.id), db.get_sum_btc(call.from_user.id))

        message_to_edit = await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                                      text=f"Время на оплату Вашего заказа №{unique_id} <b>15 минут!</b>\n\nДля зачисления "
                                                           f"{db.get_sum_btc(call.from_user.id)} BTC, Вам надо оплатить <b>{sum_to_pay}</b> сом."
                                                           f"\n\nПромокод: не используется\n\nИтого к оплате: <b>{sum_to_pay}</b> сом."
                                                           f"\n\nПосле оплаты средства будут переведены на кошелек: <code>{db.get_wallet(call.from_user.id)}"
                                                           f"</code>\n\nЕсли у Вас есть вопрос, или возникли проблемы с оплатой, пишите поддержке"
                                                           f" @Voviz\n\nРеквизиты для оплаты:", parse_mode='html')
        message_to_delete = await bot.send_message(call.message.chat.id, text="2202202171329380")

        db.set_messages_to_delete(unique_id, message_to_edit.message_id, message_to_delete.message_id)

        # Создание и отправка текста операторам
        text = f"Пользователь N{call.from_user.id} создал заявку Q{unique_id}.\n\nОжидайте платеж <b>{sum_to_pay}</b>"

        for chat_id in ADMIN_IDS:
            await bot.send_message(chat_id, text=text, reply_markup=start_execution, parse_mode='html')


# Обработка нажатий кнопки под сообщениями
@dp.callback_query_handler(lambda callback_query: True, state='*')
async def callback_handler(call: types.CallbackQuery, state: FSMContext):
    # Если мы в процессе покупки то нельзя ничего
    current_state = await state.get_state()
    if current_state == TradeRequest.Payment.state:
        # if call.data == 'mega_cancel':
        #     await state.finish()
        # if not call.data == "cancel":
        await bot.answer_callback_query(call.id, text="Для создания новой заявки оплатите предыдущую.", show_alert=True)
        return
        # await bot.send_message(call.message.chat.id, text="Вы уверены, что хотите отменить Ваш заказ?\n\nЕсли у Вас "
        #                                                   "есть вопрос "
        #                                                   "или возникли проблемы с оплатой, пишите поддержке @Voviz\n\n"
        #                                                   "Если Вы отправили деньги и отменили заказ, средства <b>не "
        #                                                   "будут возвращены.</b>",
        #                        parse_mode='html', reply_markup=mega_cancel)

    # Обработка кнопки купить бтс в главном
    if call.data == "buy_btc":
        await bot.send_message(chat_id=call.message.chat.id, text=buy_btc_text, parse_mode='html')

    # Отмена текущего действия
    if call.data == "cancel":
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text="Действие отменено.",
                                    reply_markup=main_menu_markup)
        await state.finish()

    # Нажатие на банк
    if call.data == 'sber':
        answer = "<b>Скопируйте и отправьте боту свой кошелек BTC.</b> Бот сохранит его и при следующем обмене предложит" \
                 " в виде <b>удобной кнопки снизу:</b>"

        # Создание клавиатуры с сохраненным кошельком
        wallet_markup = types.InlineKeyboardMarkup(row_width=2)
        if db.get_wallet(call.from_user.id):
            btn = types.InlineKeyboardButton(text=db.get_wallet(call.from_user.id), callback_data="pressed_wallet")
            wallet_markup.add(btn)
        wallet_markup.add(cancel_button)

        await TradeRequest.EnterWallet.set()

        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=answer,
                                    parse_mode='html', reply_markup=wallet_markup)


@dp.message_handler(state=TradeRequest.EnterWallet)
async def handle_wallet(message: types.Message):
    if not check_btc_wallet(message.text):
        pass

    # Введен кошелек
    await TradeRequest.TradeConfirmation.set()
    db.change_wallet(message.from_user.id, message.text)

    sum_to_pay = get_sum_to_pay(message.from_user.id)

    await bot.send_message(message.from_user.id, text=f"Время на оплату заказа <b>15 минут!</b>\n\nИтого к оплате "
                                                      f"<b>{sum_to_pay} сом.</b>\n\nПосле оплаты средства"
                                                      f" будут переведены на кошелек: <code>{db.get_wallet(message.from_user.id)}"
                                                      f"</code>\n\nЕсли у вас есть вопрос, или возникли проблемы с оплатой, "
                                                      f"пишите поддержке: @voviz\n\nВы согласны на обмен?",
                           parse_mode='html', reply_markup=confirm_trade_markup)

    # # Отмена текущего действия
    # if call.data == "cancel":
    #     await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
    #                                 text="Действие отменено.",
    #                                 reply_markup=main_menu_markup)
    #     await state.finish()


# Обработка сообщений в момент активного заказа
@dp.message_handler(state=TradeRequest.Payment)
async def handle_active_order(message: types.Message):
    await bot.send_message(message.from_user.id,
                           text='Для создания новой заявки сначала оплатите или отмениты предыдущий заказ.\n\n'
                                'Если у Вас есть вопрос или возникли проблемы с оплатой, пишите '
                                'поддержке @Voviz')


# Обработка введеной суммы для покупки
@dp.message_handler()
async def handle_buy_amount(message: types.Message):
    btc_to_usd_rate = get_coin_to_usd('btc')
    usd_to_tjs_rate = get_currency_to_usd('TJS')
    btc_amount = get_amount_in_btc(message.text, btc_to_usd_rate, usd_to_tjs_rate)
    float_btc = float(btc_amount)

    # Проверка на слишком маленькие и большие суммы
    if float_btc > 0.09 or float_btc < 0.0001:
        await bot.send_message(message.from_user.id, f"Не верная сумма обмена - {btc_amount}!\n\nМинимальная сумма BTC"
                                                     f" 0.0001, а максимальная 0.09")
        await bot.send_message(message.from_user.id, buy_btc_text, parse_mode='html')
        return

    # Добавление в бд суммы обмена
    db.change_sum_btc(message.from_user.id, float_btc)

    # Сумма к оплате
    to_pay = get_sum_to_pay(message.from_user.id)
    to_pay = to_pay[:-3] + ' ' + to_pay[-3:]

    # Создание клавы с выбором где купить
    payment_option_markup = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=f'СБЕРБАНК ЕПТА ({to_pay} сом.)', callback_data='sber')],
            [cancel_button]
        ]
    )

    await bot.send_message(message.from_user.id, f"Средний рыночный курс BTC ${btc_to_usd_rate}, $ - "
                                                 f"{usd_to_tjs_rate:.1f} сом.\n\nВы получите <b>{btc_amount} BTC.</b>"
                                                 f"\n\nДля продолжения выберите <b>Способ оплаты:</b>",
                           parse_mode='html',
                           reply_markup=payment_option_markup)


def get_amount_in_btc(amount, btc_rate, currency_rate):
    try:  # Возможно введено сомоли в Int
        amount = int(amount)
        return f"{amount / currency_rate / btc_rate:.8f}"
    except ValueError:
        try:  # Возможно введено количество бтс через точку
            amount = float(amount)
            return f"{amount:.8f}"
        except ValueError:
            try:  # Возможно введено количество бтс через запятую
                amount = float(amount.replace(',', '.', 1))
                return f"{amount:.8f}"
            except ValueError:  # Опять насрали
                return "0.00000000"


def get_sum_to_pay(user_id):
    fee_rate = 1.3
    sum_to_pay = f"{db.get_sum_btc(user_id) * get_coin_to_usd('btc') * get_currency_to_usd('tjs') * fee_rate:.0f}"
    return sum_to_pay


def check_btc_wallet(text):
    return True
