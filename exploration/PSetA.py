from optibook.synchronous_client import Exchange
import logging
import time
logger = logging.getLogger('client')
logger.setLevel('ERROR')

print("Setup was successful.")

instrument_id = 'PHILIPS_A'

e = Exchange()
a = e.connect()

def get_out_of_positions():
    # Get out of all positions you are currently holding, regardless of the loss involved. That means selling whatever
    # you are long, and buying-back whatever you are short. Be sure you know what you are doing when you use this logic.
    print(e.get_positions())
    for s, p in e.get_positions().items():
        if p > 0:
            e.insert_order(s, price=1, volume=p, side='ask', order_type='ioc')
        elif p < 0:
            e.insert_order(s, price=100000, volume=-p, side='bid', order_type='ioc')  
    print(e.get_positions())

# bid, volume p, price 1 - 'I want to buy p units at price 1'
# ask, volume p, price 1 - 'I want to sell p units at price 1'

# print(e.get_trade_history(instrument_id))
#book = e.get_last_price_book(instrument_id)
#print(book.bids)
#print(book.asks)

# current positions
print(e.get_positions_and_cash())

processed_order_book = e.get_last_price_book(instrument_id)
print("bid | price | ask")
for level in processed_order_book: 
    print(f"{level.bid_volume}|{level.price_level}|{level.ask_volume}")




# e.insert_order(instrument_id, price=71.70, volume=1, side='bid', order_type='limit')
"""
# buy something
e.insert_order(instrument_id, price=70, volume=1, side='bid', order_type='limit')

print(e.get_positions_and_cash())

time.sleep(1)

# sell something
e.insert_order(instrument_id, price=71, volume=1, side='ask', order_type='limit')

print(e.get_positions_and_cash())
"""