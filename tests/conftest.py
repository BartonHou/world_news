import sys
from pathlib import Path

# Make scripts/ importable so tests can `import probe` / `import filter_config`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
