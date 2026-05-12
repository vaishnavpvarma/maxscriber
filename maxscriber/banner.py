"""
MaXScriber v1.0
Branding and display utilities.
"""

import sys


def print_banner():
    """Display the Eau Rouge Edition banner."""
    red = "\033[91m"
    blue = "\033[94m"
    reset = "\033[0m"

    art = f"""
{red} █▀▄▀█ ▄▀▀▄ ▀▄ ▄▀ {blue} ▄▀▀▀ ▄▀▀▀ █▀▀▄ ▀█▀ █▀▀▄ █▀▀ █▀▀▄ 
{red} █ ▀ █ █▄▄█  █▀   {blue} ▀▀▀▄ █    █▄▄▀  █  █▀▀▄ █▀▀ █▄▄▀ 
{red} █   █ █  █ ▄▀ ▀▄ {blue} ▀▀▀  ▀▀▀  █  █ ▄█▄ █▄▄▀ ▀▀▀ █  █ 
{red} ═════════════════{blue}════════════════════════════ v1.0 ═══{reset}
# MaXScriber v1.0
"""
    try:
        print(art)
    except UnicodeEncodeError:
        # Fallback for terminals that can't render Unicode block chars (e.g. Windows cp1252)
        sys.stdout.buffer.write(art.encode('utf-8', errors='replace'))
        sys.stdout.buffer.write(b'\n')
        sys.stdout.buffer.flush()


def print_exit_message():
    """Display the exit message."""
    msg = "\nSIMPLY LOVELY 😉- Max Verstappen"
    try:
        print(msg)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(msg.encode('utf-8', errors='replace'))
        sys.stdout.buffer.write(b'\n')
        sys.stdout.buffer.flush()
