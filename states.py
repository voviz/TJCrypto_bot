from aiogram.dispatcher.filters.state import State, StatesGroup


class TradeRequest(StatesGroup):
    EnterWallet = State()
    TradeConfirmation = State()
    Payment = State()
