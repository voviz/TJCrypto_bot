from aiogram.dispatcher.filters.state import State, StatesGroup


class TradeRequest(StatesGroup):
    EnterWallet = State()
    TradeConfirmation = State()
    Payment = State()


class CardAdd(StatesGroup):
    EnterCardName = State()
    Credentials = State()
    SetLimit = State()
    ConfirmAddCard = State()

class CardEdit(StatesGroup):
    ChangeCardName = State()
    ChangeCardLimit = State()


