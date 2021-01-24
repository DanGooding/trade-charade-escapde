from optibook.synchronous_client import Exchange
import time
from enum import Enum
import logging
from strategy import Strategy
logger = logging.getLogger('client')
logger.setLevel('INFO')
import math

class DifferenceStrat(Strategy): 
    
    def __init__(self, exchange, instruments):
        super().__init__(exchange, instruments)
        self.orders_outstanding = False
        self.wait_time = time.time()
    
    
    def update(self): 
        # Check if we have any outstanding orders; don't submit any more if so
        prev_outstanding = self.orders_outstanding
        self.orders_outstanding = False
        for i in self.instruments:
            logger.info(i)
            logger.info(self.e.get_outstanding_orders(i))
            if len(self.e.get_outstanding_orders(i)) > 0:
                self.orders_outstanding = True
                
        if self.orders_outstanding and time.time() - self.wait_time >= 10.0:
            self.get_out_of_positions()
            self.orders_outstanding = False
        
        if prev_outstanding and not self.orders_outstanding:
            logger.info("Orders confirmed")
            self.log_positions_cash()
                
        
        # look at difference between ask and bid
        if not self.orders_outstanding: 
            # PHILIPS_A is more liquid, consider this? 
            m1, m2 = (0, 1)
            
            m1_id = self.instruments[0] #PHILIPS_A
            m2_id = self.instruments[1] #PHILIPS_B
            books = [self.e.get_last_price_book(x) for x in self.instruments]
            try: 
                m1_ask = books[m1].asks[0]
                m2_ask = books[m2].asks[0]
                if abs(m1_ask.price - m2_ask.price)>=0.01:
                    # m1_ask < m2_ask
                    if m1_ask.price > m2_ask.price: 
                        m1_ask, m2_ask = m2_ask, m1_ask
                        m1_id, m2_id = m2_id, m1_id
                    
                    mean_price = (m1_ask.price + m2_ask.price)/2.0
                    ask_l = mean_price - (m2_ask.price - m1_ask.price)*0.2
                    ask_h = mean_price + (m2_ask.price - m1_ask.price)*0.2
                    
                    vol = min(m1_ask.volume, m2_ask.volume)
                    
                    self.e.insert_order(m1_id, price=ask_l, volume=1, side='bid', order_type='limit')
                    self.e.insert_order(m2_id, price=ask_h, volume=1, side='ask', order_type='limit')
                    
                    logger.info(f"Can profit: buy {m1_id} at {ask_l} and sell {m2_id} at {ask_h} - choosing min vol {vol}! ASK DIFFERENCE")
                
            except Exception as e:
                print(logger.error(e))
                
            try: 
                m1_bid = books[m1].bids[0]
                m2_bid = books[m2].asks[0]
                
                if abs(m1_bid.price - m2_bid.price)>=0.01:
                    # m1_bid < m2_bid
                    if m1_bid.price > m2_bid.price: 
                        m1_bid, m2_bid = m2_bid, m1_bid
                        m1_id, m2_id = m2_id, m1_id
                    
                    mean_price = (m1_bid.price + m2_bid.price)/2.0
                    bid_l = mean_price - (m2_bid.price - m1_bid.price)*0.45
                    bid_h = mean_price + (m2_bid.price - m1_bid.price)*0.45
                    
                    vol = min(m1_bid.volume, m2_bid.volume)
                    
                    self.e.insert_order(m1_id, price=bid_l, volume=1, side='bid', order_type='limit')
                    self.e.insert_order(m2_id, price=bid_h, volume=1, side='ask', order_type='limit')
                    
                    logger.info(f"Can profit: buy {m1_id} at {bid_l} and sell {m2_id} at {bid_h} - choosing min vol {vol}! BID DIFFERENCE")
                
            except Exception as e:
                print(logger.error(e))
            self.orders_outstanding = True
            self.wait_time = time.time()