import json
import os
from abc import abstractmethod, ABC
import sys
from http import HTTPStatus

import click
from tabulate import tabulate

from modular_cli import ENTRY_POINT
from modular_cli.modular_cli_autocomplete.complete_handler import (
    enable_autocomplete_handler, disable_autocomplete_handler,
)
from modular_cli.service.config import (
    save_configuration, clean_up_configuration, add_data_to_config,
    CONF_REFRESH_TOKEN, CONF_ACCESS_TOKEN
)
from modular_cli.service.initializer import init_configuration
from modular_cli.service.utils import (
    save_meta_to_file, MODULAR_CLI_META_DIR, get_deprecation_tag,
    format_command_warnings_block_styled,
)
from modular_cli.utils.logger import get_logger
from modular_cli.utils.variables import (
    M3ADMIN_MODULE, MISSING_CONFIGURATION_MESSAGE,
)
from modular_cli.utils.exceptions import (
    ModularCliBadRequestException, ModularCliInternalException,
)
from modular_cli.version import __version__
from modular_cli.service.config import ConfigurationProvider

_LOG = get_logger(__name__)

META_JSON = 'commands_meta.json'
ROOT_META_JSON = 'root_commands.json'

HELP_STUB = (
    f'Here are the commands supported by the current version of {ENTRY_POINT}. '
    f'\nIMPORTANT: The scope of commands you can execute depends on your user '
    f'permissions'
)

GENERAL_HELP_STRING = """Description: {help_stub}
Usage: {entry_point} [module] group [subgroup] command [parameters]
Options:
  --help     Show this message and exit.
  
"""

COMMAND_HELP_STRING = """Description: {command_description}
Usage: {entry_point} {usage} [parameters]
Parameters:
{parameters}
"""

ANY_COMMANDS_AVAILABLE_HELP = """Description: {help_stub} 
Any commands available
"""

TYPE_MODULE = 'module'
TYPE_GROUP = 'group'
TYPE_COMMAND = 'command'


class HelpProcessor:
    def __init__(self, requested_command, commands_meta):
        self.requested_command = requested_command if requested_command else []
        self.module_name = requested_command[0] if requested_command else None
        self.commands_meta = commands_meta

    @staticmethod
    def get_appropriate_command(prepared_command_path, existed_command_paths):
        appropriate_command = \
            list(filter(lambda x: x['command_meta']['route']['path'] ==
                                  prepared_command_path,
                        existed_command_paths))
        if not appropriate_command:
            return
        return appropriate_command[0]

    @staticmethod
    def resolve_parameters_from_appropriate_command(appropriate_command):
        command_description = appropriate_command['command_meta'][
            'description']
        group = appropriate_command['group']
        subgroup = appropriate_command.get('subgroup', '')
        command_parameters = appropriate_command['command_meta']['parameters']
        return command_description, group, subgroup, command_parameters

    @staticmethod
    def resolve_parameters_from_appropriate_commands(appropriate_commands):
        commands = [command['command_meta']['name']
                    for command in appropriate_commands]
        appropriate_command = appropriate_commands[0]
        group = appropriate_command['group']
        subgroup = appropriate_command.get('subgroup', '')
        return group, subgroup, commands

    @staticmethod
    def get_appropriate_commands(prepared_command_path, existed_command_paths):
        return list(
            filter(lambda x: x['command_meta']['route']['path'].startswith(
                prepared_command_path), existed_command_paths))

    @staticmethod
    def prettify_command_parameters(command_parameters):
        table_data = []
        for each_param in command_parameters:
            table_data.append([
                '\t',
                '\t',
                '--' + str(each_param["name"]) + ',',
                '-' + str(each_param["alias"]) + ',' if each_param[
                    'alias'] else '',
                str('*' if each_param["required"] else ''),
                each_param["description"]
            ])
        return tabulate(tabular_data=table_data, tablefmt="plain")

    @staticmethod
    def prettify_group_subgroups(groups_subgroups_meta):
        table_data = []
        for each_param in groups_subgroups_meta:
            table_data.append([
                '\t',
                '\t',
                f'{each_param}'])
        return tabulate(tabular_data=table_data, tablefmt="plain")

    @staticmethod
    def extract_subgroup_from_command_path(command_path):
        subgroup_name = None
        splitted_command_path = command_path.split('/')
        splitted_command_path_len = len(splitted_command_path)
        if splitted_command_path_len == 5:
            *_, group_name, subgroup_name, _ = splitted_command_path
        else:
            *_, group_name, _ = splitted_command_path
        return group_name, subgroup_name

    @staticmethod
    def prepare_command_path(requested_command):
        return '/' + '/'.join(requested_command)

    def _should_show_command(
            self,
            command_meta: dict,
            is_specific_request: bool,
    ) -> bool:
        is_hidden = command_meta.get('is_command_hidden', False)
        # If it's a specific request for this command, show it even if hidden
        if is_specific_request:
            return True
        # For listings, hide commands marked as hidden
        return not is_hidden

    def get_help_message(self, token_meta: dict):
        if token_meta.get('route'):
            # Specific command help requested - show even if hidden
            return self.prepare_command_help(
                token_meta=token_meta,
                specified_tokens=self.requested_command,
            )

        level_token_types = {}
        for token_name, value in token_meta.items():
            token_type = value.get('type')
            if token_type is None:
                token_type = 'command'

            # Check if this is a command and if it should be hidden from listing
            if token_type == 'command':
                # For general help listings, skip hidden commands
                body = value.get('body', {})
                if body.get('is_command_hidden', False):
                    continue  # Skip hidden commands in listings

                # Add deprecation tag for deprecated commands in listings
                deprecation_info = body.get('deprecation')
                if deprecation_info:
                    tag = get_deprecation_tag(deprecation_info)
                    token_name = token_name + tag

            if not level_token_types.get(token_type):
                level_token_types.update({token_type: []})
            level_token_types.get(token_type).append(token_name)

        if not level_token_types:
            return ANY_COMMANDS_AVAILABLE_HELP.format(help_stub=HELP_STUB)

        help_str: str = GENERAL_HELP_STRING.format(
            help_stub=HELP_STUB, entry_point=ENTRY_POINT)
        if level_token_types.get('root command'):
            root_command = level_token_types.pop('root command')
            if level_token_types.get('command'):
                level_token_types['command'].extend(root_command)
            else:
                level_token_types['command'] = root_command
        for _type, names_list in level_token_types.items():
            names = "\n\t".join(sorted(names_list))
            help_str = help_str + f"Available {_type}s:\n\t{names}\n"
        return help_str

    def generate_module_meta(self, modules_meta, requested_command):
        prepared_command_path = self.prepare_command_path(
            requested_command=requested_command)

        subgroups_name = []
        commands_names = []
        existed_command_paths = []
        groups_name = []

        # Check if this is a request for a specific command
        # (full path with command name) vs a group listing
        is_specific_command_request = len(requested_command) >= 2

        pretty_module_name = requested_command[0]
        module_commands = modules_meta.get(pretty_module_name)
        if not module_commands:
            raise ModularCliBadRequestException(
                'Can not found requested module')

        for commands_meta in module_commands:
            for group, command_meta in commands_meta.items():
                command_route_path = command_meta['route']['path']
                group_name, subgroup_name = \
                    self.extract_subgroup_from_command_path(
                        command_path=command_route_path)

                if prepared_command_path not in command_meta['route']['path']:
                    continue

                command_name = command_meta['name']

                # Check if command should be shown
                is_hidden = command_meta.get('is_command_hidden', False)

                # For specific command requests, include even if hidden
                # For group listings, exclude hidden commands
                if not is_specific_command_request and is_hidden:
                    continue  # Skip hidden commands in group listings

                if subgroup_name and subgroup_name not in subgroups_name:
                    subgroups_name.append(subgroup_name)
                if command_name and command_name not in commands_names \
                        and not subgroup_name:
                    # Only add to commands list if not hidden or if specific request
                    if is_specific_command_request or not is_hidden:
                        commands_names.append(command_name)
                if group_name and group_name not in groups_name \
                        and group_name not in subgroups_name:
                    groups_name.append(group_name)

                existed_command_paths.append({
                    'group': group_name,
                    'subgroup': subgroup_name,
                    'command_meta': command_meta
                })

        if not any([existed_command_paths, subgroups_name, commands_names,
                    groups_name]):
            raise ModularCliBadRequestException('Invalid group or command '
                                                  'requested')

        return existed_command_paths, subgroups_name, commands_names, groups_name

    def prepare_command_help(
            self,
            token_meta: dict,
            specified_tokens: list,
    ) -> str:
        pretty_params = self.prettify_command_parameters(
            command_parameters=token_meta.get('parameters'))
        if not pretty_params:
            pretty_params = 'No parameters declared'

        command_description = token_meta.get('description', '')

        # Build combined warning block
        deprecation_info = token_meta.get('deprecation')
        is_hidden = token_meta.get('is_command_hidden', False)

        combined_warning = format_command_warnings_block_styled(
            deprecation_info=deprecation_info,
            is_hidden=is_hidden,
        )

        if combined_warning:
            combined_warning += "\n\n"

        help_string = COMMAND_HELP_STRING.format(
            entry_point=ENTRY_POINT,
            command_description=command_description,
            usage=' '.join(specified_tokens),
            parameters=pretty_params
        )

        return combined_warning + help_string


def extract_root_commands(admin_home_path):
    path_to_meta = os.path.join(admin_home_path, ROOT_META_JSON)

    if os.path.exists(path_to_meta):
        with open(path_to_meta) as file:
            root_commands = json.load(file)
        return root_commands
    else:
        raise ModularCliInternalException(
            'CLI root commands file  is missing , '
            'please write support team.')


def retrieve_commands_meta_content():
    from pathlib import Path
    admin_home_path = os.path.join(str(Path.home()), MODULAR_CLI_META_DIR)
    root_commands = extract_root_commands(
        Path(__file__).parent.parent.resolve())
    meta_path = os.path.join(admin_home_path, META_JSON)

    if not os.path.exists(meta_path):
        return root_commands
    try:
        with open(meta_path) as file:
            content = json.load(file)
            content.update(root_commands)
        return content
    except Exception:
        raise ModularCliBadRequestException(
            'Error while CLI meta loading. Please perform login again')


class AbstractStaticCommands(ABC):
    def __init__(self, config_command_help, config_params):
        self.config_command_help = config_command_help
        self.config_params = config_params

    @abstractmethod
    def define_description(self):
        pass

    def validate_params(self, configure_args):
        result = []
        missing = []
        for arg, (required, arg_type) in configure_args.items():
            if arg_type == bool:
                bool_value = arg in self.config_params
                result.append(bool_value)
            elif arg in self.config_params:
                try:
                    result.append(
                        self.config_params[self.config_params.index(arg) + 1]
                    )
                except IndexError:
                    raise ModularCliBadRequestException(
                        f'Please provide a value for: "{arg}"'
                    )
            else:
                result.append(None)
                if required:
                    missing.append(arg.replace('--', ''))
        if missing:
            raise ModularCliBadRequestException(
                f'The following parameters are missing: {", ".join(missing)}'
            )
        return result

    @abstractmethod
    def execute_command(self):
        pass

    def process_passed_command(self):
        if self.config_command_help:
            self.define_description()
        return self.execute_command()


class SetupCommandHandler(AbstractStaticCommands):
    def define_description(self):
        setup_command_help = \
            f'Usage: {ENTRY_POINT} setup [parameters]{os.linesep}' \
            f'Parameters:{os.linesep}     --username,   User name ' \
            f'associated with the Maestro user{os.linesep}     --password,  ' \
            f' Password associated with the Maestro user{os.linesep}  ' \
            f'   --api_path,   Address of the Maestro environment.'
        click.echo(setup_command_help)
        exit()

    def execute_command(self):
        from modular_cli.service.decorators import CommandResponse

        configure_args = {
            '--api_path': (True, str),
            '--username': (True, str),
            '--password': (True, str)
        }
        _force_help = True
        for param_name, is_required in configure_args.items():
            if param_name in self.config_params:
                _force_help = False
        if _force_help:
            self.define_description()

        api_path, username, password = self.validate_params(
            configure_args=configure_args)
        response = save_configuration(api_link=api_path,
                                      username=username,
                                      password=password)
        return CommandResponse(message=response)


class LoginCommandHandler(AbstractStaticCommands):
    def define_description(self):
        login_command_help = f'{os.linesep}Usage: {ENTRY_POINT} login' \
                             f'{os.linesep}{os.linesep}Returns JWT token and' \
                             f' commands meta in accordance with the user\'s ' \
                             f'permissions'
        click.echo(login_command_help)
        exit()

    def execute_command(self):
        from modular_cli.service.decorators import CommandResponse, process_meta
        adapter_sdk = init_configuration()
        if adapter_sdk is None:
            return CommandResponse(
                message=MISSING_CONFIGURATION_MESSAGE,
                code=401,
            )
        server_response = adapter_sdk.login()
        match server_response.status_code:
            case HTTPStatus.OK:
                # -> 200
                try:
                    dict_response = json.loads(server_response.text)
                except json.JSONDecodeError:
                    error_msg = (
                        f"Invalid JSON response from API. Set correct API path "
                        f"with `{ENTRY_POINT} setup ... --api_path ...`"
                    )
                    _LOG.error(f"Login response parsing failed: {error_msg}")
                    return CommandResponse(
                        code=HTTPStatus.BAD_REQUEST.value,
                        message=error_msg,
                    )

                # Validate required fields
                required_fields = ['jwt', 'refresh_token', 'version']
                missing_fields = [
                    field for field in required_fields
                    if field not in dict_response
                ]
                if missing_fields:
                    error_msg = (
                        f"API response missing required fields: "
                        f"{', '.join(missing_fields)}. "
                        f"Set correct API path with "
                        f"`{ENTRY_POINT} setup ... --api_path ...`"
                    )
                    _LOG.error(f"Login failed: {error_msg}")
                    return CommandResponse(
                        code=HTTPStatus.BAD_REQUEST.value,
                        message=error_msg,
                    )

                new_meta = process_meta(
                    server_meta=dict_response.get('meta', {})
                )
                save_meta_to_file(meta=new_meta)
                add_data_to_config(
                    name=CONF_ACCESS_TOKEN, value=dict_response.get('jwt'),
                )
                add_data_to_config(
                    name=CONF_REFRESH_TOKEN,
                    value=dict_response.get('refresh_token'),
                )
                add_data_to_config(
                    name='version', value=dict_response.get('version')
                )
                warnings = dict_response.get('warnings', [])
                return CommandResponse(
                    message='Login successful', warnings=warnings,
                )
            case HTTPStatus.UNAUTHORIZED:
                # -> 401
                return CommandResponse(
                    code=HTTPStatus.UNAUTHORIZED.value,
                    message='Invalid or missing credentials'
                )
            case HTTPStatus.NOT_FOUND:
                # -> 404
                message = (
                    'The requested URL was not found on the server. If you '
                    'entered the URL manually please check your spelling and '
                    'try again.'
                )
                return CommandResponse(
                    code=HTTPStatus.NOT_FOUND.value,
                    message=message,
                )
            case _:
                try:
                    error = server_response.json().get(
                        'message', server_response.reason,
                    )
                except Exception: # noqa
                    error = server_response.reason
                return CommandResponse(
                    message=error, code=server_response.status_code,
                )


class HealthCheckCommandHandler(AbstractStaticCommands):
    def define_description(self):
        login_command_help = (
            f'Usage: {ENTRY_POINT} health_check{os.linesep}'
            f'Returns service health status'
        )
        click.echo(login_command_help)
        exit()

    def execute_command(self):
        from modular_cli.service.decorators import CommandResponse
        adapter_sdk = init_configuration()
        if adapter_sdk is None:
            return CommandResponse(
                message=MISSING_CONFIGURATION_MESSAGE,
                code=401,
            )
        server_response = adapter_sdk.health_check()
        response_body = server_response.json()
        return CommandResponse(
            **response_body, code=server_response.status_code,
        )


class CleanupCommandHandler(AbstractStaticCommands):
    def define_description(self):
        cleanup_command_help = f'{os.linesep}Usage: {ENTRY_POINT} cleanup' \
                               f'{os.linesep}{os.linesep}Removes all the ' \
                               f'configuration data related to the tool.'
        click.echo(cleanup_command_help)
        exit()

    def execute_command(self):
        from modular_cli.service.decorators import CommandResponse
        response = clean_up_configuration()
        return CommandResponse(message=response)


class EnableAutocompleteCommandHandler(AbstractStaticCommands):
    def define_description(self):
        enable_autocomplete_command_help = (
            f'{os.linesep}Usage: {ENTRY_POINT} (then press tab){os.linesep}'
            f'{os.linesep}Enables command auto-completion suggestions as you type'
            f'{os.linesep}Parameters:{os.linesep}     '
            f'--shell   Specify your shell type (bash/zsh). '
            f'If omitted, will attempt to detect your shell automatically'
        )
        click.echo(enable_autocomplete_command_help)
        exit()

    def execute_command(self):
        from modular_cli.service.decorators import CommandResponse
        configure_args = {'--shell': (False, str)}
        _force_help = False
        for param_name, is_required in configure_args.items():
            if param_name in self.config_params:
                _force_help = False
        if _force_help:
            self.define_description()
        shell, *_ = self.validate_params(configure_args=configure_args)
        response = enable_autocomplete_handler(shell=shell)
        return CommandResponse(message=response)


class DisableAutocompleteCommandHandler(AbstractStaticCommands):
    def define_description(self):
        disable_autocomplete_command_help = f'{os.linesep}Usage: none' \
                                            f'{os.linesep}{os.linesep}Disable' \
                                            f'autocomplete'
        click.echo(disable_autocomplete_command_help)
        exit()

    def execute_command(self):
        from modular_cli.service.decorators import CommandResponse

        response = disable_autocomplete_handler()
        return CommandResponse(message=response)


class VersionCommandHandler(AbstractStaticCommands):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._config = ConfigurationProvider()

    def define_description(self):
        version_command_help = \
            f'Usage: {ENTRY_POINT} login [parameters]{os.linesep}' \
            f'Parameters:{os.linesep}     --module,   Describes specified ' \
            f'module version{os.linesep}     --detailed,  ' \
            f' Describes all module(s) version'
        click.echo(version_command_help)
        sys.exit(0)

    @staticmethod
    def _resolve_modules_versions(commands_meta):
        for module, meta in commands_meta.items():
            if meta.get('type') != 'module':
                continue
            yield module, meta['version']

    def _resolve_m3admin_version(self) -> str | None:
        # this one is kind of strange exception
        return self._config.root_admin_version

    def execute_command(self):
        from modular_cli.service.decorators import (CommandResponse, JSON_VIEW,
                                                    TABLE_VIEW)
        configure_args = {
            '--module': (False, str),
            '--detailed': (False, bool)
        }
        commands_meta = retrieve_commands_meta_content()
        module, detailed = self.validate_params(configure_args=configure_args)

        # reserved names
        versions = {
            'server': self._config.modular_api_version,
            'client': __version__
        }

        if module:
            if module == M3ADMIN_MODULE:  # exception
                name, version = M3ADMIN_MODULE, self._resolve_m3admin_version()
            else:
                name, version = next(
                    filter(lambda x: x[0] == module, self._resolve_modules_versions(commands_meta)),
                    (None, None)
                )
            if not version:
                return CommandResponse(
                    message=f'Module: "{module}" is not installed', code=404,
                )
            versions = {name: version}
        elif detailed:
            versions.update(self._resolve_modules_versions(commands_meta))
            m3admin = self._resolve_m3admin_version()
            if m3admin:
                versions[M3ADMIN_MODULE] = m3admin

        # todo kludge because CommandResponse does not suit this command
        #  and it's better to make this little kludge instead of adding
        #  some version command-specific logic to CommandResponse
        #  and ResponseFormatter
        ctx = click.get_current_context()
        if ctx.params.get(JSON_VIEW):
            click.echo(json.dumps({
                n: {'version': v} for n, v in versions.items()
            }, indent=4))
        elif ctx.params.get(TABLE_VIEW):
            return CommandResponse(
                items=[{'name': n, 'version': v} for n, v in versions.items()],
                table_title='Versions'
            )
        else:
            click.echo(os.linesep.join(
                f'{n.capitalize()}: {v}' for n, v in versions.items())
            )
        sys.exit(0)
