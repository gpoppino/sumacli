import logging
import os

from .config_mgr import ConfigManager


class SessionManager:

    def __init__(self):
        self.__current_session = None
        self.__config_manager = ConfigManager()
        self.__logger = logging.getLogger(__name__)
        self.__manager_dir = f'{self.__config_manager.get_config_dir()}/{self.__config_manager.manager_fqdn}'
        self.__session_file = f'{self.__manager_dir}/session'

    @property
    def session_key(self):
        if self.__current_session is not None:
            return self.__current_session

        if not os.path.isdir(self.__manager_dir):
            os.mkdir(self.__manager_dir, int('0700', 8))
        if os.path.isfile(self.__session_file):
            with open(self.__session_file, 'r') as session_file:
                line = session_file.readline()
                if line != '':
                    self.__config_manager.manager_login = line.split(':')[0].strip()
                    self.__current_session = line.split(':')[1].strip()
        if self.__current_session is None:
            if self.__config_manager.manager_login is not None:
                self.__logger.warning(f'Session key not found for user {self.__config_manager.manager_login}')
            else:
                self.__logger.warning(f'Session key not found for any user')
        return self.__current_session

    @session_key.setter
    def session_key(self, session_key):
        self.__current_session = session_key
        with open(self.__session_file, 'w') as session_file:
            session_file.write(f'{self.__config_manager.manager_login}:{self.__current_session}\n')
            self.__logger.debug(f'Session key saved for user {self.__config_manager.manager_login}')

    @session_key.deleter
    def session_key(self):
        if os.path.isfile(self.__session_file):
            with open(self.__session_file, 'r') as in_session_file:
                lines = in_session_file.readlines()
                for line in lines:
                    if line.startswith(self.__config_manager.manager_login):
                        lines.remove(line)

                with open(self.__session_file, 'w') as out_session_file:
                    out_session_file.writelines(lines)
