from optibook.synchronous_client import Exchange
import time
import logging
import sys

logger = logging.getLogger('client')
logger.setLevel('INFO')

class SafeExchange(Exchange):
    def __init__(self):
        super().__init__()
        
    
        
    def insert_order(self, instrument_id, *, price, volume, side, order_type = 'limit'):
        print("INSERTING")
        # Hacky way of getting around argument names needing to be the same
        a = [price, volume, side, order_type]
        super(SafeExchange, self).insert_order(instrument_id, price=a[0], volume=a[1], side=a[2], order_type=a[3])