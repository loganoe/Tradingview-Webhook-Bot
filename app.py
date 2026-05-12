import json
from flask import Flask, render_template, request, jsonify
from pybit import HTTP
import time
import ccxt
from binanceFutures import Bot as BinanceFuturesBot
from binanceSpot import Bot as BinanceSpotBot
from kucoin import Bot as KuCoinBot

def validate_bybit_api_key(session):
    try:
        result = session.get_api_key_info()
        return True
    except Exception as e:
        print("Bybit API key validation failed:", str(e))
        return False

def validate_exchange_api_key(exchange, exchange_name):
    try:
        result = exchange.fetch_balance()
        return True
    except Exception as e:
        print(exchange_name + " API key validation failed:", str(e))
        return False

app = Flask(__name__)

# load config.json
with open('config.json') as config_file:
    config = json.load(config_file)

###############################################################################
#
#             This Section is for Exchange Validation
#
###############################################################################

use_bybit = False
if 'BYBIT' in config['EXCHANGES']:
    if config['EXCHANGES']['BYBIT']['ENABLED']:
        print("Bybit is enabled!")
        use_bybit = True

    session = HTTP(
        endpoint='https://api.bybit.com',
        api_key=config['EXCHANGES']['BYBIT']['API_KEY'],
        api_secret=config['EXCHANGES']['BYBIT']['API_SECRET']
    )

use_binance_futures = False
binance_futures_exchange = None
if 'BINANCE-FUTURES' in config['EXCHANGES']:
    if config['EXCHANGES']['BINANCE-FUTURES']['ENABLED']:
        print("Binance Futures is enabled!")
        use_binance_futures = True

        binance_futures_options = {
            'apiKey': config['EXCHANGES']['BINANCE-FUTURES']['API_KEY'],
            'secret': config['EXCHANGES']['BINANCE-FUTURES']['API_SECRET'],
            'options': {
                'defaultType': 'future',
            },
        }
        if config['EXCHANGES']['BINANCE-FUTURES'].get('TESTNET'):
            binance_futures_options['urls'] = {
                'api': {
                    'public': 'https://testnet.binancefuture.com/fapi/v1',
                    'private': 'https://testnet.binancefuture.com/fapi/v1',
                },
            }

        binance_futures_exchange = ccxt.binance(binance_futures_options)
        if config['EXCHANGES']['BINANCE-FUTURES'].get('TESTNET'):
            binance_futures_exchange.set_sandbox_mode(True)

use_binance_spot = False
binance_spot_exchange = None
if 'BINANCE-SPOT' in config['EXCHANGES']:
    if config['EXCHANGES']['BINANCE-SPOT']['ENABLED']:
        print("Binance Spot is enabled!")
        use_binance_spot = True

        binance_spot_exchange = ccxt.binance({
            'apiKey': config['EXCHANGES']['BINANCE-SPOT']['API_KEY'],
            'secret': config['EXCHANGES']['BINANCE-SPOT']['API_SECRET'],
            'options': {
                'defaultType': 'spot',
            },
        })
        if config['EXCHANGES']['BINANCE-SPOT'].get('TESTNET'):
            binance_spot_exchange.set_sandbox_mode(True)

# Validate Bybit API key
if use_bybit:
    if not validate_bybit_api_key(session):
        print("Invalid Bybit API key.")
        use_bybit = False

# Validate Binance Futures API key
if use_binance_futures:
    if not validate_exchange_api_key(binance_futures_exchange, "Binance Futures"):
        print("Invalid Binance Futures API key.")
        use_binance_futures = False

# Validate Binance Spot API key
if use_binance_spot:
    if not validate_exchange_api_key(binance_spot_exchange, "Binance Spot"):
        print("Invalid Binance Spot API key.")
        use_binance_spot = False

use_kucoin = False
kucoin_exchange = None
if 'KUCOIN' in config['EXCHANGES']:
    if config['EXCHANGES']['KUCOIN']['ENABLED']:
        print("KuCoin is enabled!")
        use_kucoin = True

        kucoin_exchange = ccxt.kucoin({
            'apiKey': config['EXCHANGES']['KUCOIN']['API_KEY'],
            'secret': config['EXCHANGES']['KUCOIN']['API_SECRET'],
            'password': config['EXCHANGES']['KUCOIN']['API_PASSPHRASE'],
        })
        if config['EXCHANGES']['KUCOIN'].get('TESTNET'):
            kucoin_exchange.set_sandbox_mode(True)

# Validate KuCoin API key
if use_kucoin:
    if not validate_exchange_api_key(kucoin_exchange, "KuCoin"):
        print("Invalid KuCoin API key.")
        use_kucoin = False

@app.route('/')
def index():
    return {'message': 'Server is running!'}

@app.route('/webhook', methods=['POST'])
def webhook():
    print("Hook Received!")
    data = json.loads(request.data)
    print(data)

    if int(data['key']) != config['KEY']:
        print("Invalid Key, Please Try Again!")
        return {
            "status": "error",
            "message": "Invalid Key, Please Try Again!"
        }

    ##############################################################################
    #             Bybit
    ##############################################################################
    if data['exchange'] == 'bybit':

        if use_bybit:
            if data['close_position'] == 'True':
                print("Closing Position")
                session.close_position(symbol=data['symbol'])
            else:
                if 'cancel_orders' in data:
                    print("Cancelling Order")
                    session.cancel_all_active_orders(symbol=data['symbol'])
                if 'type' in data:
                    print("Placing Order")
                    if 'price' in data:
                        price = data['price']
                    else:
                        price = 0


                    if data['order_mode'] == 'Both':
                        take_profit_percent = float(data['take_profit_percent'])/100
                        stop_loss_percent = float(data['stop_loss_percent'])/100
                        current_price = session.latest_information_for_symbol(symbol=data['symbol'])['result'][0]['last_price']
                        if data['side'] == 'Buy':
                            take_profit_price = round(float(current_price) + (float(current_price) * take_profit_percent), 2)
                            stop_loss_price = round(float(current_price) - (float(current_price) * stop_loss_percent), 2)
                        elif data['side'] == 'Sell':
                            take_profit_price = round(float(current_price) - (float(current_price) * take_profit_percent), 2)
                            stop_loss_price = round(float(current_price) + (float(current_price) * stop_loss_percent), 2)

                        print("Take Profit Price: " + str(take_profit_price))
                        print("Stop Loss Price: " + str(stop_loss_price))

                        session.place_active_order(symbol=data['symbol'], order_type=data['type'], side=data['side'],
                                                   qty=data['qty'], time_in_force="GoodTillCancel", reduce_only=False,
                                                   close_on_trigger=False, price=price, take_profit=take_profit_price, stop_loss=stop_loss_price)

                    elif data['order_mode'] == 'Profit':
                        take_profit_percent = float(data['take_profit_percent'])/100
                        current_price = session.latest_information_for_symbol(symbol=data['symbol'])['result'][0]['last_price']
                        if data['side'] == 'Buy':
                            take_profit_price = round(float(current_price) + (float(current_price) * take_profit_percent), 2)
                        elif data['side'] == 'Sell':
                            take_profit_price = round(float(current_price) - (float(current_price) * take_profit_percent), 2)

                        print("Take Profit Price: " + str(take_profit_price))
                        session.place_active_order(symbol=data['symbol'], order_type=data['type'], side=data['side'],
                                                   qty=data['qty'], time_in_force="GoodTillCancel", reduce_only=False,
                                                   close_on_trigger=False, price=price, take_profit=take_profit_price)
                    elif data['order_mode'] == 'Stop':
                        stop_loss_percent = float(data['stop_loss_percent'])/100
                        current_price = session.latest_information_for_symbol(symbol=data['symbol'])['result'][0]['last_price']
                        if data['side'] == 'Buy':
                            stop_loss_price = round(float(current_price) - (float(current_price) * stop_loss_percent), 2)
                        elif data['side'] == 'Sell':
                            stop_loss_price = round(float(current_price) + (float(current_price) * stop_loss_percent), 2)

                        print("Stop Loss Price: " + str(stop_loss_price))
                        session.place_active_order(symbol=data['symbol'], order_type=data['type'], side=data['side'],
                                                   qty=data['qty'], time_in_force="GoodTillCancel", reduce_only=False,
                                                   close_on_trigger=False, price=price, stop_loss=stop_loss_price)

                    else:
                        session.place_active_order(symbol=data['symbol'], order_type=data['type'], side=data['side'],
                                                   qty=data['qty'], time_in_force="GoodTillCancel", reduce_only=False,
                                                   close_on_trigger=False, price=price)

        return {
            "status": "success",
            "message": "Bybit Webhook Received!"
        }
    ##############################################################################
    #             Binance Futures
    ##############################################################################
    if data['exchange'] == 'binance-futures':
        if use_binance_futures:
            bot = BinanceFuturesBot(exchange_override=binance_futures_exchange)
            bot.run(data)
            return {
                "status": "success",
                "message": "Binance Futures Webhook Received!"
            }
    ##############################################################################
    #             Binance Spot
    ##############################################################################
    if data['exchange'] == 'binance-spot':
        if use_binance_spot:
            bot = BinanceSpotBot(exchange_override=binance_spot_exchange)
            bot.run(data)
            return {
                "status": "success",
                "message": "Binance Spot Webhook Received!"
            }
    ##############################################################################
    #             KuCoin
    ##############################################################################
    if data['exchange'] == 'kucoin':
        if use_kucoin:
            bot = KuCoinBot(exchange_override=kucoin_exchange)
            bot.run(data)
            return {
                "status": "success",
                "message": "KuCoin Webhook Received!"
            }

    print("Invalid Exchange, Please Try Again!")
    return {
        "status": "error",
        "message": "Invalid Exchange, Please Try Again!"
    }

if __name__ == '__main__':
    app.run(debug=False)
