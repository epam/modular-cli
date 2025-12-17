import base64
import json
import time
from pathlib import Path
from datetime import date
from typing import Optional
import click

from modular_cli.utils.exceptions import ModularCliBadRequestException
from modular_cli.utils.variables import COMMANDS_META
from modular_cli.utils.logger import get_logger


_LOG = get_logger(__name__)

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


def parse_date_from_str(date_str: str) -> Optional[date]:
    """Parse date string in YYYY-MM-DD format."""
    try:
        return date.fromisoformat(date_str)
    except (ValueError, AttributeError, TypeError):
        return None


def days_until_removal(removal_date_str: str) -> int:
    """Calculate days until removal date."""
    removal_date = parse_date_from_str(removal_date_str)
    if not removal_date:
        return 0
    return (removal_date - date.today()).days


def format_deprecation_lines(deprecation_info: dict) -> list[str]:
    """
    Format deprecation information as warning lines.

    Args:
        deprecation_info: Dict with keys: removal_date, alternative,
                         deprecated_date, version, reason

    Returns:
        List of formatted warning lines (including separators)
    """
    if not deprecation_info:
        return []

    removal_date_str = deprecation_info.get('removal_date')
    if not removal_date_str:
        return []

    days_left = days_until_removal(removal_date_str)
    IND = "  "
    SEP = "=" * 69

    lines = [
        f"{IND}{SEP}",
        f"{IND}WARNING: This command is DEPRECATED"
    ]

    deprecated_date = deprecation_info.get('deprecated_date')
    if deprecated_date:
        lines.append(f"{IND}Deprecated since: {deprecated_date}")

    version = deprecation_info.get('version')
    if version:
        lines.append(f"{IND}Deprecated in version: {version}")

    # Format removal date message
    if days_left > 30:
        lines.append(
            f"{IND}Scheduled for removal on: {removal_date_str} "
            f"({days_left} days left)"
        )
    elif days_left > 0:
        lines.append(
            f"{IND}Will be REMOVED in {days_left} days on: {removal_date_str}"
        )
    elif days_left == 0:
        lines.append(f"{IND}Will be REMOVED TODAY on: {removal_date_str}")
    else:
        lines.append(
            f"{IND}REMOVAL DATE PASSED on: {removal_date_str} "
            f"({abs(days_left)} days ago)"
        )

    alternative = deprecation_info.get('alternative')
    if alternative:
        lines.append(f"{IND}Use instead: {alternative}")

    reason = deprecation_info.get('reason')
    if reason:
        lines.append(f"{IND}Reason: {reason}")

    lines.append(f"{IND}{SEP}")

    return lines


def format_command_warnings_block_styled(
        deprecation_info: dict = None,
        is_hidden: bool = False
) -> str:
    """
    Format combined command warnings (deprecation + hidden status) in a single block.

    Args:
        deprecation_info: Deprecation metadata
        is_hidden: Whether the command is hidden

    Returns:
        Colored string with newlines (for help display)
    """
    if not deprecation_info and not is_hidden:
        return ""

    lines = []
    IND = "  "

    # Add deprecation warnings first (higher priority)
    if deprecation_info:
        deprecation_lines = format_deprecation_lines(deprecation_info)
        if deprecation_lines:
            # Remove the separators from deprecation_lines
            # (they're at index 0 and -1)
            lines.extend(deprecation_lines[1:-1])

    # Add hidden command notice
    if is_hidden:
        if lines:  # Add blank line if we already have deprecation info
            lines.append("")
        lines.append(f"{IND}NOTICE: This is a HIDDEN COMMAND")
        lines.append(
            f"{IND}This command is not shown in standard help listings")

    # Wrap with separators
    if lines:
        SEP = "=" * 69
        lines.insert(0, f"{IND}{SEP}")
        lines.append(f"{IND}{SEP}")

    # Apply color styling
    if deprecation_info and deprecation_info.get('removal_date'):
        color = get_deprecation_color(deprecation_info['removal_date'])
    else:
        color = 'cyan'  # Default color for hidden-only commands

    styled_lines = [click.style(line, fg=color, bold=True) for line in lines]
    return '\n'.join(styled_lines)


def get_deprecation_color(removal_date_str: str) -> str:
    """
    Get appropriate color for deprecation warning.

    Returns:
        'yellow' if >30 days until removal, 'red' otherwise
    """
    days_left = days_until_removal(removal_date_str)
    return "yellow" if days_left > 30 else "red"


def format_deprecation_block_styled(deprecation_info: dict) -> str:
    """
    Format deprecation block with ANSI color styling for help text.

    Args:
        deprecation_info: Deprecation metadata

    Returns:
        Colored string with newlines (for help display)
    """
    if not deprecation_info:
        return ""

    removal_date_str = deprecation_info.get('removal_date')
    if not removal_date_str:
        return ""

    lines = format_deprecation_lines(deprecation_info)
    color = get_deprecation_color(removal_date_str)

    styled_lines = [click.style(line, fg=color, bold=True) for line in lines]
    return '\n'.join(styled_lines)


def emit_deprecation_warning(deprecation_info: dict) -> None:
    """
    Emit deprecation warning to stderr at runtime.
    This is called BEFORE command execution (like the original decorator).

    Args:
        deprecation_info: Deprecation metadata
    """
    if not deprecation_info:
        return

    removal_date_str = deprecation_info.get('removal_date')
    if not removal_date_str:
        return

    lines = format_deprecation_lines(deprecation_info)
    color = get_deprecation_color(removal_date_str)

    for line in lines:
        click.secho(line, fg=color, bold=True, err=True)

    # No blank line after - to match original behavior


def check_deprecation_enforcement(deprecation_info: dict) -> None:
    """
    Check if command should be blocked due to removal date passing.

    Args:
        deprecation_info: Deprecation metadata

    Raises:
        click.UsageError: If command is removed and enforcement is enabled
    """
    if not deprecation_info:
        return

    removal_date_str = deprecation_info.get('removal_date')
    if not removal_date_str:
        return

    days_left = days_until_removal(removal_date_str)
    enforce_removal = deprecation_info.get('enforce_removal', False)

    if enforce_removal and days_left < 0:
        # Show error message
        click.secho("  " + "=" * 69, fg="red", bold=True, err=True)
        click.secho(
            "  ERROR: This command has been REMOVED!",
            fg="red",
            bold=True,
            err=True,
        )
        click.secho(
            f"  Removal date: {removal_date_str} ({abs(days_left)} days ago)",
            fg="red",
            bold=True,
            err=True,
        )

        alternative = deprecation_info.get('alternative')
        if alternative:
            click.secho(
                f"  Use instead: {alternative}",
                fg="red",
                bold=True,
                err=True,
            )
        click.secho("  " + "=" * 69, fg="red", bold=True, err=True)

        _LOG.error(
            f"Attempted to execute removed command. Removal date: {removal_date_str}")

        raise click.UsageError(
            f"Command removed on {removal_date_str}. "
            f"Use: {alternative if alternative else 'See documentation for alternatives'}"
        )


def get_deprecation_tag(deprecation_info: dict) -> str:
    """
    Get a tag to append to command names in listings.

    Returns:
        " [DEPRECATED]", " [REMOVED]", or empty string
    """
    if not deprecation_info:
        return ""

    removal_date_str = deprecation_info.get('removal_date')
    if not removal_date_str:
        return ""

    days_left = days_until_removal(removal_date_str)

    if days_left < 0:
        return " [REMOVED]"
    else:
        return " [DEPRECATED]"
