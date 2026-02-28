import sys
from pathlib import Path

# Add src to the path so the package can be found
src_path = Path(__file__).parent / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from literaplay.main import main

if __name__ == "__main__":
    main()
