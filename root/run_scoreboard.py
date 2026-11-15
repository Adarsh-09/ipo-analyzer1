import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.evaluation.harness import run_all

print(run_all(ROOT / "data/interim/kaggle/model_base_v3.csv", ROOT / "reports/evaluation", ROOT / "reports/figures"))