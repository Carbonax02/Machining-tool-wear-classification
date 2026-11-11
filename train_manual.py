import re, warnings
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.feature_selection import SelectFromModel
from sklearn.dummy import DummyClassifier
from sklearn.metrics import balanced_accuracy_score, f1_score, recall_score
warnings.filterwarnings("ignore")

N_PER_CYCLE = 150   # windows kept per cycle (speed + equal weight per cycle). None = use all
N_REPEATS = 3
Path("results").mkdir(exist_ok=True)

# ---------- load ----------
df = pd.read_parquet("data/features.parquet")
lab = pd.read_csv("data/labels.csv")
CLASSES = ["fresh", "moderate", "severe"]
lab["y"] = lab["class"].astype(str).str.lower().map({c: i for i, c in enumerate(CLASSES)})
assert lab["y"].notna().all(), lab["class"].unique()
vb_col = next((c for c in lab.columns if "vb" in c.lower()), None)
df = df.merge(lab[["cycle", "y"]], on="cycle", how="left")
assert df["y"].notna().all()
df["y"] = df["y"].astype(int)

# ---------- feature columns (metadata can never enter) ----------
pat = re.compile(r"^(Fx|Fy|Fz|Mz|Vx|Vy|Vz|Sound)_")
feat = [c for c in df.columns if pat.match(c)]
assert len(feat) == 184, len(feat)
frc = [c for c in feat if c.startswith(("Fx_", "Fy_", "Fz_", "Mz_"))]
vib = [c for c in feat if c not in frc]
vxyz = [c for c in vib if not c.startswith("Sound_")]
snd = [c for c in vib if c.startswith("Sound_")]

# ---------- row selection (no imputation) ----------
f_ok = df[frc].notna().all(axis=1)
v_ok = df[vib].notna().all(axis=1)
A = df[f_ok]
B = df[v_ok]
C = df[f_ok & v_ok & (df.pairing == "index")]
D = df[f_ok & v_ok & df.pairing.isin(["index", "random"])]
for n, d, r, c in [("A", A, 36597, 68), ("B", B, 34273, 65), ("C", C, 28362, 54), ("D", D, 34070, 65)]:
    cc = d.groupby("cycle").y.first().value_counts().sort_index().to_dict()
    print(f"run {n}: rows={len(d)} cycles={d.cycle.nunique()} cycles per class (0/1/2)={cc}")
    assert len(d) == r and d.cycle.nunique() == c, f"run {n} row/cycle count mismatch"

def sub(d):
    if N_PER_CYCLE is None:
        return d.reset_index(drop=True)
    return pd.concat([g.sample(min(len(g), N_PER_CYCLE), random_state=0)
                      for _, g in d.groupby("cycle")]).reset_index(drop=True)

# ---------- models ----------
def lr():
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=2000, class_weight="balanced"))
def rf():
    return RandomForestClassifier(n_estimators=200, min_samples_leaf=5, class_weight="balanced_subsample",
                                  n_jobs=-1, random_state=0)
def hgb():  # class_weight needs scikit-learn >= 1.2
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200,
                                          class_weight="balanced", random_state=0)
def rf_top20():  # feature selection happens inside each training fold
    sel = SelectFromModel(RandomForestClassifier(n_estimators=100, min_samples_leaf=5, n_jobs=-1, random_state=0),
                          max_features=20, threshold=-np.inf)
    return make_pipeline(sel, rf())
def dummy():
    return DummyClassifier(strategy="prior")

# ---------- grouped CV: all windows of a cycle stay in the same fold ----------
def cv(data, cols, make, label, ycol="y"):
    X = data[cols].to_numpy(float); y = data[ycol].to_numpy(); g = data["cycle"].to_numpy()
    cyc_y = data.groupby("cycle")[ycol].first()
    rows, last = [], None
    for rep in range(N_REPEATS):
        proba = np.zeros((len(y), 3))
        for tr, te in StratifiedGroupKFold(5, shuffle=True, random_state=rep).split(X, y, g):
            assert len(np.unique(y[tr])) == 3, "a training fold lacks a class"
            m = make(); m.fit(X[tr], y[tr]); proba[te] = m.predict_proba(X[te])
        cp = pd.DataFrame(proba).groupby(g).mean()          # cycle-level = mean window probability
        ct = cyc_y.loc[cp.index].to_numpy(); pr = cp.to_numpy().argmax(1)
        rec = recall_score(ct, pr, labels=[0, 1, 2], average=None, zero_division=0)
        rows.append([balanced_accuracy_score(ct, pr), f1_score(ct, pr, average="macro"),
                     balanced_accuracy_score(y, proba.argmax(1)), *rec])
        last = cp.assign(true=ct)
    a = np.array(rows)
    out = {"run": label, "cycles": len(cyc_y), "windows": len(y)}
    for i, n in enumerate(["cyc_bal_acc", "cyc_macroF1", "win_bal_acc", "recall_fresh", "recall_mod", "recall_severe"]):
        out[n] = f"{a[:, i].mean():.3f}+-{a[:, i].std():.3f}"
    print(out, flush=True)
    return out, last

results, oof = [], None

# ---------- headline: identical 54 cycles and identical windows for every feature set ----------
Cs = sub(C)
sets = {"force": frc, "vib+sound": vib, "vib (no sound)": vxyz, "sound only": snd, "all": feat}
for sname, cols in sets.items():
    for mname, mk in [("LR", lr), ("RF", rf)]:
        r, cp = cv(Cs, cols, mk, f"C54 | {sname} | {mname}")
        results.append(r)
        if sname == "all" and mname == "RF":
            oof = cp
results.append(cv(Cs, feat, rf_top20, "C54 | all, top-20 (in-fold) | RF")[0])
results.append(cv(Cs, feat, hgb, "C54 | all | HGB")[0])

# ---------- negative controls ----------
rng = np.random.default_rng(0)
cy = Cs.groupby("cycle").y.first()
shuf = pd.Series(rng.permutation(cy.values), index=cy.index)
Cs["y_shuf"] = Cs["cycle"].map(shuf)
results.append(cv(Cs, feat, rf, "CONTROL shuffled labels | all | RF", ycol="y_shuf")[0])
results.append(cv(Cs, feat, dummy, "BASELINE majority class")[0])

# ---------- full cycle sets ----------
results.append(cv(sub(A), frc, rf, "A68 | force | RF")[0])
results.append(cv(sub(B), vib, rf, "B65 | vib+sound | RF")[0])
results.append(cv(sub(D), feat, rf, "D65 | all (sensitivity, incl. random-paired) | RF")[0])

res = pd.DataFrame(results)
res.to_csv("results/manual_results.csv", index=False)
print("\n", res.to_string(index=False))

# ---------- descriptive feature ranking (fit on all 54 cycles; not an accuracy estimate) ----------
m = rf().fit(Cs[feat].to_numpy(float), Cs["y"].to_numpy())
imp = pd.Series(m.feature_importances_, index=feat).sort_values(ascending=False).head(20)
imp.to_csv("results/top20_features.csv")
print("\nTop 20 features:\n", imp.to_string())

# ---------- cycle-level predictions vs wear ----------
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
oof.index.name = "cycle"
oof = oof.reset_index()
oof.columns = ["cycle", "P_fresh", "P_moderate", "P_severe", "true"]
if vb_col:
    oof = oof.merge(lab[["cycle", vb_col]], on="cycle", how="left")
oof.to_csv("results/oof_cycle_probs_all_rf.csv", index=False)
fig, ax = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
if vb_col:
    ax[0].plot(oof["cycle"], oof[vb_col], "k.-")
    ax[0].axhline(0.15, color="g", ls="--"); ax[0].axhline(0.30, color="r", ls="--")
    ax[0].set_ylabel("VBmax (mm)")
for k, c in [("P_fresh", "green"), ("P_moderate", "orange"), ("P_severe", "red")]:
    ax[1].plot(oof["cycle"], oof[k], color=c, marker=".", ls="-", label=k)
ax[1].set_xlabel("cycle"); ax[1].set_ylabel("out-of-fold probability"); ax[1].legend()
plt.tight_layout(); plt.savefig("results/oof_cycles.png", dpi=150)
print("saved results/manual_results.csv, top20_features.csv, oof_cycle_probs_all_rf.csv, oof_cycles.png")
