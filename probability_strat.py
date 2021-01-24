from optibook.synchronous_client import Exchange
import time
from enum import Enum
import logging
from strategy import Strategy
logger = logging.getLogger('client')
logger.setLevel('INFO')

import numpy as np
import pandas as pd

data = []
n = 30
instruments = ["PHILIPS_A", "PHILIPS_B"]


class ProbabilityStrat(Strategy): 
    
    def __init__(self, exchange, instruments):
        super().__init__(exchange, instruments)
        self.orders_outstanding = False
        self.wait_time = time.time()
        
        for i in range(n): 
            get_data()
    
    def get_data(): # gets the data from the trade ticker
        try: 
            tradeticks_a = e.get_last_price_book(instruments[0])
            tradeticks_b = e.get_last_price_book(instruments[1])
            data.append((time.time(), tradeticks_a.bids[0].price, tradeticks_a.asks[0].price, tradeticks_b.bids[0].price, tradeticks_b.asks[0].price))
            if len(data) > n: 
                data.pop(0)
        except Exception as ex:
            print(ex)
            continue
        time.sleep(0.05)
        
    def analyse(): 
        pass
        #use pandas. splin interpolate. find first and second derivatives
        #look at % change. if trend is increasing and hits local maximum, then make shorts
        
    
    def update(self): 
        # Check if we have any outstanding orders; don't submit any more if so
        prev_outstanding = self.orders_outstanding
        self.orders_outstanding = False
        for i in self.instruments:
            logger.info(i)
            logger.info(self.e.get_outstanding_orders(i))
            if len(self.e.get_outstanding_orders(i)) > 0:
                self.orders_outstanding = True
        
        #if self.orders_outstanding and time.time() - self.wait_time >= 1.0:
        #    self.get_out_of_positions()
        #    self.orders_outstanding = False
        
        if prev_outstanding and not self.orders_outstanding:
            logger.info("Orders confirmed")
            self.log_positions_cash()
                
        
        # look at difference between ask and bid
        if not self.orders_outstanding: 
            