import sys
import time
import threading
import random
from pathlib import Path

project_dir = str(Path(__file__).resolve().parent)
print("Project directory:", project_dir)
sys.path.insert(0, project_dir)

import traceback

import inquirer
from rich.live import Live
import argparse
from pathlib import Path
import config
from config import load_config, Config
from config import VERSION
from api.manager import Manager

from directionalscalper.core.exchanges.lbank import LBankExchange
from directionalscalper.core.exchanges.mexc import MexcExchange
from directionalscalper.core.exchanges.huobi import HuobiExchange
from directionalscalper.core.exchanges.bitget import BitgetExchange
from directionalscalper.core.exchanges.binance import BinanceExchange
from directionalscalper.core.exchanges.hyperliquid import HyperLiquidExchange
from directionalscalper.core.exchanges.bybit import BybitExchange
from directionalscalper.core.exchanges.exchange import Exchange


import directionalscalper.core.strategies.bybit.scalping as bybit_scalping
import directionalscalper.core.strategies.bybit.hedging as bybit_hedging
from directionalscalper.core.strategies.binance import *
from directionalscalper.core.strategies.huobi import *

from live_table_manager import LiveTableManager, shared_symbols_data


from directionalscalper.core.strategies.logger import Logger

from collections import deque

thread_to_symbol = {}
thread_to_symbol_lock = threading.Lock()
active_symbols = set()
active_threads = []

threads = {}  # Threads for each symbol
thread_start_time = {}  # Dictionary to track the start time for each symbol's thread
symbol_last_started_time = {}

extra_symbols = set()  # To track symbols opened past the limit
under_review_symbols = set()

logging = Logger(logger_name="MultiBot", filename="MultiBot.log", stream=True)

def standardize_symbol(symbol):
    return symbol.replace('/', '').split(':')[0]

def get_available_strategies():
    return [
        'qstrend',
        'qstrendemas',
        'mfieritrend',
        'qstrendob',
        'qstrendlongonly',
        'qstrendshortonly',
        'qstrend_unified',
        'qstrend_dca',
        'basicgrid',
        'basicgridmfirsi',
        'basicgridmfipersist'
        'qstrendspot',
    ]

def choose_strategy():
    questions = [
        inquirer.List('strategy',
                      message='Which strategy would you like to run?',
                      choices=get_available_strategies())
    ]
    answers = inquirer.prompt(questions)
    return answers['strategy']

def get_available_exchanges():
    return ['bybit', 'hyperliquid']

def ask_for_missing_arguments(args):
    questions = []
    if not args.exchange:
        questions.append(inquirer.List('exchange', message="Which exchange do you want to use?", choices=get_available_exchanges()))
    if not args.strategy:
        questions.append(inquirer.List('strategy', message="Which strategy do you want to use?", choices=get_available_strategies()))
    if not args.account_name:
        questions.append(inquirer.Text('account_name', message="Please enter the name of the account:"))

    if questions:
        answers = inquirer.prompt(questions)
        args.exchange = args.exchange or answers.get('exchange')
        args.strategy = args.strategy or answers.get('strategy')
        args.account_name = args.account_name or answers.get('account_name')

    return args

class DirectionalMarketMaker:
    def __init__(self, config: Config, exchange_name: str, account_name: str):
        self.config = config
        self.exchange_name = exchange_name
        self.account_name = account_name
        exchange_config = None

        for exch in config.exchanges:
            if exch.name == exchange_name and exch.account_name == account_name:  # Check both fields
                exchange_config = exch
                break

        if not exchange_config:
            raise ValueError(f"Exchange {exchange_name} with account {account_name} not found in the configuration file.")
        
        api_key = exchange_config.api_key
        secret_key = exchange_config.api_secret
        passphrase = exchange_config.passphrase
        
        # if exchange_name.lower() == 'bybit' or exchange_name.lower() == 'bybit_spot':
        #     market_type = 'spot' if exchange_name.lower() == 'bybit_spot' else 'swap'
        #     self.exchange = BybitExchange(api_key, secret_key, passphrase, market_type)
        if exchange_name.lower() == 'bybit':
            market_type = 'swap'
            self.exchange = BybitExchange(api_key, secret_key, passphrase, market_type)
        elif exchange_name.lower() == 'bybit_spot':
            market_type = 'spot'
            self.exchange = BybitExchange(api_key, secret_key, passphrase, market_type)
        elif exchange_name.lower() == 'hyperliquid':
            self.exchange = HyperLiquidExchange(api_key, secret_key, passphrase)
        elif exchange_name.lower() == 'huobi':
            self.exchange = HuobiExchange(api_key, secret_key, passphrase)
        elif exchange_name.lower() == 'bitget':
            self.exchange = BitgetExchange(api_key, secret_key, passphrase)
        elif exchange_name.lower() == 'binance':
            self.exchange = BinanceExchange(api_key, secret_key, passphrase)
        elif exchange_name.lower() == 'mexc':
            self.exchange = MexcExchange(api_key, secret_key, passphrase)
        elif exchange_name.lower() == 'lbank':
            self.exchange = LBankExchange(api_key, secret_key, passphrase)
        else:
            self.exchange = Exchange(self.exchange_name, api_key, secret_key, passphrase)

    def run_strategy(self, symbol, strategy_name, config, account_name, symbols_to_trade=None, rotator_symbols_standardized=None):
        symbols_allowed = None
        for exch in config.exchanges:
            #print(f"Checking: {exch.name} vs {self.exchange_name} and {exch.account_name} vs {account_name}")
            if exch.name == self.exchange_name and exch.account_name == account_name:
                symbols_allowed = exch.symbols_allowed
                print(f"Matched exchange: {exchange_name}, account: {args.account_name}. Symbols allowed: {symbols_allowed}")
                break

        print(f"Multibot.py: symbols_allowed from config: {symbols_allowed}")
        
        if symbols_to_trade:
            print(f"Calling run method with symbols: {symbols_to_trade}")

        # Pass symbols_allowed to the strategy constructors
        if strategy_name.lower() == 'bybit_1m_qfl_mfi_eri_walls':
            strategy = bybit_scalping.BybitMMOneMinuteQFLMFIERIWalls(self.exchange, self.manager, config.bot, symbols_allowed)
            strategy.run(symbol, rotator_symbols_standardized=rotator_symbols_standardized)
        elif strategy_name.lower() == 'bybit_1m_qfl_mfi_eri_autohedge_walls_atr':
            strategy = bybit_hedging.BybitMMOneMinuteQFLMFIERIAutoHedgeWallsATR(self.exchange, self.manager, config.bot, symbols_allowed)
            strategy.run(symbol, rotator_symbols_standardized=rotator_symbols_standardized)
        elif strategy_name.lower() == 'bybit_mfirsi_imbalance':
            strategy = bybit_scalping.BybitMFIRSIERIOBImbalance(self.exchange, self.manager, config.bot, symbols_allowed)
            strategy.run(symbol, rotator_symbols_standardized=rotator_symbols_standardized)
        elif strategy_name.lower() == 'bybit_mfirsi_quickscalp':
            strategy = bybit_scalping.BybitMFIRSIQuickScalp(self.exchange, self.manager, config.bot, symbols_allowed)
            strategy.run(symbol, rotator_symbols_standardized=rotator_symbols_standardized)
        elif strategy_name.lower() == 'qstrend':
            strategy = bybit_scalping.BybitQuickScalpTrend(self.exchange, self.manager, config.bot, symbols_allowed)
            strategy.run(symbol, rotator_symbols_standardized=rotator_symbols_standardized)
        elif strategy_name.lower() == 'qstrend_dca':
            strategy = bybit_scalping.BybitQuickScalpTrendDCA(self.exchange, self.manager, config.bot, symbols_allowed)
            strategy.run(symbol, rotator_symbols_standardized=rotator_symbols_standardized)
        elif strategy_name.lower() == 'mfieritrend':
            strategy = bybit_scalping.BybitMFIERILongShortTrend(self.exchange, self.manager, config.bot, symbols_allowed)
            strategy.run(symbol, rotator_symbols_standardized=rotator_symbols_standardized)
        elif strategy_name.lower() == 'qstrendlongonly':
            strategy = bybit_scalping.BybitMFIRSIQuickScalpLong(self.exchange, self.manager, config.bot, symbols_allowed)
            strategy.run(symbol, rotator_symbols_standardized=rotator_symbols_standardized)
        elif strategy_name.lower() == 'qstrendshortonly':
            strategy = bybit_scalping.BybitMFIRSIQuickScalpShort(self.exchange, self.manager, config.bot, symbols_allowed)
            strategy.run(symbol, rotator_symbols_standardized=rotator_symbols_standardized)
        elif strategy_name.lower() == 'qstrendob':
            strategy = bybit_scalping.BybitQuickScalpTrendOB(self.exchange, self.manager, config.bot, symbols_allowed)
            strategy.run(symbol, rotator_symbols_standardized=rotator_symbols_standardized)
        elif strategy_name.lower() == 'qstrend_unified':
            strategy = bybit_scalping.BybitQuickScalpUnified(self.exchange, self.manager, config.bot, symbols_allowed)
            strategy.run(symbol, rotator_symbols_standardized=rotator_symbols_standardized)
        elif strategy_name.lower() == 'qstrendemas':
            strategy = bybit_scalping.BybitQSTrendDoubleMA(self.exchange, self.manager, config.bot, symbols_allowed)
            strategy.run(symbol, rotator_symbols_standardized=rotator_symbols_standardized)
        elif strategy_name.lower() == 'basicgrid':
            strategy = bybit_scalping.BybitBasicGrid(self.exchange, self.manager, config.bot, symbols_allowed)
            strategy.run(symbol, rotator_symbols_standardized=rotator_symbols_standardized)
        elif strategy_name.lower() == 'basicgridmfirsi':
            strategy = bybit_scalping.BybitBasicGridMFIRSI(self.exchange, self.manager, config.bot, symbols_allowed)
            strategy.run(symbol, rotator_symbols_standardized=rotator_symbols_standardized)
        elif strategy_name.lower() == 'basicgridmfipersist':
            strategy = bybit_scalping.BybitBasicGridMFIRSIPersisent(self.exchange, self.manager, config.bot, symbols_allowed)
            strategy.run(symbol, rotator_symbols_standardized=rotator_symbols_standardized)
        elif strategy_name.lower() == 'qstrendspot':
            strategy = bybit_scalping.BybitQuickScalpTrendSpot(self.exchange, self.manager, config.bot, symbols_allowed)
            strategy.run(symbol, rotator_symbols_standardized=rotator_symbols_standardized)


    def get_balance(self, quote, market_type=None, sub_type=None):
        if self.exchange_name == 'bitget':
            return self.exchange.get_balance_bitget(quote)
        elif self.exchange_name == 'bybit':
            #self.exchange.retry_api_call(self.exchange.get_balance_bybit, quote)
            # return self.exchange.retry_api_call(self.exchange.get_balance_bybit(quote))
            return self.exchange.get_balance_bybit(quote)
        elif self.exchange_name == 'bybit_unified':
            return self.exchange.retry_api_call(self.exchange.get_balance_bybit(quote))
        elif self.exchange_name == 'mexc':
            return self.exchange.get_balance_mexc(quote, market_type='swap')
        elif self.exchange_name == 'huobi':
            print("Huobi starting..")
        elif self.exchange_name == 'okx':
            print(f"Unsupported for now")
        elif self.exchange_name == 'binance':
            return self.exchange.get_balance_binance(quote)
        elif self.exchange_name == 'phemex':
            print(f"Unsupported for now")

    def create_order(self, symbol, order_type, side, amount, price=None):
        return self.exchange.create_order(symbol, order_type, side, amount, price)

    def get_symbols(self):
        return self.exchange.symbols


BALANCE_REFRESH_INTERVAL = 600  # in seconds

def run_bot(symbol, args, manager, account_name, symbols_allowed, rotator_symbols_standardized):
    current_thread = threading.current_thread()

    try:
        with thread_to_symbol_lock:
            thread_to_symbol[current_thread] = symbol

            time.sleep(1)

        # Correct the path for the configuration file
        if not args.config.startswith('configs/'):
            config_file_path = Path('configs/' + args.config)
        else:
            config_file_path = Path(args.config)
        print("Loading config from:", config_file_path)
        config = load_config(config_file_path)

        # Initialize balance cache and last fetch time at the beginning
        cached_balance = None
        last_balance_fetch_time = 0

        exchange_name = args.exchange  # These are now guaranteed to be non-None
        strategy_name = args.strategy
        account_name = args.account_name  # Get the account_name from args

        print(f"Trading symbol: {symbol}")
        print(f"Exchange name: {exchange_name}")
        print(f"Strategy name: {strategy_name}")
        print(f"Account name: {account_name}") 

        # Pass account_name to DirectionalMarketMaker constructor
        market_maker = DirectionalMarketMaker(config, exchange_name, account_name)
        market_maker.manager = manager
        
        # Pass rotator_symbols_standardized to the run_strategy method
        market_maker.run_strategy(symbol, strategy_name, config, account_name, symbols_to_trade=symbols_allowed, rotator_symbols_standardized=rotator_symbols_standardized)

        quote = "USDT"
        current_time = time.time()
        # if current_time - last_balance_fetch_time > BALANCE_REFRESH_INTERVAL or not cached_balance:
        #     if exchange_name.lower() == 'huobi':
        #         print(f"Loading huobi strategy..")
        #     elif exchange_name.lower() == 'mexc':
        #         cached_balance = market_maker.get_balance(quote, type='swap')
        #         print(f"Futures balance: {cached_balance}")
        #     else:
        #         cached_balance = market_maker.get_balance(quote)
        #         print(f"Futures balance: {cached_balance}")
        #     last_balance_fetch_time = current_time
    except Exception as e:
        logging.error(f"An error occurred in run_bot for symbol {symbol}: {e}")

    finally:
        with thread_to_symbol_lock:
            if current_thread in thread_to_symbol:
                del thread_to_symbol[current_thread]
        logging.info(f"Thread for symbol {symbol} has completed.")

def start_thread_for_symbol(symbol, args, manager, account_name, symbols_allowed, rotator_symbols_standardized):
    time.sleep(1)
    if symbol in active_symbols:
        logging.info(f"Symbol {symbol} is already being processed by another thread.")
        return

    thread = threading.Thread(target=run_bot, args=(symbol, args, manager, account_name, symbols_allowed, rotator_symbols_standardized))
    thread.start()
    active_threads.append(thread)
    thread_to_symbol[thread] = symbol  # Associate the thread with the symbol
    active_symbols.add(symbol)  # Mark the symbol as active
    logging.info(f"Started thread for symbol: {symbol}")


def start_threads_for_new_symbols(new_symbols, args, manager, account_name, symbols_allowed, rotator_symbols_standardized):
    for symbol in new_symbols:
        time.sleep(1)
        start_thread_for_symbol(symbol, args, manager, account_name, symbols_allowed, rotator_symbols_standardized)

def rotate_inactive_symbols(active_symbols, rotator_symbols_queue, thread_start_time, rotation_threshold=60, max_symbols_allowed=5):
    current_time = time.time()
    rotated_out_symbols = []
    added_symbols = []

    for symbol in list(active_symbols):
        if current_time - thread_start_time.get(symbol, 0) > rotation_threshold:
            active_symbols.remove(symbol)
            del thread_start_time[symbol]  # Remove symbol from thread_start_time tracking
            rotated_out_symbols.append(symbol)

            # Add new symbol from the rotator queue if it doesn't exceed max_symbols_allowed
            while len(rotator_symbols_queue) > 0 and len(active_symbols) < max_symbols_allowed:
                new_symbol = rotator_symbols_queue.popleft()  # Get the next symbol from the queue
                if new_symbol not in active_symbols:
                    active_symbols.add(new_symbol)
                    thread_start_time[new_symbol] = current_time
                    added_symbols.append(new_symbol)
                    rotator_symbols_queue.append(new_symbol)  # Add it back to the end of the queue
                    break

    if rotated_out_symbols:
        logging.info(f"Rotated out symbols: {rotated_out_symbols}")
    if added_symbols:
        logging.info(f"Added new symbols: {added_symbols}")

    return active_symbols, thread_start_time


# Define the update function for the rotator queue
def update_rotator_queue(rotator_queue, latest_symbols):
    # Convert the queue to a set for efficient operations
    rotator_set = set(rotator_queue)
    # Add new symbols to the set
    rotator_set.update(latest_symbols)
    # Remove symbols no longer in the latest list
    rotator_set.intersection_update(latest_symbols)
    time.sleep(1)
    # Return a new deque from the updated set
    return deque(rotator_set)

last_rotator_update_time = 0

def bybit_auto_rotation(args, manager, symbols_allowed):
    global latest_rotator_symbols, last_rotator_update_time

    try:
        current_time = time.time()

        # Fetching open position symbols and standardizing them
        if args.exchange.lower() == 'bybit':
            open_position_symbols = {standardize_symbol(pos['symbol']) for pos in market_maker.exchange.get_all_open_positions_bybit()}
        elif args.exchange.lower() == 'bybit_spot':
            open_position_symbols = {standardize_symbol(pos['symbol']) for pos in market_maker.exchange.get_all_open_positions_bybit_spot()}
        
        logging.info(f"Open position symbols: {open_position_symbols}")

        if current_time - last_rotator_update_time >= 50:  # Update every 50 seconds
            strategy_name = args.strategy.lower()
            long_mode = config.bot.linear_grid['long_mode']
            short_mode = config.bot.linear_grid['short_mode']

            if strategy_name == 'basicgrid':
                if long_mode and not short_mode:
                    # Fetching only bullish symbols from manager for BybitBasicGrid strategy
                    potential_symbols = manager.get_bullish_rotator_symbols(min_qty_threshold=None, blacklist=blacklist, whitelist=whitelist, max_usd_value=max_usd_value)
                    logging.info(f"Potential bullish symbols for BybitBasicGrid: {potential_symbols}")
                elif short_mode and not long_mode:
                    # Fetching only bearish symbols from manager for BybitBasicGrid strategy
                    potential_symbols = manager.get_bearish_rotator_symbols(min_qty_threshold=None, blacklist=blacklist, whitelist=whitelist, max_usd_value=max_usd_value)
                    logging.info(f"Potential bearish symbols for BybitBasicGrid: {potential_symbols}")
                else:
                    # Fetching both bullish and bearish symbols from manager for BybitBasicGrid strategy
                    potential_bullish_symbols = manager.get_bullish_rotator_symbols(min_qty_threshold=None, blacklist=blacklist, whitelist=whitelist, max_usd_value=max_usd_value)
                    potential_bearish_symbols = manager.get_bullish_rotator_symbols(min_qty_threshold=None, blacklist=blacklist, whitelist=whitelist, max_usd_value=max_usd_value)
                    potential_symbols = potential_bullish_symbols + potential_bearish_symbols
                    logging.info(f"Potential bullish and bearish symbols for BybitBasicGrid: {potential_symbols}")
            elif strategy_name == 'basicgridmfirsi':
                if long_mode and not short_mode:
                    # Fetching only bullish symbols with MFIRSI signal from manager for BybitBasicGridMFIRSI strategy
                    potential_symbols = manager.get_bullish_rotator_symbols(min_qty_threshold=None, blacklist=blacklist, whitelist=whitelist, max_usd_value=max_usd_value)
                    logging.info(f"Potential bullish symbols with MFIRSI signal for BybitBasicGridMFIRSI: {potential_symbols}")
                elif short_mode and not long_mode:
                    # Fetching only bearish symbols with MFIRSI signal from manager for BybitBasicGridMFIRSI strategy
                    potential_symbols = manager.get_bullish_rotator_symbols(min_qty_threshold=None, blacklist=blacklist, whitelist=whitelist, max_usd_value=max_usd_value)
                    logging.info(f"Potential bearish symbols with MFIRSI signal for BybitBasicGridMFIRSI: {potential_symbols}")
                else:
                    # Fetching both bullish and bearish symbols with MFIRSI signal from manager for BybitBasicGridMFIRSI strategy
                    potential_bullish_symbols = manager.get_bullish_rotator_symbols(min_qty_threshold=None, blacklist=blacklist, whitelist=whitelist, max_usd_value=max_usd_value)
                    potential_bearish_symbols = manager.get_bearish_rotator_symbols(min_qty_threshold=None, blacklist=blacklist, whitelist=whitelist, max_usd_value=max_usd_value)
                    potential_symbols = potential_bullish_symbols + potential_bearish_symbols
                    logging.info(f"Potential bullish and bearish symbols with MFIRSI signal for BybitBasicGridMFIRSI: {potential_symbols}")
            elif strategy_name == 'basicgridmfipersist':
                if long_mode and not short_mode:
                    # Fetching only bullish symbols with MFIRSI signal from manager for BybitBasicGridMFIPersist strategy
                    potential_symbols = manager.get_bullish_rotator_symbols(min_qty_threshold=None, blacklist=blacklist, whitelist=whitelist, max_usd_value=max_usd_value)
                    logging.info(f"Potential bullish symbols with MFIRSI signal for BybitBasicGridMFIPersist: {potential_symbols}")
                elif short_mode and not long_mode:
                    # Fetching only bearish symbols with MFIRSI signal from manager for BybitBasicGridMFIPersist strategy
                    potential_symbols = manager.get_bullish_rotator_symbols(min_qty_threshold=None, blacklist=blacklist, whitelist=whitelist, max_usd_value=max_usd_value)
                    logging.info(f"Potential bearish symbols with MFIRSI signal for BybitBasicGridMFIPersist: {potential_symbols}")
                else:
                    # Fetching both bullish and bearish symbols with MFIRSI signal from manager for BybitBasicGridMFIPersist strategy
                    potential_bullish_symbols = manager.get_bullish_rotator_symbols(min_qty_threshold=None, blacklist=blacklist, whitelist=whitelist, max_usd_value=max_usd_value)
                    potential_bearish_symbols = manager.get_bearish_rotator_symbols(min_qty_threshold=None, blacklist=blacklist, whitelist=whitelist, max_usd_value=max_usd_value)
                    potential_symbols = potential_bullish_symbols + potential_bearish_symbols
                    logging.info(f"Potential bullish and bearish symbols with MFIRSI signal for BybitBasicGridMFIPersist: {potential_symbols}")
            elif strategy_name == 'qstrendlongonly':
                # Fetching only bullish symbols from manager for BybitMFIRSIQuickScalpLong strategy
                potential_symbols = manager.get_bullish_rotator_symbols(min_qty_threshold=None, blacklist=blacklist, whitelist=whitelist, max_usd_value=max_usd_value)
                logging.info(f"Potential bullish symbols for BybitMFIRSIQuickScalpLong: {potential_symbols}")
            elif strategy_name == 'qstrendshortonly':
                # Fetching only bearish symbols from manager for BybitMFIRSIQuickScalpShort strategy
                potential_symbols = manager.get_bearish_rotator_symbols(min_qty_threshold=None, blacklist=blacklist, whitelist=whitelist, max_usd_value=max_usd_value)
                logging.info(f"Potential bearish symbols for BybitMFIRSIQuickScalpShort: {potential_symbols}")
            else:
                # Fetching potential symbols from manager for other strategies
                potential_symbols = manager.get_auto_rotate_symbols(min_qty_threshold=None, blacklist=blacklist, whitelist=whitelist, max_usd_value=max_usd_value)
                logging.info(f"Potential symbols: {potential_symbols}")

            latest_rotator_symbols = set(standardize_symbol(sym) for sym in potential_symbols)
            logging.info(f"Latest rotator symbols: {latest_rotator_symbols}")

            last_rotator_update_time = current_time  # Update the last update time


        # Thread management
        running_threads_info = []
        for symbol, thread in list(threads.items()):
            if thread.is_alive():
                running_threads_info.append(symbol)
            else:
                logging.info(f"Thread for symbol {symbol} is not alive and will be removed.")
                active_symbols.discard(symbol)
                del threads[symbol]
                thread_start_time.pop(symbol, None)
                logging.info(f"Thread for symbol {symbol} has been removed.")
        logging.info(f"Currently running threads for symbols: {running_threads_info}")

        # Check to ensure a thread exists for each open position symbol
        for open_pos_symbol in open_position_symbols:
            if open_pos_symbol not in threads or not threads[open_pos_symbol].is_alive():
                logging.warning(f"No active thread for open position symbol: {open_pos_symbol}. Starting a new thread.")
                new_thread = threading.Thread(target=run_bot, args=(open_pos_symbol, args, manager, args.account_name, symbols_allowed, latest_rotator_symbols))
                new_thread.start()
                threads[open_pos_symbol] = new_thread
                active_symbols.add(open_pos_symbol)
                thread_start_time[open_pos_symbol] = time.time()

        # Start threads for symbols with open positions
        for symbol in open_position_symbols:
            if symbol not in active_symbols and len(active_symbols) < symbols_allowed:
                logging.info(f"Starting thread for open position symbol: {symbol}")
                thread = threading.Thread(target=run_bot, args=(symbol, args, manager, args.account_name, symbols_allowed, latest_rotator_symbols))
                thread.start()
                threads[symbol] = thread
                active_symbols.add(symbol)
                thread_start_time[symbol] = time.time()

        # Start threads for additional symbols from latest_rotator_symbols
        for symbol in latest_rotator_symbols:
            if symbol not in active_symbols and len(active_symbols) < symbols_allowed:
                logging.info(f"Starting thread for additional symbol: {symbol}")
                thread = threading.Thread(target=run_bot, args=(symbol, args, manager, args.account_name, symbols_allowed, latest_rotator_symbols))
                thread.start()
                threads[symbol] = thread
                active_symbols.add(symbol)
                thread_start_time[symbol] = time.time()

        # Rotate out inactive symbols and replace with new ones
        for symbol in list(active_symbols):
            if symbol not in open_position_symbols and current_time - thread_start_time.get(symbol, 0) > rotation_threshold:
                if latest_rotator_symbols:
                    available_symbols = latest_rotator_symbols - active_symbols
                    if available_symbols:
                        new_symbol = random.choice(list(available_symbols))
                        logging.info(f"Rotating out inactive symbol {symbol} for new symbol {new_symbol}")
                        if threads.get(symbol):
                            thread = threads[symbol]
                            thread.join(timeout=10)
                            if thread.is_alive():
                                logging.warning(f"Thread {symbol} still running after timeout. Skipping termination.")
                        active_symbols.discard(symbol)
                        del threads[symbol]
                        thread_start_time.pop(symbol, None)
                        new_thread = threading.Thread(target=run_bot, args=(new_symbol, args, manager, args.account_name, symbols_allowed, latest_rotator_symbols))
                        new_thread.start()
                        threads[new_symbol] = new_thread
                        active_symbols.add(new_symbol)
                        thread_start_time[new_symbol] = time.time()
                        latest_rotator_symbols.discard(new_symbol)
                    else:
                        logging.info(f"No available new symbols to replace {symbol}")
    except Exception as e:
        logging.error(f"Exception caught in bybit_auto_rotation: {str(e)}")
        # Log the traceback for more detailed information
        logging.error(traceback.format_exc())
        
def hyperliquid_auto_rotation(args, manager, symbols_allowed):
    # Fetching open position symbols and standardizing them
    open_position_symbols = {standardize_symbol(pos['symbol']) for pos in market_maker.exchange.get_all_open_positions_hyperliquid()}
    logging.info(f"Open position symbols: {open_position_symbols}")

    # Implement HyperLiquid-specific auto-rotation logic here
    # ...

def huobi_auto_rotation(args, manager, symbols_allowed):
    # Fetching open position symbols and standardizing them
    open_position_symbols = {standardize_symbol(pos['symbol']) for pos in market_maker.exchange.get_all_open_positions_huobi()}
    logging.info(f"Open position symbols: {open_position_symbols}")

    # Implement Huobi-specific auto-rotation logic here
    # ...

def bitget_auto_rotation(args, manager, symbols_allowed):
    # Fetching open position symbols and standardizing them
    open_position_symbols = {standardize_symbol(pos['symbol']) for pos in market_maker.exchange.get_all_open_positions_bitget()}
    logging.info(f"Open position symbols: {open_position_symbols}")

    # Implement Bitget-specific auto-rotation logic here
    # ...

def binance_auto_rotation(args, manager, symbols_allowed):
    # Fetching open position symbols and standardizing them
    open_position_symbols = {standardize_symbol(pos['symbol']) for pos in market_maker.exchange.get_all_open_positions_binance()}
    logging.info(f"Open position symbols: {open_position_symbols}")

    # Implement Binance-specific auto-rotation logic here
    # ...

def mexc_auto_rotation(args, manager, symbols_allowed):
    # Fetching open position symbols and standardizing them
    open_position_symbols = {standardize_symbol(pos['symbol']) for pos in market_maker.exchange.get_all_open_positions_binance()}
    logging.info(f"Open position symbols: {open_position_symbols}")

    # Implement Binance-specific auto-rotation logic here
    # ...

def lbank_auto_rotation(args, manager, symbols_allowed):
    # Fetching open position symbols and standardizing them
    open_position_symbols = {standardize_symbol(pos['symbol']) for pos in market_maker.exchange.get_all_open_positions_binance()}
    logging.info(f"Open position symbols: {open_position_symbols}")

    # Implement Binance-specific auto-rotation logic here
    # ...
    

if __name__ == '__main__':
    # ASCII Art and Text
    sword = "====||====>"

    print("\n" + "=" * 50)
    print(f"DirectionalScalper {VERSION}".center(50))
    print(f"Developed by Tyler Simpson and contributors at Quantum Void Labs".center(50))
    print("=" * 50 + "\n")

    print("Initializing", end="")
    # Loading animation
    for i in range(3):
        time.sleep(0.5)
        print(".", end="", flush=True)
    print("\n")

    # Display the ASCII art
    print("Battle-Ready Algorithm".center(50))
    print(sword.center(50) + "\n")

    parser = argparse.ArgumentParser(description='DirectionalScalper')
    parser.add_argument('--config', type=str, default='configs/config.json', help='Path to the configuration file')
    parser.add_argument('--account_name', type=str, help='The name of the account to use')
    parser.add_argument('--exchange', type=str, help='The name of the exchange to use')
    parser.add_argument('--strategy', type=str, help='The name of the strategy to use')
    parser.add_argument('--symbol', type=str, help='The trading symbol to use')
    parser.add_argument('--amount', type=str, help='The size to use')

    args = parser.parse_args()

    args = ask_for_missing_arguments(args)

    print(f"DirectionalScalper {VERSION} Initialized Successfully!".center(50))
    print("=" * 50 + "\n")

    # Correct the path for the configuration file
    if not args.config.startswith('configs/'):
        config_file_path = Path('configs/' + args.config)
    else:
        config_file_path = Path(args.config)

    config = load_config(config_file_path)

    # config_file_path = Path('configs/' + args.config)
    # config = load_config(config_file_path)

    exchange_name = args.exchange  # Now it will have a value
    market_maker = DirectionalMarketMaker(config, exchange_name, args.account_name)

    manager = Manager(
        market_maker.exchange, 
        exchange_name=args.exchange, 
        data_source_exchange=config.api.data_source_exchange,
        api=config.api.mode, 
        path=Path("data", config.api.filename), 
        url=f"{config.api.url}{config.api.filename}"
    )

    print(f"Using exchange {config.api.data_source_exchange} for API data")

    whitelist = config.bot.whitelist
    blacklist = config.bot.blacklist
    max_usd_value = config.bot.max_usd_value

    # symbols_allowed = config.bot.symbols_allowed

    # Loop through the exchanges to find the correct exchange and account name
    for exch in config.exchanges:
        if exch.name == exchange_name and exch.account_name == args.account_name:
            logging.info(f"Symbols allowed changed to symbols_allowed from config")
            symbols_allowed = exch.symbols_allowed
            break
    else:
        # Default to a reasonable value if symbols_allowed is None
        logging.info(f"Symbols allowed defaulted to 10")
        symbols_allowed = 10  # You can choose an appropriate default value

    ### ILAY ###
    table_manager = LiveTableManager()
    display_thread = threading.Thread(target=table_manager.display_table)
    display_thread.daemon = True
    display_thread.start()
    ### ILAY ###

    # Fetch all symbols that meet your criteria and standardize them
    all_symbols_standardized = [standardize_symbol(symbol) for symbol in manager.get_auto_rotate_symbols(min_qty_threshold=None, blacklist=blacklist, whitelist=whitelist, max_usd_value=max_usd_value)]

    # Get symbols with open positions and standardize them
    open_position_data = market_maker.exchange.get_all_open_positions_bybit()
    open_positions_symbols = [standardize_symbol(position['symbol']) for position in open_position_data]

    print(f"Open positions symbols: {open_positions_symbols}")

    # Combine open positions symbols with potential new symbols
    symbols_to_trade = list(set(open_positions_symbols + all_symbols_standardized[:symbols_allowed]))

    print(f"Symbols to trade: {symbols_to_trade}")

    rotation_threshold = 30  # Adjust as necessary

    while True:
        try:
            # Fetching symbols from the config
            whitelist = config.bot.whitelist
            blacklist = config.bot.blacklist
            max_usd_value = config.bot.max_usd_value

            if exchange_name.lower() == 'bybit':
                bybit_auto_rotation(args, manager, symbols_allowed)
            elif exchange_name.lower() == 'hyperliquid':
                hyperliquid_auto_rotation(args, manager, symbols_allowed)
            elif exchange_name.lower() == 'huobi':
                huobi_auto_rotation(args, manager, symbols_allowed)
            elif exchange_name.lower() == 'bitget':
                bitget_auto_rotation(args, manager, symbols_allowed)
            elif exchange_name.lower() == 'binance':
                binance_auto_rotation(args, manager, symbols_allowed)
            elif exchange_name.lower() == 'mexc':
                mexc_auto_rotation(args, manager, symbols_allowed)
            elif exchange_name.lower() == 'lbank':
                lbank_auto_rotation(args, manager, symbols_allowed)
            else:
                logging.warning(f"Auto-rotation not implemented for exchange: {exchange_name}")

            logging.info(f"Active symbols: {active_symbols}")
            logging.info(f"Total active symbols: {len(active_symbols)}")

            time.sleep(15)
        except Exception as e:
            logging.error(f"Exception caught in main loop: {e}")