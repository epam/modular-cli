import os

from modular_cli.service.config import ConfigurationProvider, get_credentials_folder
from modular_cli.utils.logger import get_logger
from modular_cli.utils.variables import CREDENTIALS_FILE_NAME

SYSTEM_LOG = get_logger(__name__)


def init_configuration():
    from modular_cli.service.adapter_client import AdapterClient
    config_path = get_credentials_folder() / CREDENTIALS_FILE_NAME
    # todo refactor all this. Make composition relation between config class
    #  and adapter class (btw why is it called adapter?, isn't it just
    #  api client?). Anyway, make config class be able to read and write
    #  and fully manage its data. It means to remove "add_data_to_config",
    #  "save_configuration" functions and other such. Make config json
    #  instead of yaml because it's not used by humans.
    if os.path.exists(config_path):
        config = ConfigurationProvider()
        return AdapterClient(
            adapter_api=config.api_link,
            username=config.username,
            secret=config.password,
            token=config.access_token,
        )
    else:
        SYSTEM_LOG.info(
            f'Configuration is missing by path {config_path}. Initialization '
            f'skipped.'
        )
