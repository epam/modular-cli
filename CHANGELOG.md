CHANGELOG
=========

# [2.3.31] - 2026-05-20
* The command output format has been improved, and the root-level commands `set_output` and `get_output` have been added to control the default output format

# [2.3.30] - 2026-03-05
* Fix inconsistent column alignment across help output sections:
  - Compute a single global column width across all item types (modules, groups, commands)
  - Ensure description separators (`-`) align uniformly regardless of section
  - Add `_compute_max_name_width` helper to calculate width from all sections before rendering
  - Add `fixed_name_width` parameter to `_format_items_with_descriptions` to accept pre-computed width

# [2.3.29] - 2026-02-17
* Improve help output formatting:
  - Implement dynamic column width calculation based on longest command name
  - Add minimum width parameter (24 characters) with auto-expansion for longer names
  - Fix description truncation to break at word boundaries instead of mid-word
  - Remove trailing punctuation before adding ellipsis to prevent double periods (e.g., `...` instead of `....`)
  - Clean up descriptions (remove newlines and extra spaces) before display
  - Ensure proper alignment of command descriptions in help listings
* Fix help output display order:
  - Enforce consistent hierarchical type order: modules → groups → commands
  - Apply ordering to both root help and group-level help displays
  - Fix issue where groups could appear after commands in listings

# [2.3.28] - 2026-02-11
* Add additional notice for the hidden group of commands

# [2.3.27] - 2026-01-14
* Add group deprecation support:
  - Extend `find_token_meta()` to collect `_parent_deprecations` from parent groups
  - Add `_current_group_info` metadata for group help display
  - Add `check_all_deprecation_enforcement()` to block removed groups and commands
  - Add `emit_all_deprecation_warnings()` to emit warnings for deprecated groups and commands
  - Add `format_group_deprecation_info()` for group deprecation display in help
  - Show deprecation tags for groups in help listings (not just commands)
  - Show group deprecation warnings when executing commands under deprecated groups
* Refactor deprecation helpers in `utils.py`:
  - Consolidate `parse_date_from_str()` and `days_until_removal()` into `_days_until()`
  - Rename `get_deprecation_color()` to `_get_color()` (private)
  - Rename `format_deprecation_lines()` to `_format_deprecation_lines()` with `entity_type` param
  - Remove unused `format_deprecation_block_styled()`
* Consolidate `find_token_meta()` - remove duplicate from `help_client.py`, use `utils.py` version
* Improve `get_deprecation_tag()` with styled output and days remaining (e.g., `[DEPRECATED - 15d left]`)

# [2.3.26] - 2026-01-13
* Add description display support in help system:
  - Add `_get_item_description()` method to extract descriptions from metadata
  - Add `_format_items_with_descriptions()` method for aligned column formatting
  - Update `get_help_message()` to display descriptions alongside modules/groups/commands
  - Store items as `(name, description)` tuples for proper formatting
  - Truncate long descriptions to 50 characters with ellipsis
* Update `root_commands.json`:
  - Add `type: "root command"` field to all root commands
  - Add `enable_autocomplete` and `disable_autocomplete` commands
  - Clean up descriptions (remove redundant "Usage:" prefixes)

# [2.3.25] - 2026-01-12
* Add hidden group support in help system:
  - Add `_should_show_group()` method to determine group visibility
  - Filter hidden groups from help listings while keeping them executable
  - Add `find_token_meta()` function for metadata navigation with hidden item handling
  - Add `_filter_hidden_items()` helper to filter hidden groups and commands from display

# [2.3.24] - 2026-01-08
* Remove extra indentation from deprecation/hidden command warnings in help output

# [2.3.23] - 2026-01-08
* Fix hidden root commands appearing in module help listings (e.g., `billing --help`)

# [2.3.22] - 2026-01-05
* Fix `version` command to work without configuration by gracefully handling missing setup
* Fix `version` command help text incorrectly showing "login" instead of "version"

# [2.3.21] - 2026-01-02
* Improve error message when invalid parameters are provided

# [2.3.20] - 2025-12-11
* Fix duplicate validation warnings in `CommandResponse` by skipping client-side validation for server responses

# [2.3.19] - 2025-12-10
* Fix case-sensitive enum parameter validation to accept values regardless of case

# [2.3.18] - 2025-12-05
* Add validation for enum parameters using `allowed_choices` field from command metadata

# [2.3.17] - 2025-11-24
* Fix file permission error handling to display accurate error messages instead of generic `file not found` with traceback
* Improve file reading to use context manager for proper resource management

# [2.3.16] - 2025-11-20
* Improve `README.md`

# [2.3.15] - 2025-11-03
* Add support for processing command deprecation metadata from API

# [2.3.14] - 2025-10-16
* Add `DEPRECATION_FLOW.md` file describing the deprecation process for the CLI tool

# [2.3.13] - 2025-10-16
* Update library `click` from 7.1.2 to 8.3.0

# [2.3.12] - 2025-09-04
### Add
- Support for hidden commands in help system
- Hidden commands are now properly filtered from group help listings
- Direct execution and help access for hidden commands when specifically requested
### Change
- `HelpProcessor.get_help_message()` now filters out commands with `is_command_hidden` flag from general listings
- `HelpProcessor.generate_module_meta()` excludes hidden commands from group listings but includes them for specific requests
### Improve
- Help system now respects command visibility settings from modular-api
- Better alignment with Click's native hidden command behavior

# [2.3.11] - 2025-08-05
* HTTP error handling improvements in `modular_cli.utils.exceptions` and `modular_cli.service.decorators`:
  * Dynamic exception mapping generation using dict comprehension for `HTTP_CODE_EXCEPTION_MAPPING`
  * Error type resolution in `unpack_error_result_values()`:
    - Add assertion: `error_code >= 400`
    - Direct fallback to `HTTPStatus` for unmapped codes
* Update README.md configuration section to reflect the new installation process

# [2.3.10] - 2025-07-01
* Update libraries:
  * `prettytable` from `3.9.0` to `3.16.0`
  * `PyYAML` from `6.0.1` to `6.0.2`
  * `requests` from `2.31.0` to `2.32.4`
* Remove `requirements.txt`
* Fix `LoginCommandHandler.execute_command()` to handle non-JSON responses when status is
`HTTPStatus.OK` by catching `json.JSONDecodeError` and returning user-friendly error message

# [2.3.9] - 2025-04-25
* Fix the path to the help file for containers
* Update code to use dynamic `ENTRY_POINT` instead of static `modular-cli` for logging, exception handling, and messages

# [2.3.8] - 2025-04-15
* Fix shell detection in containers for `m3admin enable_autocomplete` command
* Add library `shellingham==1.5.4`
* Add `--shell` parameter to the `enable_autocomplete` command

# [2.3.7] - 2025-03-25
* Add `health_check` command

# [2.3.6] - 2025-02-25
[EPMCEOOS-6631]:
* Improve re-login help message and handled token expiration in CLI

# [2.3.5] - 2025-02-06
* Add `MISSING_CONFIGURATION_MESSAGE` constant for error handling
[EPMCEOOS-6591]:
* Fix code based on SonarQube recommendations

# [2.3.4] - 2025-01-08
* Add ability to hide and input parameters interactively by supporting `interactive_settings`

# [2.3.3] - 2024-11-12
* Update output message to include alias if it exists when required parameters are missing

# [2.3.2] - 2024-10-31
* Fix bug `NoneType` object has no attribute `login` if configuration is missing

# [2.3.1] - 2024-10-29
* Update `README.md` file for `PYPI`

# [2.3.0] - 2024-09-20
* Fix output of `modular-cli version` command

# [2.2.0] - 2024-08-22
* Update CLI to support `refresh token` implementation and store it in the 
`credentials` file
* Fix issue where JSON conversion prompt appears even when table fits in terminal

# [2.1.0] - 2024-08-20
* Reduce all output parameter keys to the same style

# [2.0.11] - 2024-08-19
* Fix `get_entry_point` to return the intended entry point by specifically 
checking for the default package name in package resources

# [2.0.10] - 2024-07-19
* Support more successful status codes

# [2.0.9] - 2024-07-01
* Fix `'str' object has no attribute 'items'` issue when `--table` flag is present

# [2.0.8] - 2024-06-25
* Fix bug in `process_table_view` method causing table breakage if `\r\n` are in
object set into a table

# [2.0.7] - 2024-06-10
* Add exit code 1 for handling non-200 status code responses

# [2.0.6] - 2024-05-07
* Enhance table view by increasing value of `MAX_COLUMNS_WIDTH` and reusing this
constant instead of using hardcoded value
* Fix a bug in the `process_table_view` method that breaks the table and shifts
it if the headers are not in each json block

# [2.0.5] - 2024-04-19
* Enhance readability by using the `modular setup` command if an invalid link is
provided by the user.

# [2.0.4] - 2024-03-05
* hide error logs when executing cli commands on MacOS

# [2.0.3] - 2024-02-07
* Update the `README.md` file: 
  * Add the `Open Source Code` link
  * Change the `Support` email

# [2.0.2] - 2024-02-07
* Update python version in the `README.md` file

# [2.0.1] - 2023-10-30
* Implemented proper bool type command option processing

# [2.0.0] - 2023-09-25
* Update libraries to support Python 3.10:
  * `prettytable` from 3.2.0 to 3.9.0
  * `PyYAML` from 6.0 to 6.0.1
  * `requests` from 2.27.1 to 2.31.0
  * `tabulate` from 0.8.9 to 0.9.0
  * `typing_extensions` from 4.2.0 to 4.7.1
  * `zipp` from 3.8.0 to 3.12.0
  * `wcwidth` from 0.2.5 to 0.2.6

## [1.2.9] - 2023-07-24
* Add dynamic resolving of console script` entry point to improve help-strings 
templates

## [1.2.9] - 2023-08-02
* Add ability to set custom log path by environment variable `SERVICE_LOGS` [EPMCEOOS-5023]

## [1.2.8] - 2023-07-24
* Add ability to set up entry point for console script by env. variable named 
`MODULAR_CLI_ENTRY_POINT`

## [1.2.7] - 2023-07-20
* Repository structure refactoring

## [1.2.6] - 2023-06-08
* Update README.md file for Open Source

## [1.2.5] - 2023-05-25
* Fix a bug with auto login in case if headers not received by Modular-API

## [1.2.4] - 2023-05-03
* Implement automated re-login for users [EPMCEOOS-4864]

## [1.2.3] - 2023-04-18
* Add 201, 203, 204, 205, 206 to list of successful codes;
* Support 204 code separately by showing such a message 
  `Request is successful. No content returned` when the code occurs;


## [1.2.2] - 2023-04-11
* Show module-specific extra attributes in `Meta` attribute for json view 
  and as yellow text for table view
* Update error message in case if user credentials are expired

## [1.2.1] - 2023-04-07
* Rename configuration folder from `~/m3modularcli` to `~/.m3modularcli`
  keeping backward compatibility

## [1.2.0] - 2023-04-05
* Update README.md file
* Rework `m3admin login` command
* Update README.md file

## [1.1.5] - 2023-02-28
* Combine root and regular commands for prettify display output

## [1.1.4] - 2023-02-15
* Add new success code `202`

## [1.1.3] - 2023-02-15
* Fix a bug associated with inability to work with autocomplete for multiple users 
on one instance

## [1.1.2] - 2023-02-14
* Fix an error associated with inability to describe root M3admin tool version 
during performing `m3admin version --detailed`

## [1.1.1] - 2023-01-26
* Fix an error associated with inability clear respond on missed value for 
parameter during processing request from terminal

## [1.1.0] - 2022-11-02
* Implement version compatibility check

## [1.0.13] - 2022-11-02
* Implement `m3admin version` command which describes all user available 
tool(s) version or current component  

## [1.0.12] - 2022-11-02
* Fix an error associated with incorrect processing of negative parameter 
values passed from terminal 

## [1.0.11] - 2022-11-02
* Fix incorrect processing input URL during execution `setup` command which 
leads to `404 Not Found` error during commands in case URL ends with `/` char   

## [1.0.10] - 2022-09-30
* Added the processing of the `LOG_PATH` environment variable for storing 
  logs by the custom path. Changed the default path of the storing logs 
  on the Linux-based VMs to the 
  `/var/log/<app_name>/<user_name>/<app_name.log>`path. [SFTGMSTR-6234]

# [1.0.9] - 2022-09-06
* Fix the bug related to incorrect response parsing

# [1.0.8] - 2022-08-22
* Fix the bug related to the inability to use autocomplete after changing 
  the save path of the commands meta file [SFTGMSTR-6277]

# [1.0.7] - 2022-08-17
* Move storage of commands meta to the user home directory

# [1.0.6] - 2022-06-24
* Fix invalid API path resolving when submitting request to server

# [1.0.5] - 2022-06-17
* Implemented `hidden` parameters which allows securing sensitive 
information in logs [SFTGMSTR-5931]

# [1.0.4] - 2022-06-06
* Fix parameters parsing in autocomplete
* Added ability to authenticate through JWT

# [1.0.3] - 2022-05-23
* Add version command

# [1.0.2] - 2022-04-20
* Add ability to submit passed files to server

# [1.0.1] - 2022-04-20
* Changed tool name from `m3modularcli` to `m3admin`

# [1.0.0] - 2022-04-15
* Fix an error associated with command freeze in case to `setup` command 
passed invalid link
* Added logging to the tool
