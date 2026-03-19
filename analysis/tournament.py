import pandas as pd
from pathlib import Path
import dtale

project_root = Path(__file__).resolve().parents[1]
tournament_dir = project_root / "exports" / "tournaments"

df = pd.read_csv(f"{tournament_dir}/10_3_5_10000_tournament.csv")

d = dtale.show(df, subprocess=False)

