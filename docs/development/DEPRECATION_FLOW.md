# Command Deprecation Guide

## Quick Reference

```python
from modular_cli_sdk.utils.view_utils import deprecated

@deprecated(
    removal_date='2025-06-01',        # Required: YYYY-MM-DD
    alternative='new-command',        # Recommended
    deprecated_date='2025-01-01',     # Optional
    version='3.0.0',                  # Optional
    reason='Better implementation',   # Optional
    enforce_removal=False,            # Optional: block after date
)
@google.command(name='old_cmd')  # @deprecated BEFORE @command
def old_cmd():
    """Command description"""
    pass
```

**Metadata format (API-driven):**
```json
{
  "deprecation": {
    "removal_date": "2025-06-01",
    "alternative": "new-command"
  }
}
```

**Timeline:** Yellow (>30 days) → Red (≤30 days) → Remove command

---

## Table of Contents

1. [Installation](#installation)
2. [How It Works](#how-it-works)
3. [Usage](#usage)
4. [Parameters](#parameters)
5. [Warning Levels](#warning-levels)
6. [Best Practices](#best-practices)
7. [FAQ](#faq)
8. [Migration Examples](#migration-examples)

---

## Installation

```bash
pip install modular-cli-sdk>=3.1.0
```

Decorator location: `modular_cli_sdk/utils/view_utils.py`

## How It Works

### Two Usage Modes

**Standalone CLI** - Direct decorator usage:
```python
@deprecated(removal_date='2025-06-01')
@click.command()
def old_cmd():
    pass
```

**Integrated API+CLI** - Metadata-driven flow:

```
┌─────────────────────────────────────────┐
│ Developer adds @deprecated in code      │
└──────────────┬──────────────────────────┘
               ▼
┌─────────────────────────────────────────┐
│ modular-api parses decorator            │
│ Extracts parameters → adds to metadata  │
│ Sends JSON to CLI during login          │
└──────────────┬──────────────────────────┘
               ▼
┌─────────────────────────────────────────┐
│ modular-cli receives metadata           │
│ - Shows warnings on execution           │
│ - Adds to --help text                   │
│ - Tags in command listings              │
│ - Blocks if enforce_removal=True        │
└─────────────────────────────────────────┘
```

**Key principle:** Write `@deprecated` once, both systems handle it automatically.

## Usage

### Decorator Placement

**Important:** `@deprecated` must come **before** `@click.command()` or `@group.command()`.

**Correct:**
```python
@deprecated(removal_date='2025-06-01')
@google.command(name='old_cmd')
def old_cmd():
    pass
```

**Wrong:**
```python
@google.command(name='old_cmd')
@deprecated(removal_date='2025-06-01')  # Too late!
def old_cmd():
    pass
```

### Basic Example

```python
from modular_cli_sdk.utils.view_utils import deprecated
import click

@deprecated(
    removal_date='2027-01-01',
    alternative='google terraform init',
    deprecated_date='2026-10-19',
    reason='Outdated logic',
)
@google.command(name='activate_terraform', hidden=True)
@click.option('--tenant', '-tn', required=True)
def activate_terraform(tenant: str):
    """Creates service account keys"""
    return handler.activate_terraform(tenant)
```

**User experience:**

Runtime warning:
```
  =====================================================================
  WARNING: This command is DEPRECATED
  Deprecated since: 2026-10-19
  Scheduled for removal on: 2027-01-01 (423 days left)
  Reason: Outdated logic
  =====================================================================
```

Help text:
```
$ m3admin google activate-terraform --help

  =====================================================================
  WARNING: This command is DEPRECATED
  Deprecated since: 2026-10-19
  Scheduled for removal on: 2027-01-01 (423 days left)
  Reason: Outdated logic
  =====================================================================

Usage: m3admin google activate-terraform [OPTIONS]
  Creates service account keys

Options:
  --tenant, -tn TEXT  [required]
```

Command listing:
```
$ m3admin google --help

Available commands:
    activate_terraform [DEPRECATED]
    ...
```

### API Metadata Format

When using metadata-driven approach, API returns:

```json
{
  "command": "google",
  "subcommand": "activate_terraform",
  "description": "Creates service account keys",
  "deprecation": {
    "deprecated_date": "2026-10-19",
    "removal_date": "2027-01-01",
    "reason": "Outdated logic"
  }
}
```

**Note:** Field name is `deprecation` (not `deprecated`).

## Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `removal_date` | **Yes** | `YYYY-MM-DD` | When command will be removed |
| `alternative` | Recommended | string | Replacement command |
| `deprecated_date` | No | `YYYY-MM-DD` | When deprecation started |
| `version` | No | string | Version deprecated in |
| `reason` | No | string | Why deprecated |
| `enforce_removal` | No | bool | Raise error after date (default: `False`) |

### Enforcement Mode

**Default (`enforce_removal=False`):**
- Before date: Shows warnings, command works
- After date: Shows "REMOVAL DATE PASSED", command still works

**Strict (`enforce_removal=True`):**
- Before date: Shows warnings, command works
- After date: Raises error, command **blocked**

```python
@deprecated(
    removal_date='2025-06-01',
    alternative='new-cmd',
    enforce_removal=True,  # Command will fail after date
)
@click.command()
def strict_cmd():
    pass
```

**After 2025-06-01:**
```
  =====================================================================
  ERROR: This command has been REMOVED!
  Removal date: 2025-06-01 (10 days ago)
  Use instead: new-cmd
  =====================================================================
Error: Command removed on 2025-06-01. Use: new-cmd
```

## Warning Levels

### Color Coding

| Days Until Removal | Color | Message | Tag |
|-------------------|-------|---------|-----|
| >30 | Yellow | "Scheduled for removal on: DATE (X days left)" | `[DEPRECATED]` |
| 1-30 | Red | "Will be REMOVED in X days on: DATE" | `[DEPRECATED]` |
| 0 | Red | "Will be REMOVED TODAY on: DATE" | `[DEPRECATED]` |
| <0 | Red | "REMOVAL DATE PASSED on: DATE (X days ago)" | `[REMOVED]` |

### Warning Locations

**Runtime (stderr):**
- Shows every time command executes
- Color-coded by urgency
- Doesn't affect command output (goes to stderr)

**Help text (stdout):**
- Shows when user runs `--help`
- Same color coding as runtime
- Appears at top of help

**Command listings (stdout):**
- Shows when user runs `m3admin group --help`
- Adds `[DEPRECATED]` or `[REMOVED]` tag
- Hidden commands don't appear in listings

### Combined: Hidden + Deprecated

Commands can be both hidden and deprecated:

```python
@deprecated(removal_date='2027-01-01', reason='Outdated')
@google.command(name='internal_tool', hidden=True)
def internal_tool():
    pass
```

**Behavior:**
- Not shown in command listings (`hidden=True`)
- If executed directly, shows deprecation warning
- Use for internal commands being phased out

## Best Practices

### Recommended Workflow

```
Phase 1: Soft Deprecation (2-3 months)
├─ Add @deprecated with enforce_removal=False
├─ Users see yellow/red warnings
├─ Command still works
├─ Announce in changelog
└─ Monitor usage if possible

Phase 2: Grace Period (Optional)
├─ Removal date passes
├─ Users see "REMOVAL DATE PASSED"
├─ Command still works (grace period)
└─ Give extra time if needed

Phase 3: Hard Removal
├─ Option A: Delete command from code
│  OR
├─ Option B: Enable enforce_removal=True
└─ Update docs and changelog
```

### DO

- Place `@deprecated` **before** `@command()`
- Provide `alternative` parameter
- Give 2-3 months notice for common commands
- Keep command working during deprecation (unless enforce_removal)
- Remove after date passes
- Document in changelog

### DON'T

- Remove before announced date
- Change command behavior during deprecation
- Use less than 1 month timeframes
- Forget to provide alternative
- Use `enforce_removal=True` immediately

### Timeline Guidelines

| Command Usage | Notice Period |
|---------------|---------------|
| Low usage / Internal | 1 month |
| Moderate usage | 2 months |
| High usage / Critical | 3+ months |

## FAQ

**Q: What's required?**  
A: Only `removal_date`. But always add `alternative` for better UX.

**Q: What happens after the date?**  
A: Depends on `enforce_removal`:
- `False` (default): Warning changes to "REMOVAL DATE PASSED", command works
- `True`: Command raises error and stops working

**Q: Can I change the date?**  
A: Yes, just update the parameter.

**Q: Do I deprecate in API and CLI separately?**  
A: No. Add `@deprecated` in your API code once. API parses it → sends metadata → CLI displays warnings automatically.

**Q: Which approach should I use?**  
A: 
- **Decorator**: Standalone CLI modules
- **Metadata**: API-driven commands (most common)

**Q: Does this break CI/CD?**  
A: No. Warnings go to stderr. Exit codes unchanged (unless enforcement enabled).

**Q: How do I deprecate a flag/option?**  
A: Deprecate the command, mention the option in `reason`:
```python
@deprecated(
    removal_date='2025-06-01',
    alternative='command --new-flag',
    reason='Flag --old-flag deprecated, use --new-flag'
)
```

**Q: What's the difference between hidden and deprecated?**

| Feature | `hidden=True` | `@deprecated` |
|---------|--------------|---------------|
| Shows in listings | No | Yes (with tag) |
| Shows warnings | No | Yes |
| Intended use | Internal tools | Phasing out |

**Q: Can I combine hidden + deprecated?**  
A: Yes! Command won't appear in listings but shows warning if executed directly.

**Q: Where do warnings appear?**  
A: 
- Runtime: stderr (colored)
- Help: stdout (as part of `--help`)
- Listings: stdout (as tags like `[DEPRECATED]`)

**Q: Metadata field name?**  
A: Use `deprecation` (not `deprecated`) in JSON.

## Migration Examples

### Example 1: Basic Deprecation

```python
# Before
@google.command(name='old_command')
def old_command():
    return handler.do_something()

# After
@deprecated(
    removal_date='2025-06-01',
    alternative='google new_command',
    reason='Replaced with improved implementation'
)
@google.command(name='old_command')
def old_command():
    return handler.do_something()
```

### Example 2: Hidden + Deprecated

```python
@deprecated(
    removal_date='2026-12-31',
    reason='Internal tool no longer needed'
)
@google.command(name='diagnostic_tool', hidden=True)
def diagnostic_tool():
    """Internal diagnostics"""
    return handler.run_diagnostics()
```

### Example 3: Strict Enforcement

```python
@deprecated(
    removal_date='2025-04-01',
    alternative='secure_command --auth',
    reason='Security vulnerability',
    enforce_removal=True  # Blocks after date
)
@admin.command(name='insecure_command')
def insecure_command():
    return handler.insecure_operation()
```

### Example 4: Complete Metadata

```python
@deprecated(
    deprecated_date='2025-01-15',
    removal_date='2025-06-01',
    alternative='environment customer admin remove',
    version='3.5.0',
    reason='Inconsistent naming convention',
    enforce_removal=False
)
@environment.command(name='delete_customer_admins')
@click.option('--customer-id', required=True)
@click.option('--email', required=True)
def delete_customer_admins(customer_id, email):
    """Remove customer admin users"""
    return handler.remove_admins(customer_id, email)
```

## Summary

1. Add `@deprecated(removal_date='2025-06-01')` **before** `@command()`
2. Users see yellow (>30 days) or red (≤30 days) warnings
3. Wait for removal date to pass
4. Delete command or enable `enforce_removal=True`
5. Document in changelog

**Questions?** SupportSyndicateTeam@epam.com  
**Last Updated:** 2025-11-06
**Version:** 1.0.0
