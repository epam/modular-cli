import os
import shellingham
import sys

from modular_cli import ENTRY_POINT
from modular_cli.modular_cli_autocomplete import (
    BASH_COMPLETE_SCRIPT, ZSH_COMPLETE_SCRIPT, RELATIVE_PATH_TO_COMPLETE,
    PROFILE_D_PATH, PROFILE_ZSH_COMPLETE_SCRIPT, PROFILE_BASH_COMPLETE_SCRIPT,
    COMPLETE_PROCESS_FILE, TEMP_HELP_FILE,
)
from modular_cli.utils.logger import get_logger

_LOG = get_logger(__name__)
PYTHON_SYMLINK = 'PYTHON_SYMLINK'
SCRIPT_PATH = 'SCRIPT_PATH'
HELP_FILE = 'HELP_FILE'
BASH_INTERPRETER = 'bash'
ZSH_INTERPRETER = 'zsh'
COMMAND_TO_CHECK_INTERPRETER = "echo $SHELL"
SUPPORTED_SHELLS = [BASH_INTERPRETER, ZSH_INTERPRETER]
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
            _LOG.info(
                f"Autocomplete for '{ENTRY_POINT}' has been successfully "
                f"injected to the RC file: {rc_file_path}"
            )
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
    _LOG.info(
        f"Autocomplete for '{ENTRY_POINT}' has been successfully removed from "
        f"the RC file: {rc_file_path}"
    )


def _get_interpreter_and_appropriate_script(
        shell_name: str | None = None,
) -> tuple:
    if sys.platform not in ['darwin', 'linux']:
        raise OSError(
            f'The OS is not applicable for autocompletion setup. '
            f'Current OS is {sys.platform}'
        )

    if shell_name is not None:
        if shell_name not in SUPPORTED_SHELLS:
            raise ValueError(
                f'Provided shell "{shell_name}" is unsupported. '
                f'Supported shells are: {SUPPORTED_SHELLS}'
            )
        _LOG.info(f'Using provided interpreter: {shell_name}')
        interpreter = shell_name
    else:  # Auto-detection logic
        try:
            detected_shell, shell_path = shellingham.detect_shell()
            if detected_shell not in SUPPORTED_SHELLS:
                raise ValueError(
                    f'Detected shell "{detected_shell}" is unsupported. '
                    f'Supported shells are: {SUPPORTED_SHELLS}'
                )
            interpreter = detected_shell
            _LOG.info(
                f'Detected interpreter: {detected_shell}, path: {shell_path}'
            )
        except shellingham.ShellDetectionFailure:
            _LOG.warning(
                "Shell detection failed. Unable to detect current interpreter. "
                f"Autocomplete for '{ENTRY_POINT}' will be skipped"
            )
            raise RuntimeError(
                "The interpreter cannot be checked. Autocomplete for "
                f"'{ENTRY_POINT}' will be skipped"
            )

    interpreter, script = _get_appropriate_script_name(interpreter)
    if not interpreter:
        raise ValueError(
            f"Unsupported interpreter '{interpreter}'. Autocomplete for "
            f"'{ENTRY_POINT}' will be skipped"
        )
    return interpreter, script


def enable_autocomplete_handler(shell: str | None = None) -> str:
    interpreter, script = \
        _get_interpreter_and_appropriate_script(shell_name=shell)
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
                if SCRIPT_PATH in line.strip("\n") and not script_was_found:
                    line = f'SCRIPT_PATH={python_script}\n'
                    script_was_found = True
                if HELP_FILE in line.strip("\n") and not help_was_found:
                    line = 'HELP_FILE=/home/$USER/modular_cli_help.txt'
                    help_was_found = True
                f.write(line)
        message = (
            f"Autocomplete for '{ENTRY_POINT}' has been successfully set up. "
            f"Path to the 'profile.d' file: {processed_profile_script_path}"
        )
        _LOG.info(message)
        return message
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
        return f"Autocomplete for '{ENTRY_POINT}' has been successfully removed"
    except Exception as e:
        _LOG.error(f'Something happened while removing autocomplete. Reason: {e}')
        raise
