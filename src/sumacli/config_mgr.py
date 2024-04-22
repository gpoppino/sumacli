import configparser
import logging
import os
import sys


class ConfigManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_file=None):
        self.__config_dir = os.path.expanduser('~/.sumacli')
        if config_file is not None:
            config_filename = config_file
        else:
            config_filename = os.path.join(self.__config_dir, 'config')

        if not os.path.isfile(config_filename):
            logging.error(f'Configuration file {config_filename} does not exist. Creating a new one.')
            try:
                if not os.path.isdir(self.__config_dir) and config_file is None:
                    os.mkdir(self.__config_dir, int('0700', 8))

                handle = open(config_filename, 'w')
                handle.write('[server]\n')
                handle.write('api_url = https://localhost/rpc/api\n')
                handle.write('fqdn = localhost.localdomain\n')
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
        self.__MANAGER_LOGIN = None
        self.__MANAGER_PASSWORD = None
        if 'credentials' in config:
            if 'username' in config['credentials']:
                self.__MANAGER_LOGIN = config['credentials']['username']
            if 'password' in config['credentials']:
                self.__MANAGER_PASSWORD = config['credentials']['password']

    def get_config_dir(self):
        return self.__config_dir

    @property
    def manager_api_url(self):
        return self.__MANAGER_API_URL

    @property
    def manager_fqdn(self):
        return self.__MANAGER_FQDN

    @property
    def manager_login(self):
        return self.__MANAGER_LOGIN

    @manager_login.setter
    def manager_login(self, username):
        self.__MANAGER_LOGIN = username

    @property
    def manager_password(self):
        return self.__MANAGER_PASSWORD
