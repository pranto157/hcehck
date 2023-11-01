from threading import Lock
from werkzeug.wsgi import extract_path_info

class PathDispatcher(object):
    def __init__(self, default_app, instances):
        self.default_app = default_app
        self.lock = Lock()
        self.instances = instances

    def get_application(self, prefix):
        with self.lock:
            return self.instances.get(prefix)

    def __call__(self, environ, start_response):
        app = self.get_application(environ['PATH_INFO'])
        if app is None:
            app = self.default_app
        return app(environ, start_response)
