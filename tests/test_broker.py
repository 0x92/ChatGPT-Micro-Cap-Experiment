import pathlib
from pathlib import Path
import sys
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import os
import json
from unittest import mock

import pytest

import importlib
import src.broker as broker
from src.broker import place_order, get_account, list_positions


def test_place_order_makes_request(monkeypatch):
    calls = {}

    def fake_post(url, json=None, headers=None, timeout=10):
        calls['url'] = url
        calls['json'] = json
        calls['headers'] = headers
        class Resp:
            def raise_for_status(self):
                pass
            def json(self):
                return {'status': 'accepted'}
        return Resp()

    monkeypatch.setenv('BROKER_API_KEY', 'key')
    monkeypatch.setenv('BROKER_SECRET_KEY', 'secret')
    monkeypatch.setenv('BROKER_BASE_URL', 'http://example.com')
    monkeypatch.setattr('src.broker.requests.post', fake_post)

    result = place_order('AAA', 1, 'buy')

    assert calls['url'] == 'http://example.com/v2/orders'
    assert calls['json']['symbol'] == 'AAA'
    assert calls['json']['qty'] == 1
    assert calls['headers']['APCA-API-KEY-ID'] == 'key'
    assert result['status'] == 'accepted'


def test_portfolio_paper_buy_calls_broker(monkeypatch):
    from src.portfolio import Portfolio

    recorded = {}
    def fake_place(ticker, qty, side, order_type='market', time_in_force='gtc'):
        recorded['ticker'] = ticker
        recorded['qty'] = qty
        recorded['side'] = side
        return {'ok': True}

    monkeypatch.setattr('src.portfolio.place_order', fake_place)

    p = Portfolio(today='2025-08-05')
    result = p.paper_buy('BBB', 3)
    assert recorded['ticker'] == 'BBB'
    assert recorded['qty'] == 3
    assert recorded['side'] == 'buy'
    assert result['ok']


def test_get_account_makes_request(monkeypatch):
    calls = {}

    def fake_get(url, headers=None, timeout=10):
        calls['url'] = url
        calls['headers'] = headers

        class Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return {'equity': '1000'}

        return Resp()

    monkeypatch.setenv('BROKER_API_KEY', 'key')
    monkeypatch.setenv('BROKER_SECRET_KEY', 'secret')
    monkeypatch.setenv('BROKER_BASE_URL', 'http://example.com')
    monkeypatch.setattr('src.broker.requests.get', fake_get)

    result = get_account()

    assert calls['url'] == 'http://example.com/v2/account'
    assert calls['headers']['APCA-API-KEY-ID'] == 'key'
    assert result['equity'] == '1000'


def test_list_positions_makes_request(monkeypatch):
    calls = {}

    def fake_get(url, headers=None, timeout=10):
        calls['url'] = url
        calls['headers'] = headers

        class Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return [{'symbol': 'AAA'}]

        return Resp()

    monkeypatch.setenv('BROKER_API_KEY', 'key')
    monkeypatch.setenv('BROKER_SECRET_KEY', 'secret')
    monkeypatch.setenv('BROKER_BASE_URL', 'http://example.com')
    monkeypatch.setattr('src.broker.requests.get', fake_get)

    result = list_positions()

    assert calls['url'] == 'http://example.com/v2/positions'
    assert calls['headers']['APCA-API-KEY-ID'] == 'key'
    assert result[0]['symbol'] == 'AAA'


def test_dotenv_loaded(monkeypatch):
    recorded = {}

    def fake(path, override=False):
        recorded['path'] = Path(path)
        recorded['override'] = override

    monkeypatch.setattr('dotenv.load_dotenv', fake)
    importlib.reload(broker)

    expected = Path(broker.__file__).resolve().parents[2] / '.env'
    assert recorded['path'] == expected
    assert recorded['override'] is False


def test_list_assets(monkeypatch):
    calls = {}

    def fake_get(url, headers=None, params=None, timeout=10):
        calls['url'] = url
        calls['params'] = params
        calls['headers'] = headers

        class Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return [{'symbol': 'AAA'}]

        return Resp()

    monkeypatch.setenv('BROKER_API_KEY', 'key')
    monkeypatch.setenv('BROKER_SECRET_KEY', 'secret')
    monkeypatch.setenv('BROKER_BASE_URL', 'http://example.com')
    monkeypatch.setattr('src.broker.requests.get', fake_get)

    result = broker.list_assets(status='active')

    assert calls['url'] == 'http://example.com/v2/assets'
    assert calls['params']['status'] == 'active'
    assert result[0]['symbol'] == 'AAA'


def test_get_order(monkeypatch):
    calls = {}

    def fake_get(url, headers=None, timeout=10):
        calls['url'] = url
        calls['headers'] = headers

        class Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return {'id': '123'}

        return Resp()

    monkeypatch.setenv('BROKER_API_KEY', 'key')
    monkeypatch.setenv('BROKER_SECRET_KEY', 'secret')
    monkeypatch.setenv('BROKER_BASE_URL', 'http://example.com')
    monkeypatch.setattr('src.broker.requests.get', fake_get)

    result = broker.get_order('123')

    assert calls['url'] == 'http://example.com/v2/orders/123'
    assert result['id'] == '123'


def test_cancel_order(monkeypatch):
    calls = {}

    def fake_delete(url, headers=None, timeout=10):
        calls['url'] = url
        calls['headers'] = headers

        class Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return {'status': 'canceled'}

        return Resp()

    monkeypatch.setenv('BROKER_API_KEY', 'key')
    monkeypatch.setenv('BROKER_SECRET_KEY', 'secret')
    monkeypatch.setenv('BROKER_BASE_URL', 'http://example.com')
    monkeypatch.setattr('src.broker.requests.delete', fake_delete)

    result = broker.cancel_order('abc')

    assert calls['url'] == 'http://example.com/v2/orders/abc'
    assert result['status'] == 'canceled'


def test_list_orders(monkeypatch):
    calls = {}

    def fake_get(url, headers=None, params=None, timeout=10):
        calls['url'] = url
        calls['params'] = params
        calls['headers'] = headers

        class Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return [{'id': '1'}]

        return Resp()

    monkeypatch.setenv('BROKER_API_KEY', 'key')
    monkeypatch.setenv('BROKER_SECRET_KEY', 'secret')
    monkeypatch.setenv('BROKER_BASE_URL', 'http://example.com')
    monkeypatch.setattr('src.broker.requests.get', fake_get)

    result = broker.list_orders(status='all', limit=5)

    assert calls['url'] == 'http://example.com/v2/orders'
    assert calls['params']['status'] == 'all'
    assert calls['params']['limit'] == 5
    assert result[0]['id'] == '1'


def test_close_position(monkeypatch):
    calls = {}

    def fake_delete(url, headers=None, timeout=10):
        calls['url'] = url
        calls['headers'] = headers

        class Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return {'status': 'closed'}

        return Resp()

    monkeypatch.setenv('BROKER_API_KEY', 'key')
    monkeypatch.setenv('BROKER_SECRET_KEY', 'secret')
    monkeypatch.setenv('BROKER_BASE_URL', 'http://example.com')
    monkeypatch.setattr('src.broker.requests.delete', fake_delete)

    result = broker.close_position('ZZZ')

    assert calls['url'] == 'http://example.com/v2/positions/ZZZ'
    assert result['status'] == 'closed'

