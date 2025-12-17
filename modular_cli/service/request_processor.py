import os
from base64 import b64encode
import getpass

from modular_cli.utils.exceptions import ModularCliBadRequestException

ROUTE = 'route'
NAME = 'name'
TYPE = 'type'
PATH = 'path'
ALIAS = 'alias'
NUMERIC = 'num'
BOOLEAN = 'bool'
METHOD = 'method'
PARAMS = 'parameters'
REQUIRED = 'required'
BOOL_PARAM_MAP = {
    'true': True,
    'false': False
}


def validate_params(appropriate_command, passed_parameters):
    missed_param = [
        f"{param[NAME]} or {param[ALIAS]}" if param[ALIAS] is not None else param[NAME]
        for param in appropriate_command[PARAMS]
        if param[REQUIRED] and param[NAME] not in passed_parameters
    ]

    if missed_param:
        raise ModularCliBadRequestException(
            f'The following parameters are missing: '
            f'{", ".join(missed_param)}.\n'
            f'Try \'--help\' for help or list subcommands.')

    passed_parameters_names = passed_parameters.keys()
    for checked_name in passed_parameters_names:
        found = False
        for item in appropriate_command.get(PARAMS):
            name = item.get(NAME)
            if checked_name == name:
                param_type = item.get(TYPE)
                value = passed_parameters.get(checked_name)
                check_param_type(p_name=checked_name, p_type=param_type,
                                 value=value)
                found = True
                break
        if not found:
            raise ModularCliBadRequestException(f"Invalid parameter "
                                                  f"\'{checked_name}\'.")


def check_param_type(p_name, p_type, value):
    if p_type == BOOLEAN and not isinstance(value, bool):
        raise ModularCliBadRequestException(
            f'Invalid value of parameter \'{p_name}\'.\nShould be a flag or '
            f'boolean type expected.')
    if p_type == NUMERIC:
        try:
            float(value)
        except ValueError:
            raise ModularCliBadRequestException(
                f'Invalid parameter \'{p_name}\'. Numeric value expected.')


def alias_to_parameter(command, params):
    updated_params = {}
    params_meta = command.get(PARAMS)

    # validate aliases
    for param in params:
        found = False
        if param.startswith("-"):
            for item in params_meta:
                alias = item.get(ALIAS)
                if alias and param == ("-" + alias):
                    found = True
            if not found:
                raise ModularCliBadRequestException(f"Invalid alias "
                                                      f"\'{param}\'")

    # replace aliases by full name parameters
    for param in params:
        if param.startswith("-"):
            for item in params_meta:
                alias = item.get(ALIAS)
                if alias and "-" + alias == param:
                    full_name = item.get(NAME)
                    value = params.get(param)
                    updated_params[full_name] = value
        else:
            updated_params[param] = params.get(param)

    return updated_params


def resolve_secure_parameters(command, params):
    secure_parameters = {param: value for param, value in params.items()
                         if param in command['secure_parameters']}
    params_to_log = {}
    for param, value in params.items():
        if param in secure_parameters:
            value = '*****'
        params_to_log.update({param: value})
    return params_to_log


def resolve_passed_files(
        command: dict,
        params: dict,
) -> dict:
    parameters = command['parameters']
    for parameter in parameters:
        is_file = parameter.get('convert_content_to_file')
        parameter_name = parameter.get('name')
        if not is_file or parameter_name not in params:
            continue

        path_to_file = params[parameter_name]
        *_, filename = os.path.split(path_to_file)
        filename, file_extension = os.path.splitext(filename)
        allowed_extensions = parameter.get('temp_file_extension')
        if allowed_extensions and file_extension not in allowed_extensions:
            raise ModularCliBadRequestException(
                f'File must have the following extensions: '
                f'{", ".join(allowed_extensions)}'
            )
        if not os.path.isfile(path_to_file):
            raise ModularCliBadRequestException(
                'Provided file path does not exist'
            )

        # Distinguish between permission errors and other issues
        try:
            with open(path_to_file, 'rb') as f:
                encoded_str = str(b64encode(f.read()))[2:-1]
        except PermissionError:
            raise ModularCliBadRequestException(
                f'Permission denied: unable to read file at {path_to_file}'
            )
        except FileNotFoundError:
            raise ModularCliBadRequestException(
                'Provided file path does not exist'
            )
        except OSError as e:
            raise ModularCliBadRequestException(
                f'Unable to read file: {str(e)}'
            )

        params.update({
            parameter_name: {
                'file_content': encoded_str,
                'filename': filename,
                'file_extension': file_extension,
            },
        })
    return params


def process_input_parameters(
        token_meta: dict,
        passed_parameters: list,
) -> dict:
    index = 0
    processed_parameters = {}
    for idx, param in enumerate(passed_parameters):
        if idx < index:
            continue
        existed_param = [
            parameter for parameter in token_meta['parameters']
            if f'-{parameter["alias"]}' == param or
               f'--{parameter["name"]}' == param
        ]
        if not existed_param:
            raise ModularCliBadRequestException(f"No such option: '{param}'")

        existed_param = existed_param[0]

        param_name = existed_param['name']
        is_bool_param = existed_param['type'] == 'bool'
        is_flag_param = existed_param.get('is_flag')

        # process bool parameter type
        if is_flag_param:
            processed_parameters[param_name] = True
            index += 1
        elif is_bool_param:
            try:
                processed_parameters[param_name] = BOOL_PARAM_MAP.get(
                    passed_parameters[index + 1].lower()
                )
                index += 2
                if not isinstance(processed_parameters[param_name], bool):
                    raise ModularCliBadRequestException(
                        f'Missed value for "{param}" parameter. '
                        f'Bool type expected'
                    )
            except IndexError:
                raise ModularCliBadRequestException(
                    f'Missed value for "{param}" parameter. Bool type expected'
                )
        elif param_name in processed_parameters:
            # process multiple parameter type
            existed_param_value = processed_parameters[param_name]
            if existed_param_value and isinstance(existed_param_value, list):
                processed_parameters[param_name].append(
                    passed_parameters[index + 1]
                )
            else:
                processed_parameters[param_name] = [
                    existed_param_value,
                    passed_parameters[index + 1]
                ]
            index += 2

        else:
            try:
                processed_parameters[existed_param['name']] = passed_parameters[idx+1]
            except IndexError:
                raise ModularCliBadRequestException(
                    f'Missed value for "{param}" parameter'
                )
            index += 2

    prompts_map = {
        parameter['name']: parameter['interactive_settings']
        for parameter in token_meta['parameters']
        if parameter.get('interactive_settings')
    }

    for prompt_name, interactive_settings in prompts_map.items():
        if prompt_name not in processed_parameters:
            continue
        target_option = interactive_settings['target_option']
        if target_option in processed_parameters:
            raise ModularCliBadRequestException(
                f"Conflict: both '{prompt_name}' and '{target_option}' are "
                f"present in processed_parameters"
            )

        prompt_text = interactive_settings['prompt_text']
        hide_input = interactive_settings['hide_input']

        if processed_parameters[prompt_name]:
            if hide_input:
                user_input = getpass.getpass(f"{prompt_text}: ")
            else:
                user_input = input(f"{prompt_text}: ")
            processed_parameters[target_option] = user_input

        del processed_parameters[prompt_name]

    return processed_parameters


def prepare_request(
        token_meta: dict,
        passed_parameters: list,
) -> tuple:
    passed_parameters = process_input_parameters(
        token_meta=token_meta,
        passed_parameters=passed_parameters,
    )
    passed_parameters = resolve_passed_files(
        command=token_meta,
        params=passed_parameters,
    )
    validate_params(token_meta, passed_parameters)
    params_to_log = resolve_secure_parameters(
        command=token_meta,
        params=passed_parameters,
    )
    route = token_meta[ROUTE]
    return route[PATH], route[METHOD], passed_parameters, params_to_log
