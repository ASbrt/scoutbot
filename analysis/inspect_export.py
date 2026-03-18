from pathlib import Path
import pandas as pd
import dtale

"""This will print a bunch of errors - it works though. Just follow the links for Turns and Flips"""

def make_dtale_safe(df: pd.DataFrame) -> pd.DataFrame:
    """Dtale fails to open the pkl files directly since it is not made to handle python objects"""
    df = df.reset_index().copy()
    object_cols = df.select_dtypes(include=["object"]).columns
    df[object_cols] = df[object_cols].astype(str)
    return df

# Select files
exports = Path(__file__).resolve().parents[1] / "exports"
turns_file = sorted(exports.glob("*_turns.pkl"))[-1]
stem = turns_file.name.removesuffix("_turns.pkl")
flips_file = exports / f"{stem}_flips.pkl"

turns = pd.read_pickle(turns_file)
flips = pd.read_pickle(flips_file)

turns.info()
flips.info()

d1 = dtale.show(make_dtale_safe(turns), name="turns")
d2 = dtale.show(make_dtale_safe(flips), name="flips")

print("Turns:", d1._main_url)
print("Flips:", d2._main_url)

input("Press Enter to stop D-Tale")

