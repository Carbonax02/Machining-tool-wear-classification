import pandas as pd, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

df = pd.read_parquet("data/features.parquet")
lab = pd.read_csv("data/labels.csv")
vb = "VBmax_smoothed" if "VBmax_smoothed" in lab.columns else next(c for c in lab.columns if "vb" in c.lower())
feats = ["Fx_rms", "Fy_rms", "Fx_peak", "Fy_peak", "Fx_harmonic_1", "Fy_harmonic_1", "Vx_kurtosis", "Sound_rms"]
feats = [f for f in feats if f in df.columns]

g = df.groupby("cycle")[feats].mean()
day = df.groupby("cycle").source_file.first().str[:5]
g = g.join(lab.set_index("cycle")[vb])
print("Spearman with VBmax (cycle means):")
for f in feats:
    print(f"  {f:16s} {spearmanr(g[f], g[vb], nan_policy='omit')[0]:+.2f}")
print(f"  cycle number     {spearmanr(g.index, g[vb])[0]:+.2f}")

fig, axs = plt.subplots(len(feats) + 1, 1, figsize=(10, 2 * (len(feats) + 1)), sharex=True)
axs[0].plot(g.index, g[vb], "k.-"); axs[0].set_ylabel(vb)
for ax, f in zip(axs[1:], feats):
    ax.plot(g.index, g[f], ".-"); ax.set_ylabel(f, fontsize=8)
edges = [c for c, (a, b) in zip(g.index[1:], zip(day.values[:-1], day.values[1:])) if a != b]
for ax in axs:
    for e in edges: ax.axvline(e - 0.5, color="grey", lw=0.5, ls=":")
axs[-1].set_xlabel("cycle (dotted lines = new day)")
plt.tight_layout(); plt.savefig("results/feature_trends.png", dpi=150)
print("saved results/feature_trends.png")
