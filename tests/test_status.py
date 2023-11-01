import os
import socket
import threading
import time

import pytest
import redis
import requests
from elasticsearch import Elasticsearch
import sqlalchemy as db

from werkzeug.serving import run_simple
from werkzeug.wrappers import Request

import hcheck
from hcheck.config import Config


def application(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain')])
    yield b'Hello, World\n'


def unavailable():
    raise Exception('Service Error')


class TestHealthcheck(object):
    @classmethod
    def setup_class(cls):
        cls.host = '127.0.0.1'
        cls.port = 9092

        dependencies={
            'sqlalchemy': {
                'db': db.create_engine(Config.DB_URL),
                'broken-db': db.create_engine('mysql://root:asdf@localhost:3306'),
            },
            'redis': {
                'cache': lambda: redis.StrictRedis.from_url(Config.REDIS_URL),
                'broken-cache': lambda: redis.StrictRedis.from_url('redis://localhost:6000/0')
            },
            'es': {
                'es': lambda: Elasticsearch([Config.ES_URL]),
                'invalid-es': lambda: Elasticsearch(['127.1.3.1:9200'])
            },
            'custom': lambda: 'Service Available',
            'custom-default-message': lambda: None,
            'broken-custom': unavailable,
        }

        cls.application = hcheck.add_routes(application, dependencies=dependencies)

        start_server = lambda: run_simple(cls.host, cls.port, cls.application, use_debugger=True)
        cls.server_thread = threading.Thread(target=start_server)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        cls._wait_until_ready()

    @classmethod
    def _wait_until_ready(cls, timeout=5.0):
        elapsed = 0
        interval = 0.1

        while True:
            try:
                s = socket.socket()
                s.settimeout(timeout)
                s.connect((cls.host, cls.port))
            except socket.error:
                assert elapsed < timeout, 'Failed to start server within %s seconds' % timeout
                time.sleep(interval)
                elapsed += interval
            else:
                s.close()
                break
    
    def test_status(self):
        resp = requests.get('http://{0.host}:{0.port}/_status'.format(self))
        assert resp.status_code == 200
        response = resp.json()
        assert response['status'] == 'OK'
        expected_related = [
            '/_status/broken-cache',
            '/_status/broken-db',
            '/_status/cache',
            '/_status/db',
            '/_status/es',
            '/_status/invalid-es',
            '/_status/custom',
            '/_status/custom-default-message',
            '/_status/broken-custom',
        ]
        assert sorted(response['related']) == sorted(expected_related)

    def test_redis_status(self):
        resp = requests.get('http://{0.host}:{0.port}/_status/cache'.format(self))
        assert resp.status_code == 200
        assert resp.json() == {u'status': u'Ok'}

    def test_es_status(self):
        resp = requests.get('http://{0.host}:{0.port}/_status/es'.format(self))
        assert resp.status_code == 200
        assert resp.json() == {u'status': u'Ok'}

    def test_db_status(self):
        resp = requests.get('http://{0.host}:{0.port}/_status/db'.format(self))
        assert resp.status_code == 200
        assert resp.json() == {u'status': u'OK'}

    def test_broken_redis_status(self):
        resp = requests.get('http://{0.host}:{0.port}/_status/broken-cache'.format(self))
        assert resp.status_code == 503
        assert resp.json() == {u'status': u'Redis is not available'}

    def test_broken_es_status(self):
        resp = requests.get('http://{0.host}:{0.port}/_status/invalid-es'.format(self))
        assert resp.status_code == 503
        assert resp.json() == {u'status': u'ES is not available'}

    def test_broken_db_status(self):
        resp = requests.get('http://{0.host}:{0.port}/_status/broken-db'.format(self))
        assert resp.status_code == 503
        assert resp.json() == {u'status': u'DB Not available'}

    def test_custom_dependency_status(self):
        resp = requests.get('http://{0.host}:{0.port}/_status/custom'.format(self))
        assert resp.status_code == 200
        assert resp.json() == {'status': 'Service Available'}

    def test_custom_dependency_status_default_message(self):
        resp = requests.get('http://{0.host}:{0.port}/_status/custom-default-message'.format(self))
        assert resp.status_code == 200
        assert resp.json() == {'status': 'custom-default-message is available'}

    def test_broken_custom_dependency_status(self):
        resp = requests.get('http://{0.host}:{0.port}/_status/broken-custom'.format(self))
        assert resp.status_code == 503
        assert resp.json() == {'status': 'broken-custom is not available: Service Error'}


def test_sqlite_engine_not_accepted():
    with pytest.raises(ValueError):
        hcheck.add_routes(application, dependencies={
            'sqlalchemy': {
                'db': db.create_engine('sqlite:///:memory:'),
            },
        })
