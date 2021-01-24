
from strategy import Strategy
import time

class MimicStrategy(Strategy):
    """ copies a previous trade """
    
    def update(self):
        
        for instrument_id in self.instruments:
            trade_ticks = self.e.poll_new_trade_ticks(instrument_id)
            
            trade_ticks = [tick for tick in trade_ticks if (tick.buyer != 'team-36') and tick.seller != 'team-36']
            
            if not trade_ticks:
                continue
            
            prev_trade = trade_ticks[-1]
            
            self.insert_biased_order(instrument_id, price=prev_trade.price, volume=1, side=prev_trade.aggressor_side, order_type='ioc')
            time.sleep(0.5)
    
