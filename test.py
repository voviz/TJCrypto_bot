import re
import datetime
from load_all import db

def parse_message(message):
    return re.search(r'(?<=N)\d+', message).group(0)


print()
def get_date():
    offset = datetime.timedelta(hours=3)
    tz = datetime.timezone(offset)
    return datetime.datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
print(datetime.datetime.now())
print(get_date())
print(datetime.datetime.strptime(str(get_date()), '%Y-%m-%d %H:%M:%S'))
# print(db.get_orders_waiting_payment()[1][1])
# print((datetime.datetime.now() - datetime.datetime.strptime(db.get_orders_waiting_payment()[1][1], '%Y-%m-%d %H:%M:%S')).total_seconds())
# print(parse_message("Пользователь создал заявку N12415872 Ожидайте сумму 1501").group(0))


# 1000 1 389

#print(1 * 389 % 1000)
list_a = [0] * 1000


# for i in range(1, 1000):
#     encoded = i * 389 % 1000
#     decoded = encoded * 509 % 1000
#     list_a[i] = encoded
#     #print(decoded)
#
# for i in range(1, 999):
#     for j in range(i+1, 1000):
#         if list_a[i] == list_a[j]:
#             print('you dumb ass')
#             print(list_a[i], i, j)

#print("Everything is cool!")