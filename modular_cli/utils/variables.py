# new tool folder name is '.m3modularcli'. It's resolved dynamically
# keeping backward compatibility
from modular_cli import ENTRY_POINT


TOOL_FOLDER_NAME = 'm3modularcli'  # obsolete
TOOL_CONFIGURATION_FOLDER = '.modular_cli'  # new
LOG_FILE_NAME = 'modular_cli.log'

# Configuration
CREDENTIALS_FILE_NAME = 'credentials'
TEMPORARY_CREDS_FILENAME = 'temporary_creds.json'
COMMANDS_META = 'commands_meta.json'

DEFAULT_CONNECTION_TIMEOUT = 15

# 204
NO_CONTENT_RESPONSE_MESSAGE = 'Request is successful. No content returned'

ENV_LOG_PATH = 'MODULAR_CLI_LOG_PATH'
ENV_LOG_LEVEL = 'MODULAR_CLI_LOG_LEVEL'
ENV_CLI_DEBUG = 'MODULAR_CLI_DEBUG'


M3ADMIN_MODULE = 'm3admin'

MISSING_CONFIGURATION_MESSAGE = \
    f"The configuration is missing. Use '{ENTRY_POINT} setup' command first"
