from optibook.synchronous_client import Exchange
import time
from enum import Enum
import logging
from strategy import Strategy
logger = logging.getLogger('client')
logger.setLevel('INFO')

class State(Enum):
    CHECK_MARKETS = 0
    WAIT_FOR_ORDER_COMPLETE = 1
    UNFULFILLED_ORDER_DELAY = 2

class QuoteStrat(Strategy):
    def __init__(self, exchange, instruments):
        super().__init__(exchange, instruments)
        self.state = State.CHECK_MARKETS
        self.changed_at = time.time()
        self.orders = {}
        self.positions = [0 for _ in range(len(instruments))]
    
    def orders_complete(self):
        outstanding = {}
        for i in self.instruments:
            for order in self.e.get_outstanding_orders(i):
                if order in self.orders:
                    outstanding[order]=self.orders[order]
        self.orders = outstanding
        return len(outstanding)==0
    
    def change_state(self, newstate):
        logger.info("Changed state")
        self.state = newstate
        self.changed_at = time.time()
    
    def get_out_of_outstanding(self):
        for k, (v_id, v_type) in self.orders.items():
            if v_type == 'bid':
                self.e.insert_order(v_id, price=1, volume=1, side='ask', order_type='ioc')
            else:
                self.e.insert_order(v_id, price=100000, volume=-1, side='bid', order_type='ioc') 
    
    def update(self):
        t = time.time()
        if self.state == State.CHECK_MARKETS:
            if self.check_for_discrepancies():
                self.change_state(State.WAIT_FOR_ORDER_COMPLETE)
        elif self.state == State.WAIT_FOR_ORDER_COMPLETE:
            if self.orders_complete():
                self.change_state(State.CHECK_MARKETS)
            elif t - self.changed_at >= 1.0:
                self.get_out_of_outstanding()
                self.change_state(State.UNFULFILLED_ORDER_DELAY)
        else: 
            if t - self.changed_at >= 0.1:
                self.change_state(State.CHECK_MARKETS)
        
    def check_for_discrepancies(self):
        books = [self.e.get_last_price_book(x) for x in self.instruments]
        
        # check asks
        try:
            arr = sorted([(books[0].asks[0], self.instruments[0]), (books[1].asks[0], self.instruments[1])])
        except Exception as e:
            pass
        if arr[0]>
        
        for m1, m2 in [(0,1), (1,0)]:
            m1_id = self.instruments[m1]
            m2_id = self.instruments[m2]
            try:
                m1_ask = books[m1].asks[0]
                m2_bid = books[m2].bids[0] 
                if m1_ask.price < m2_bid.price:
                    logger.info(f"Can profit: buy {m1_id} at {m1_ask} and sell {m2_id} at {m2_bid}")
                    self.orders[self.e.insert_order(m1_id, price=m1_ask.price, volume=1, side='bid', order_type='limit')]=(m1_id, 'bid')
                    self.orders[self.e.insert_order(m2_id, price=m2_bid.price, volume=1, side='ask', order_type='limit')]=(m2_id, 'ask')
                    return True
            except Exception as e:
                # logger.info(e)
                continue
        return False