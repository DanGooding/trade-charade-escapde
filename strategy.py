from abc import ABC, abstractmethod
from optibook.synchronous_client import Exchange
import logging
from math import log
import time
from collections import defaultdict

logger = logging.getLogger('client')
logger.setLevel('INFO')

# Your algorithm is not allowed to cross a few pre-predefined limits:
#    - Total position (positive or negative) per instrument cannot go over 500
#    - You are not allowed to have total orders outstanding for over 800 lots per instrument 
#    - You are only allowed to send 25 updates (inserts/deletes/amends) to the market per second

class Strategy(ABC):
    def __init__(self, exchange, instruments):
        self.e = exchange
        self.instruments = instruments
        self.outstanding_order_ids = defaultdict(set)  # {instrument: {order_id}}
        
    @abstractmethod
    def update(self):
        pass
    
    """
    def get_out_of_positions(self, instrument = None):
        # Get out of all positions you are currently holding, regardless of the loss involved. That means selling whatever
        # you are long, and buying-back whatever you are short. Be sure you know what you are doing when you use this logic.
        print(self.e.get_positions())
        for s, p in self.e.get_positions().items():
            if p > 0 and (instrument == None or s == instrument):
                self.e.insert_order(s, price=1, volume=p, side='ask', order_type='ioc')
            elif p < 0 and (instrument == None or s == instrument):
                self.e.insert_order(s, price=100000, volume=-p, side='bid', order_type='ioc')  
        print(self.e.get_positions())
    """
    # Intention is to quickly complete incomplete order-pairs
    def get_out_of_positions(self, target=0, instrument=None):
        # Delete all outstanding orders
        for i in self.instruments:
            outstanding = self.e.get_outstanding_orders(i)
            for o in outstanding.values():
                result = self.e.delete_order(i, order_id=o.order_id)
                print(f"Tried to delete order id {o.order_id}: {result}")

        print(f"Positions before getting out: {self.e.get_positions()}")
        bad_positions = True
        while bad_positions:
            time.sleep(1)
            bad_positions = False
            for s, p in self.e.get_positions().items():
                if instrument != None and s != instrument:
                    continue
                if abs(p) > target:
                    bad_positions = True
                    book = self.e.get_last_price_book(s)
                
                    lowest_ask = book.asks[0].price if len(book.asks) > 0 else 100000
                    highest_bid = book.bids[0].price if len(book.bids) > 0 else 1
                    price_gap = lowest_ask/highest_bid
                    
                    # Price gap of less than 1.001 is never reached as this requires ask==bid on same instrument
                    if price_gap < 1.002:
                        if p > 0:
                            # We've bought but haven't been able to sell! Try to get rid as quickly & safely as possible
                            # Prices are sane - match them using ioc
                            print(f"Getting out of position={p} by posting ioc ask price={book.bids[0].price} volume={min(abs(p), book.bids[0].volume)}")
                            self.e.insert_order(s, price=book.bids[0].price, volume=min(abs(p)-target, book.bids[0].volume), side='ask', order_type='ioc')
                        elif p < 0:
                            # We've sold but havent been able to buy! Try to get out of negative position quickly.
                            # Prices are sane - match them using ioc
                            print(f"Getting out of position={p} by posting ioc bid price={book.asks[0].price} volume={min(abs(p), book.asks[0].volume)}")
                            self.e.insert_order(s, price=book.asks[0].price, volume=min(abs(p)-target, book.asks[0].volume), side='bid', order_type='ioc')
        print(f"Positions after getting out: {self.e.get_positions()}")
    
    
    def insert_biased_order(self, instrument_id, price, volume, side, order_type='limit', position=None):
        if position is None:
            position = self.e.get_positions()[instrument_id]
        
        if abs(position) > 20:
            
            # bid higher when we need more
            # ask higher when we have lots
            bias_higher = (position < 0) == (side == 'bid')
            
            change = 0.01 * log(abs(position))
            
            price += (1 if bias_higher else -1) * change * price
        
        return self.insert_order(instrument_id, price=price, volume=volume, side=side, order_type=order_type)
    
    
    def insert_order(self, instrument_id, price, volume, side, order_type='limit'):
        order_id = self.e.insert_order(instrument_id, price=price, volume=volume, side=side, order_type=order_type)
        self.outstanding_order_ids[instrument_id].add(order_id)
        return order_id
    
    def delete_order(self, instrument_id, order_id):
        self.outstanding_order_ids[instrument_id].remove(order_id)
        return self.e.delete_order(instrument_id, order_id=order_id)
    
    def delete_orders(self, instrument_id):
        to_delete = set(self.outstanding_order_ids[instrument_id])
        for order_id in to_delete:
            self.delete_order(instrument_id, order_id)
    
    def get_outstanding_orders(self, instrument_id):
        all_orders = self.e.get_outstanding_orders(instrument_id)
        print(type(all_orders))
        self.outstanding_order_ids[instrument_id] = all_orders.keys() & self.outstanding_order_ids[instrument_id]
        return {oid: all_orders[oid] for oid in self.outstanding_order_ids[instrument_id]}
    
    # TODO: we can still see 'our' trades from other strategies, in the pricebook
    
    
    # Logging functions
    def log_new_trade_ticks(self):
        logger.info("Polling new trade ticks")
        for i in self.instruments:
            tradeticks = self.e.poll_new_trade_ticks(i)
            for t in tradeticks:
                logger.info(f"[{t.instrument_id}] price({t.price}), volume({t.volume}), aggressor_side({t.aggressor_side}), buyer({t.buyer}), seller({t.seller})")
    
    def log_positions_cash(self):
        logger.info(self.e.get_positions_and_cash())

    def log_pnl(self):
        logger.info(f"PnL {self.e.get_pnl()}")
    
    
    