import re, sys, numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor
cyc = int(sys.argv[1]); BUF = int(sys.argv[2]) if len(sys.argv) > 2 else 3
df = pd.read_parquet("data/features.parquet")
lab = pd.read_csv("data/labels.csv")
df = df.merge(lab[["cycle", "VBmax_smoothed"]], on="cycle")
frc = [c for c in df.columns if re.match(r"^(Fx|Fy|Fz|Mz)_", c)]
df = df[df[frc].notna().all(axis=1)]
tr = df[(df.cycle - cyc).abs() > BUF]
tr = pd.concat([g.sample(min(len(g), 150), random_state=0) for _, g in tr.groupby("cycle")])
te = df[df.cycle == cyc]
m = RandomForestRegressor(300, min_samples_leaf=5, n_jobs=-1, random_state=0)
m.fit(tr[frc].to_numpy(float), tr.VBmax_smoothed.to_numpy())
pred = m.predict(te[frc].to_numpy(float)).mean()
true = te.VBmax_smoothed.iloc[0]; base = tr.VBmax_smoothed.mean()
print(f"cycle {cyc} (trained without cycles {cyc-BUF}-{cyc+BUF})")
print(f"predicted wear: {pred:.3f} mm | measured: {true:.3f} mm | error: {abs(pred-true):.3f} mm")
print(f"mean-predictor baseline would say {base:.3f} mm (error {abs(base-true):.3f} mm)")
