from __future__ import annotations

import base64
import json
import time
from datetime import date
from pathlib import Path

import click

from modular_cli.utils.exceptions import ModularCliBadRequestException
from modular_cli.utils.logger import get_logger
from modular_cli.utils.variables import COMMANDS_META

_LOG = get_logger(__name__)

MODULAR_CLI_META_DIR = '.modular_cli'


def save_meta_to_file(meta: dict) -> None:
    admin_home_path = Path.home() / MODULAR_CLI_META_DIR
    admin_home_path.mkdir(exist_ok=True)
    path_to_meta = admin_home_path / COMMANDS_META
    with open(path_to_meta, 'w') as f:
        json.dump(meta, f, separators=(',', ':'))


def find_token_meta(
        commands_meta: dict,
        specified_tokens: list | None,
) -> dict:
    """
    Navigate through commands_meta to find the metadata for specified tokens.
    Also collects deprecation info from parent groups along the path.
    """
    if not specified_tokens:
        return commands_meta

    current_meta = commands_meta
    parent_deprecations = []
    first_token = specified_tokens[0]

    # If first token not found at root, search inside modules
    if first_token not in current_meta:
        for module_name, module_meta in commands_meta.items():
            if not isinstance(module_meta, dict):
                continue
            if module_meta.get('type') != 'module':
                continue
            module_body = module_meta.get('body', {})
            if first_token in module_body:
                current_meta = module_body
                break
        else:
            raise ModularCliBadRequestException(
                f'Failed to find specified command: {first_token}'
            )

    for i, token in enumerate(specified_tokens):
        is_last_token = (i == len(specified_tokens) - 1)

        if token not in current_meta:
            if isinstance(current_meta, dict) and 'body' in current_meta \
                    and token in current_meta['body']:
                current_meta = current_meta['body'][token]
            else:
                raise ModularCliBadRequestException(
                    f'Failed to find specified command: {token}'
                )
        else:
            current_meta = current_meta[token]

        # Collect group deprecation info
        if isinstance(current_meta, dict):
            if current_meta.get('type') == 'group' \
                    and current_meta.get('deprecation'):
                parent_deprecations.append({
                    'name': token,
                    'type': 'group',
                    'deprecation': current_meta['deprecation'],
                })

        if isinstance(current_meta, dict) and 'body' in current_meta:
            if is_last_token:
                body = current_meta.get('body', {})
                if isinstance(body, dict):
                    body = body.copy()
                    if parent_deprecations:
                        body['_parent_deprecations'] = parent_deprecations
                    body['_current_group_info'] = {
                        'name': token,
                        'type': current_meta.get('type'),
                        'description': current_meta.get('description', ''),
                        'deprecation': current_meta.get('deprecation'),
                        'is_group_hidden': current_meta.get('is_group_hidden', False),
                    }
                    return body
                return current_meta
            else:
                current_meta = current_meta['body']

    if isinstance(current_meta, dict) and parent_deprecations:
        current_meta = current_meta.copy()
        current_meta['_parent_deprecations'] = parent_deprecations

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
            return None

    def is_expired(self) -> bool:
        p = self.payload
        if p is None:
            return True
        exp = p.get('exp')
        if not exp:
            return False
        return exp < time.time() + self._exp_threshold


# ============================================================================
# DEPRECATION HELPER FUNCTIONS
# ============================================================================

def _days_until(removal_date_str: str) -> int:
    """Calculate days until removal date."""
    try:
        removal_date = date.fromisoformat(removal_date_str)
        return (removal_date - date.today()).days
    except (ValueError, AttributeError, TypeError):
        return 0


def _get_color(removal_date_str: str) -> str:
    """Get color based on days until removal."""
    return "yellow" if _days_until(removal_date_str) > 30 else "red"


def _format_deprecation_lines(
        deprecation_info: dict,
        entity_type: str = "command",
) -> list[str]:
    """Format deprecation warning as list of lines (without separators)."""
    removal_date_str = deprecation_info.get('removal_date', '')
    days_left = _days_until(removal_date_str)

    lines = [f"WARNING: This {entity_type} is DEPRECATED"]

    if deprecation_info.get('deprecated_date'):
        lines.append(f"Deprecated since: {deprecation_info['deprecated_date']}")

    if deprecation_info.get('version'):
        lines.append(f"Deprecated in version: {deprecation_info['version']}")

    if removal_date_str:
        if days_left > 30:
            lines.append(
                f"Scheduled for removal on: {removal_date_str} "
                f"({days_left} days left)"
            )
        elif days_left > 0:
            lines.append(
                f"Will be REMOVED in {days_left} days on: {removal_date_str}"
            )
        elif days_left == 0:
            lines.append(f"Will be REMOVED TODAY on: {removal_date_str}")
        else:
            lines.append(
                f"REMOVAL DATE PASSED on: {removal_date_str} "
                f"({abs(days_left)} days ago)"
            )

    if deprecation_info.get('alternative'):
        lines.append(f"Use instead: {deprecation_info['alternative']}")

    if deprecation_info.get('reason'):
        lines.append(f"Reason: {deprecation_info['reason']}")

    return lines


def check_deprecation_enforcement(deprecation_info: dict | None) -> None:
    """Check if command should be blocked due to removal date passing."""
    if not deprecation_info:
        return
    if not deprecation_info.get('enforce_removal', False):
        return
    removal_date_str = deprecation_info.get('removal_date')
    if not removal_date_str:
        return
    if _days_until(removal_date_str) >= 0:
        return

    alternative = deprecation_info.get('alternative')
    days_ago = abs(_days_until(removal_date_str))

    click.secho("=" * 69, fg="red", bold=True, err=True)
    click.secho(
        "  ERROR: This command has been REMOVED!",
        fg="red", bold=True, err=True,
    )
    click.secho(
        f"  Removal date: {removal_date_str} ({days_ago} days ago)",
        fg="red", bold=True, err=True,
    )
    if alternative:
        click.secho(
            f"  Use instead: {alternative}",
            fg="red", bold=True, err=True,
        )
    click.secho("=" * 69, fg="red", bold=True, err=True)

    _LOG.error(
        f"Attempted to execute removed command. Removal date: {removal_date_str}"
    )
    raise click.UsageError(
        f"Command removed on {removal_date_str}. Use: "
        f"{alternative or 'See documentation for alternatives'}"
    )


def check_all_deprecation_enforcement(token_meta: dict) -> None:
    """Check deprecation enforcement for both command AND parent groups."""
    for parent in token_meta.get('_parent_deprecations', []):
        deprecation = parent.get('deprecation')
        if not deprecation or not deprecation.get('enforce_removal', False):
            continue
        removal_date_str = deprecation.get('removal_date')
        if not removal_date_str or _days_until(removal_date_str) >= 0:
            continue

        group_name = parent.get('name', 'unknown')
        alternative = deprecation.get('alternative')
        days_ago = abs(_days_until(removal_date_str))

        click.secho("=" * 69, fg="red", bold=True, err=True)
        click.secho(
            f"  ERROR: The '{group_name}' command group has been REMOVED!",
            fg="red", bold=True, err=True)
        click.secho(f"  Removal date: {removal_date_str} ({days_ago} days ago)",
                    fg="red", bold=True, err=True)
        if alternative:
            click.secho(f"  Use instead: {alternative}", fg="red", bold=True,
                        err=True)
        click.secho("=" * 69, fg="red", bold=True, err=True)

        raise click.UsageError(
            f"Command group '{group_name}' removed on {removal_date_str}. "
            f"Use: {alternative or 'See documentation'}"
        )

    check_deprecation_enforcement(token_meta.get('deprecation'))


def emit_deprecation_warning(deprecation_info: dict | None) -> None:
    """Emit deprecation warning to stderr at runtime."""
    if not deprecation_info:
        return
    removal_date_str = deprecation_info.get('removal_date')
    if not removal_date_str:
        return

    color = _get_color(removal_date_str)
    click.secho("=" * 69, fg=color, bold=True, err=True)
    for line in _format_deprecation_lines(deprecation_info):
        click.secho(line, fg=color, bold=True, err=True)
    click.secho("=" * 69, fg=color, bold=True, err=True)


def emit_all_deprecation_warnings(token_meta: dict) -> None:
    """Emit deprecation warnings for both parent groups AND command."""
    for parent in token_meta.get('_parent_deprecations', []):
        deprecation = parent.get('deprecation')
        if not deprecation:
            continue
        removal_date_str = deprecation.get('removal_date')
        if not removal_date_str:
            continue

        group_name = parent.get('name', 'unknown')
        color = _get_color(removal_date_str)

        click.secho("=" * 69, fg=color, bold=True, err=True)
        for line in _format_deprecation_lines(
                deprecation, f"command group '{group_name}'"):
            click.secho(line, fg=color, bold=True, err=True)
        click.secho("=" * 69, fg=color, bold=True, err=True)

    emit_deprecation_warning(token_meta.get('deprecation'))


def get_deprecation_tag(deprecation_info: dict | None) -> str:
    """Get styled deprecation tag for help listings."""
    if not deprecation_info:
        return ""
    removal_date_str = deprecation_info.get('removal_date')
    if not removal_date_str:
        return click.style(" [DEPRECATED]", fg="yellow", bold=True)

    days_left = _days_until(removal_date_str)
    if days_left < 0:
        return click.style(" [REMOVED]", fg="red", bold=True)
    elif days_left <= 30:
        return click.style(f" [DEPRECATED - {days_left}d left]", fg="red",
                           bold=True)
    return click.style(" [DEPRECATED]", fg="yellow", bold=True)


def format_command_warnings_block_styled(
        deprecation_info: dict | None = None,
        is_hidden: bool = False,
) -> str:
    """Format combined warning block for command help display."""
    if not deprecation_info and not is_hidden:
        return ""

    SEP = "=" * 69
    lines = []

    # Determine color
    if deprecation_info and deprecation_info.get('removal_date'):
        color = _get_color(deprecation_info['removal_date'])
    else:
        color = "cyan"

    lines.append(click.style(SEP, fg=color, bold=True))

    # Deprecation warning first
    if deprecation_info and deprecation_info.get('removal_date'):
        for line in _format_deprecation_lines(deprecation_info):
            lines.append(click.style(line, fg=color, bold=True))

    # Hidden notice second
    if is_hidden:
        if deprecation_info:
            lines.append("")
        lines.append(click.style(
            "NOTICE: This is a HIDDEN command", fg=color, bold=True))
        lines.append(click.style(
            "This command is not shown in help listings but is still "
            "executable.", fg=color))

    lines.append(click.style(SEP, fg=color, bold=True))
    return "\n".join(lines)

def format_group_warnings_block_styled(
        deprecation_info: dict | None = None,
        is_hidden: bool = False,
) -> str:
    """Format combined warning block for group help display."""
    if not deprecation_info and not is_hidden:
        return ""

    SEP = "=" * 69
    lines = []

    # Determine color based on deprecation if present, otherwise cyan for hidden-only
    if deprecation_info and deprecation_info.get('removal_date'):
        color = _get_color(deprecation_info['removal_date'])
    else:
        color = "cyan"

    lines.append(click.style(text=SEP, fg=color, bold=True))

    # Deprecation warning first
    if deprecation_info and deprecation_info.get('removal_date'):
        for line in _format_deprecation_lines(deprecation_info, "command group"):
            lines.append(click.style(text=line, fg=color, bold=True))

    # Hidden notice second
    if is_hidden:
        if deprecation_info and deprecation_info.get('removal_date'):
            lines.append("")
        lines.append(click.style(
            text="NOTICE: This is a HIDDEN command group",
            fg=color,
            bold=True,
        ))
        lines.append(click.style(
            text="This command group is not shown in standard help listings",
            fg=color,
        ))

    lines.append(click.style(text=SEP, fg=color, bold=True))
    return "\n".join(lines)


def format_group_deprecation_info(deprecation_info: dict | None) -> str:
    """Format deprecation info for group help display."""
    if not deprecation_info:
        return ""
    removal_date_str = deprecation_info.get('removal_date', '')
    if not removal_date_str:
        return ""

    color = _get_color(removal_date_str)
    SEP = "=" * 69
    lines = [SEP]
    lines.extend(_format_deprecation_lines(deprecation_info, "command group"))
    lines.append(SEP)
    return "\n".join([click.style(line, fg=color, bold=True) for line in lines])
