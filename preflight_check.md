# Preflight checks before full feature extraction

## Findings

- Force `Time` values were scanned in all 68 files. Every file measures approximately 10,000 Hz.
- The previous 20-cycle parquet had 44,680 rows because the old extractor stacked separate feature rows for each of the 4 force channels and 4 vibration/sound channels. It did not create one row per 1-second window. The extractor now joins channel features by `window_index`.
- The force window length is 1.0 s, the hop is 1.0 s, and there is no overlap. The `force_windows` column is `floor(samples / fs)`; the remaining fraction of a second is discarded. `samples / fs` differs from the measured `last Time - first Time` by one sample interval (0.0001 s).
- Three sampled CSV files measured 10 kHz from their timestamp changes. Their timestamps are quantized to milliseconds and repeat for approximately 10 samples per timestamp.
- The three XLSX signal files also measure 10 kHz from their shared timestamp strings. For fs=10 kHz, 5 kHz is Nyquist: the `2000-5000 Hz` band uses a half-open interval and excludes the exactly-5-kHz bin. If a future file has fs below 10 kHz, the top band is clipped to its Nyquist frequency.
- The XLSX exports are malformed: `02-01-01.xlsx` and `02-20-02.xlsx` each have an incomplete trailing worksheet row; the shared-string XML in these files is also malformed. The custom reader retains only complete numeric sensor rows and warns about the trailing partial row.
- Cycle 21 (`02-01-01.xlsx`) retains 4,570,449 complete vibration/sound samples out of 5,226,200 force samples: **87.453%** of the expected duration, or 457 complete 1-second windows. Keep the cycle, but only windows present in all eight channels are retained.
- Cycle 54 (`02-20-02.xlsx`) retains 410,034 complete vibration/sound samples out of 5,291,300 force samples: **7.749%** of the expected duration, or 41 complete 1-second windows. This is below 50%, so exclude cycle 54 from every feature-set comparison and the final model summary.
- Start-time synchronization cannot be confirmed from the available `Time` columns. The force files start at relative time 0; the vibration files start at absolute timestamps `2011-01-01 00:15:19.804` (cycle 21) and `2011-01-01 02:13:51.325` (cycle 54). The two clocks have no shared origin or synchronization marker, so aligning by sample/window index assumes their first samples coincide. Do not start full extraction until this assumption is accepted or synchronization metadata is supplied.
- Date/sequence keys in both signal folders are increasing and match force/vibration files exactly except cycle 2. The README says cycle 2 vibration data was lost. The README and wear workbook do not provide calendar dates to independently verify the filename dates; the workbook provides cycle numbers 1-68 only.
- Current mapping has exactly one missing vibration file: cycle 2. It will not be imputed. Cycles 2 and 54 are excluded from force-only, vibration/sound-only, all-channel, and sound-only comparisons. This leaves 66 cycles; every comparison will use the same complete eight-channel windows.
- Wear labels across all 68 cycles: fresh 11, moderate 43, severe 14. After excluding cycles 2 and 54: fresh 10, moderate 43, severe 13.
- Evaluation now uses 3-fold `StratifiedGroupKFold` on cycle-level labels. Each fold includes all three classes. Imputation, feature selection, and scaling are fitted only on its training cycles.
- On the 66 eligible cycles, fold counts (fresh/moderate/severe) are: Fold 1 train 7/28/9, validation 3/15/4; Fold 2 train 6/29/9, validation 4/14/4; Fold 3 train 7/29/8, validation 3/14/5.
- The extractor now drops any 1-second channel window with non-finite samples. Training further requires finite features from all eight channels, ensuring identical windows across the feature-set comparisons.
- Resume logic was tested on a small synthetic dataset: completed cycle checkpoints are validated and reused on rerun; the final Parquet is assembled atomically only after selected cycles are complete. No full extraction has started.
- `project/data/` currently contains `labels.csv` only; no feature parquet cache exists.

## Cycle-by-cycle mapping and force window counts

`duration_s` is the elapsed span measured from the first and last force `Time` values. `force_windows` is the count of complete, non-overlapping 1-second windows from the force sample count and measured rate.

| Cycle | Force file | Samples | fs (Hz) | duration_s | force_windows | Vibration file | VBmax_smoothed (mm) | Class |
|---:|---|---:|---:|---:|---:|---|---:|---|
| 1 | 01-26-1.txt | 5,248,130 | 10,000 | 524.8129 | 524 | 01-26-01.csv | 0.04360 | fresh |
| 2 | 01-26-2.txt | 11,013,800 | 10,000 | 1,101.3799 | 1,101 | MISSING | 0.09020 | fresh |
| 3 | 01-26-3.txt | 5,410,500 | 10,000 | 541.0499 | 541 | 01-26-03.csv | 0.09910 | fresh |
| 4 | 01-26-4.txt | 5,289,800 | 10,000 | 528.9799 | 528 | 01-26-04.csv | 0.10895 | fresh |
| 5 | 01-27-1.txt | 5,315,400 | 10,000 | 531.5399 | 531 | 01-27-01.csv | 0.11340 | fresh |
| 6 | 01-27-2.txt | 5,508,000 | 10,000 | 550.7999 | 550 | 01-27-02.csv | 0.11675 | fresh |
| 7 | 01-27-3.txt | 5,294,500 | 10,000 | 529.4499 | 529 | 01-27-03.csv | 0.12455 | fresh |
| 8 | 01-28-1.txt | 5,242,000 | 10,000 | 524.1999 | 524 | 01-28-01.csv | 0.13130 | fresh |
| 9 | 01-28-2.txt | 5,254,500 | 10,000 | 525.4499 | 525 | 01-28-02.csv | 0.13235 | fresh |
| 10 | 01-28-3.txt | 5,216,000 | 10,000 | 521.5999 | 521 | 01-28-03.csv | 0.14035 | fresh |
| 11 | 01-29-1.txt | 5,266,500 | 10,000 | 526.6499 | 526 | 01-29-01.csv | 0.17000 | moderate |
| 12 | 01-29-2.txt | 5,238,300 | 10,000 | 523.8299 | 523 | 01-29-02.csv | 0.19110 | moderate |
| 13 | 01-29-3.txt | 5,204,600 | 10,000 | 520.4599 | 520 | 01-29-03.csv | 0.19700 | moderate |
| 14 | 01-30-1.txt | 5,182,400 | 10,000 | 518.2399 | 518 | 01-30-01.csv | 0.19950 | moderate |
| 15 | 01-30-2.txt | 5,219,000 | 10,000 | 521.8999 | 521 | 01-30-02.csv | 0.22440 | moderate |
| 16 | 01-30-3.txt | 5,184,700 | 10,000 | 518.4699 | 518 | 01-30-03.csv | 0.23000 | moderate |
| 17 | 01-30-4.txt | 5,191,400 | 10,000 | 519.1399 | 519 | 01-30-04.csv | 0.23130 | moderate |
| 18 | 01-31-1.txt | 5,215,063 | 10,000 | 521.5062 | 521 | 01-31-01.csv | 0.23575 | moderate |
| 19 | 01-31-2.txt | 5,192,300 | 10,000 | 519.2299 | 519 | 01-31-02.csv | 0.24040 | moderate |
| 20 | 01-31-3.txt | 5,166,900 | 10,000 | 516.6899 | 516 | 01-31-03.csv | 0.24040 | moderate |
| 21 | 02-01-01.txt | 5,226,200 | 10,000 | 522.6199 | 522 | 02-01-01.xlsx (truncated; 87.453% retained; 457 common windows) | 0.21675 | moderate |
| 22 | 02-01-02.txt | 6,182,000 | 10,000 | 618.1999 | 618 | 02-01-02.xlsx | 0.21675 | moderate |
| 23 | 02-01-03.txt | 5,220,800 | 10,000 | 522.0799 | 522 | 02-01-03.csv | 0.22280 | moderate |
| 24 | 02-01-04.txt | 5,255,400 | 10,000 | 525.5399 | 525 | 02-01-04.csv | 0.22280 | moderate |
| 25 | 02-01-05.txt | 5,280,500 | 10,000 | 528.0499 | 528 | 02-01-05.csv | 0.20250 | moderate |
| 26 | 02-01-06.txt | 5,315,700 | 10,000 | 531.5699 | 531 | 02-01-06.csv | 0.20250 | moderate |
| 27 | 02-02-01.txt | 5,635,200 | 10,000 | 563.5199 | 563 | 02-02-01.csv | 0.22195 | moderate |
| 28 | 02-02-02.txt | 5,325,600 | 10,000 | 532.5599 | 532 | 02-02-02.csv | 0.22600 | moderate |
| 29 | 02-02-03.txt | 5,283,100 | 10,000 | 528.3099 | 528 | 02-02-03.csv | 0.24330 | moderate |
| 30 | 02-02-04.txt | 5,303,500 | 10,000 | 530.3499 | 530 | 02-02-04.csv | 0.24475 | moderate |
| 31 | 02-04-01.txt | 5,244,100 | 10,000 | 524.4099 | 524 | 02-04-01.csv | 0.24475 | moderate |
| 32 | 02-04-02.txt | 5,234,100 | 10,000 | 523.4099 | 523 | 02-04-02.csv | 0.24475 | moderate |
| 33 | 02-04-03.txt | 5,308,900 | 10,000 | 530.8899 | 530 | 02-04-03.csv | 0.22385 | moderate |
| 34 | 02-05-01.txt | 5,311,300 | 10,000 | 531.1299 | 531 | 02-05-01.csv | 0.22385 | moderate |
| 35 | 02-05-02.txt | 5,247,900 | 10,000 | 524.7899 | 524 | 02-05-02.csv | 0.18145 | moderate |
| 36 | 02-05-03.txt | 5,194,600 | 10,000 | 519.4599 | 519 | 02-05-03.csv | 0.17865 | moderate |
| 37 | 02-05-04.txt | 5,203,500 | 10,000 | 520.3499 | 520 | 02-05-04.csv | 0.15860 | moderate |
| 38 | 02-05-05.txt | 5,193,900 | 10,000 | 519.3899 | 519 | 02-05-05.csv | 0.14865 | fresh |
| 39 | 02-16-01.txt | 4,436,077 | 10,000 | 443.6076 | 443 | 02-16-01.csv | 0.15860 | moderate |
| 40 | 02-16-02.txt | 5,280,400 | 10,000 | 528.0399 | 528 | 02-16-02.csv | 0.16065 | moderate |
| 41 | 02-16-03.txt | 5,213,549 | 10,000 | 521.3548 | 521 | 02-16-03.csv | 0.21835 | moderate |
| 42 | 02-16-04.txt | 5,191,300 | 10,000 | 519.1299 | 519 | 02-16-04.csv | 0.27790 | moderate |
| 43 | 02-17-01.txt | 5,235,571 | 10,000 | 523.5570 | 523 | 02-17-01.csv | 0.23305 | moderate |
| 44 | 02-17-02.txt | 5,107,200 | 10,000 | 510.7199 | 510 | 02-17-02.csv | 0.27160 | moderate |
| 45 | 02-17-03.txt | 5,246,100 | 10,000 | 524.6099 | 524 | 02-17-03.csv | 0.27160 | moderate |
| 46 | 02-18-01.txt | 5,242,300 | 10,000 | 524.2299 | 524 | 02-18-01.csv | 0.27160 | moderate |
| 47 | 02-18-02.txt | 5,216,700 | 10,000 | 521.6699 | 521 | 02-18-02.csv | 0.23875 | moderate |
| 48 | 02-18-03.txt | 5,213,500 | 10,000 | 521.3499 | 521 | 02-18-03.csv | 0.22385 | moderate |
| 49 | 02-18-04.txt | 5,231,000 | 10,000 | 523.0999 | 523 | 02-18-04.csv | 0.22385 | moderate |
| 50 | 02-19-01.txt | 5,207,308 | 10,000 | 520.7307 | 520 | 02-19-01.csv | 0.22400 | moderate |
| 51 | 02-19-02.txt | 5,137,125 | 10,000 | 513.7124 | 513 | 02-19-02.csv | 0.22400 | moderate |
| 52 | 02-19-03.txt | 5,199,400 | 10,000 | 519.9399 | 519 | 02-19-03.csv | 0.22400 | moderate |
| 53 | 02-20-01.txt | 5,313,300 | 10,000 | 531.3299 | 531 | 02-20-01.csv | 0.32005 | severe |
| 54 | 02-20-02.txt | 5,291,300 | 10,000 | 529.1299 | 529 | 02-20-02.xlsx (truncated; 7.749% retained; EXCLUDED) | 0.32005 | severe |
| 55 | 02-20-03.txt | 5,295,300 | 10,000 | 529.5299 | 529 | 02-20-03.csv | 0.29270 | moderate |
| 56 | 02-20-04.txt | 5,344,800 | 10,000 | 534.4799 | 534 | 02-20-04.csv | 0.29270 | moderate |
| 57 | 02-20-05.txt | 6,177,200 | 10,000 | 617.7199 | 617 | 02-20-05.csv | 0.30150 | severe |
| 58 | 02-21-01.txt | 5,314,100 | 10,000 | 531.4099 | 531 | 02-21-01.csv | 0.30150 | severe |
| 59 | 02-21-02.txt | 5,420,600 | 10,000 | 542.0599 | 542 | 02-21-02.csv | 0.30735 | severe |
| 60 | 02-21-03.txt | 6,163,900 | 10,000 | 616.3899 | 616 | 02-21-03.csv | 0.31435 | severe |
| 61 | 02-22-01.txt | 5,878,619 | 10,000 | 587.8618 | 587 | 02-22-01.csv | 0.39700 | severe |
| 62 | 02-22-02.txt | 5,622,100 | 10,000 | 562.2099 | 562 | 02-22-02.csv | 0.39795 | severe |
| 63 | 02-27-01.txt | 5,233,550 | 10,000 | 523.3549 | 523 | 02-27-01.csv | 0.40890 | severe |
| 64 | 02-27-02.txt | 5,223,800 | 10,000 | 522.3799 | 522 | 02-27-02.csv | 0.40000 | severe |
| 65 | 03-02-01.txt | 5,391,600 | 10,000 | 539.1599 | 539 | 03-02-01.csv | 0.40000 | severe |
| 66 | 03-02-02.txt | 5,312,400 | 10,000 | 531.2399 | 531 | 03-02-02.csv | 0.33460 | severe |
| 67 | 03-04-01.txt | 5,121,576 | 10,000 | 512.1575 | 512 | 03-04-01.csv | 0.33460 | severe |
| 68 | 03-04-02.txt | 5,196,400 | 10,000 | 519.6399 | 519 | 03-04-02.csv | 0.34920 | severe |

## CV cycle counts after excluding cycle 2

| Fold | Training: fresh / moderate / severe | Validation: fresh / moderate / severe |
|---:|---:|---:|
| 1 | 6 / 29 / 9 | 4 / 14 / 5 |
| 2 | 7 / 29 / 9 | 3 / 14 / 5 |
| 3 | 7 / 28 / 10 | 3 / 15 / 4 |
