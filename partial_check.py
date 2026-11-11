import pandas as pd, numpy as np
from scipy.stats import spearmanr, rankdata, pearsonr

df = pd.read_parquet("data/features.parquet")
lab = pd.read_csv("data/labels.csv")
vb = "VBmax_smoothed" if "VBmax_smoothed" in lab.columns else next(c for c in lab.columns if "vb" in c.lower())
feats = [f for f in ["Fx_rms","Fy_rms","Fx_peak","Fy_peak","Fx_harmonic_1","Fy_harmonic_1","Vx_kurtosis","Sound_rms"] if f in df.columns]

g = df.groupby("cycle")[feats].mean().join(lab.set_index("cycle")[vb])
g["day"] = df.groupby("cycle").source_file.first().str[:5]
print("cycles per day:", g.day.value_counts().describe()[["count","min","max"]].to_dict())

def resid(y, x):
    b = np.polyfit(x, y, 1); return y - np.polyval(b, x)

print("\n feature            partial rho (cycle removed)   within-day rho")
for f in feats:
    s = g[[f, vb, "day"]].dropna().copy(); s["c"] = s.index.values
    rf, rv, rc = rankdata(s[f]), rankdata(s[vb]), rankdata(s["c"])
    partial = pearsonr(resid(rf, rc), resid(rv, rc))[0]
    dm = s[[f, vb]] - s.groupby("day")[[f, vb]].transform("mean")
    keep = s.groupby("day")[f].transform("size") >= 2
    within = spearmanr(dm[f][keep], dm[vb][keep])[0]
    print(f" {f:16s} {partial:+.2f}                        {within:+.2f}")
