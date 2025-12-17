import sys
from json import JSONDecodeError
from http import HTTPStatus
import click

from modular_cli import ENTRY_POINT
from modular_cli.service.decorators import (
    dynamic_dispatcher, CommandResponse, ResponseDecorator,
)
from modular_cli.service.help_client import (
    retrieve_commands_meta_content, HelpProcessor,
)
from modular_cli.service.config import (
    ConfigurationProvider, add_data_to_config, CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
)
from modular_cli.service.initializer import init_configuration
from modular_cli.service.request_processor import prepare_request
from modular_cli.service.utils import (
    find_token_meta, check_deprecation_enforcement, emit_deprecation_warning,
)
from modular_cli.utils.exceptions import (
    ModularCliInternalException, ModularCliUnauthorizedException,
)
from modular_cli.service.utils import JWTToken
from modular_cli.utils.logger import get_logger
from modular_cli.utils.variables import (
    NO_CONTENT_RESPONSE_MESSAGE, MISSING_CONFIGURATION_MESSAGE,
)
from modular_cli.service.adapter_client import AdapterClient

CONTEXT_SETTINGS = dict(allow_extra_args=True, ignore_unknown_options=True)
# if you are going to change the value of the next line - please change
# correspond value in Modular-API

_LOG = get_logger(__name__)


@click.command(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@click.option('--help', is_flag=True, default=False)
@click.option('--json', is_flag=True, default=False)
@click.option('--table', is_flag=True, default=False)
@ResponseDecorator(click.echo, 'Response is broken.')
@dynamic_dispatcher
def modular_cli(
        command: list | None = None,
        parameters: list | None = None,
        help: bool = False,
        view_type: str | None = None,
) -> CommandResponse:
    commands_meta = retrieve_commands_meta_content()
    token_meta = find_token_meta(
        commands_meta=commands_meta, specified_tokens=command,
    )
    is_help = __is_help_required(
        token_meta=token_meta, specified_parameters=parameters, help_flag=help,
    )
    if is_help:
        help_processor = HelpProcessor(
            requested_command=command, commands_meta=commands_meta,
        )
        help_message = help_processor.get_help_message(token_meta=token_meta)
        click.echo(help_message)
        sys.exit(0)

    # ========================================
    # Check deprecation BEFORE execution
    # (mimics original @deprecated decorator)
    # ========================================
    deprecation_info = token_meta.get('deprecation')
    check_deprecation_enforcement(deprecation_info)  # Raises error if removed + enforced
    emit_deprecation_warning(deprecation_info)  # Shows warning to stderr

    resource, method, parameters, params_to_log = prepare_request(
        token_meta=token_meta, passed_parameters=parameters,
    )
    adapter_sdk = init_configuration()
    if adapter_sdk:
        adapter_sdk = handle_token_expiration(adapter_sdk)
    if adapter_sdk is None:
        return CommandResponse(
            message=MISSING_CONFIGURATION_MESSAGE,
            code=401,
        )

    response = adapter_sdk.execute_command(
        resource=resource,
        parameters=parameters,
        method=method,
        params_to_log=params_to_log,
    )
    if response.status_code == HTTPStatus.NO_CONTENT.value:
        return CommandResponse(message=NO_CONTENT_RESPONSE_MESSAGE)
    try:
        response_body = response.json()
    except JSONDecodeError:
        return CommandResponse(
            message='Can not parse response into json. Please check logs',
            code=int(HTTPStatus.BAD_REQUEST),
        )
    except Exception:
        raise ModularCliInternalException(
            'Unexpected error happened. Please contact the Maestro support team'
        )

    return CommandResponse(**response_body, code=response.status_code)


def __is_help_required(token_meta, specified_parameters, help_flag):
    if help_flag:
        return help_flag
    if not token_meta.get('route'):
        return True
    required_parameters = [
        param for param in token_meta.get('parameters') if param.get('required')
    ]
    return required_parameters and not specified_parameters


def handle_token_expiration(adapter_sdk: AdapterClient) -> AdapterClient | None:
    """
    Tries to refresh access token. Returns new adapter client. Can return
    the save object or new object
    """
    st = adapter_sdk.session_token
    rt = ConfigurationProvider().refresh_token
    if (not st or JWTToken(st).is_expired()) \
            and (not rt or JWTToken(rt).is_expired()):
        error_message = (
            f'The provided tokens have expired or do not exist. Please '
            f're-login to get new tokens `{ENTRY_POINT} login`'
        )
        raise ModularCliUnauthorizedException(error_message)

    if st and not JWTToken(st).is_expired():
        _LOG.debug('Access token has not expired yet. Using it')
        return adapter_sdk

    # no access token or expired
    if not rt or JWTToken(rt).is_expired():
        _LOG.debug('Refresh token does not exist or expired. Cannot refresh')
        return adapter_sdk

    resp = adapter_sdk.refresh(rt)
    if not resp.ok:
        _LOG.warning(f'Could not refresh token: {resp.text}')
        return adapter_sdk

    data = resp.json()
    add_data_to_config(name=CONF_ACCESS_TOKEN, value=data.get('jwt'))
    add_data_to_config(name=CONF_REFRESH_TOKEN, value=data.get('refresh_token'))
    return init_configuration()
