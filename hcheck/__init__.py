import json

import requests
from requests.exceptions import RequestException, ConnectTimeout
from werkzeug.wrappers import Response

from .pathdispatcher import PathDispatcher
from .service import BackEndService, Platform, FrontEnd, FileServer


SERVICES = {
    'backend': BackEndService,
    'platform': Platform,
    'frontend': FrontEnd,
    'file-server': FileServer,
}

AWS_AMI_METADATA_ENDPOINT = 'http://169.254.169.254/latest/meta-data/ami-id'


def add_routes(app, **options):

    def get_related_routes(dependencies):
        related_routes = {}
        dependencies = (options.get('dependencies') or {}).copy()

        for key, service in dependencies.pop('services', {}).items():
            if key in SERVICES:
                related_routes['/_status/' + key] = service_status(key, service['url'])

        for resource_name, client in dependencies.pop('sqlalchemy', {}).items():
            related_routes['/_status/' + resource_name] = check_db(client)

        for resource_name, client in dependencies.pop('redis', {}).items():
            related_routes['/_status/' + resource_name] = check_redis(client)

        for resource_name, client in dependencies.pop('es', {}).items():
            related_routes['/_status/' + resource_name] = check_es(client)

        for resource_name, status_check in dependencies.items():
            related_routes['/_status/' + resource_name] = check_custom_dependency(resource_name, status_check)

        return related_routes

    def status(environ, start_response):
        status_code = 200
        status_dict = {
            'status': 'OK',
        }

        if 'dependencies' in options:
            status_dict['related'] = list(get_related_routes(dependencies))

        response = _response(status_dict, status_code)
        return response(environ, start_response)

    def check_custom_dependency(resource_name, get_status):
        def dependency_status(environ, start_response):
            try:
                status_message = get_status() or ('%s is available' % resource_name)
            except Exception as e:
                status_message = '%s is not available: %s' % (resource_name, e)
                status_code = 503
            else:
                status_code = 200

            status_dict = {
                'status': status_message,
            }
            response = _response(status_dict, status_code)
            return response(environ, start_response)
        return dependency_status

    def check_db(db):
        if db.url.get_backend_name() == 'sqlite':
            raise ValueError('Status check is not supported for SQLite backend')

        def db_status(environ, start_response):
            status_message = 'OK'
            status_code = 200

            try:
                db.execute('SELECT 1')
            except:
                status_message = 'DB Not available'
                status_code = 503

            status_dict = {
                'status': status_message,
            }
            response = _response(status_dict, status_code)
            return response(environ, start_response)
        return db_status

    def check_redis(redis):
        def redis_status(environ, start_response):
            status_message = 'Redis is not available'
            status_code = 503
            try:
                if redis().ping():
                    status_message = 'Ok'
                    status_code = 200
            except:
                pass

            status_dict = {
                'status': status_message,
            }
            response = _response(status_dict, status_code)
            return response(environ, start_response)
        return redis_status

    def check_es(es):
        def es_status(environ, start_response):
            status_message = 'ES is not available'
            status_code = 503
            try:
                if es().ping():
                    status_message = 'Ok'
                    status_code = 200
            except:
                pass

            status_dict = {
                'status': status_message,
            }
            response = _response(status_dict, status_code)
            return response(environ, start_response)
        return es_status

    def service_status(service, url):
        """Generic view for service status
        """
        def check_service_status(environ, start_response):
            status_check_error = SERVICES[service](user_agent=options.get('user_agent'), url=url).check_status()
            if status_check_error:
                status_message = 'FAILED'
                status_code = 503
            else:
                status_message = 'OK'
                status_code = 200

            response = _response({'status': status_message, 'errors': status_check_error}, status_code)
            return response(environ, start_response)
        return check_service_status

    def ami_status(environ, start_response):
        try:
            resp = requests.get(AWS_AMI_METADATA_ENDPOINT, timeout=(0.5, 3))
            resp.raise_for_status()
            response = _response({'ami-id': resp.text}, 200)
            return response(environ, start_response)
        except ConnectTimeout:
            response = _response({'ami-id': None}, 200)
            return response(environ, start_response)
        except RequestException as e:
            response = _response({'error': str(e)}, 500)
            return response(environ, start_response)

    def _response(status_dict, status):
        return Response(
            response=json.dumps(status_dict),
            status=status,
            mimetype='application/json'
        )

    dependencies = options.get('dependencies')
    related_routes = {
        '/_status': status,
        '/_status/ami': ami_status
    }
    if dependencies:
        related_routes.update(get_related_routes(dependencies))

    return PathDispatcher(app, related_routes)
