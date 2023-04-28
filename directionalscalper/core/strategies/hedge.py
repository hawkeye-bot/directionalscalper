import time
from decimal import Decimal, ROUND_HALF_UP
from .strategy import Strategy

class HedgeStrategy(Strategy):
    def __init__(self, exchange, manager, config):
        super().__init__(exchange, config)
        self.manager = manager

    def limit_order(self, symbol, side, amount, price, reduce_only=False):
        min_qty_usd = 5
        current_price = self.exchange.get_current_price(symbol)
        min_qty_bitget = min_qty_usd / current_price

        print(f"Min trade quantitiy for {symbol}: {min_qty_bitget}")

        if float(amount) < min_qty_bitget:
            print(f"The amount you entered ({amount}) is less than the minimum required by Bitget for {symbol}: {min_qty_bitget}.")
            #log.warning(f"Order amount {amount} is less than the minimum required amount of {min_amount} USDT.")
            return
        order = self.exchange.create_order(symbol, 'limit', side, amount, price, reduce_only=reduce_only)
        #order = self.exchange.create_order(symbol, 'limit', side, amount, price, params={"reduceOnly": reduce_only})
        return order

    def take_profit_order(self, symbol, side, amount, price, reduce_only=True):
        min_qty_usd = 5
        current_price = self.exchange.get_current_price(symbol)
        min_qty_bitget = min_qty_usd / current_price

        print(f"Min trade quantitiy for {symbol}: {min_qty_bitget}")

        if float(amount) < min_qty_bitget:
            print(f"The amount you entered ({amount}) is less than the minimum required by Bitget for {symbol}: {min_qty_bitget}.")
            #log.warning(f"Order amount {amount} is less than the minimum required amount of {min_amount} USDT.")
            return
        order = self.exchange.create_order(symbol, 'limit', side, amount, price, reduce_only=reduce_only)
        #order = self.exchange.create_limit_order(symbol, side, amount, price, reduce_only=reduce_only)
        return order

    def close_position(self, symbol, side, amount):
        try:
            self.exchange.create_market_order(symbol, side, amount)
            print(f"Closed {side} position for {symbol} with amount {amount}")
        except Exception as e:
            print(f"An error occurred while closing the position: {e}")


    def parse_symbol(self, symbol):
        if "bitget" in self.exchange.name.lower():
            return symbol.replace("_UMCBL", "")
        return symbol

    def cancel_take_profit_orders(self, symbol):
        self.exchange.cancel_close_bitget(symbol, "long")
        self.exchange.cancel_close_bitget(symbol, "short")

    def has_open_orders(self, symbol):
        open_orders = self.exchange.get_open_orders(symbol)
        return len(open_orders) > 0

    def calculate_short_take_profit(self, short_pos_price, symbol):
        if short_pos_price is None:
            return None

        five_min_data = self.manager.get_5m_moving_averages(symbol)
        price_precision = int(self.exchange.get_price_precision(symbol))

        if five_min_data is not None:
            ma_6_high = Decimal(five_min_data["MA_6_H"])
            ma_6_low = Decimal(five_min_data["MA_6_L"])

            short_target_price = Decimal(short_pos_price) - (ma_6_high - ma_6_low)
            short_target_price = short_target_price.quantize(
                Decimal('1e-{}'.format(price_precision)),
                rounding=ROUND_HALF_UP
            )

            short_profit_price = short_target_price
            print(f"Debug: Short profit price: {short_profit_price}")

            return float(short_profit_price)
        return None

    def calculate_long_take_profit(self, long_pos_price, symbol):
        if long_pos_price is None:
            return None

        five_min_data = self.manager.get_5m_moving_averages(symbol)
        price_precision = int(self.exchange.get_price_precision(symbol))

        if five_min_data is not None:
            ma_6_high = Decimal(five_min_data["MA_6_H"])
            ma_6_low = Decimal(five_min_data["MA_6_L"])

            long_target_price = Decimal(long_pos_price) + (ma_6_high - ma_6_low)
            long_target_price = long_target_price.quantize(
                Decimal('1e-{}'.format(price_precision)),
                rounding=ROUND_HALF_UP
            )

            long_profit_price = long_target_price
            print(f"Debug: Long profit price: {long_profit_price}")

            return float(long_profit_price)
        return None


    # def calculate_short_take_profit(self, short_pos_price, symbol):
    #     if short_pos_price is None:
    #         return None

    #     five_min_data = self.manager.get_5m_moving_averages(symbol)
    #     price_precision = int(self.exchange.get_price_precision(symbol))

    #     if five_min_data is not None:
    #         print("Debug: five_min_data:", five_min_data)
    #         ma_6_high = Decimal(five_min_data["MA_6_H"])
    #         ma_6_low = Decimal(five_min_data["MA_6_L"])
    #         print("Debug: ma_6_high:", ma_6_high)  # Added print statement
    #         print("Debug: ma_6_low:", ma_6_low)  # Added print statement

    #         short_target_price = Decimal(short_pos_price) - (ma_6_high - ma_6_low)
    #         short_target_price = short_target_price.quantize(
    #             Decimal('1e-{}'.format(price_precision)),
    #             rounding=ROUND_HALF_UP
    #         )

    #         short_profit_price = short_target_price - Decimal(short_pos_price)
    #         print(f"Debug: Short profit price: {short_profit_price}")

    #         return float(short_profit_price)
    #     return None

    # def calculate_long_take_profit(self, long_pos_price, symbol):
    #     if long_pos_price is None:
    #         return None

    #     five_min_data = self.manager.get_5m_moving_averages(symbol)
    #     price_precision = int(self.exchange.get_price_precision(symbol))

    #     if five_min_data is not None:
    #         print("Debug: five_min_data:", five_min_data)
    #         ma_6_high = Decimal(five_min_data["MA_6_H"])
    #         ma_6_low = Decimal(five_min_data["MA_6_L"])
    #         print("Debug: ma_6_high:", ma_6_high)  # Added print statement
    #         print("Debug: ma_6_low:", ma_6_low)  # Added print statement

    #         long_target_price = Decimal(long_pos_price) + (ma_6_high - ma_6_low)
    #         long_target_price = long_target_price.quantize(
    #             Decimal('1e-{}'.format(price_precision)),
    #             rounding=ROUND_HALF_UP
    #         )

    #         long_profit_price = long_target_price - Decimal(long_pos_price)
    #         print(f"Debug: Long profit price: {long_profit_price}")

    #         return float(long_profit_price)
    #     return None


    # def calculate_short_take_profit(self, short_pos_price, symbol):
    #     if short_pos_price is None:
    #         return None

    #     five_min_data = self.manager.get_5m_moving_averages(symbol)
    #     price_precision = int(self.exchange.get_price_precision(symbol))

    #     if five_min_data is not None:
    #         ma_6_high = five_min_data["MA_6_H"]
    #         ma_6_low = five_min_data["MA_6_L"]

    #         print("ma_6_high:", ma_6_high)
    #         print("ma_6_low:", ma_6_low)
    #         print("price_precision:", price_precision)

    #         short_profit_price = Decimal(short_pos_price - (ma_6_high - ma_6_low))
    #         short_profit_price = short_profit_price.quantize(
    #             Decimal('1e-{}'.format(price_precision)),
    #             rounding=ROUND_HALF_UP
    #         )

    #         print("short_profit_price:", short_profit_price)
    #         return float(short_profit_price)
    #     return None


    # def calculate_long_take_profit(self, long_pos_price, symbol):
    #     if long_pos_price is None:
    #         return None

    #     five_min_data = self.manager.get_5m_moving_averages(symbol)
    #     price_precision = int(self.exchange.get_price_precision(symbol))

    #     if five_min_data is not None:
    #         ma_6_high = five_min_data["MA_6_H"]
    #         ma_6_low = five_min_data["MA_6_L"]

    #         print("ma_6_high:", ma_6_high)
    #         print("ma_6_low:", ma_6_low)
    #         print("price_precision:", price_precision)

    #         long_profit_price = Decimal(long_pos_price + (ma_6_high - ma_6_low))
    #         long_profit_price = long_profit_price.quantize(
    #             Decimal('1e-{}'.format(price_precision)),
    #             rounding=ROUND_HALF_UP
    #         )

    #         print("long_profit_price:", long_profit_price)
    #         return float(long_profit_price)
    #     return None

    def run(self, symbol, amount):
        long_initial_placed = False
        short_initial_placed = False
        wallet_exposure = self.config.wallet_exposure

        while True:

            # Max trade qty calculation
            quote_currency = "USDT"  # Change this to your desired quote currency
            dex_equity = self.exchange.get_balance_bitget(quote_currency)

            market_data = self.exchange.get_market_data_bitget(symbol)
            best_ask_price = self.exchange.get_orderbook(symbol)['asks'][0][0]

            leverage = float(market_data["leverage"]) if market_data["leverage"] != 0 else 50.0

            max_trade_qty = round(
                (float(dex_equity) * wallet_exposure / float(best_ask_price))
                / (100 / leverage),
                int(float(market_data["min_qty"])),
            )

            print(f"Max trade quantity for {symbol}: {max_trade_qty}")

            # min_qty_bitget = market_data["min_qty"]

            min_qty_usd = 5
            current_price = self.exchange.get_current_price(symbol)
            min_qty_bitget = min_qty_usd / current_price

            print(f"Min trade quantitiy for {symbol}: {min_qty_bitget}")

            if float(amount) < min_qty_bitget:
                print(f"The amount you entered ({amount}) is less than the minimum required by Bitget for {symbol}: {min_qty_bitget}.")
                break
            else:
                print(f"The amount you entered ({amount}) is valid for {symbol}")

            # Orderbook data
            orderbook = self.exchange.get_orderbook(symbol)
            bid_price = orderbook['bids'][0][0]
            ask_price = orderbook['asks'][0][0]

            print(f"Bid: {bid_price}")
            print(f"Ask: {ask_price}")

            min_dist = self.config.min_distance
            min_vol = self.config.min_volume
            print(f"Min volume: {min_vol}")
            print(f"Min distance: {min_dist}")


            # Hedge logic starts

            # Get data from manager
            data = self.manager.get_data()

            # Parse the symbol according to the exchange being used
            parsed_symbol = self.parse_symbol(symbol)

            # Data we need from API
            one_minute_volume = self.manager.get_asset_value(parsed_symbol, data, "1mVol")
            five_minute_distance = self.manager.get_asset_value(parsed_symbol, data, "5mSpread")
            trend = self.manager.get_asset_value(parsed_symbol, data, "Trend")
            print(f"1m Volume: {one_minute_volume}")
            print(f"5m Spread: {five_minute_distance}")
            print(f"Trend: {trend}")

            # data = self.exchange.exchange.fetch_positions([symbol])
            # print(f"Bitget positions response: {data}")   
 

            # Get pos data from exchange
            position_data = self.exchange.get_positions_bitget(symbol) 
            print(f"Fetching position data")
            #print(f"Raw position data: {position_data}")

            # Extract short and long position prices
            # short_pos_price = position_data["short"]["price"]
            # long_pos_price = position_data["long"]["price"]

            short_pos_qty = position_data["short"]["qty"]
            long_pos_qty = position_data["long"]["qty"]

            print(f"Short pos qty: {short_pos_qty}")
            print(f"Long pos qty: {long_pos_qty}")

            short_pos_price = position_data["short"]["price"] if short_pos_qty > 0 else None
            long_pos_price = position_data["long"]["price"] if long_pos_qty > 0 else None

            print(f"Short pos price: {short_pos_price}")
            print(f"Long pos price: {long_pos_price}")

            # Get the 1-minute moving averages
            print(f"Fetching MA data")
            m_moving_averages = self.manager.get_1m_moving_averages(symbol)
            m5_moving_averages = self.manager.get_5m_moving_averages(symbol)

            # Define MAs for ease of use
            ma_1m_3_high = self.manager.get_1m_moving_averages(symbol)["MA_3_H"]
            ma_5m_3_high = self.manager.get_5m_moving_averages(symbol)["MA_3_H"]

            print(f"Long pos price: {long_pos_price}")
            print(f"Short pos price: {short_pos_price}")

            short_take_profit = self.calculate_short_take_profit(short_pos_price, symbol)
            long_take_profit = self.calculate_long_take_profit(long_pos_price, symbol)

            print(f"Short take profit: {short_take_profit}")
            print(f"Long take profit: {long_take_profit}")


            # Call the new methods
            should_short = self.short_trade_condition(ask_price, m_moving_averages["MA_3_H"])
            should_long = self.long_trade_condition(bid_price, m_moving_averages["MA_3_L"])


            should_add_to_short = short_pos_price is not None and \
                                self.add_short_trade_condition(short_pos_price, m_moving_averages["MA_6_L"]) and \
                                ask_price > short_pos_price and \
                                short_pos_qty < max_trade_qty

            should_add_to_long = long_pos_price is not None and \
                                self.add_long_trade_condition(long_pos_price, m_moving_averages["MA_6_L"]) and \
                                bid_price < long_pos_price and \
                                long_pos_qty < max_trade_qty

            # should_add_to_short = self.add_short_trade_condition(short_pos_price, m_moving_averages["MA_6_L"])
            # should_add_to_long = self.add_long_trade_condition(long_pos_price, m_moving_averages["MA_6_L"])

            print(f"Short condition: {should_short}")
            print(f"Long condition: {should_long}")
            print(f"Add short condition: {should_add_to_short}")
            print(f"Add long condition: {should_add_to_long}")

            # close_short_position = short_pos_qty > 0 and ask_price <= short_take_profit
            # close_long_position = long_pos_qty > 0 and bid_price >= long_take_profit

            close_short_position = short_pos_qty > 0 and current_price <= short_take_profit
            close_long_position = long_pos_qty > 0 and current_price >= long_take_profit

            print(f"Current price: {current_price}")
            print(f"Close short position condition: {close_short_position}")
            print(f"Close long position condition: {close_long_position}")
            #self.exchange.debug_open_orders(symbol)

            # New hedge logic
            if trend is not None and isinstance(trend, str):
                if one_minute_volume is not None and five_minute_distance is not None:
                    if one_minute_volume > min_vol and five_minute_distance > min_dist:

                        if trend.lower() == "long" and should_long and long_pos_qty == 0:

                            self.limit_order(symbol, "buy", amount, bid_price, reduce_only=False)
                            print(f"Placed initial long entry")
                        else:
                            if trend.lower() == "long" and should_add_to_long and long_pos_qty < max_trade_qty:
                                print(f"Placed additional long entry")
                                self.limit_order(symbol, "buy", amount, bid_price, reduce_only=False)

                        if trend.lower() == "short" and should_short and short_pos_qty == 0:

                            self.limit_order(symbol, "sell", amount, ask_price, reduce_only=False)
                            print("Placed initial short entry")
                        else:
                            if trend.lower() == "short" and should_add_to_short and short_pos_qty < max_trade_qty:
                                print(f"Placed additional short entry")
                                self.limit_order(symbol, "sell", amount, ask_price, reduce_only=False)


            if long_pos_qty > 0 and long_take_profit is not None:
                try:
                    print(f"DEBUG LONG TAKE PROFIT {long_take_profit}")
                    print(f"Long position details: {position_data['long']}")
                    print(f"Account balance: {self.exchange.get_balance_bitget(quote_currency)}")
                    print(f"Long position quantity: {long_pos_qty}")
                    print(f"Short position quantity: {short_pos_qty}")

                    self.exchange.create_take_profit_order(symbol, "limit", "sell", long_pos_qty, long_take_profit, reduce_only=True)
                    #self.exchange.create_take_profit_order(symbol, "limit", "buy", long_pos_qty, long_take_profit, reduce_only=True)
                    print(f"Long take profit set at {long_take_profit}")
                    time.sleep(0.05)
                except Exception as e:
                    print(f"Error in placing long TP: {e}")
                    #self.log.warning(f"{e}")

            if short_pos_qty > 0 and short_take_profit is not None:
                try:
                    print(f"DEBUG LONG TAKE PROFIT {short_take_profit}")
                    print(f"Short position details: {position_data['short']}")
                    print(f"Account balance: {self.exchange.get_balance_bitget(quote_currency)}")
                    print(f"Long position quantity: {long_pos_qty}")
                    print(f"Short position quantity: {short_pos_qty}")

                    self.exchange.create_take_profit_order(symbol, "limit", "buy", short_pos_qty, short_take_profit, reduce_only=True)
                    print(f"Short take profit set at {short_take_profit}")
                    time.sleep(0.05)
                except Exception as e:
                    print(f"Error in placing short TP: {e}")
                    #self.log.warning(f"{e}")

            # Cancel entries
            try:
                self.exchange.cancel_all_entries(symbol)
                print(f"Canceled entry orders for {symbol}")
            except Exception as e:
                print(f"An error occurred while canceling entry orders: {e}")
                
            # if close_long_position:
            #     try:
            #         print(f"Closing long position")
            #         self.exchange.create_market_order(symbol, "sell", long_pos_qty, close_position=True)
            #     except Exception as e:
            #         print(f"Error while closing long position: {e}")

            # if close_short_position:
            #     try:
            #         print(f"Closing short position")
            #         self.exchange.create_market_order(symbol, "buy", short_pos_qty, close_position=True)
            #     except Exception as e:
            #         print(f"Error while closing short position: {e}")



            # Check if volume and distance requirements are met
            # if one_minute_volume > min_vol and five_minute_distance > min_dist:
            # if trend is not None and isinstance(trend, str):
            #     if one_minute_volume is not None and five_minute_distance is not None:
            #         if one_minute_volume > min_vol and five_minute_distance > min_dist:
            #         # Place the initial long trade if the trend is long and long trade condition is True
            #             if trend.lower() == "long" and should_long and not long_initial_placed and long_pos_qty < max_trade_qty:
            #                 self.execute(symbol, "buy", amount, bid_price)
            #                 print(f"Placed the initial long trade for {symbol} at {bid_price}")
            #                 long_initial_placed = True

            #             # Place the initial short trade if the trend is short and short trade condition is True
            #             elif trend.lower() == "short" and should_short and not short_initial_placed and short_pos_qty < max_trade_qty:
            #                 self.execute(symbol, "sell", amount, ask_price)
            #                 print(f"Placed the initial short trade for {symbol} at {ask_price}")
            #                 short_initial_placed = True

            #             # If the initial long trade is placed, check for adding long orders
            #             elif long_initial_placed and should_add_to_long and long_pos_qty < max_trade_qty:
            #                 self.execute(symbol, "buy", amount, bid_price)
            #                 print(f"Added a long trade for {symbol} at {bid_price}")

            #             # If the initial short trade is placed, check for adding short orders
            #             elif short_initial_placed and should_add_to_short and short_pos_qty < max_trade_qty:
            #                 self.execute(symbol, "sell", amount, ask_price)
            #                 print(f"Added a short trade for {symbol} at {ask_price}")

            # Take profit logic
            # if close_long_position or close_short_position:
                # # Check if the conditions to close the position are met
                # open_orders = self.exchange.fetch_open_orders(symbol)
                # take_profit_orders = [order for order in open_orders if order['type'] == 'take_profit']
                # long_take_profit_exists = any(order for order in take_profit_orders if order['side'] == 'sell' and order['reduce_only'] == True)
                # short_take_profit_exists = any(order for order in take_profit_orders if order['side'] == 'buy' and order['reduce_only'] == True)

                # if close_long_position:
                #     try:
                #         print(f"Closing long position")
                #         self.exchange.create_take_profit_order(symbol, 'limit', "buy", long_pos_qty, price=current_price, reduce_only=True)
                #         print(f"Long position closed at {current_price}")
                #     except Exception as e:
                #         print(f"Error while closing long position: {e}")

                # if close_short_position:
                #     try:
                #         print(f"Closing short position")
                #         self.exchange.create_take_profit_order(symbol, 'limit', "sell", short_pos_qty, price=current_price, reduce_only=True)
                #         print(f"Short position closed at {current_price}")
                #     except Exception as e:
                #         print(f"Error while closing short position: {e}")

                # if close_long_position:
                #     try:
                #         print(f"Closing long position")
                #         self.exchange.create_take_profit_order(symbol, 'limit', "sell", long_pos_qty, price=current_price, reduce_only=True)
                #         print(f"Long position closed at {current_price}")
                #     except Exception as e:
                #         print(f"Error while closing long position: {e}")

                # if close_short_position:
                #     try:
                #         print(f"Closing short position")
                #         self.exchange.create_take_profit_order(symbol, 'limit', "buy", short_pos_qty, price=current_price, reduce_only=True)
                #         print(f"Short position closed at {current_price}")
                #     except Exception as e:
                #         print(f"Error while closing short position: {e}")

                # time.sleep(0.05)


                # if close_long_position:
                #     try:
                #         print(f"Closing long position")
                #         #self.exchange.create_order(symbol, "limit", "sell", long_pos_qty, bid_price, params={"reduceOnly": True})
                #         self.take_profit_order(symbol, "limit", "sell", long_pos_qty, bid_price, reduce_only=True)
                #     except Exception as e:
                #         print(f"Error while closing long position: {e}")

                # if close_short_position:
                #     try:
                #         print(f"Closing short position")
                #         self.take_profit_order(symbol, "limit", "buy", short_pos_qty, ask_price, reduce_only=True)
                #         #self.exchange.create_order(symbol, "limit", "buy", short_pos_qty, ask_price, params={"reduceOnly": True})
                #     except Exception as e:
                #         print(f"Error while closing short position: {e}")

            # if close_long_position or close_short_position:
            #     # Check if the conditions to close the position are met

            #     # self.cancel_take_profit_orders(symbol)
            #     # print(f"Take profits canceled")
            #     # time.sleep(0.05)

            #     if close_long_position:
            #         try:
            #             print(f"Closing long position")
            #             self.exchange.create_order(symbol, "limit", "sell", long_pos_qty, params={"reduceOnly": True})
            #         except Exception as e:
            #             print(f"Error while closing long position: {e}")

            #     if close_short_position:
            #         try:
            #             print(f"Closing short position")
            #             self.exchange.create_order(symbol, "limit", "buy", short_pos_qty, params={"reduceOnly": True})
            #         except Exception as e:
            #             print(f"Error while closing short position: {e}")



                # if close_long_position:
                #     try:
                #         print(f"Closing long position")
                #         self.close_position(symbol, "sell", long_pos_qty)
                #     except Exception as e:
                #         print(f"Error while closing long position: {e}")

                # if close_short_position:
                #     try:
                #         print(f"Closing short position")
                #         self.close_position(symbol, "buy", short_pos_qty)
                #     except Exception as e:
                #         print(f"Error while closing short position: {e}")
                                            
            # if (long_pos_qty > 0 and bid_price < long_pos_price) or (short_pos_qty > 0 and ask_price > short_pos_price):
            #     # Check if the conditions to close the position are met

            #     # self.cancel_take_profit_orders(symbol)
            #     # print(f"Take profits canceled")
            #     # time.sleep(0.05)

            #     if long_pos_qty > 0 and long_take_profit is not None:
            #         try:
            #             # Check if the current_price is >= long_take_profit
            #             if current_price >= long_take_profit:
            #                 print(f"Closing long position")
            #                 self.close_position(symbol, "sell", long_pos_qty)
            #         except Exception as e:
            #             print(f"Error while closing long position: {e}")

            #     if short_pos_qty > 0 and short_take_profit is not None:
            #         try:
            #             # Check if the current_price is <= short_take_profit
            #             if current_price <= short_take_profit:
            #                 print(f"Closing short position")
            #                 self.close_position(symbol, "buy", short_pos_qty)
            #         except Exception as e:
            #             print(f"Error while closing short position: {e}")



                # if long_pos_qty > 0 and long_take_profit is not None:
                #     try:
                #         # Close short position with a market order
                #         if close_short_position:
                #             print(f"Closing short position at {ask_price}")
                #             self.exchange.create_market_order(symbol, 'buy', short_pos_qty)
                #         #self.take_profit_order(symbol, "sell", long_pos_qty, long_take_profit, reduce_only=True)
                #         print(f"Long take profit set at {long_take_profit}")
                #         time.sleep(0.05)
                #     except Exception as e:
                #         print(f"Error in placing long TP: {e}")
                #         #self.log.warning(f"{e}")

                # if short_pos_qty > 0 and short_take_profit is not None:
                #     try:
                #         # Close long position with a market order
                #         if close_long_position:
                #             print(f"Closing long position at {bid_price}")
                #             self.exchange.create_market_order(symbol, 'sell', long_pos_qty)
                #         #self.take_profit_order(symbol, "buy", short_pos_qty, short_take_profit, reduce_only=True)
                #         print(f"Short take profit set at {short_take_profit}")
                #         time.sleep(0.05)
                #     except Exception as e:
                #         print(f"Error in placing short TP: {e}")
                #         #self.log.warning(f"{e}")

            # Set and cancel take profit orders
            # if long_pos_qty > 0 or short_pos_qty > 0:
            # if long_pos_qty > 0 and bid_price < long_pos_price or short_pos_qty > 0 and ask_price > short_pos_price:
            #     self.cancel_take_profit_orders(symbol)
            #     print(f"Take profits canceled")
            #     time.sleep(0.05)

            # Entry cancellation reworked
            # if trend is not None and isinstance(trend, str):
            #     if trend.lower() == "long":
            #         #if ask_price < ma_1m_3_high or ask_price < ma_5m_3_high:
            #         if ask_price > ma_1m_3_high or ask_price > ma_5m_3_high:
            #         #if long_pos_price is not None and bid_price > long_pos_price:
            #             try:
            #                 # Cancel the long entry orders
            #                 self.exchange.cancel_long_entry(symbol)
            #                 print(f"Canceled long entry orders for {symbol}")
            #             except Exception as e:
            #                 print(f"An error occurred while canceling long entry orders: {e}")
            #     elif trend.lower() == "short":
            #         #if ask_price < ma_1m_3_high or ask_price < ma_5m_3_high:
            #         if ask_price > ma_1m_3_high or ask_price > ma_5m_3_high:
            #         #if short_pos_price is not None and ask_price > short_pos_price:
            #             try:
            #                 # Cancel the short entry orders
            #                 self.exchange.cancel_short_entry(symbol)
            #                 print(f"Canceled short entry orders for {symbol}")
            #             except Exception as e:
            #                 print(f"An error occurred while canceling short entry orders: {e}")

            # # Cancel entries if ask > 1m or 5m MA 3 High
            # if ask_price < ma_1m_3_high or ask_price < ma_5m_3_high:
            # #if long_pos_qty or short_pos_qty > 0:
            #     try:
            #         # Cancel the entry orders
            #         self.exchange.cancel_all_entries(symbol)
            #         print(f"Canceled entry orders for {symbol}")
            #     except Exception as e:
            #         print(f"An error occurred while canceling entry orders: {e}")

            time.sleep(30)