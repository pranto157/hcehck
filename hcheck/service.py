import requests


class Services(object): 

    CONNECT_TIMEOUT = 5.0
    READ_TIMEOUT = 10.0

    def check_status(self, url, user_agent, handle_http_error=True):
      try:
          response = requests.head(url, 
            timeout=(self.CONNECT_TIMEOUT, self.READ_TIMEOUT), 
            headers={'User-Agent': user_agent})
          response.raise_for_status()
      except requests.RequestException as e:
          if handle_http_error:
              return self._handle_http_status_check_failure(e)
          raise

    def _handle_status_check_failure(self, exc, message):
        return {'message': message, 'error': str(exc)}

    def _handle_http_status_check_failure(self, exc):
        if isinstance(exc, requests.Timeout):
            message = 'Request timed out: %s' % exc.request.url
        elif isinstance(exc, requests.ConnectionError):
            message = 'Connection failed: %s' % exc.request.url
        elif isinstance(exc, requests.RequestException):
            message = 'Request failed: %s' % exc.request.url
        else:
            assert False, 'Only RequestException instances should be handled by this method'

        return self._handle_status_check_failure(exc, message)


class BackEndService(Services): 

    def __init__(self, user_agent, url):
        self.USER_AGENT = user_agent
        self.CMP_ADMIN_HOST = url

    def check_status(self):
      url = self.CMP_ADMIN_HOST + '/admin/_status'
      return super().check_status(url, self.USER_AGENT)


class Platform(Services): 

    def __init__(self, user_agent, url):
        self.USER_AGENT = user_agent
        self.PLATFORM_HOST = url

    def check_status(self):
      url = self.PLATFORM_HOST + '/crossdomain.xml'
      return super().check_status(url, self.USER_AGENT)


class FrontEnd(Services): 

    def __init__(self, user_agent, url):
        self.USER_AGENT = user_agent
        self.ASSETS_HOST = url

    def check_status(self):
      url = self.ASSETS_HOST + '/_status'
      return super().check_status(url, self.USER_AGENT)


class FileServer(FrontEnd): 

    def __init__(self, user_agent, url):
        self.USER_AGENT = user_agent
        self.FILE_SERVER_INTERNAL_HOST = url

    def check_status(self):
      url = self.FILE_SERVER_INTERNAL_HOST + '/_status'

      return super().check_status(url, self.USER_AGENT)
