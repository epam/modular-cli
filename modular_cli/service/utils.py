import base64
import json
import time
from pathlib import Path

from modular_cli.utils.exceptions import ModularCliBadRequestException
from modular_cli.utils.variables import COMMANDS_META

MODULAR_CLI_META_DIR = '.modular_cli'


def save_meta_to_file(meta: dict):
    admin_home_path = Path.home() / MODULAR_CLI_META_DIR
    admin_home_path.mkdir(exist_ok=True)
    path_to_meta = admin_home_path / COMMANDS_META
    with open(path_to_meta, 'w') as f:
        json.dump(meta, f, separators=(',', ':'))


def find_token_meta(commands_meta, specified_tokens):
    if not specified_tokens:
        return commands_meta
    current_meta = commands_meta
    for token in specified_tokens:
        token_meta = current_meta.get(token)
        if not token_meta:
            raise ModularCliBadRequestException(
                f'Failed to find specified command: {token}')
        current_meta = token_meta.get('body')

    return current_meta


class JWTToken:
    """
    A simple wrapper over jwt token
    """
    EXP_THRESHOLD = 300  # in seconds

    def __init__(self, token: str, exp_threshold: int = EXP_THRESHOLD):
        self._token = token
        self._exp_threshold = exp_threshold

    @property
    def raw(self) -> str:
        return self._token

    @property
    def payload(self) -> dict | None:
        try:
            return json.loads(
                base64.b64decode(self._token.split('.')[1] + '==').decode()
            )
        except Exception:
            return

    def is_expired(self) -> bool:
        p = self.payload
        if p is None:
            return True
        exp = p.get('exp')
        if not exp:
            return False
        return exp < time.time() + self._exp_threshold
