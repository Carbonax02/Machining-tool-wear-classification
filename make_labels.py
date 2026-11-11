from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def load_wear_sheet(excel_path: Path) -> pd.DataFrame:
    df = pd.read_excel(excel_path, sheet_name=0, header=None)
    if df.shape[0] < 5:
        raise ValueError(f"Unexpected Excel layout in {excel_path}")

    data = df.iloc[4:].copy()
    columns = []
    for edge_idx in range(1, 5):
        columns.extend([f"side_{edge_idx}_vbmax", f"side_{edge_idx}_vbhalf", f"side_{edge_idx}_s"])
    for edge_idx in range(1, 5):
        columns.extend([f"end_{edge_idx}_vbmax", f"end_{edge_idx}_s"])
    data.columns = ["cycle"] + columns
    data["cycle"] = pd.to_numeric(data["cycle"], errors="coerce")
    data = data.dropna(subset=["cycle"]).reset_index(drop=True)
    return data


def smooth_cycle_vbmax(vbmax: pd.Series) -> pd.Series:
    """Simple rolling median smoothing across cycles.

    This is intentionally conservative: it removes isolated spikes while keeping the overall wear trend.
    We apply a centered 3-cycle rolling median and then fill the first and last cycle with the nearest valid value.
    """
    smoothed = vbmax.rolling(window=3, center=True, min_periods=1).median()
    smoothed.iloc[0] = vbmax.iloc[0]
    smoothed.iloc[-1] = vbmax.iloc[-1]
    return smoothed


def assign_class(vbmax_smoothed: pd.Series) -> pd.Series:
    lbl = pd.Series("fresh", index=vbmax_smoothed.index, dtype=object)
    lbl[(vbmax_smoothed >= 0.15) & (vbmax_smoothed <= 0.30)] = "moderate"
    lbl[vbmax_smoothed > 0.30] = "severe"
    return lbl


def build_cycle_labels(excel_path: Path, output_path: Path) -> pd.DataFrame:
    wear = load_wear_sheet(excel_path)
    side_df = wear[[f"side_{edge}_vbmax" for edge in range(1, 5)]]
    cycle_vbmax = side_df.median(axis=1)
    cycle_vbmax.name = "VBmax"
    labels = pd.DataFrame({"cycle": wear["cycle"].astype(int), "VBmax": cycle_vbmax.values})
    labels["VBmax_smoothed"] = smooth_cycle_vbmax(labels["VBmax"]).astype(float)
    labels["class"] = assign_class(labels["VBmax_smoothed"])
    labels = labels[["cycle", "VBmax", "VBmax_smoothed", "class"]]
    labels = labels.sort_values("cycle").reset_index(drop=True)
    labels.to_csv(output_path, index=False)
    return labels


def main():
    parser = argparse.ArgumentParser(description="Build per-cycle tool wear labels from the QIT CEMC label workbook.")
    parser.add_argument("--excel", type=str, default=r"e:\27323346\Milling dataset from QIT\tool wear.xls", help="Path to the Excel workbook.")
    parser.add_argument("--output", type=str, default=r"e:\27323346\Milling dataset from QIT\project\data\labels.csv", help="Destination CSV path.")
    args = parser.parse_args()

    build_cycle_labels(Path(args.excel), Path(args.output))
    print(f"Saved labels to {args.output}")


if __name__ == "__main__":
    main()
