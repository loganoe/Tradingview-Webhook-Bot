import json
import random
import string

import ccxt

with open('config.json') as config_file:
    config = json.load(config_file)


exchange_config = (
    config['EXCHANGES'].get('BINANCE-SPOT')
    or config['EXCHANGES'].get('binance-spot')
    or {}
)

exchange = ccxt.binance({
    'apiKey': exchange_config.get('API_KEY', ''),
    'secret': exchange_config.get('API_SECRET', ''),
    'options': {
        'defaultType': 'spot',
    },
})

if exchange_config.get('TESTNET'):
    exchange.set_sandbox_mode(True)


class Bot:

    def __init__(self, exchange_override=None):
        self.exchange = exchange_override or exchange

    def create_string(self):
        token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
        self.clientId = 'x-40PTWbMI' + token

    def close_position(self, symbol):
        base_currency = symbol.split('/')[0]
        balance = self.exchange.fetch_balance()
        free_balance = balance.get(base_currency, {}).get('free')

        if free_balance is None:
            free_balance = balance.get('free', {}).get(base_currency, 0)

        amount = float(free_balance or 0)
        if amount <= 0:
            print("No Binance Spot balance available to close for " + base_currency)
            return None

        self.create_string()
        return self.exchange.create_order(
            symbol,
            'market',
            'sell',
            amount,
            params={"newClientOrderId": self.clientId}
        )

    def run(self, data):
        if data['close_position'] == 'True':
            print("Closing Binance Spot position")
            return self.close_position(symbol=data['symbol'])

        if 'cancel_orders' in data:
            print("Cancelling Binance Spot orders")
            self.exchange.cancel_all_orders(symbol=data['symbol'])

        if 'type' not in data:
            return {'status': 'success'}

        print("Placing Binance Spot order")
        self.create_string()
        order_type = data['type'].lower()
        side = data['side'].lower()
        price = float(data['price']) if order_type == 'limit' and 'price' in data else None

        params = {"newClientOrderId": self.clientId}
        return self.exchange.create_order(
            data['symbol'],
            order_type,
            side,
            float(data['qty']),
            price=price,
            params=params
        )
