import getpass
import logging
import sys
from xmlrpc.client import ServerProxy, Fault
from sumacli.config_mgr import ConfigManager
import ssl

from sumacli.session_mgr import SessionManager


class _MultiCallMethod:
    def __init__(self, client, name):
        self.__client = client
        self.__name = name

    def __getattr__(self, name):
        return _MultiCallMethod(self.__client, "%s.%s" % (self.__name, name))

    def __call__(self, *args):
        m = getattr(self.__client.get_instance(), self.__name)
        if args == ():
            return m(self.__client.get_session_key())
        else:
            return m(self.__client.get_session_key(), *args)


class SumaClient:

    def __init__(self, config_file=None):
        self.__config_manager = ConfigManager(config_file)
        self.__session_manager = SessionManager()
        self.__logger = logging.getLogger(__name__)

        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        self.__client = ServerProxy(self.__config_manager.manager_api_url, context=context)

    def __getattr__(self, name):
        return _MultiCallMethod(self, name)

    def login(self):
        if self.__session_manager.session_key is not None:
            # try to run a query to the server to see if the session is still valid
            try:
                self.__client.user.listAssignableRoles(self.__session_manager.session_key)
                api_url = self.__config_manager.manager_api_url
                self.__logger.info(f'User {self.__config_manager.manager_login} already logged in to {api_url}')
                return
            except Fault as e:
                self.__logger.warning(f'Session key is not valid anymore: {e.faultString}')

        if self.__config_manager.manager_login is None:
            self.__config_manager.manager_login = input('Enter your username: ')

        manager_password = self.__config_manager.manager_password
        if manager_password is None:
            manager_password = getpass.getpass(
                f'Enter your password for username {self.__config_manager.manager_login}: ')

        try:
            self.__session_manager.session_key = self.__client.auth.login(
                self.__config_manager.manager_login, manager_password)
        except Fault as e:
            self.__logger.error(f'Could not login: {e.faultString} as user {self.__config_manager.manager_login}')
            sys.exit(1)
        self.__logger.info(f'User {self.__config_manager.manager_login} logged in')

    def logout(self):
        if self.__session_manager.session_key is not None:
            self.__client.auth.logout(self.__session_manager.session_key)
            self.__client("close")()
        del self.__session_manager.session_key
        if self.__config_manager.manager_login is not None:
            self.__logger.info(f'User {self.__config_manager.manager_login} logged out')

    def is_logged_in(self):
        return self.__session_manager.session_key is not None

    def get_session_key(self):
        return self.__session_manager.session_key

    def get_instance(self):
        return self.__client
