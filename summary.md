# Smoke-test summary for the QIT CEMC tool-wear pipeline

This summary reflects the debug run on the first 20 cycles (fresh to moderate wear) rather than the full 68-cycle dataset. It is intended to verify the pipeline structure, feature extraction, and training logic.

## Step 0 findings

- README: the dataset contains force/torque signals, vibration/sound signals, and image files, with a wear label workbook.
- Force folder: 68 `*.txt` files with `Time`, `Fx`, `Fy`, `Fz`, `Mz`.
- Vibration folder: 67 signal files, Vx/Vy/Vz/Sound, with the second cycle noted as missing from the raw vibration stream.
- Excel labels: one sheet named `tool wear`; 68 cycles with side-edge and end-edge wear metrics.
- No `extract_features.py` or `make_labels.py` existed in the workspace, so they were created under `src/`.
- Assumption used for coding: one force file ~ one cycle, and the vibration stream is missing cycle 2.

## Quick sanity check

- Features parquet: `project/data/features_20.parquet`
- Labels: `project/data/labels.csv`
- 20-cycle feature extraction produced 44,680 rows and 188 columns.
- NaNs remain in vibration-related channels for the missing cycle 2, which is handled by the training `SimpleImputer`.

## Baseline comparison (20-cycle smoke test)

| Model | Feature set | Accuracy | Macro-F1 | Balanced accuracy |
|---|---|---:|---:|---:|
| LogReg | Force | 0.728 | 0.485 | 0.738 |
| LogReg | Vibration | 0.533 | 0.236 | 0.504 |
| LogReg | All | 0.732 | 0.487 | 0.741 |
| LogReg | Sound | 0.530 | 0.231 | 0.500 |
| RandomForest | Force | 0.784 | 0.522 | 0.792 |
| RandomForest | Vibration | 0.533 | 0.235 | 0.503 |
| RandomForest | All | 0.788 | 0.524 | 0.796 |
| RandomForest | Sound | 0.530 | 0.231 | 0.500 |
| GradientBoosting | Force | 0.747 | 0.496 | 0.751 |
| GradientBoosting | Vibration | 0.533 | 0.235 | 0.503 |
| GradientBoosting | All | 0.747 | 0.496 | 0.751 |
| GradientBoosting | Sound | 0.530 | 0.231 | 0.500 |

## Interpretation

- The first 20 cycles include only `fresh` and `moderate` classes, which explains the 0.0 severe precision/recall values in the smoke metrics.
- Force-based features consistently outperform vibration-only features in this small subset, which is consistent with the expected physics of the cutting forces.
- This should be treated as a smoke test only; the full run over all cycles will be needed before drawing final scientific conclusions.
- The final project still needs the full-dataset run and plotting stage to produce confusion matrices, cycle plots, and a final feature-importance report.
