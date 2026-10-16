"""
Deprecated entry point.

The old synthesizer wrote generic HowToPlay templates on top of stemmed Melandra
descriptions. Use scripts/fix_game_texts.py instead — it restores real BGG
prose and rebuilds the custom Aatam DB.
"""

import runpy
import sys


if __name__ == "__main__":
    print(
        "[deprecated] Forwarding to scripts/fix_game_texts.py "
        "(restores BGG descriptions + rebuilds custom DB)...",
        flush=True,
    )
    sys.argv = [sys.argv[0]]
    runpy.run_path(
        __file__.replace("add_rules_and_strategies_columns.py", "fix_game_texts.py"),
        run_name="__main__",
    )
