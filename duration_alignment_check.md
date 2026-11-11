# Force and vibration/sound duration and alignment check

No feature extraction was run for this check.

## Summary

- Force `Time` was measured at approximately 10,000 Hz for every cycle. Force duration is calculated from sample count / measured rate; the first force timestamp is relative `0.0000 s`.
- Vibration/sound CSV timestamp samples and XLSX shared timestamp strings measure approximately 10,000 Hz. CSV sample counts were counted from file records; XLSX counts include complete sensor rows only, excluding truncated rows.
- Duration difference is `vibration duration - force duration`; percent difference is relative to force duration.
- If absolute duration difference is below 2%, the requested rule allows pairing windows by index provisionally. **54 of 67 available vibration cycles** meet this duration check.
- **13 cycles exceed 2%** and do not have a shared time origin: force time is relative seconds starting at zero, while vibration/sound time is an absolute 2011 timestamp. The timestamps cannot be compared to calculate an offset. These cycles must not be paired by index without further direction.
- The first 20 cycles include cycle 2 with missing vibration. Of the 19 signal-present cycles, **17 pass** the <2% duration check and cycles 6 and 11 fail.
- The full extraction remains unstarted. There is no `features.parquet` output.

## Per-cycle duration table

Force start time is `0.0000 s` for every file. Vibration start times are shown as recorded; they are absolute datetimes and therefore do not define a known offset relative to the force clock.

| Cycle | Force file | Vibration file | Force duration (s) | Vibration duration (s) | Difference (s) | Difference (%) | Vibration first timestamp | Decision |
|---:|---|---|---:|---:|---:|---:|---|---|
| 1 | 01-26-1.txt | 01-26-01.csv | 524.8129 | 527.5000 | +2.6871 | +0.512% | 2011-01-01 01:06:34.780 | <2% |
| 2 | 01-26-2.txt | MISSING | 1101.3799 | — | — | — | — | Missing |
| 3 | 01-26-3.txt | 01-26-03.csv | 541.0499 | 539.1000 | -1.9499 | -0.360% | 2011-01-01 05:10:47.508 | <2% |
| 4 | 01-26-4.txt | 01-26-04.csv | 528.9799 | 527.5000 | -1.4799 | -0.280% | 2011-01-01 06:23:34.972 | <2% |
| 5 | 01-27-1.txt | 01-27-01.csv | 531.5399 | 531.6000 | +0.0601 | +0.011% | 2011-01-01 01:06:24.183 | <2% |
| 6 | 01-27-2.txt | 01-27-02.csv | 550.7999 | 536.5000 | -14.2999 | -2.596% | 2011-01-01 02:32:09.658 | HOLD: no shared clock |
| 7 | 01-27-3.txt | 01-27-03.csv | 529.4499 | 523.0000 | -6.4499 | -1.218% | 2011-01-01 04:19:28.514 | <2% |
| 8 | 01-28-1.txt | 01-28-01.csv | 524.1999 | 528.3000 | +4.1001 | +0.782% | 2011-01-01 05:33:35.152 | <2% |
| 9 | 01-28-2.txt | 01-28-02.csv | 525.4499 | 520.4000 | -5.0499 | -0.961% | 2011-01-01 06:45:03.461 | <2% |
| 10 | 01-28-3.txt | 01-28-03.csv | 521.5999 | 526.0000 | +4.4001 | +0.844% | 2011-01-01 00:12:48.854 | <2% |
| 11 | 01-29-1.txt | 01-29-01.csv | 526.6499 | 540.0000 | +13.3501 | +2.535% | 2011-01-01 00:24:47.713 | HOLD: no shared clock |
| 12 | 01-29-2.txt | 01-29-02.csv | 523.8299 | 521.0000 | -2.8299 | -0.540% | 2011-01-01 04:04:11.535 | <2% |
| 13 | 01-29-3.txt | 01-29-03.csv | 520.4599 | 520.1000 | -0.3599 | -0.069% | 2011-01-01 07:16:36.803 | <2% |
| 14 | 01-30-1.txt | 01-30-01.csv | 518.2399 | 518.6000 | +0.3601 | +0.069% | 2011-01-01 00:15:00.927 | <2% |
| 15 | 01-30-2.txt | 01-30-02.csv | 521.8999 | 518.4000 | -3.4999 | -0.671% | 2011-01-01 02:10:15.682 | <2% |
| 16 | 01-30-3.txt | 01-30-03.csv | 518.4699 | 518.4000 | -0.0699 | -0.013% | 2011-01-01 04:47:01.975 | <2% |
| 17 | 01-30-4.txt | 01-30-04.csv | 519.1399 | 518.1000 | -1.0399 | -0.200% | 2011-01-01 06:01:00.320 | <2% |
| 18 | 01-31-1.txt | 01-31-01.csv | 521.5062 | 518.8000 | -2.7062 | -0.519% | 2011-01-01 07:16:49.969 | <2% |
| 19 | 01-31-2.txt | 01-31-02.csv | 519.2299 | 518.5000 | -0.7299 | -0.141% | 2011-01-01 08:22:13.897 | <2% |
| 20 | 01-31-3.txt | 01-31-03.csv | 516.6899 | 517.1000 | +0.4101 | +0.079% | 2011-01-01 00:04:46.717 | <2% |
| 21 | 02-01-01.txt | 02-01-01.xlsx | 522.6199 | 457.0449 | -65.5750 | -12.547% | 2011-01-01 00:15:19.804 | HOLD: no shared clock |
| 22 | 02-01-02.txt | 02-01-02.xlsx | 618.1999 | 656.8000 | +38.6001 | +6.244% | 2011-01-01 01:44:37.093 | HOLD: no shared clock |
| 23 | 02-01-03.txt | 02-01-03.csv | 522.0799 | 526.1000 | +4.0201 | +0.770% | 2011-01-01 05:22:39.737 | <2% |
| 24 | 02-01-04.txt | 02-01-04.csv | 525.5399 | 524.1000 | -1.4399 | -0.274% | 2011-01-01 06:35:10.582 | <2% |
| 25 | 02-01-05.txt | 02-01-05.csv | 528.0499 | 531.6000 | +3.5501 | +0.672% | 2011-01-01 07:27:02.419 | <2% |
| 26 | 02-01-06.txt | 02-01-06.csv | 531.5699 | 528.2000 | -3.3699 | -0.634% | 2011-01-01 08:27:07.772 | <2% |
| 27 | 02-02-01.txt | 02-02-01.csv | 563.5199 | 568.3000 | +4.7801 | +0.848% | 2011-01-01 00:59:32.332 | <2% |
| 28 | 02-02-02.txt | 02-02-02.csv | 532.5599 | 532.3000 | -0.2599 | -0.049% | 2011-01-01 02:28:42.791 | <2% |
| 29 | 02-02-03.txt | 02-02-03.csv | 528.3099 | 521.7000 | -6.6099 | -1.251% | 2011-01-01 03:42:46.659 | <2% |
| 30 | 02-02-04.txt | 02-02-04.csv | 530.3499 | 529.5000 | -0.8499 | -0.160% | 2011-01-01 04:43:09.971 | <2% |
| 31 | 02-04-01.txt | 02-04-01.csv | 524.4099 | 520.0000 | -4.4099 | -0.841% | 2011-01-01 01:03:56.138 | <2% |
| 32 | 02-04-02.txt | 02-04-02.csv | 523.4099 | 521.4000 | -2.0099 | -0.384% | 2011-01-01 05:02:22.931 | <2% |
| 33 | 02-04-03.txt | 02-04-03.csv | 530.8899 | 519.9000 | -10.9899 | -2.070% | 2011-01-01 07:01:45.902 | HOLD: no shared clock |
| 34 | 02-05-01.txt | 02-05-01.csv | 531.1299 | 531.6000 | +0.4701 | +0.089% | 2011-01-01 00:12:38.191 | <2% |
| 35 | 02-05-02.txt | 02-05-02.csv | 524.7899 | 522.9000 | -1.8899 | -0.360% | 2011-01-01 01:48:37.343 | <2% |
| 36 | 02-05-03.txt | 02-05-03.csv | 519.4599 | 521.2000 | +1.7401 | +0.335% | 2011-01-01 03:25:35.858 | <2% |
| 37 | 02-05-04.txt | 02-05-04.csv | 520.3499 | 520.6000 | +0.2501 | +0.048% | 2011-01-01 04:20:37.248 | <2% |
| 38 | 02-05-05.txt | 02-05-05.csv | 519.3899 | 520.5000 | +1.1101 | +0.214% | 2011-01-01 05:32:33.616 | <2% |
| 39 | 02-16-01.txt | 02-16-01.csv | 443.6076 | 530.1928 | +86.5852 | +19.518% | 2011-01-01 00:50:53.397 | HOLD: no shared clock |
| 40 | 02-16-02.txt | 02-16-02.csv | 528.0399 | 521.1000 | -6.9399 | -1.314% | 2011-01-01 02:17:25.605 | <2% |
| 41 | 02-16-03.txt | 02-16-03.csv | 521.3548 | 524.7000 | +3.3452 | +0.642% | 2011-01-01 03:22:30.240 | <2% |
| 42 | 02-16-04.txt | 02-16-04.csv | 519.1299 | 523.6000 | +4.4701 | +0.861% | 2011-01-01 04:11:57.680 | <2% |
| 43 | 02-17-01.txt | 02-17-01.csv | 523.5570 | 530.3000 | +6.7430 | +1.288% | 2011-01-01 00:58:14.522 | <2% |
| 44 | 02-17-02.txt | 02-17-02.csv | 510.7199 | 519.2000 | +8.4801 | +1.660% | 2011-01-01 05:09:55.129 | <2% |
| 45 | 02-17-03.txt | 02-17-03.csv | 524.6099 | 178.4381 | -346.1718 | -65.987% | 2011-01-01 06:20:28.968 | HOLD: no shared clock |
| 46 | 02-18-01.txt | 02-18-01.csv | 524.2299 | 525.9000 | +1.6701 | +0.319% | 2011-01-01 00:28:21.723 | <2% |
| 47 | 02-18-02.txt | 02-18-02.csv | 521.6699 | 523.4000 | +1.7301 | +0.332% | 2011-01-01 01:25:50.863 | <2% |
| 48 | 02-18-03.txt | 02-18-03.csv | 521.3499 | 521.1000 | -0.2499 | -0.048% | 2011-01-01 02:09:38.521 | <2% |
| 49 | 02-18-04.txt | 02-18-04.csv | 523.0999 | 523.1000 | +0.0001 | +0.000% | 2011-01-01 02:57:32.750 | <2% |
| 50 | 02-19-01.txt | 02-19-01.csv | 520.7307 | 522.7000 | +1.9693 | +0.378% | 2011-01-01 00:06:07.933 | <2% |
| 51 | 02-19-02.txt | 02-19-02.csv | 513.7124 | 526.6000 | +12.8876 | +2.509% | 2011-01-01 00:52:03.573 | HOLD: no shared clock |
| 52 | 02-19-03.txt | 02-19-03.csv | 519.9399 | 519.8000 | -0.1399 | -0.027% | 2011-01-01 01:30:20.821 | <2% |
| 53 | 02-20-01.txt | 02-20-01.csv | 531.3299 | 526.5000 | -4.8299 | -0.909% | 2011-01-01 01:10:24.817 | <2% |
| 54 | 02-20-02.txt | 02-20-02.xlsx | 529.1299 | 41.0034 | -488.1265 | -92.251% | 2011-01-01 02:13:51.325 | HOLD: no shared clock |
| 55 | 02-20-03.txt | 02-20-03.csv | 529.5299 | 520.3000 | -9.2299 | -1.743% | 2011-01-01 05:26:16.690 | <2% |
| 56 | 02-20-04.txt | 02-20-04.csv | 534.4799 | 538.0000 | +3.5201 | +0.659% | 2011-01-01 06:07:49.953 | <2% |
| 57 | 02-20-05.txt | 02-20-05.csv | 617.7199 | 620.8999 | +3.1800 | +0.515% | 2011-01-01 06:47:43.195 | <2% |
| 58 | 02-21-01.txt | 02-21-01.csv | 531.4099 | 531.8999 | +0.4900 | +0.092% | 2011-01-01 07:23:31.843 | <2% |
| 59 | 02-21-02.txt | 02-21-02.csv | 542.0599 | 544.9000 | +2.8401 | +0.524% | 2011-01-01 00:10:16.040 | <2% |
| 60 | 02-21-03.txt | 02-21-03.csv | 616.3899 | 523.6000 | -92.7899 | -15.054% | 2011-01-01 01:04:03.287 | HOLD: no shared clock |
| 61 | 02-22-01.txt | 02-22-01.csv | 587.8618 | 523.7000 | -64.1618 | -10.914% | 2011-01-01 01:37:15.914 | HOLD: no shared clock |
| 62 | 02-22-02.txt | 02-22-02.csv | 562.2099 | 523.8000 | -38.4099 | -6.832% | 2011-01-01 02:13:55.638 | HOLD: no shared clock |
| 63 | 02-27-01.txt | 02-27-01.csv | 523.3549 | 525.6000 | +2.2451 | +0.429% | 2011-01-01 00:10:12.143 | <2% |
| 64 | 02-27-02.txt | 02-27-02.csv | 522.3799 | 522.7000 | +0.3201 | +0.061% | 2011-01-01 01:20:59.203 | <2% |
| 65 | 03-02-01.txt | 03-02-01.csv | 539.1599 | 527.3000 | -11.8599 | -2.200% | 2011-01-01 01:20:08.268 | HOLD: no shared clock |
| 66 | 03-02-02.txt | 03-02-02.csv | 531.2399 | 524.8000 | -6.4399 | -1.212% | 2011-01-01 02:33:04.922 | <2% |
| 67 | 03-04-01.txt | 03-04-01.csv | 512.1575 | 510.4000 | -1.7575 | -0.343% | 2011-01-01 00:36:23.069 | <2% |
| 68 | 03-04-02.txt | 03-04-02.csv | 519.6399 | 518.5000 | -1.1399 | -0.219% | 2011-01-01 01:51:57.468 | <2% |

## Vibration eligibility and comparison cycle sets

Per the follow-up policy, cycle 54 is excluded from every vibration/sound-based run, but remains eligible for force-only runs. The same under-50%-of-force-duration rule excludes cycle 45 as well:

| Cycle | Force duration (s) | Vibration duration (s) | Vibration / force | Complete 1 s vibration windows* | Smoothed class | Vibration-run decision |
|---:|---:|---:|---:|---:|---|---|
| 45 | 524.6099 | 178.4381 | 34.013% | 178 | moderate | Exclude: under 50% |
| 54 | 529.1299 | 41.0034 | 7.749% | 41 | severe | Exclude: under 50%; retain for force-only |

The window counts above are expected complete, non-overlapping 1 s windows (`floor(duration)`), not extracted feature rows. No extraction has been run.

| Run / comparison subset | Cycles | Fresh | Moderate | Severe | Notes |
|---|---:|---:|---:|---:|---|
| Force-only, all cycles | 68 | 11 | 41 | 16 | Includes cycles 2, 45, and 54 |
| Vibration/sound-only eligible cycles | 65 | 10 | 40 | 15 | Excludes missing cycle 2 and under-50% cycles 45 and 54 |
| All-channel primary | 54 | 9 | 34 | 11 | Excludes 13 duration mismatches, missing cycle 2, and under-50% cycles (45 and 54 already among the 13) |
| All-channel sensitivity | 65 | 10 | 40 | 15 | Includes 11 of the 13 mismatched cycles; excludes 45 and 54 and missing cycle 2 |
| Force-only on vibration/sensitivity subset | 65 | 10 | 40 | 15 | Same cycles as vibration-only and all-channel sensitivity |
| Force-only on all-channel primary subset | 54 | 9 | 34 | 11 | Same cycles as all-channel primary |

For the sensitivity run, the 11 retained >2%-mismatch cycles will use seeded random within-cycle window pairing; cycles below the 2% threshold can use index pairing. No common time origin was verified for any cycle. The fair primary comparison should use the 54-cycle primary subset for force-only, vibration-only, and all-channel; the additional 65-cycle modality comparison can compare force-only and vibration-only on the full vibration-eligible set.
