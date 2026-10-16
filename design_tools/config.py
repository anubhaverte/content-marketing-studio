"""
Forwarding module to studio.design_tools.config.
Allows running and importing design_tools.config directly from repository root.
"""
import sys
from pathlib import Path

# Ensure repo root is in sys.path so studio package can be imported
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from studio.design_tools.config import *
import studio.design_tools.config as _sc

if __name__ == "__main__":
    _sc.print_summary()
