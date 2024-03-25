import os
import sys
from xmlrpc.client import ServerProxy
import configparser
import ssl
import logging


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

    def __init__(self):
        conf_dir = os.path.expanduser('~/.sumacli')
        config_filename = os.path.join(conf_dir, 'config')

        if not os.path.isfile(config_filename):
            try:
                # create ~/.sumacli
                if not os.path.isdir(conf_dir):
                    os.mkdir(conf_dir, int('0700', 8))

                handle = open(config_filename, 'w')
                handle.write('[server]\n')
                handle.write('api_url = https://localhost/rpc/api\n')
                handle.write('fqdn = localhost\n')
                handle.write('\n')
                handle.write('[credentials]\n')
                handle.write('username = admin\n')
                handle.write('password = admin\n')
                handle.close()
                logging.info(
                    f'Created {config_filename} file. Please, edit it with your credentials and server information.')
                sys.exit(1)
            except IOError:
                logging.error(f'Could not create {config_filename}')

        config = configparser.ConfigParser()
        config.read(config_filename)

        self.__MANAGER_API_URL = config['server']['api_url']
        self.__MANAGER_FQDN = config['server']['fqdn']
        self.__MANAGER_LOGIN = config['credentials']['username']
        self.__MANAGER_PASSWORD = config['credentials']['password']
        self.__key = None
        self.__client = None

    def __getattr__(self, name):
        return _MultiCallMethod(self, name)

    def login(self):
        if self.__key is not None:
            return
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        self.__client = ServerProxy(self.__MANAGER_API_URL, context=context)
        self.__key = self.__client.auth.login(
            self.__MANAGER_LOGIN, self.__MANAGER_PASSWORD)

    def logout(self):
        if self.__key is None:
            return
        self.__client.auth.logout(self.__key)
        self.__client("close")()
        self.__key = None

    def is_logged_in(self):
        return self.__key is not None

    def get_session_key(self):
        return self.__key

    def get_instance(self):
        return self.__client

    @property
    def manager_login(self):
        return self.__MANAGER_LOGIN

    @property
    def manager_fqdn(self):
        return self.__MANAGER_FQDN
