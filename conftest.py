import pathlib
import sys

# Make `src` importable when running pytest from the repository root.
sys.path.insert(0, str(pathlib.Path(__file__).parent))
