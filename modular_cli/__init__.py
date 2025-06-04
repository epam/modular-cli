import os
import sys
import re


def get_entry_point() -> str:
    """
    Returns the entry point. If no entry point is found, it returns 'modular-cli'
    """
    if not sys.argv:
        return 'modular-cli'
    return os.path.basename(re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0]))


ENTRY_POINT = get_entry_point()
