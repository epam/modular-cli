import json
import os
import sys
import re

from pathlib import Path


RELATIVE_PATH_TO_COMPLETE = 'modular_cli_autocomplete'
NO_DESCRIPTION = 'No description'
HELP = 'help'
BASH_INTERPRETER = 'bash'
ZSH_INTERPRETER = 'zsh'
MODULAR_CLI_DIR = '.modular_cli'
ROOT_META_FILE = 'root_commands.json'
CMD_META = 'commands_meta.json'
HELP_FILE = 'modular_cli_help.txt'


def load_meta_file():
    root_commands = os.path.join(Path(__file__).parent.parent, ROOT_META_FILE)
    with open(root_commands) as file:
        root_file = json.load(file)

    meta_file = os.path.join(str(Path.home()), MODULAR_CLI_DIR, CMD_META)
    if not os.path.exists(meta_file):
        return root_file

    with open(meta_file) as meta_file:
        meta_file = json.loads(meta_file.read())
        meta_file.update(root_file)

    return meta_file


def process_start_suggestion(token, meta):
    suggestions = {}

    for key, value in meta.items():
        if key.startswith(token):
            command_description = value.get('description', None)
            suggestions[key] = command_description \
                if command_description else NO_DESCRIPTION

    format_response(suggestions)


def process_suggestions(request, meta):
    suggestions = {}
    completed_request = False
    is_group = False

    for token in request:
        if meta.get(token):
            meta = meta.get(token).get('body')
            completed_request = True
            is_group = True
        elif token == request[-1] and not token.startswith('--'):
            completed_request = False
            is_group = False
        elif token.startswith('--') and 'parameters' in meta:
            completed_request = True
            is_group = False
            break

    if 'parameters' in meta:
        is_group = False

    if is_group:
        for item in meta:
            suggestions[item] = None
        format_response(suggestions)

    if completed_request:
        if meta.get('parameters', None):
            parameters_list = meta.get('parameters')
            index_of_first_param = 0
            for index, token in enumerate(request):
                if '--' in token:
                    index_of_first_param = index
                    break

            no_params_request = request[:index_of_first_param]
            params_request = [param for param in
                              list(set(request) - set(no_params_request))
                              if re.match(r'^--[a-z]', param)]

            for parameter in parameters_list:
                param = parameter.get('name')
                param_description = parameter.get('description', None)
                suggestions[
                    f'--{param}'] = param_description if param_description \
                    else NO_DESCRIPTION

            updated_suggestions = {}
            for specified_param in params_request:
                if specified_param not in suggestions.keys():
                    for suggested_param in suggestions.keys():
                        if suggested_param.startswith(specified_param) \
                                and specified_param != suggested_param:
                            updated_suggestions[
                                suggested_param] = suggestions.get(
                                suggested_param)
                else:
                    del suggestions[specified_param]

            if updated_suggestions:
                suggestions = updated_suggestions
        else:
            suggestions = []

        format_response(suggestions)

    process_start_suggestion(request[-1], meta)


def format_response(suggestions):
    help_file = os.path.join(str(Path.home()), HELP_FILE)
    if isinstance(suggestions, list):
        with open(help_file, 'w+') as result_file:
            result_file.write(f'{os.linesep}'.join(sorted(suggestions)))
        exit(0)
    if isinstance(suggestions, str):
        with open(help_file, 'w+') as result_file:
            for each in suggestions:
                result_file.write(each)
        exit(0)
    suggestions = dict(sorted(suggestions.items()))
    response_array = []
    for key, value in suggestions.items():
        response_array.append(key)
    response_str = f'{os.linesep}'.join(response_array)
    with open(help_file, 'w+') as result_file:
        result_file.write(response_str)
    sys.exit(0)


if __name__ == '__main__':
    if len(sys.argv) == 2:
        sys.exit()
    interpreter = sys.argv[1]
    meta = load_meta_file()
    request = sys.argv[2:]
    response_str = ''

    if len(request) == 1:
        groups_meta = meta
        suggestions = ''
        if interpreter == BASH_INTERPRETER:
            suggestions = [key for key in groups_meta]
        if interpreter == ZSH_INTERPRETER:
            suggestions = {key: value.get(HELP).split(os.linesep)[0]
                           for key, value in meta.items()}
        format_response(suggestions=suggestions)

    global_suggestion = {}

    process_suggestions(request, meta)
