from optibook.synchronous_client import Exchange
from strategy import Strategy
# from safe_exchange import SafeExchange
import time
import logging
import dual_market_strat
import safe_dual_strat
import difference_strat
import extremes_strat
import dual_paper_strat
import dual_hedge_strat
import mimic_strat
import sys

logger = logging.getLogger('client')
logger.setLevel('INFO')


# Main loop: run a number of different strategies
if __name__ == '__main__':
    exchange = Exchange()
    logging.info(exchange.connect())
    logging.info("Setup was successful.")
    try:
        # we can run multiple strategies at once, but really having separate bots to do this would be simpler
        # since currently we can't ignore our own orders in aggregate data such as the pricebook
        # strats = [dual_market_strat.DualMarketStrat(exchange, ["PHILIPS_A", "PHILIPS_B"])]
        # strats = [safe_dual_strat.SafeDualStrat(exchange, ["PHILIPS_A", "PHILIPS_B"])]
        # strats = [difference_strat.DifferenceStrat(exchange, ["PHILIPS_A", "PHILIPS_B"])]
        #strats = [dual_paper_strat.DualPaperStrat(exchange, ["PHILIPS_A", "PHILIPS_B"])]
        strats = [dual_hedge_strat.DualHedgeStrat(exchange, "PHILIPS_A", "PHILIPS_B")]
        while True:
            time.sleep(0.2)
            for s in strats:
                try:
                    s.update();
                except AssertionError as e: # if get disconnected than do something else
                    # Try to reconnect
                    while not exchange.is_connected():
                        logger.info("disconnected, trying to reconnect")
                        time.sleep(15)
                        exchange.connect()
                    # Once reconnected, make strategy that experienced disconnection do cleanup
                    s.get_out_of_positions(300)
                    continue
            # logger.info(exchange.get_cash())
    except KeyboardInterrupt as e:
        print(e)
        strats[0].get_out_of_positions()
        #raise
        #sys.exit(0)
    