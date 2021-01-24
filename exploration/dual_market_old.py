from abc import ABC, abstractmethod 
from optibook.synchronous_client import Exchange
import time
import logging
logger = logging.getLogger('client')
logger.setLevel('INFO')

class Strategy(ABC):
    def update():
        pass



class Bot:
    instruments = ["PHILIPS_A", "PHILIPS_B"]
    
    def __init__(self):
        self.e = Exchange()
        logging.info(self.e.connect())
        logging.info("Setup was successful.")

    def get_out_of_positions(self):
        # Get out of all positions you are currently holding, regardless of the loss involved. That means selling whatever
        # you are long, and buying-back whatever you are short. Be sure you know what you are doing when you use this logic.
        print(self.e.get_positions())
        for s, p in self.e.get_positions().items():
            if p > 0:
                self.e.insert_order(s, price=1, volume=p, side='ask', order_type='ioc')
            elif p < 0:
                self.e.insert_order(s, price=100000, volume=-p, side='bid', order_type='ioc')  
        print(self.e.get_positions())
    
    # Logging functions
    
    def log_new_trade_ticks(self):
        logger.info("Polling new trade ticks")
        for i in self.instruments:
            tradeticks = self.e.poll_new_trade_ticks(i)
            for t in tradeticks:
                logger.info(f"[{t.instrument_id}] price({t.price}), volume({t.volume}), aggressor_side({t.aggressor_side}), buyer({t.buyer}), seller({t.seller})")
    
    def log_positions_cash(self):
        logger.info(self.e.get_positions_and_cash())
    
    def log_all_outstanding_orders(self):
        for i in self.instruments:
            logger.info(self.e.get_outstanding_orders(i))
    
    def wait_until_orders_complete(self):
        orders_outstanding = True
        while orders_outstanding:
            orders_outstanding = False
            for i in self.instruments:
                if len(self.e.get_outstanding_orders(i)) > 0:
                    orders_outstanding = True
            self.log_all_outstanding_orders()
            #time.sleep(0.1)
    
    def mainloop(self):
        while True:
            # check for trade differences
            # m1 ask < m2 bid
            #logger.info("Checking for discrepancies:")
            books = [self.e.get_last_price_book(x) for x in self.instruments]
            for m1, m2 in [(0,1), (1,0)]:
                m1_id = self.instruments[m1]
                m2_id = self.instruments[m2]
                try:
                    m1_ask = books[m1].asks[0]
                    m2_bid = books[m2].bids[0] 
                    if m1_ask.price < m2_bid.price:
                        logger.info(f"Can profit: buy {m1_id} at {m1_ask} and sell {m2_id} at {m2_bid}")
                        self.e.insert_order(m1_id, price=m1_ask.price, volume=1, side='bid', order_type='limit')
                        self.e.insert_order(m2_id, price=m2_bid.price, volume=1, side='ask', order_type='limit')
                        self.log_all_outstanding_orders()
                        self.wait_until_orders_complete()
                        self.log_positions_cash()
                except Exception as e:
                    print(logger.error(e))
                    continue
            time.sleep(1.0/25)

if __name__ == '__main__':
    bot = Bot()
    bot.mainloop()
