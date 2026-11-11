import pandas as pd
from pathlib import Path

parts = sorted(Path(r"data\features.parquet.parts").glob("cycle_*.parquet"))
print("parts found:", len(parts))
dfs = {int(p.stem.split("_")[1]): pd.read_parquet(p) for p in parts}

ref_cols = list(dfs[1].columns)
ref_set = set(ref_cols)
problems = False
for c, d in dfs.items():
    cols = list(d.columns)
    missing = [x for x in ref_cols if x not in cols]
    extra = [x for x in cols if x not in ref_set]
    if missing or extra:
        problems = True
        print(f"cycle {c}: missing={missing[:8]}{'...' if len(missing)>8 else ''} ({len(missing)}) extra={extra[:8]} ({len(extra)})")
    elif cols != ref_cols:
        print(f"cycle {c}: same columns, different order (harmless)")
print("any missing/extra columns:", problems)

for c, d in dfs.items():
    for col in ["window_index_force", "window_index_vibration"]:
        if col in d: d[col] = d[col].astype("float64")
    if "vibration_source_file" in d:
        d["vibration_source_file"] = d["vibration_source_file"].astype("object")

df = pd.concat(list(dfs.values()), ignore_index=True)
df = df[ref_cols + [c for c in df.columns if c not in ref_set]]
df.to_parquet(r"data\features.parquet", index=False)

print("shape:", df.shape)
print("cycles present 1..68:", sorted(df.cycle.unique()) == list(range(1, 69)))
vib = [c for c in df.columns if c.startswith(("Vx", "Vy", "Vz", "Sound"))]
frc = [c for c in df.columns if c.startswith(("Fx", "Fy", "Fz", "Mz"))]
no_vib = df.groupby("cycle")[vib].apply(lambda g: g.isna().all().all())
print("cycles with no vibration features:", no_vib[no_vib].index.tolist())
print("force NaNs:", int(df[frc].isna().sum().sum()))
c39 = df[df.cycle == 39]
print("cycle 39 rows:", len(c39), "| corrupt_vib:", c39.corrupt_vib.unique(), "| n_invalid_dropped:", c39.n_invalid_dropped.unique())
print(df.groupby("pairing").cycle.nunique())
