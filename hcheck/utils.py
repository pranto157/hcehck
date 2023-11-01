import json

def load_config_from_json(filename, silent=False):
    try:
        with open(filename) as json_file:
            obj = json.loads(json_file.read())
            return obj
    except IOError as e:
        if silent:
            return False
        e.strerror = 'Unable to load configuration file (%s)' % e.strerror
        raise
