import re, sys, numpy as np, pandas as pd
from sklearn.ensemble import RandomForestClassifier
cyc, BUF = int(sys.argv[1]), 3
names = ["fresh", "moderate", "severe"]
df = pd.read_parquet("data/features.parquet")
lab = pd.read_csv("data/labels.csv")
lab["y"] = lab["class"].str.lower().map({n: i for i, n in enumerate(names)})
df = df.merge(lab[["cycle", "y", "VBmax_smoothed"]], on="cycle")
frc = [c for c in df.columns if re.match(r"^(Fx|Fy|Fz|Mz)_", c)]
df = df[df[frc].notna().all(axis=1)]
tr = df[(df.cycle - cyc).abs() > BUF]
tr = pd.concat([g.sample(min(len(g), 150), random_state=0) for _, g in tr.groupby("cycle")])
te = df[df.cycle == cyc]
m = RandomForestClassifier(300, min_samples_leaf=5, class_weight="balanced_subsample", n_jobs=-1, random_state=0)
m.fit(tr[frc].to_numpy(float), tr.y.to_numpy())
p = np.zeros((len(te), 3)); p[:, m.classes_] = m.predict_proba(te[frc].to_numpy(float))
mean = p.mean(0)
print(f"cycle {cyc}: {len(te)} windows, trained without cycles {cyc-BUF}-{cyc+BUF}")
print("mean probability  fresh %.2f | moderate %.2f | severe %.2f" % tuple(mean))
print("predicted:", names[mean.argmax()], "| true:", names[int(te.y.iloc[0])], "| measured VBmax_smoothed: %.3f mm" % te.VBmax_smoothed.iloc[0])
