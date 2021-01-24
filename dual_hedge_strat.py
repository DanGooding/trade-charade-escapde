from optibook.synchronous_client import Exchange
from strategy import Strategy
import time
import logging
logger = logging.getLogger('client')
logger.setLevel('INFO')
from collections import defaultdict

class DualHedgeStrat(Strategy):
    def __init__(self, exchange, instruments):
        super().__init__(exchange, instruments)
        # only trade on one instrument
        self.instrument = self.instruments[1]
        self.hedge = self.instruments[0]

        self.wait_time = 1.0
        self.update_time = 0.5
        
        self.execution_time = time.time()
        self.quote_time = time.time()
        self.prev_num_orders = 0
        
        self.id_bid = 0
        self.id_ask = 0
    
    def get_price_spread(self, book):
        if len(book.asks) == 0 and len(book.bids) == 0:
            ask_price = 0
            bid_price = 0
        elif len(book.asks) == 0:
            bid_price = book.bids[0].price
            ask_price = bid_price
        elif len(book.bids) == 0:
            ask_price = book.asks[0].price
            bid_price = ask_price
        else:
            ask_price = book.asks[0].price
            bid_price = book.bids[0].price
        return ((ask_price + bid_price)/2, ask_price - bid_price)
    
    def quote_bid_ask(self):
        liquid_book = self.e.get_last_price_book(self.hedge)
        theo, spread = self.get_price_spread(liquid_book)  # was get_avg_price?
        
        delta = 0.4 * spread
        
        our_bid = theo - delta
        our_ask = theo + delta
        
        self.id_bid = self.insert_order(self.instrument, price=our_bid, volume=1, side='bid', order_type='limit')
        self.id_ask = self.insert_order(self.instrument, price=our_ask, volume=1, side='ask', order_type='limit')
        logger.info(f"Placed orders for {self.instrument} bid {our_bid} ask {our_ask}")
        logger.info(f"Bid ID: {self.id_bid} Ask ID: {self.id_ask}")
        
    def run_hedge(self):
        orders = self.e.get_outstanding_orders(self.instrument)
        orders = list(orders)
        assert len(orders) == 1
        self.e.delete_orders(self.instrument)
        book = self.e.get_last_price_book(self.instrument)
        lowest_ask = book.asks[0].price if len(book.asks) > 0 else 100000
        highest_bid = book.bids[0].price if len(book.bids) > 0 else 1
        logger.info("Hedging")
        print(self.id_bid, self.id_ask)
        print(orders)
        if orders[0] == self.id_bid: ## orders[0].side == 'bid'
            # need to place a bid
            self.insert_order(self.hedge, price=lowest_ask, volume=1, side='bid', order_type='ioc')
            logger.info(f"Placed hedge for {self.hedge} bid {lowest_ask}")
        elif orders[0] == self.id_ask:
            # need to place an ask
            self.insert_order(self.hedge, price=highest_bid, volume=1, side='ask', order_type='ioc')
            logger.info(f"Placed hedge for {self.hedge} ask {highest_bid}")
        else:
            assert (1==0)
    
    def update(self):
        num_orders = len(self.e.get_outstanding_orders(self.instrument))
        t = time.time()
        if num_orders == 0:
            logger.info("0 orders")
            self.quote_bid_ask()
            self.quote_time = t
            self.log_pnl()
        elif num_orders == 1:
            if self.prev_num_orders != 1:
                self.execution_time = t
            if t - self.execution_time > self.wait_time:
                logger.info("1 order wait time exceeded")
                self.run_hedge()
                logger.info("Run hedge")
                self.quote_bid_ask()
                self.quote_time = t
                self.log_pnl()
        else:
            if t - self.quote_time > self.update_time:
                logger.info("2 orders wait time exceeded")
                self.e.delete_orders(self.instrument)
                self.quote_bid_ask()
                self.quote_time = t
                self.log_pnl()
        self.prev_num_orders = num_orders
