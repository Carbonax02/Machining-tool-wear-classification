# Vibration/sound file integrity audit

Before extraction resumed, every vibration/sound file was validated. CSV physical rows were checked for the expected field count, a well-formed timestamp consistent with the file header date, and finite numeric sensor values. The last four CSVs (cycles 65?68) have eight sensor fields; all are validated while Vx/Vy/Vz/Sound are selected by header. XLSX files were checked in worksheet order; cycle 21 and 22 full reads were completed during the earlier extraction attempt, and cycle 54 was read for this audit.

No eligible vibration file exceeds the 1% invalid-record threshold. Cycle 39 contains 11,292 invalid physical records out of 5,301,928 (0.21298%); its measured rate is 9,996.09 Hz. Invalid rows are retained as holes at their original sample indexes; no repair, interpolation, or splicing is performed. Fifteen of its 530 complete 1-second windows contain invalid records and are discarded; 515 (97.17%) remain, so cycle 39 remains eligible for vibration-only and all-channel sensitivity. It remains excluded from the primary all-channel run as a duration mismatch.

Cycles 21, 45, and 54 each have one malformed final/partial record. Each is outside a complete 1-second window, so none of their complete windows is discarded for this reason. Cycles 45 and 54 are already force-only under the under-50% vibration rule. Cycle 21 remains flagged truncated. The cycle-45 partial vibration file is likewise excluded from vibration runs by the coverage rule.

| Cycle | Vibration file | Physical records | Invalid records | Invalid (%) | Complete 1 s windows | Discarded | Kept |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | 01-26-01.csv | 5275000 | 0 | 0.00000% | 527 | 0 | 527 |
| 2 | MISSING | 0 | 0 | 0.00000% | 0 | 0 | 0 |
| 3 | 01-26-03.csv | 5391000 | 0 | 0.00000% | 539 | 0 | 539 |
| 4 | 01-26-04.csv | 5275000 | 0 | 0.00000% | 527 | 0 | 527 |
| 5 | 01-27-01.csv | 5316000 | 0 | 0.00000% | 531 | 0 | 531 |
| 6 | 01-27-02.csv | 5365000 | 0 | 0.00000% | 536 | 0 | 536 |
| 7 | 01-27-03.csv | 5230000 | 0 | 0.00000% | 523 | 0 | 523 |
| 8 | 01-28-01.csv | 5283000 | 0 | 0.00000% | 528 | 0 | 528 |
| 9 | 01-28-02.csv | 5204000 | 0 | 0.00000% | 520 | 0 | 520 |
| 10 | 01-28-03.csv | 5260000 | 0 | 0.00000% | 526 | 0 | 526 |
| 11 | 01-29-01.csv | 5400000 | 0 | 0.00000% | 540 | 0 | 540 |
| 12 | 01-29-02.csv | 5210000 | 0 | 0.00000% | 521 | 0 | 521 |
| 13 | 01-29-03.csv | 5201000 | 0 | 0.00000% | 520 | 0 | 520 |
| 14 | 01-30-01.csv | 5186000 | 0 | 0.00000% | 518 | 0 | 518 |
| 15 | 01-30-02.csv | 5184000 | 0 | 0.00000% | 518 | 0 | 518 |
| 16 | 01-30-03.csv | 5184000 | 0 | 0.00000% | 518 | 0 | 518 |
| 17 | 01-30-04.csv | 5181000 | 0 | 0.00000% | 518 | 0 | 518 |
| 18 | 01-31-01.csv | 5188000 | 0 | 0.00000% | 518 | 0 | 518 |
| 19 | 01-31-02.csv | 5185000 | 0 | 0.00000% | 518 | 0 | 518 |
| 20 | 01-31-03.csv | 5171000 | 0 | 0.00000% | 517 | 0 | 517 |
| 21 | 02-01-01.xlsx | 4570450 | 1 | 0.00002% | 457 | 0 | 457 |
| 22 | 02-01-02.xlsx | 6568000 | 0 | 0.00000% | 656 | 0 | 656 |
| 23 | 02-01-03.csv | 5261000 | 0 | 0.00000% | 526 | 0 | 526 |
| 24 | 02-01-04.csv | 5241000 | 0 | 0.00000% | 524 | 0 | 524 |
| 25 | 02-01-05.csv | 5316000 | 0 | 0.00000% | 531 | 0 | 531 |
| 26 | 02-01-06.csv | 5282000 | 0 | 0.00000% | 528 | 0 | 528 |
| 27 | 02-02-01.csv | 5683000 | 0 | 0.00000% | 568 | 0 | 568 |
| 28 | 02-02-02.csv | 5323000 | 0 | 0.00000% | 532 | 0 | 532 |
| 29 | 02-02-03.csv | 5217000 | 0 | 0.00000% | 521 | 0 | 521 |
| 30 | 02-02-04.csv | 5295000 | 0 | 0.00000% | 529 | 0 | 529 |
| 31 | 02-04-01.csv | 5200000 | 0 | 0.00000% | 520 | 0 | 520 |
| 32 | 02-04-02.csv | 5214000 | 0 | 0.00000% | 521 | 0 | 521 |
| 33 | 02-04-03.csv | 5199000 | 0 | 0.00000% | 519 | 0 | 519 |
| 34 | 02-05-01.csv | 5316000 | 0 | 0.00000% | 531 | 0 | 531 |
| 35 | 02-05-02.csv | 5229000 | 0 | 0.00000% | 522 | 0 | 522 |
| 36 | 02-05-03.csv | 5212000 | 0 | 0.00000% | 521 | 0 | 521 |
| 37 | 02-05-04.csv | 5206000 | 0 | 0.00000% | 520 | 0 | 520 |
| 38 | 02-05-05.csv | 5205000 | 0 | 0.00000% | 520 | 0 | 520 |
| 39 | 02-16-01.csv | 5301928 | 11292 | 0.21298% | 530 | 15 | 515 |
| 40 | 02-16-02.csv | 5211000 | 0 | 0.00000% | 521 | 0 | 521 |
| 41 | 02-16-03.csv | 5247000 | 0 | 0.00000% | 524 | 0 | 524 |
| 42 | 02-16-04.csv | 5236000 | 0 | 0.00000% | 523 | 0 | 523 |
| 43 | 02-17-01.csv | 5303000 | 0 | 0.00000% | 530 | 0 | 530 |
| 44 | 02-17-02.csv | 5192000 | 0 | 0.00000% | 519 | 0 | 519 |
| 45 | 02-17-03.csv | 1784381 | 1 | 0.00006% | 178 | 0 | 178 |
| 46 | 02-18-01.csv | 5259000 | 0 | 0.00000% | 525 | 0 | 525 |
| 47 | 02-18-02.csv | 5234000 | 0 | 0.00000% | 523 | 0 | 523 |
| 48 | 02-18-03.csv | 5211000 | 0 | 0.00000% | 521 | 0 | 521 |
| 49 | 02-18-04.csv | 5231000 | 0 | 0.00000% | 523 | 0 | 523 |
| 50 | 02-19-01.csv | 5227000 | 0 | 0.00000% | 522 | 0 | 522 |
| 51 | 02-19-02.csv | 5266000 | 0 | 0.00000% | 526 | 0 | 526 |
| 52 | 02-19-03.csv | 5198000 | 0 | 0.00000% | 519 | 0 | 519 |
| 53 | 02-20-01.csv | 5265000 | 0 | 0.00000% | 526 | 0 | 526 |
| 54 | 02-20-02.xlsx | 410035 | 1 | 0.00024% | 41 | 0 | 41 |
| 55 | 02-20-03.csv | 5203000 | 0 | 0.00000% | 520 | 0 | 520 |
| 56 | 02-20-04.csv | 5380000 | 0 | 0.00000% | 538 | 0 | 538 |
| 57 | 02-20-05.csv | 6209000 | 0 | 0.00000% | 620 | 0 | 620 |
| 58 | 02-21-01.csv | 5319000 | 0 | 0.00000% | 531 | 0 | 531 |
| 59 | 02-21-02.csv | 5449000 | 0 | 0.00000% | 544 | 0 | 544 |
| 60 | 02-21-03.csv | 5236000 | 0 | 0.00000% | 523 | 0 | 523 |
| 61 | 02-22-01.csv | 5237000 | 0 | 0.00000% | 523 | 0 | 523 |
| 62 | 02-22-02.csv | 5238000 | 0 | 0.00000% | 523 | 0 | 523 |
| 63 | 02-27-01.csv | 5256000 | 0 | 0.00000% | 525 | 0 | 525 |
| 64 | 02-27-02.csv | 5227000 | 0 | 0.00000% | 522 | 0 | 522 |
| 65 | 03-02-01.csv | 5273000 | 0 | 0.00000% | 527 | 0 | 527 |
| 66 | 03-02-02.csv | 5248000 | 0 | 0.00000% | 524 | 0 | 524 |
| 67 | 03-04-01.csv | 5104000 | 0 | 0.00000% | 510 | 0 | 510 |
| 68 | 03-04-02.csv | 5185000 | 0 | 0.00000% | 518 | 0 | 518 |
