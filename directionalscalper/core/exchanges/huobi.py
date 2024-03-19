import uuid
from .exchange import Exchange
import logging
import time
from ccxt.base.errors import RateLimitExceeded

class HuobiExchange(Exchange):
    def __init__(self, api_key, secret_key, passphrase=None, market_type='swap'):
        super().__init__('huobi', api_key, secret_key, passphrase, market_type)

    def fetch_balance_huobi(self, params={}):
        try:
            balance = self.exchange.fetch_balance(params)
            logging.info(f"Fetched balance from Huobi: {balance}")
            return balance
        except Exception as e:
            logging.error(f"Error occurred while fetching balance from Huobi: {e}")
            return None
        
    def cancel_close_huobi(self, symbol: str, side: str, offset: str) -> None:
        side_map = {"long": "buy", "short": "sell"}
        try:
            orders = self.exchange.fetch_open_orders(symbol)
            print(f"Orders: {orders}")
            if orders:
                for order in orders:
                    order_info = order["info"]
                    order_id = order_info["order_id"]
                    order_status = order_info["status"]
                    order_direction = order_info["direction"]
                    order_offset = order_info["offset"]
                    reduce_only = order_info["reduce_only"]

                    if (
                        order_status == '3'  # Assuming '3' represents open orders
                        and order_direction == side_map[side]
                        and order_offset == offset
                        and reduce_only == '1'  # Assuming '1' represents reduce_only orders
                    ):
                        self.exchange.cancel_order(symbol=symbol, id=order_id)
                        logging.info(f"Cancelling order: {order_id}")
        except Exception as e:
            logging.warning(f"An unknown error occurred in cancel_close_huobi(): {e}")

    def create_take_profit_order_huobi(self, symbol, order_type, side, amount, price=None, reduce_only=False):
        if order_type == 'limit':
            if price is None:
                raise ValueError("A price must be specified for a limit order")

            if side not in ["buy", "sell"]:
                raise ValueError(f"Invalid side: {side}")

            params = {"offset": "close" if reduce_only else "open"}
            return self.exchange.create_order(symbol, order_type, side, amount, price, params)
        else:
            raise ValueError(f"Unsupported order type: {order_type}")

    def create_contract_order_huobi(self, symbol, order_type, side, amount, price=None, params={}):
        params = {'leverRate': 50}
        return self.exchange.create_contract_order(symbol, order_type, side, amount, price, params)

    def huobi_test_orders(self, symbol: str) -> None:
        try:
            orders = self.exchange.fetch_open_orders(symbol)
            print(orders)
        except Exception as e:
            print(f"Exception caught {e}")

    def cancel_all_entries_huobi(self, symbol: str) -> None:
        try:
            orders = self.exchange.fetch_open_orders(symbol)
            long_orders = 0
            short_orders = 0

            # Count the number of open long and short orders
            for order in orders:
                order_info = order["info"]
                order_status = str(order_info["status"])  # status seems to be a string of a number
                order_direction = order_info["direction"]
                order_offset = order_info["offset"]

                if order_status != "4" and order_status != "6":  # Assuming 4 is 'Filled' and 6 is 'Cancelled'
                    if order_direction == "buy" and order_offset == "open":
                        long_orders += 1
                    elif order_direction == "sell" and order_offset == "open":
                        short_orders += 1

            # Cancel extra long or short orders if more than one open order per side
            if long_orders > 1 or short_orders > 1:
                for order in orders:
                    order_info = order["info"]
                    order_id = order_info["order_id"]  # It's 'order_id' in Huobi, not 'orderId'
                    order_status = str(order_info["status"])
                    order_direction = order_info["direction"]
                    order_offset = order_info["offset"]

                    if order_status != "4" and order_status != "6":
                        self.exchange.cancel_order(symbol=symbol, id=order_id)
                        logging.info(f"Cancelling order: {order_id}")
        except Exception as e:
            logging.info(f"An unknown error occurred in cancel_entry(): {e}")

    def check_account_type_huobi(self):
        if self.exchange_id.lower() != 'huobi':
            logging.info("This operation is only available for Huobi.")
            return

        response = self.exchange.contractPrivateGetLinearSwapApiV3SwapUnifiedAccountType()
        return response
    
    def switch_account_type_huobi(self, account_type: int):
        if self.exchange_id.lower() != 'huobi':
            logging.info("This operation is only available for Huobi.")
            return

        body = {
            "account_type": account_type
        }

        response = self.exchange.contractPrivatePostLinearSwapApiV3SwapSwitchAccountType(body)
        return response
    
    # Huobi
    def fetch_max_leverage_huobi(self, symbol, max_retries=3, delay_between_retries=5):
        """
        Retrieve the maximum leverage for a given symbol
        :param str symbol: unified market symbol
        :param int max_retries: Number of times to retry fetching
        :param int delay_between_retries: Delay in seconds between retries
        :returns int: maximum leverage for the symbol
        """
        retries = 0
        while retries < max_retries:
            try:
                leverage_tiers = self.exchange.fetch_leverage_tiers([symbol])
                if symbol in leverage_tiers:
                    symbol_tiers = leverage_tiers[symbol]
                    max_leverage = max([tier['maxLeverage'] for tier in symbol_tiers])
                    return max_leverage
                else:
                    return None
            except ccxt.NetworkError:
                retries += 1
                if retries < max_retries:
                    time.sleep(delay_between_retries)
                else:
                    raise  # if max_retries is reached, raise the exception to be handled by the caller

            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                return None
            
    # Huobi
    def get_market_data_huobi(self, symbol: str) -> dict:
        values = {"precision": 0.0, "min_qty": 0.0, "leverage": 0.0}
        try:
            self.exchange.load_markets()
            symbol_data = self.exchange.market(symbol)
            
            if "precision" in symbol_data:
                values["precision"] = symbol_data["precision"]["price"]
            if "limits" in symbol_data:
                values["min_qty"] = symbol_data["limits"]["amount"]["min"]
            if "info" in symbol_data and "leverage-ratio" in symbol_data["info"]:
                values["leverage"] = float(symbol_data["info"]["leverage-ratio"])
        except Exception as e:
            logging.info(f"An unknown error occurred in get_market_data_huobi(): {e}")
        return values

    def fetch_margin_balance_huobi(self, params={}):
        response = self.exchange.private_get_margin_accounts_balance(params)
        return self._parse_huobi_balance(response)

    def fetch_futures_balance_huobi(self, params={}):
        response = self.exchange.linearGetV2AccountInfo(params)
        return self._parse_huobi_balance(response)

    def fetch_swaps_balance_huobi(self, params={}):
        response = self.exchange.swapGetSwapBalance(params)
        return self._parse_huobi_balance(response)

    def _parse_huobi_balance(self, response):
        if 'data' in response:
            balance_data = response['data']
            parsed_balance = {}
            for currency_data in balance_data:
                currency = currency_data['currency']
                parsed_balance[currency] = {
                    'free': float(currency_data.get('available', 0)),
                    'used': float(currency_data.get('frozen', 0)),
                    'total': float(currency_data.get('balance', 0))
                }
            return parsed_balance
        else:
            return {}

    #Huobi 
    def safe_order_operation(self, operation, *args, **kwargs):
        while True:
            try:
                return operation(*args, **kwargs)
            except ccxt.BaseError as e:
                e_str = str(e)
                if 'In settlement' in e_str or 'In delivery' in e_str or 'Settling. Unable to place/cancel orders currently.' in e_str:
                    print(f"Contract is in settlement or delivery. Cannot perform operation currently. Retrying in 10 seconds...")
                    time.sleep(10)
                elif 'Insufficient close amount available' in e_str:
                    print(f"Insufficient close amount available. Retrying in 5 seconds...")
                    time.sleep(5)
                else:
                    raise

    # Huobi     
    def get_contract_size_huobi(self, symbol, max_retries=3, retry_delay=5):
        for i in range(max_retries):
            try:
                markets = self.exchange.fetch_markets_by_type_and_sub_type('swap', 'linear')
                for market in markets:
                    if market['symbol'] == symbol:
                        return market['contractSize']
                # If the contract size is not found in the markets, return None
                return None

            except Exception as e:
                if i < max_retries - 1:  # If not the last attempt
                    logging.info(f"An unknown error occurred in get_contract_size_huobi(): {e}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logging.info(f"Failed to fetch contract size after {max_retries} attempts: {e}")
                    raise e  # If it's still failing after max_retries, re-raise the exception.
 
    # Huobi
    def get_positions_huobi(self, symbol) -> dict:
        print(f"Symbol received in get_positions_huobi: {symbol}")
        self.exchange.load_markets()
        if symbol not in self.exchange.markets:
            print(f"Market symbol {symbol} not found in Huobi markets.")
            return None
        values = {
            "long": {
                "qty": 0.0,
                "price": 0.0,
                "realised": 0,
                "cum_realised": 0,
                "upnl": 0,
                "upnl_pct": 0,
                "liq_price": 0,
                "entry_price": 0,
            },
            "short": {
                "qty": 0.0,
                "price": 0.0,
                "realised": 0,
                "cum_realised": 0,
                "upnl": 0,
                "upnl_pct": 0,
                "liq_price": 0,
                "entry_price": 0,
            },
        }
        try:
            data = self.exchange.fetch_positions([symbol])
            for position in data:
                if "info" not in position or "direction" not in position["info"]:
                    continue
                side = "long" if position["info"]["direction"] == "buy" else "short"
                values[side]["qty"] = float(position["info"]["volume"])  # Updated to use 'volume'
                values[side]["price"] = float(position["info"]["cost_open"])
                values[side]["realised"] = float(position["info"]["profit"])
                values[side]["cum_realised"] = float(position["info"]["profit"])  # Huobi API doesn't seem to provide cumulative realised profit
                values[side]["upnl"] = float(position["info"]["profit_unreal"])
                values[side]["upnl_pct"] = float(position["info"]["profit_rate"])
                values[side]["liq_price"] = 0.0  # Huobi API doesn't seem to provide liquidation price
                values[side]["entry_price"] = float(position["info"]["cost_open"])
        except Exception as e:
            logging.info(f"An unknown error occurred in get_positions_huobi(): {e}")
        return values

    def get_open_orders_huobi(self, symbol: str) -> list:
        open_orders_list = []
        try:
            orders = self.exchange.fetch_open_orders(symbol)
            #print(f"Debug: {orders}")
            if len(orders) > 0:
                for order in orders:
                    if "info" in order:
                        try:
                            # Extracting the necessary fields for Huobi orders
                            order_info = {
                                "id": order["info"]["order_id"],
                                "price": float(order["info"]["price"]),
                                "qty": float(order["info"]["volume"]),
                                "order_status": order["info"]["status"],
                                "side": order["info"]["direction"],  # assuming 'direction' indicates 'buy' or 'sell'
                            }
                            open_orders_list.append(order_info)
                        except KeyError as e:
                            logging.info(f"Key {e} not found in order info.")
        except Exception as e:
            logging.info(f"An unknown error occurred in get_open_orders_huobi(): {e}")
        return open_orders_list
    