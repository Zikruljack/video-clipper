from __future__ import annotations

from src.heatmap_pipeline import *
from src.heatmap_pipeline import main


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
