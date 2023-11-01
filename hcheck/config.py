from hcheck.utils import load_config_from_json

class Config(object):
    DB_URL = 'mysql://root:@localhost:3306'
    REDIS_URL = 'redis://localhost:6379/0'
    ES_URL = '127.0.0.1:9200'

    locals().update(load_config_from_json('/opt/nc-healthcheck/conf/nc-healthcheck.json', silent=True) or {})
