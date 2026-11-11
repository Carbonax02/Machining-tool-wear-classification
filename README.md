# QIT CEMC milling wear classification pipeline

## 1. Dataset overview

The raw dataset is in the project root folder, not inside this `project/` folder:

- `Force and torque data/` — 68 `*.txt` files, one per cycle in this working assumption.
- `Vibration and sound data/` — 67 files (`*.csv` / `*.xlsx`), with cycle 2 assumed missing from the vibration stream.
- `Image/` — images for experiment setup and supporting documentation.
- `tool wear.xls` — wear labels with cycle-wise flank wear for four side edges and four end edges.

This project builds a sensor-only wear classifier using non-overlapping 1-second windows (1-second hop, no overlap). Force and vibration/sound features are retained independently. The 65 vibration-eligible cycles have paired rows for all-channel analyses: matching window indexes are used when duration difference is at most 2%; otherwise, a fixed-seed, within-cycle random permutation is recorded. Extra unpaired modality windows remain available to that modality's own model. The `pairing` field is `index`, `random`, or `none`; it and the cycle/window/source/truncation metadata are never model inputs.
Cycle 2 has no vibration recording. Cycles 45 and 54 have less than 50% vibration coverage and are force-only. Cycle 54 is flagged truncated; cycle 21 is also flagged truncated and its malformed trailing XLSX row is skipped, retaining 4,570,449 complete vibration samples (457 complete 1-second windows). XLSX worksheets are read in numeric worksheet order and complete rows are preserved.

The force `Time` columns start at relative time 0, while vibration/sound `Time` values are absolute 2011 timestamps. No common time origin or offset is verified. For the 13 cycles whose recording durations differ by more than 2%, paired sensitivity rows use the agreed seeded random within-cycle pairing; the primary all-channel evaluation excludes those cycles. Vibration features are never padded to match force windows.

## 2. Setup

```bash
cd "e:\27323346\Milling dataset from QIT\project"
python -m pip install -r requirements.txt
```

## 3. Generate labels

```bash
python src/make_labels.py --excel "e:\27323346\Milling dataset from QIT\tool wear.xls" --output "e:\27323346\Milling dataset from QIT\project\data\labels.csv"
```

## 4. Extract features

```bash
python src/extract_features.py --dataset-root "e:\27323346\Milling dataset from QIT" --output "e:\27323346\Milling dataset from QIT\project\data\features.parquet" --max-cycles 3
```

Use `--max-cycles 3` for a quick smoke test. Remove the flag to run on everything. Completed cycles are checkpointed in `features.parquet.parts` and reused if extraction is interrupted; each cycle is read and processed separately. The parts folder is removed after a successful full run. The extraction log reports force duration, non-overlapping window counts, pairing policy, and cycle processing time.

## 5. Sanity check

```bash
python -c "import pandas as pd; df=pd.read_parquet(r'e:\27323346\Milling dataset from QIT\project\data\features.parquet'); print(df.shape); print(df.isna().sum().sum()); print(df['cycle'].nunique(), 'unique cycles')"
```

Then check the labels:

```bash
python -c "import pandas as pd; df=pd.read_csv(r'e:\27323346\Milling dataset from QIT\project\data\labels.csv'); print(df['class'].value_counts())"
```

## 6. Train and evaluate models

```bash
python src/train_eval.py --features "e:\27323346\Milling dataset from QIT\project\data\features.parquet" --labels "e:\27323346\Milling dataset from QIT\project\data\labels.csv"
```

This script is configured for repeated StratifiedGroupKFold (5 folds x 5 fixed-seed repeats), falling back to leave-one-cycle-out if any class is missing from a train or validation fold. Force-only runs use all cycles; vibration/sound runs use their eligible cycle-specific windows; the primary force/vibration/all-channel comparison uses the same eligible 54-cycle subset; and an all-channel sensitivity run includes the 11 mismatched but eligible cycles using their random within-cycle pairings. Imputation, scaling, and feature selection are fitted only on each training fold. Do not run training until feature extraction and sanity checks are complete.

## 7. Plotting

```bash
python src/plots.py --features "e:\27323346\Milling dataset from QIT\project\data\features.parquet" --labels "e:\27323346\Milling dataset from QIT\project\data\labels.csv" --out-dir "e:\27323346\Milling dataset from QIT\project\results"
```

## Important notes

- This code assumes one force file corresponds to one cycle and that the vibration dataset is missing cycle 2.
- File names are date-based, so the mapping is not explicit in the file names themselves.
- The final results summary must flag cycles 21 and 54 as truncated; cycle 54 is excluded because less than half its vibration recording survived.
- The vibration and force time columns use different origins; no actual time alignment is claimed.
- The project intentionally keeps metadata (`cycle`, `tool`, `window_index`, `source_file`, `pairing`, and `truncated`) out of the model input matrix.
- The label workbook is used only to create `VBmax`-based cycle labels and to evaluate model error near the wear thresholds.
