"""Shared loader: import geocode_locations.py without running main().

The script guards execution behind `if __name__ == "__main__"`, so importing it
under a different module name is safe and has NO side effects (verified). We load
it by file path so the eval suite works regardless of cwd.
"""

import importlib.util
import os

_SCRIPT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "scripts", "geocode_locations.py")
)


def load_geocoder():
    if not os.path.exists(_SCRIPT):
        raise FileNotFoundError(f"Cannot find geocoder script at {_SCRIPT}")
    spec = importlib.util.spec_from_file_location("geocode_locations_under_test", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # safe: main() is __main__-guarded
    return module


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
