import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MAPS = REPO.parent / "maps"
SMOKE_MAP = MAPS / "map-smoke"

sys.path.insert(0, str(REPO))
