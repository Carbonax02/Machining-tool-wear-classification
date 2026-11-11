from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Sequence

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

try:
    import xgboost as xgb
except Exception:  # pragma: no cover
    xgb = None


SEED = 42
MODEL_ORDER = ["logreg", "rf", "gb"]
FORCE_ONLY_CYCLES = {2, 45, 54}
MISMATCHED_CYCLES = {6, 11, 21, 22, 33, 39, 45, 51, 54, 60, 61, 62, 65}


def class_order(labels: Sequence[str]) -> List[str]:
    return ["fresh", "moderate", "severe"]


def build_model(name: str):
    if name == "logreg":
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=3000, class_weight="balanced", random_state=SEED)),
        ])
    if name == "rf":
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestClassifier(
                n_estimators=300,
                class_weight="balanced",
                random_state=SEED,
                n_jobs=-1,
                min_samples_leaf=1,
            )),
        ])
    if name == "gb":
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", GradientBoostingClassifier(random_state=SEED)),
        ])
    if name == "xgb":
        if xgb is None:
            raise RuntimeError("xgboost is not installed")
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", xgb.XGBClassifier(
                objective="multi:softprob",
                n_estimators=200,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=SEED,
                eval_metric="mlogloss",
            )),
        ])
    raise ValueError(f"Unknown model name: {name}")


def feature_set_for_columns(columns: Sequence[str], feature_group: str):
    if feature_group == "force":
        return [c for c in columns if c.split("_")[0] in {"Fx", "Fy", "Fz", "Mz"}]
    if feature_group == "vibration":
        return [c for c in columns if c.split("_")[0] in {"Vx", "Vy", "Vz", "Sound"}]
    if feature_group == "sound":
        return [c for c in columns if c.split("_")[0] == "Sound"]
    if feature_group == "all":
        return list(columns)
    raise ValueError(f"Unsupported feature_group: {feature_group}")


def aggregate_cycle_predictions(y_true: np.ndarray, y_prob: np.ndarray, cycles: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    unique_cycles = np.unique(cycles)
    pred_cycle = []
    true_cycle = []
    for cycle in unique_cycles:
        cycle_mask = cycles == cycle
        avg_prob = y_prob[cycle_mask].mean(axis=0)
        cycle_pred = np.argmax(avg_prob)
        pred_cycle.append(cycle_pred)
        true_cycle.append(y_true[cycle_mask][0])
    return np.asarray(true_cycle), np.asarray(pred_cycle)


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, labels: Sequence[str]):
    accuracy = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)
    balanced = balanced_accuracy_score(y_true, y_pred)
    precision, recall, _, _ = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    return {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "balanced_accuracy": balanced,
        "precision": {label: float(p) for label, p in zip(labels, precision)},
        "recall": {label: float(r) for label, r in zip(labels, recall)},
        "confusion_matrix": cm,
    }


def cycle_splits(y: pd.Series, cycles: pd.Series):
    cycle_table = pd.DataFrame({"cycle": cycles.to_numpy(), "class": y.to_numpy()}).drop_duplicates("cycle")
    if cycle_table["cycle"].nunique() < 3:
        raise ValueError("Need at least three cycle groups for 3-fold cross-validation.")

    cycle_ids = cycle_table["cycle"].to_numpy()
    cycle_classes = cycle_table["class"].to_numpy()
    all_classes = set(np.unique(cycle_classes))
    splits = []
    for repeat in range(5):
        splitter = StratifiedGroupKFold(
            n_splits=5,
            shuffle=True,
            random_state=SEED + repeat,
        )
        repeat_splits = [
            (cycle_ids[train_idx], cycle_ids[val_idx])
            for train_idx, val_idx in splitter.split(
                cycle_table[["cycle"]],
                cycle_classes,
                groups=cycle_ids,
            )
        ]
        if any(
            set(cycle_table.loc[cycle_table["cycle"].isin(val_cycles), "class"]) != all_classes
            or set(cycle_table.loc[cycle_table["cycle"].isin(train_cycles), "class"]) != all_classes
            for train_cycles, val_cycles in repeat_splits
        ):
            splits = []
            break
        splits.extend(repeat_splits)
    if splits:
        return splits

    print(
        "Repeated 5-fold StratifiedGroupKFold could not put all classes in every "
        "train/validation fold; falling back to leave-one-cycle-out."
    )
    return [
        (cycle_ids[cycle_ids != held_out], np.asarray([held_out]))
        for held_out in cycle_ids
    ]


def evaluate_model(model_name: str, X: pd.DataFrame, y: pd.Series, cycles: pd.Series, feature_group: str):
    labels = class_order(y.unique())
    fold_metrics = []

    cols = feature_set_for_columns(X.columns, feature_group)
    X_sel = X[cols].copy()

    for train_cycles, val_cycles in cycle_splits(y, cycles):
        train_idx = np.flatnonzero(cycles.isin(train_cycles).to_numpy())
        val_idx = np.flatnonzero(cycles.isin(val_cycles).to_numpy())
        X_train, X_val = X_sel.iloc[train_idx], X_sel.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        # Fit preprocessing inside the training fold only.
        imputer = SimpleImputer(strategy="median")
        X_train_imp = imputer.fit_transform(X_train)
        X_val_imp = imputer.transform(X_val)

        k = min(20, X_train_imp.shape[1])
        selector = SelectKBest(score_func=f_classif, k=k)
        X_train_sel = selector.fit_transform(X_train_imp, y_train)
        X_val_sel = selector.transform(X_val_imp)

        model = build_model(model_name)
        if model_name == "logreg":
            scaler = StandardScaler()
            X_train_model = scaler.fit_transform(X_train_sel)
            X_val_model = scaler.transform(X_val_sel)
            model = LogisticRegression(max_iter=3000, class_weight="balanced", random_state=SEED)
            model.fit(X_train_model, y_train)
            y_pred = model.predict(X_val_model)
        else:
            model.fit(X_train_sel, y_train)
            y_pred = model.predict(X_val_sel)

        metrics = compute_metrics(y_val.to_numpy(), y_pred, labels)
        fold_metrics.append(metrics)

    mean_metrics = {}
    for metric_name in ["accuracy", "macro_f1", "balanced_accuracy"]:
        values = [m[metric_name] for m in fold_metrics]
        mean_metrics[metric_name] = float(np.mean(values))
        mean_metrics[f"{metric_name}_std"] = float(np.std(values, ddof=0))

    mean_metrics["precision"] = {label: float(np.mean([m["precision"][label] for m in fold_metrics])) for label in labels}
    mean_metrics["recall"] = {label: float(np.mean([m["recall"][label] for m in fold_metrics])) for label in labels}
    mean_metrics["precision_std"] = {
        label: float(np.std([m["precision"][label] for m in fold_metrics], ddof=0))
        for label in labels
    }
    mean_metrics["recall_std"] = {
        label: float(np.std([m["recall"][label] for m in fold_metrics], ddof=0))
        for label in labels
    }

    final = {
        "model": model_name,
        "feature_group": feature_group,
        "metrics": mean_metrics,
    }
    return final


def run_training(feature_path: Path, label_path: Path):
    features = pd.read_parquet(feature_path)
    labels = pd.read_csv(label_path)
    merged = features.merge(labels[["cycle", "class"]], on="cycle", how="left")
    merged = merged.dropna(subset=["class"]).copy()
    meta_cols = [
        "cycle", "tool", "window_index", "window_index_force",
        "window_index_vibration", "source_file", "vibration_source_file",
        "pairing", "truncated", "n_invalid_dropped", "corrupt_vib", "class",
    ]
    feature_cols = [c for c in merged.columns if c not in meta_cols]
    groups = {
        "force": feature_set_for_columns(feature_cols, "force"),
        "vibration": feature_set_for_columns(feature_cols, "vibration"),
        "sound": feature_set_for_columns(feature_cols, "sound"),
        "all": feature_set_for_columns(feature_cols, "all"),
    }

    def finite_group_rows(columns: List[str]) -> pd.Series:
        return pd.Series(
            np.isfinite(merged[columns].to_numpy(dtype=float)).all(axis=1),
            index=merged.index,
        )

    force_finite = finite_group_rows(groups["force"])
    vibration_finite = finite_group_rows(groups["vibration"])
    all_finite = finite_group_rows(groups["all"])
    paired = merged["pairing"].isin(["index", "random"])
    eligible_cycles = set(merged.loc[vibration_finite, "cycle"].unique())
    primary_cycles = eligible_cycles - MISMATCHED_CYCLES

    run_specs = [
        ("force_all_cycles", force_finite, ["force"]),
        ("vibration_all_eligible", vibration_finite, ["vibration", "sound"]),
        (
            "headline_primary_same_54_cycles",
            merged["cycle"].isin(primary_cycles),
            ["force", "vibration", "all"],
        ),
        (
            "all_channel_sensitivity_65_cycles",
            vibration_finite & paired,
            ["all"],
        ),
    ]
    report = []
    for cohort, row_mask, feature_groups in run_specs:
        cohort_frame = merged.loc[row_mask].copy()
        if cohort == "headline_primary_same_54_cycles":
            cohort_frame = cohort_frame[cohort_frame["cycle"].isin(primary_cycles)]
        if cohort.startswith("all_channel"):
            cohort_frame = cohort_frame[cohort_frame["pairing"].isin(["index", "random"])]
        for feature_group in feature_groups:
            feature_mask = finite_group_rows(groups[feature_group]).loc[cohort_frame.index]
            model_frame = cohort_frame.loc[feature_mask]
            cycle_table = model_frame[["cycle", "class"]].drop_duplicates("cycle")
            print(
                f"{cohort}/{feature_group}: {cycle_table['cycle'].nunique()} cycles, "
                f"{len(model_frame)} windows, classes="
                f"{cycle_table['class'].value_counts().to_dict()}"
            )
            X = model_frame[feature_cols]
            y = model_frame["class"]
            cycles = model_frame["cycle"]
            for model_name in MODEL_ORDER:
                result = evaluate_model(model_name, X, y, cycles, feature_group)
                result["cohort"] = cohort
                report.append(result)

    return report


def main():
    parser = argparse.ArgumentParser(description="Train baseline models on QIT CEMC window features.")
    parser.add_argument("--features", type=str, default=r"e:\27323346\Milling dataset from QIT\project\data\features.parquet", help="Path to extracted feature parquet.")
    parser.add_argument("--labels", type=str, default=r"e:\27323346\Milling dataset from QIT\project\data\labels.csv", help="Path to cycle labels CSV.")
    args = parser.parse_args()

    report = run_training(Path(args.features), Path(args.labels))
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
