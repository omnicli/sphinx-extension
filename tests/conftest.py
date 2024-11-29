# -*- coding: utf-8 -*-

import sys
from pathlib import Path

# Get the absolute path to the lib directory
lib_path = str(Path(__file__).parent.parent / "lib")

# Add the lib directory to Python path if not already there
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)
