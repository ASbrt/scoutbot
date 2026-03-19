from pathlib import Path
import pandas as pd
import dtale

def make_dtale_safe(df: pd.DataFrame) -> pd.DataFrame:
    """Storing python objects in the pkl files so we need to change dtypes for dtale to work"""
    df = df.reset_index().copy()
    object_cols = df.select_dtypes(include=["object", "string"]).columns
    df[object_cols] = df[object_cols].astype(str)
    return df

exports = Path(__file__).resolve().parents[1] / "exports"
turns_file = sorted(exports.glob("*_turns.pkl"))[-1]
stem = turns_file.name.removesuffix("_turns.pkl")
flips_file = exports / f"{stem}_flips.pkl"

turns = pd.read_pickle(turns_file)
flips = pd.read_pickle(flips_file)

d1 = dtale.show(make_dtale_safe(turns), name="turns", subprocess=False)
d2 = dtale.show(make_dtale_safe(flips), name="flips", subprocess=False)

print("Turns:", d1._main_url)
print("Flips:", d2._main_url)

