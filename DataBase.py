import sqlite3
from datetime import datetime, timedelta, timezone
from random import randint


class DataBase:

    def __init__(self, database_file):
        """Подключение к БД и сохранение курсора"""
        self.connection = sqlite3.connect(database_file)
        self.cursor = self.connection.cursor()

    def user_exists(self, user_id):
        """Проверка есть ли пользователь в базе"""
        with self.connection:
            self.cursor.execute("SELECT * FROM usersInfo WHERE user_id = (?)", (user_id,))
            return bool(self.cursor.fetchall())

    def add_user(self, user_id, first_name, last_name, username, chat_id):
        """Добавление нового пользователя"""
        self.cursor.execute(
            """INSERT INTO usersInfo (user_id, first_name, last_name, username, chat_id) VALUES (?, ?, ?, ?, ?)""",
            (user_id, first_name, last_name, username, chat_id))
        self.cursor.execute("""INSERT INTO payment_info (user_id) VALUES (?)""", (user_id,))
        return self.connection.commit()

    def set_sum_to_pay(self, user_id, sum_to_pay):
        """Задание суммы в сомоли для платежа"""
        self.cursor.execute("""UPDATE payment_info SET sum_to_pay = ? WHERE user_id = ?""", (sum_to_pay, user_id))
        return self.connection.commit()

    def get_sum_to_pay(self, user_id):
        """Получение суммы платежа из БД"""
        return self.cursor.execute("""SELECT sum_to_pay from payment_info WHERE user_id = ?""", (user_id,)).fetchone()[
            0]

    def set_chosen_card_id(self, user_id, chosen_card_id):
        """Установка выбранной карты"""
        self.cursor.execute("""UPDATE payment_info SET chosen_card_id = ? WHERE user_id = ?""",
                            (chosen_card_id, user_id))
        return self.connection.commit()

    def get_chosen_card_id(self, user_id):
        """Получение выбранной карты"""
        return \
        self.cursor.execute("""SELECT chosen_card_id FROM payment_info WHERE user_id = ?""", (user_id,)).fetchone()[0]

    def change_sum_btc(self, user_id, sum_btc):
        """Изменения количества бтс для покупки"""
        self.cursor.execute("UPDATE payment_info SET sum_to_pay_btc = ? WHERE user_id = ?", (sum_btc, user_id))
        return self.connection.commit()

    def get_sum_btc(self, user_id):
        """Получение суммы бтс для покупки"""
        sum_btc = \
            self.cursor.execute("""SELECT sum_to_pay_btc from payment_info WHERE user_id = (?)""",
                                (user_id,)).fetchone()[0]
        return sum_btc

    def change_wallet(self, user_id, wallet):
        """Изменения сохраненного кошелька"""
        self.cursor.execute("UPDATE payment_info SET saved_wallet = ? WHERE user_id = ?", (wallet, user_id))
        return self.connection.commit()

    def get_wallet(self, user_id):
        """Получение сохраненного кошелька"""
        wallet = self.cursor.execute("""SELECT saved_wallet FROM payment_info WHERE user_id = (?)""",
                                     (user_id,)).fetchone()[0]
        return wallet

    def create_request(self, user_id, wallet, sum_btc, card_id):
        """Создание заявки"""
        self.cursor.execute(
            "INSERT INTO active_requests (client_id, wallet, sum_btc, creation_time, card_id) VALUES (?, ?, ?, ?, ?)",
            (user_id, wallet, sum_btc, self.get_date(), card_id))
        self.connection.commit()
        pr_id = self.cursor.execute("SELECT pr_id FROM active_requests WHERE client_id = (?)",
                                    (user_id,)).fetchall()[-1][0]
        unique_id = self.generate_unique_id(pr_id)
        self.cursor.execute("""UPDATE active_requests SET unique_id = ? WHERE pr_id = ?""", (unique_id, pr_id))
        self.connection.commit()
        return unique_id

    def get_active_card_id(self, user_id, wallet):
        pass


    def get_order_ids_waiting_payment(self):
        """Получение всех неоплаченных заказов"""
        orders = self.cursor.execute("""SELECT unique_id FROM active_requests WHERE status = ?""",
                                     ('payment',)).fetchall()
        return orders

    def get_client_id(self, unique_id):
        """Получение айди пользователя"""
        client_id = self.cursor.execute("""SELECT client_id FROM active_requests WHERE unique_id = ?""",
                                        (unique_id,)).fetchone()[0]
        return client_id

    def get_creation_date(self, unique_id):
        """Получение даты создания заказа"""
        creation_date = self.cursor.execute("""SELECT creation_time FROM active_requests WHERE unique_id = ?""",
                                            (unique_id,)).fetchone()[0]
        return creation_date

    def get_user_message_order(self, unique_id):
        """Получение номера сообщения с заказом для удаления"""
        message_order = self.cursor.execute("""SELECT user_message_order FROM messages_to_delete WHERE unique_id = ?""",
                                            (unique_id,)).fetchone()[0]
        return message_order

    def get_user_message_card(self, unique_id):
        """Получение номера сообщения с картой для удаления"""
        message_card = self.cursor.execute("""SELECT user_message_card FROM messages_to_delete WHERE unique_id = ?""",
                                           (unique_id,)).fetchone()[0]
        return message_card

    def get_active_sum_btc(self, unique_id):
        """Получение суммы бтс из активного ордера"""
        sum_btc = self.cursor.execute("""SELECT sum_btc FROM active_requests WHERE unique_id = ?""",
                                      (unique_id,)).fetchone()[0]
        return sum_btc

    def get_active_wallet(self, unique_id):
        """Получение кошелька из активного ордера"""
        wallet = self.cursor.execute("""SELECT wallet FROM active_requests WHERE unique_id = ?""",
                                     (unique_id,)).fetchone()[0]
        return wallet

    def set_messages_to_delete(self, unique_id, message_order, message_card):
        """Задание сообщений которые нужно изменить"""
        self.cursor.execute("""INSERT INTO messages_to_delete (unique_id, user_message_order, user_message_card)
         VALUES (?, ?, ?) """, (unique_id, message_order, message_card))
        return self.connection.commit()

    def set_admin_message_order(self, unique_id, admin_message_order):
        """Установка номера сообщения админа с заказом"""
        self.cursor.execute("""UPDATE messages_to_delete SET admin_message_order = ? WHERE unique_id = ?""",
                            (admin_message_order, unique_id))
        return self.connection.commit()

    def get_admin_message_order(self, unique_id):
        """Получение номера сообщения админа с заказом"""
        return self.cursor.execute("""SELECT admin_message_order FROM messages_to_delete WHERE unique_id = ?""",
                                   (unique_id,)).fetchone()[0]

    def set_admin_messages_to_delete(self, unique_id, admin_message_wallet, admin_message_sum):
        """Установка номеров сообщений админа кошелька и суммы для дальнейшего удаления"""
        self.cursor.execute("""UPDATE messages_to_delete SET admin_message_wallet = ?, admin_message_sum = ? WHERE 
        unique_id = ?""", (admin_message_wallet, admin_message_sum, unique_id))

    def get_admin_message_wallet(self, unique_id):
        """Получение номера сообщения админа с кошельком"""
        message = self.cursor.execute("""SELECT admin_message_wallet FROM messages_to_delete WHERE unique_id = ?""",
                                      (unique_id,)).fetchone()[0]
        return message

    def get_admin_message_sum(self, unique_id):
        """Получение номера сообщения админа с суммой в бтс"""
        return self.cursor.execute("""SELECT admin_message_sum FROM messages_to_delete WHERE unique_id = ?""",
                                   (unique_id,)).fetchone()[0]

    def get_executor(self, unique_id):
        """Получение исполнителя"""
        try:
            executor = self.cursor.execute("""SELECT executor FROM active_requests WHERE unique_id = (?)""",
                                           (unique_id,)).fetchone()[0]
        except TypeError:
            return False
        return executor

    def set_executor(self, unique_id, executor_id):
        """Задание исполнителя к заказу"""
        self.cursor.execute("""UPDATE active_requests SET executor = (?) WHERE unique_id = (?)""",
                            (executor_id, unique_id))
        return self.connection.commit()

    def get_status(self, unique_id):
        """Получение статуса заказа"""
        status = self.cursor.execute("""SELECT status FROM active_requests WHERE unique_id = ?""",
                                     (unique_id,)).fetchone()[0]
        return status

    def expire_order(self, unique_id):
        """Заказ просрочился"""
        self.cursor.execute("""UPDATE active_requests SET status = ? WHERE unique_id = ?""", ('expired', unique_id))
        return self.connection.commit()

    def change_status(self, unique_id, status):
        """Изменения статуса"""
        self.cursor.execute("""UPDATE active_requests SET status = (?) WHERE unique_id = (?)""",
                            (status, unique_id))
        return self.connection.commit()

    def add_card(self, card_number, card_limit, card_name):
        """Добавление новой карты"""
        self.cursor.execute("""INSERT INTO cards (card_number, card_limit, card_name) VALUES (?, ?, ?)""",
                            (card_number, card_limit, card_name))
        self.connection.commit()
        pr_id = self.cursor.execute("""SELECT pr_id FROM cards WHERE card_name = ?""", (card_name,)).fetchall()[-1][0]
        card_id = self.generate_card_unique_id(pr_id)
        self.cursor.execute("""UPDATE cards SET card_id = ? WHERE pr_id = ?""", (card_id, pr_id))
        return self.connection.commit()

    def get_cards(self):
        """Получение списка карт, подходящих под размер платежа"""
        cards_list = self.cursor.execute("""SELECT card_name, card_limit, card_id FROM cards""").fetchall()
        cards_result = []
        for card in cards_list:
            # Добавление в результат названия карты и её айди
            cards_result.append((card[0], card[2], card[1]))  # [0]-название [1]-card_id [2]-card limit

        return cards_result

    def decrease_card_limit(self, card_id, decrease_sum):
        """Уменьшение лимита переводов на карту после перевода"""
        return self.cursor.execute("""UPDATE cards SET card_limit = card_limit - ? WHERE card_id = ?""",
                            (decrease_sum, card_id))

    def increase_card_limit(self, card_id, increase_sum):
        """Увеличение лимита переводов на карту"""
        return self.cursor.execute("""UPDATE cards SET card_limit = card_limit + ? WHERE card_id = ?""",
                                   (increase_sum, card_id))

    def get_card_number(self, card_id):
        """Получение реквизитов карты"""
        return self.cursor.execute("""SELECT card_number FROM cards WHERE card_id = ?""", (card_id,)).fetchone()[0]

    def delete_card(self, card_id):
        """Удаление карты"""
        self.cursor.execute("""DELETE FROM cards WHERE card_id = ?""", (card_id,))
        return self.connection.commit()

    def change_card_name(self, card_id, new_name):
        """Изменение названия карты"""
        self.cursor.execute("""UPDATE cards SET card_name = ? WHERE card_id = ?""", (new_name, card_id))
        return self.connection.commit()

    def change_card_limit(self, card_id, new_limit):
        """Изменение лимита карты"""
        self.cursor.execute("""UPDATE cards SET card_limit = ?  WHERE  card_id = ?""", (new_limit, card_id))
        return self.connection.commit()

    # Генерация случайного уникального номера
    def generate_unique_id(self, pr_id):
        modulo = 100000000
        x = 34637019
        # inverso_modulo = 75114579
        return x * pr_id % modulo

    def get_date(self):
        offset = timedelta(hours=3)
        tz = timezone(offset)
        return datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

    def generate_card_unique_id(self, num):
        alphabet = 'qwErVtSLGAIplaznmKyuiHdfROFJoCQXZgUTbcvM0DPksjeYBxNWh'
        length_alphabet = len(alphabet)
        hashh = ''
        while num > 0:
            hashh += alphabet[num % length_alphabet]
            num = num // length_alphabet

        return hashh + '-' + str(randint(0, 100))
# db_file = 'database.db'
# db = DataBase(db_file)
# print(db.get_orders_waiting_payment())
