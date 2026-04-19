# conftest.py
# Adds the project root to the Python path so modules can be found

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))