import os
import subprocess
import sys

from modular_cli.modular_cli_autocomplete import (
    BASH_COMPLETE_SCRIPT, ZSH_COMPLETE_SCRIPT, RELATIVE_PATH_TO_COMPLETE,
    PROFILE_D_PATH, PROFILE_ZSH_COMPLETE_SCRIPT, PROFILE_BASH_COMPLETE_SCRIPT,
    COMPLETE_PROCESS_FILE,
)
from modular_cli.utils.logger import get_logger

_LOG = get_logger(__name__)
PYTHON_SYMLINK = 'PYTHON_SYMLINK'
SCRIPT_PATH = 'SCRIPT_PATH'
HELP_FILE = 'HELP_FILE'
BASH_INTERPRETER = 'bash'
ZSH_INTERPRETER = 'zsh'
COMMAND_TO_CHECK_INTERPRETER = "echo $SHELL"
SHRC_AUTOCOMPLETE_MARKER = 'admin_autocomplete_system_settings'


def _get_appropriate_script_name(stdout):
    if BASH_INTERPRETER in stdout:
        return BASH_INTERPRETER, BASH_COMPLETE_SCRIPT
    if ZSH_INTERPRETER in stdout:
        return ZSH_INTERPRETER, ZSH_COMPLETE_SCRIPT
    return None, None


def _add_str_to_rc_file(interpreter, script, admin_home_path,
                        installed_python_link):
    script_path = os.path.join(admin_home_path,
                               RELATIVE_PATH_TO_COMPLETE, script)
    source_string = f'\nsource {script_path} "{installed_python_link}" ' \
                    f'"{admin_home_path}"'
    rc_file_path = os.path.expanduser('~') + f'/.{interpreter}rc'
    with open(rc_file_path, 'r+') as f:
        if SHRC_AUTOCOMPLETE_MARKER not in f.read():
            f.write(f'\n# {SHRC_AUTOCOMPLETE_MARKER}')
            f.write(source_string)
            _LOG.info(f'Modular-CLI autocomplete have been '
                      f'successfully injected to the RC file. '
                      f'Path to the RC file: {rc_file_path}')
    return source_string


def _delete_str_from_rc_file(interpreter):
    rc_file_path = os.path.expanduser('~') + f'/.{interpreter}rc'
    with open(rc_file_path, 'r+') as f:
        lines = f.readlines()

    first_string_found = False
    with open(rc_file_path, 'w') as f:
        for line in lines:
            if SHRC_AUTOCOMPLETE_MARKER in line.strip("\n"):
                first_string_found = True
                continue
            if first_string_found:
                first_string_found = False
                continue
            f.write(line)
    _LOG.info(f'Modular-CLI autocomplete have been '
              f'successfully removed from the RC file. ')


def _get_interpreter_and_appropriate_script():
    if sys.platform not in ['darwin', 'linux']:
        raise OSError(
            f'The OS is not applicable for autocompletion setup. '
            f'Current OS is {sys.platform}'
        )
    stdout = subprocess.check_output(COMMAND_TO_CHECK_INTERPRETER,
                                     shell=True).decode('utf-8').strip()
    _LOG.info(f'Current interpreter: {stdout}')
    if not stdout:
        raise RuntimeError(
            'The interpreter can not be checked. Modular-CLI autocomplete '
            'installation will be skipped...'
        )
    interpreter, script = _get_appropriate_script_name(stdout)
    if not interpreter:
        raise ValueError(
            f'Unsupported interpreter {stdout}. Modular-CLI autocomplete '
            f'installation will be skipped...'
        )
    return interpreter, script


def enable_autocomplete_handler():
    interpreter, script = _get_interpreter_and_appropriate_script()
    from platform import python_version
    installed_python_link = 'python' + '.'.join(
        python_version().lower().split('.')[0:-1])
    try:
        import pathlib
        admin_home_path = pathlib.Path(__file__).parent.parent.resolve()
        if not os.path.exists(PROFILE_D_PATH):
            _LOG.info('Going to edit RC file')
            source_string = _add_str_to_rc_file(interpreter, script,
                                                admin_home_path,
                                                installed_python_link)
            return f'Autocomplete has been successfully installed and ' \
                   f'will start work after the current terminal session ' \
                   f'reload. If you want to manually activate ' \
                   f'autocomplete without reloading the terminal session, ' \
                   f'please run the following command \n {source_string}'
        # if admin instance installation
        _LOG.info(f'Going to copy autocomplete files to {PROFILE_D_PATH}')
        init_profile_script_path = os.path.join(admin_home_path,
                                                RELATIVE_PATH_TO_COMPLETE,
                                                script)
        python_script = os.path.join(admin_home_path,
                                     RELATIVE_PATH_TO_COMPLETE,
                                     COMPLETE_PROCESS_FILE)
        script = 'profile_' + script
        processed_profile_script_path = os.path.join(PROFILE_D_PATH, script)
        with open(init_profile_script_path, 'r+') as f:
            lines = f.readlines()
        script_was_found = False
        help_was_found = False
        with open(processed_profile_script_path, 'w') as f:
            for line in lines:
                if SCRIPT_PATH in line.strip(
                        "\n") and not script_was_found:
                    line = f'SCRIPT_PATH={python_script}\n'
                    script_was_found = True
                if HELP_FILE in line.strip("\n") and not help_was_found:
                    line = 'HELP_FILE=/home/$USER/modular_cli_help.txt'
                    help_was_found = True
                f.write(line)
        _LOG.info(f'Modular-CLI autocomplete has been '
                  f'successfully set up. Path to the "profile.d" file: '
                  f'{processed_profile_script_path}')
        return f'Modular-CLI autocomplete has been ' \
               f'successfully set up. Path to the "profile.d" file: ' \
               f'{processed_profile_script_path}'
    except AttributeError:
        _LOG.error('Autocomplete installation is not available')
        raise
    except Exception as e:
        _LOG.error(f'Something happen while setup autocomplete. Reason: {e}')
        raise


def disable_autocomplete_handler():
    interpreter, _ = _get_interpreter_and_appropriate_script()
    try:
        _delete_str_from_rc_file(interpreter)
        if os.path.exists(PROFILE_D_PATH):
            for each in os.listdir(PROFILE_D_PATH):
                if each in [
                    ZSH_COMPLETE_SCRIPT,
                    BASH_COMPLETE_SCRIPT,
                    PROFILE_ZSH_COMPLETE_SCRIPT,
                    PROFILE_BASH_COMPLETE_SCRIPT,
                ]:
                    os.remove(os.path.join(PROFILE_D_PATH, each))
        return 'Modular-CLI autocomplete has been successfully deleted'
    except Exception as e:
        _LOG.error(f'Something happened while removing autocomplete. Reason: {e}')
        raise
