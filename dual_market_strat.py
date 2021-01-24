from optibook.synchronous_client import Exchange
from strategy import Strategy
import time
import logging
logger = logging.getLogger('client')
logger.setLevel('INFO')

class DualMarketStrat(Strategy):
    def __init__(self, exchange, instruments):
        super().__init__(exchange, instruments)
        self.orders_outstanding = False
    
    def update(self):
        # Check if we have any outstanding orders; don't submit any more if so
        prev_outstanding = self.orders_outstanding
        self.orders_outstanding = False
        for i in self.instruments:
            if len(self.e.get_outstanding_orders(i)) > 0:
                self.orders_outstanding = True
        
        if prev_outstanding and not self.orders_outstanding:
            logger.info("Orders confirmed")
            self.log_positions_cash()
        
        # Look for trade differences (m1 ask < m2 bid)
        if not self.orders_outstanding:
            # logger.info("Checking for discrepancies")
            for m1, m2 in [(0,1), (1,0)]:
                books = [self.e.get_last_price_book(x) for x in self.instruments]
                if len(books[m1].asks) > 0 and len(books[m2].bids) > 0:
                    m1_id = self.instruments[m1]
                    m2_id = self.instruments[m2]
                    m1_ask = books[m1].asks[0]
                    m2_bid = books[m2].bids[0]
                    try:
                        if m1_ask.price < m2_bid.price:
                            vol = min([m1_ask.volume, m2_bid.volume])
                            self.insert_biased_order(m1_id, price=m1_ask.price, volume=vol, side='bid', order_type='limit')
                            self.insert_biased_order(m2_id, price=m2_bid.price, volume=vol, side='ask', order_type='limit')
                            logger.info(f"Can profit: buy {m1_id} at {m1_ask} and sell {m2_id} at {m2_bid} - for volume {vol}!")
    
                            self.orders_outstanding = True
                    except Exception as e:
                        print(logger.error(e))
                        continue
