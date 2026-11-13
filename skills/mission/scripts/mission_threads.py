"""Alias: `mission threads import <slug>` runs mission_thread.py import. See mission_thread.py for every subcommand."""
import sys

from mission_thread import main

if __name__ == "__main__":
    sys.exit(main())
