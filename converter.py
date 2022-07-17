import requests


def get_coin_to_usd(coin):
    coin = coin.upper()
    data = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={coin}USDT")
    return float(data.json()["price"])


def get_currency_to_usd(currency):
    currency = currency.upper()
    data = requests.get('https://v6.exchangerate-api.com/v6/43df0b2e895ac20415a2779c/latest/USD').json()
    rate = data['conversion_rates'][currency]
    return float(rate)


# print(type(get_currency_to_usd("TJS")))
