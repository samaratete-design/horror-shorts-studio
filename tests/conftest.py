import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
_API_APP_DIR = os.path.join(_ROOT, "apps", "api")

if _API_APP_DIR not in sys.path:
    sys.path.insert(0, _API_APP_DIR)
