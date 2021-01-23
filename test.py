
from optibook_client.synchronous_client import Exchange


import logging
logger = logging.getLogger('client')
logger.setLevel('ERROR')

print("Setup was successful.")

instrument_id = 'PHILIPS_A'

e = Exchange()
print(e)
a = e.connect()
print(a)

orders = e.get_outstanding_orders(instrument_id)
for o in orders.values():
    print(o)

print(e.is_connected())


