import unittest

from kucoin import Bot


class FakeExchange:
    def __init__(self):
        self.orders = []
        self.cancelled_symbols = []
        self.balance = {'KCS': {'free': 12}}

    def create_order(self, symbol, order_type, side, amount, price=None, params=None):
        order = {
            'symbol': symbol,
            'type': order_type,
            'side': side,
            'amount': amount,
            'price': price,
            'params': params or {},
        }
        self.orders.append(order)
        return order

    def cancel_all_orders(self, symbol):
        self.cancelled_symbols.append(symbol)

    def fetch_balance(self):
        return self.balance


class KuCoinBotTest(unittest.TestCase):
    def test_places_market_order(self):
        exchange = FakeExchange()
        bot = Bot(exchange_override=exchange)

        bot.run({
            'symbol': 'KCS/USDT',
            'type': 'Market',
            'side': 'Buy',
            'qty': '2',
            'close_position': 'False',
        })

        self.assertEqual(exchange.orders[0]['symbol'], 'KCS/USDT')
        self.assertEqual(exchange.orders[0]['type'], 'market')
        self.assertEqual(exchange.orders[0]['side'], 'buy')
        self.assertEqual(exchange.orders[0]['amount'], 2)
        self.assertIsNone(exchange.orders[0]['price'])
        self.assertIn('clientOid', exchange.orders[0]['params'])

    def test_places_limit_order_with_price(self):
        exchange = FakeExchange()
        bot = Bot(exchange_override=exchange)

        bot.run({
            'symbol': 'KCS/USDT',
            'type': 'Limit',
            'side': 'Sell',
            'qty': '3.5',
            'price': '15.25',
            'close_position': 'False',
        })

        self.assertEqual(exchange.orders[0]['type'], 'limit')
        self.assertEqual(exchange.orders[0]['side'], 'sell')
        self.assertEqual(exchange.orders[0]['amount'], 3.5)
        self.assertEqual(exchange.orders[0]['price'], 15.25)

    def test_cancels_open_orders_before_placing_order(self):
        exchange = FakeExchange()
        bot = Bot(exchange_override=exchange)

        bot.run({
            'symbol': 'KCS/USDT',
            'type': 'Market',
            'side': 'Buy',
            'qty': '2',
            'close_position': 'False',
            'cancel_orders': 'True',
        })

        self.assertEqual(exchange.cancelled_symbols, ['KCS/USDT'])
        self.assertEqual(len(exchange.orders), 1)

    def test_close_position_sells_available_base_balance(self):
        exchange = FakeExchange()
        bot = Bot(exchange_override=exchange)

        bot.run({
            'symbol': 'KCS/USDT',
            'close_position': 'True',
        })

        self.assertEqual(exchange.orders[0]['type'], 'market')
        self.assertEqual(exchange.orders[0]['side'], 'sell')
        self.assertEqual(exchange.orders[0]['amount'], 12)


if __name__ == '__main__':
    unittest.main()
