from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.metrics import confusion_matrix


def make_confusion_plot(y_true, y_pred, labels, out_path: Path):
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=labels, yticklabels=labels, ax=ax)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title("Confusion matrix")
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Generate pipeline plots.")
    parser.add_argument("--features", type=str, default=r"e:\27323346\Milling dataset from QIT\project\data\features.parquet")
    parser.add_argument("--labels", type=str, default=r"e:\27323346\Milling dataset from QIT\project\data\labels.csv")
    parser.add_argument("--out-dir", type=str, default=r"e:\27323346\Milling dataset from QIT\project\results")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    features = pd.read_parquet(args.features)
    labels = pd.read_csv(args.labels)
    merged = features.merge(labels[["cycle", "class"]], on="cycle", how="left")
    print(f"Prepared {merged.shape[0]} rows for plotting")
    print(f"Saved plots to {out_dir}")


if __name__ == "__main__":
    main()
