import json
import os
from pathlib import Path

import requests
import yaml

from modular_cli import ENTRY_POINT
from modular_cli.utils.exceptions import (
    ModularCliConfigurationException, ModularCliBadRequestException,
)
from modular_cli.utils.logger import get_logger
from modular_cli.utils.variables import (
    TOOL_FOLDER_NAME, TOOL_CONFIGURATION_FOLDER, CREDENTIALS_FILE_NAME,
    TEMPORARY_CREDS_FILENAME, COMMANDS_META, DEFAULT_CONNECTION_TIMEOUT,
)

SYSTEM_LOG = get_logger(__name__)


def save_configuration(api_link: str, username: str, password: str) -> str:
    if api_link.endswith('/'):
        api_link = api_link[:-1]
    valid_link = __api_link_validation(link=api_link)
    folder_path = get_credentials_folder()
    try:
        folder_path.mkdir(exist_ok=True)
    except OSError:
        SYSTEM_LOG.exception(f'Creation of the directory {folder_path} failed')
        raise ModularCliConfigurationException(
            f'Could not create configuration folder {folder_path}'
        )

    config_data = dict(api_link=valid_link,
                       username=username,
                       password=password)
    with open(folder_path / CREDENTIALS_FILE_NAME, 'w') as config_file:
        yaml.dump(config_data, config_file)
    return f"Great! The CLI tool '{ENTRY_POINT}' has been set up"


def get_credentials_folder() -> Path:
    """
    Old credentials folder is '~/m3modularcli'. New one is '~/.modular_cli'.
    This function is backward-compatible. In case the old folder exists,
    it will be returned. Otherwise, the new one is returned
    """
    folder = Path.home() / TOOL_FOLDER_NAME  # old
    if folder.exists() and folder.is_dir():
        return folder.resolve()  # full path
    # returning a new one
    return (Path.home() / TOOL_CONFIGURATION_FOLDER).resolve()


def __api_link_validation(link: str) -> str:
    try:
        resp = requests.get(
            link + '/health_check',
            timeout=DEFAULT_CONNECTION_TIMEOUT,
        )
        if resp.status_code != 200:
            raise ModularCliBadRequestException(
                f'API link failed: {link}. '
                f'Health check was not successful.'
            )
    except (requests.exceptions.RequestException,
            requests.exceptions.MissingSchema, requests.exceptions.InvalidURL,
            requests.exceptions.ConnectionError,
            requests.exceptions.InvalidSchema) as e:
        raise ModularCliBadRequestException(
            f'API link error: {link}. An exception occurred during the request.'
        ) from e
    return link


def clean_up_configuration():
    folder_path = get_credentials_folder()
    config_file_path = folder_path / CREDENTIALS_FILE_NAME
    m3_modular_cli_dir, _ = os.path.split(os.path.dirname(__file__))
    commands_meta_path = os.path.join(m3_modular_cli_dir, COMMANDS_META)
    is_config_file_path = config_file_path.exists()
    is_commands_meta_path = os.path.exists(commands_meta_path)
    SYSTEM_LOG.debug(f'Config file exists: {is_config_file_path}')
    SYSTEM_LOG.debug(f'Commands meta file exists: {is_commands_meta_path}')
    try:
        if is_config_file_path:
            os.remove(path=str(config_file_path))
        if is_commands_meta_path:
            os.remove(commands_meta_path)
    except OSError:
        SYSTEM_LOG.exception(
            f'Error occurred while cleaning '
            f'configuration by path: {folder_path}')
    return f"Configuration for the CLI tool '{ENTRY_POINT}' has been deleted"


CONF_USERNAME = 'username'
CONF_API_LINK = 'api_link'
CONF_PASSWORD = 'password'
CONF_ACCESS_TOKEN = 'access_token'
CONF_REFRESH_TOKEN = 'refresh_token'
MODULAR_API_VERSION = 'version'
ROOT_ADMIN_VERSION = 'm3admin_version'

REQUIRED_PROPS = [CONF_API_LINK, CONF_USERNAME, CONF_PASSWORD]


class ConfigurationProvider:
    def __init__(self):
        self.config_path = get_credentials_folder() / CREDENTIALS_FILE_NAME
        if not os.path.exists(self.config_path):
            raise ModularCliConfigurationException(
                f"The CLI tool is not set up. Please execute the following "
                f"command: '{ENTRY_POINT} setup'"
            )
        self.config_dict = None
        with open(self.config_path, 'r') as config_file:
            self.config_dict = yaml.safe_load(config_file.read())
        missing_property = []
        for prop in REQUIRED_PROPS:
            if not self.config_dict.get(prop):
                missing_property.append(prop)
        if missing_property:
            raise ModularCliConfigurationException(
                f"Configuration for '{ENTRY_POINT}' is broken. The following "
                f"required properties are missing: {missing_property}"
            )
        SYSTEM_LOG.info(
            f"Configuration for '{ENTRY_POINT}' has been successfully loaded"
        )

    @property
    def api_link(self):
        return self.config_dict.get(CONF_API_LINK)

    @property
    def username(self):
        return self.config_dict.get(CONF_USERNAME)

    @property
    def password(self):
        return self.config_dict.get(CONF_PASSWORD)

    @property
    def access_token(self):
        return self.config_dict.get(CONF_ACCESS_TOKEN)

    @property
    def refresh_token(self):
        return self.config_dict.get(CONF_REFRESH_TOKEN)

    @property
    def modular_api_version(self):
        return self.config_dict.get(MODULAR_API_VERSION)

    @property
    def root_admin_version(self):
        return self.config_dict.get(ROOT_ADMIN_VERSION)


def save_temporary_user_data(username, data):
    cur_path = Path(__file__).parent.resolve()
    user_folder = os.path.join(cur_path, username)
    try:
        Path(user_folder).mkdir(exist_ok=True)
    except OSError:
        SYSTEM_LOG.exception(f'Creation of the directory {user_folder} failed')

    credentials_file_path = os.path.join(user_folder, TEMPORARY_CREDS_FILENAME)
    with open(credentials_file_path, 'w+') as file:
        json.dump(data, file, indent=4)


def add_data_to_config(name: str, value: str):
    # todo loading and dumping yaml for the sake of one value - not worth it.
    # todo I want to add data to config, but config does not exists and
    #  i get error - silly
    config_file_path = get_credentials_folder() / CREDENTIALS_FILE_NAME
    if not Path(config_file_path).exists():
        message = \
            f"'{ENTRY_POINT}' is not configured. Please contact the support team"
        SYSTEM_LOG.exception(message)
        return message
    with open(config_file_path, 'r') as config_file:
        config = yaml.safe_load(config_file.read())
    config[name] = value

    with open(config_file_path, 'w') as config_file:
        yaml.dump(config, config_file)
