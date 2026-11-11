from __future__ import annotations

import argparse
import array
import datetime as dt
import html
import json
import os
import re
import time
import warnings
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from tqdm import tqdm


CHANNELS = ["Fx", "Fy", "Fz", "Mz", "Vx", "Vy", "Vz", "Sound"]
FORCE_CHANNELS = ["Fx", "Fy", "Fz", "Mz"]
VIBRATION_CHANNELS = ["Vx", "Vy", "Vz", "Sound"]
CACHE_VERSION = 4
RANDOM_PAIRING_SEED = 42
MISMATCH_TOLERANCE = 0.02
VIBRATION_MINIMUM_COVERAGE = 0.50
TRUNCATED_CYCLES = {21, 54}
FORCE_ONLY_CYCLES = {2, 45, 54}

BAND_EDGES = [
    (0, 50),
    (50, 250),
    (250, 500),
    (500, 1000),
    (1000, 2000),
    (2000, 5000),
]


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def read_force_file(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t")
    expected = ["Time", "Fx", "Fy", "Fz", "Mz"]
    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in {path.name}: {missing}")
    return df[["Time", "Fx", "Fy", "Fz", "Mz"]].copy()


def _estimate_xlsx_fs(zf: zipfile.ZipFile) -> float:
    shared = zf.open("xl/sharedStrings.xml")
    pending = b""
    values = []
    item_pattern = re.compile(rb"<si>(.*?)</si>", re.DOTALL)
    text_pattern = re.compile(rb"<t(?:\s[^>]*)?>(.*?)</t>", re.DOTALL)
    while len(values) < 5000:
        chunk = shared.read(1024 * 1024)
        if not chunk:
            break
        pending += chunk
        matches = list(item_pattern.finditer(pending))
        if matches:
            for match in matches:
                text_match = text_pattern.search(match.group(1))
                values.append(
                    html.unescape(text_match.group(1).decode("utf-8", errors="replace"))
                    if text_match
                    else ""
                )
                if len(values) >= 5000:
                    break
            pending = pending[matches[-1].end():]
    time_values = pd.to_datetime(pd.Series(values[5:]), errors="coerce").dropna()
    if len(time_values) < 2:
        raise ValueError("Could not measure the XLSX sampling rate from its timestamp strings.")
    time_ns = time_values.astype("datetime64[ns]").astype("int64").to_numpy()
    changes = np.flatnonzero(np.diff(time_ns) > 0) + 1
    if changes.size == 0:
        raise ValueError("XLSX timestamps do not advance in the sampled rows.")
    first_change = int(changes[0])
    delta_ns = int(time_ns[first_change] - time_ns[0])
    if delta_ns <= 0:
        raise ValueError("XLSX timestamp interval is not positive.")
    return float(first_change * 1_000_000_000 / delta_ns)


def _read_xlsx_signal(path: Path) -> pd.DataFrame:
    """Read the dataset's split-sheet XLSX signals without loading its malformed shared-string XML."""
    with zipfile.ZipFile(path) as zf:
        fs = _estimate_xlsx_fs(zf)
        def worksheet_number(name: str) -> int:
            match = re.fullmatch(r"xl/worksheets/sheet(\d*)\.xml", name)
            if not match:
                raise ValueError(f"Unexpected worksheet path in {path.name}: {name}")
            return int(match.group(1) or "1")

        worksheets = sorted(
            (
                name for name in zf.namelist()
                if re.fullmatch(r"xl/worksheets/sheet\d*\.xml", name)
            ),
            key=worksheet_number,
        )
        columns = [array.array("d") for _ in range(4)]
        sample_indices = array.array("q")
        invalid_sample_indices = []
        total_samples = 0
        cell_pattern = re.compile(rb'<c r="([A-E])(\d+)"([^>]*)>(.*?)</c>', re.DOTALL)
        for sheet_name in worksheets:
            with zf.open(sheet_name) as source:
                pending = b""
                trailing_partial_row = False
                malformed_rows = 0
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    pending += chunk
                    while True:
                        start = pending.find(b"<row ")
                        if start < 0:
                            pending = pending[-16:]
                            break
                        end = pending.find(b"</row>", start)
                        if end < 0:
                            pending = pending[start:]
                            break
                        row_bytes = pending[start:end + len(b"</row>")]
                        pending = pending[end + len(b"</row>"):]
                        cells = {}
                        string_cells = set()
                        time_cell_valid = False
                        invalid_row = False
                        for match in cell_pattern.finditer(row_bytes):
                            col = match.group(1).decode("ascii")
                            content = match.group(4)
                            value_match = re.search(rb"<v>(.*?)</v>", content, re.DOTALL)
                            if value_match is None:
                                invalid_row = True
                                continue
                            if col == "A":
                                time_cell_valid = (
                                    b't="s"' in match.group(3)
                                    and value_match.group(1).isdigit()
                                )
                                if not time_cell_valid:
                                    invalid_row = True
                                continue
                            if b't="s"' in match.group(3):
                                string_cells.add(col)
                                continue
                            try:
                                cells[col] = float(value_match.group(1))
                            except ValueError:
                                invalid_row = True
                        is_header = (
                            len(string_cells) == 4
                            and time_cell_valid
                            and not cells
                        )
                        if (
                            len(cells) == 4
                            and time_cell_valid
                            and not invalid_row
                            and all(np.isfinite(v) for v in cells.values())
                        ):
                            for idx, col in enumerate(("B", "C", "D", "E")):
                                columns[idx].append(cells[col])
                            sample_indices.append(total_samples)
                            total_samples += 1
                        elif not is_header:
                            malformed_rows += 1
                            invalid_sample_indices.append(total_samples)
                            total_samples += 1
                if b"<row " in pending:
                    trailing_partial_row = True
                    invalid_sample_indices.append(total_samples)
                    total_samples += 1
                if trailing_partial_row or malformed_rows:
                    warnings.warn(
                        f"{path.name} contains a partial or malformed row in {sheet_name}; "
                        f"only complete sensor rows are retained ({malformed_rows} malformed closed rows"
                        f"{' and a trailing partial row' if trailing_partial_row else ''}).",
                        RuntimeWarning,
                    )

    sample_count = len(columns[0])
    if sample_count == 0 or any(len(values) != sample_count for values in columns):
        raise ValueError(f"Could not read consistent sensor columns from {path.name}.")
    frame = pd.DataFrame({
        "Time": np.frombuffer(sample_indices, dtype=np.int64).astype(np.float64) / fs,
        "sample_index": np.frombuffer(sample_indices, dtype=np.int64),
        "Vx": np.frombuffer(columns[0], dtype=np.float64),
        "Vy": np.frombuffer(columns[1], dtype=np.float64),
        "Vz": np.frombuffer(columns[2], dtype=np.float64),
        "Sound": np.frombuffer(columns[3], dtype=np.float64),
    })
    frame.attrs["sampling_rate"] = fs
    frame.attrs["total_samples"] = total_samples
    frame.attrs["invalid_sample_indices"] = np.asarray(invalid_sample_indices, dtype=np.int64)
    frame.attrs["n_invalid_dropped"] = len(invalid_sample_indices)
    return frame


def _parse_csv_timestamp_ms(value: bytes) -> int:
    if not re.fullmatch(rb"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}", value):
        raise ValueError("Invalid timestamp format")
    if len(value) != 23 or value[4:5] != b"-" or value[7:8] != b"-" or value[10:11] != b" ":
        raise ValueError("Invalid timestamp format")
    if value[13:14] != b":" or value[16:17] != b":" or value[19:20] != b".":
        raise ValueError("Invalid timestamp format")
    year, month, day = int(value[0:4]), int(value[5:7]), int(value[8:10])
    hour, minute, second, millisecond = (
        int(value[11:13]),
        int(value[14:16]),
        int(value[17:19]),
        int(value[20:23]),
    )
    if hour > 23 or minute > 59 or second > 59:
        raise ValueError("Invalid timestamp value")
    day_number = dt.date(year, month, day).toordinal()
    return (
        day_number * 86_400_000
        + hour * 3_600_000
        + minute * 60_000
        + second * 1_000
        + millisecond
    )


def _read_csv_signal(path: Path) -> pd.DataFrame:
    time_values = array.array("q")
    sample_indices = array.array("q")
    channels = [array.array("d") for _ in range(4)]
    positive_time_deltas = array.array("q")
    timestamp_run_lengths = array.array("q")
    invalid_sample_indices = []
    total_samples = 0
    last_time_ms = None
    current_run_length = 0

    with path.open("rb") as source:
        header = source.readline().decode("cp1252", errors="replace").strip().split(",")
        if len(header) < 5:
            raise ValueError(f"Expected at least five CSV columns in {path.name}, got {len(header)}.")
        lower_header = [column.lower() for column in header]
        channel_fragments = {
            "Vx": "ai1-01",
            "Vy": "ai1-02",
            "Vz": "ai1-03",
            "Sound": "ai1-07",
        }
        channel_columns = {
            channel: next(
                (index for index, name in enumerate(lower_header) if fragment in name),
                None,
            )
            for channel, fragment in channel_fragments.items()
        }
        if any(index is None for index in channel_columns.values()):
            raise ValueError(f"Unexpected vibration/sound header in {path.name}: {header}")
        header_time = re.search(
            r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\]",
            header[0],
        )
        expected_start_ms = (
            _parse_csv_timestamp_ms(header_time.group(1).encode("ascii"))
            if header_time
            else None
        )
        expected_date = header_time.group(1)[:10].encode("ascii") if header_time else None

        for sample_index, line in enumerate(source):
            total_samples += 1
            fields = line.rstrip(b"\r\n").split(b",")
            try:
                if not fields or expected_date is not None and fields[0][:10] != expected_date:
                    raise ValueError("Timestamp date differs from file header")
                timestamp_ms = _parse_csv_timestamp_ms(fields[0])
                if (
                    expected_start_ms is not None
                    and abs(timestamp_ms - expected_start_ms - sample_index / 10.0) > 5000.0
                ):
                    raise ValueError("Timestamp is inconsistent with its original sample index")
            except (ValueError, OverflowError):
                invalid_sample_indices.append(sample_index)
                continue

            if last_time_ms is not None and timestamp_ms < last_time_ms:
                invalid_sample_indices.append(sample_index)
                continue
            if last_time_ms is None:
                current_run_length = 1
            elif timestamp_ms == last_time_ms:
                current_run_length += 1
            else:
                timestamp_run_lengths.append(current_run_length)
                positive_time_deltas.append(timestamp_ms - last_time_ms)
                current_run_length = 1
            last_time_ms = timestamp_ms

            if len(fields) != len(header):
                invalid_sample_indices.append(sample_index)
                continue
            try:
                all_sensor_values = [float(value) for value in fields[1:]]
            except (ValueError, OverflowError):
                invalid_sample_indices.append(sample_index)
                continue
            if not np.isfinite(all_sensor_values).all():
                invalid_sample_indices.append(sample_index)
                continue
            values = [
                all_sensor_values[channel_columns[channel] - 1]
                for channel in VIBRATION_CHANNELS
            ]

            time_values.append(timestamp_ms)
            sample_indices.append(sample_index)
            for idx, value in enumerate(values):
                channels[idx].append(value)

    if current_run_length:
        timestamp_run_lengths.append(current_run_length)
    if not sample_indices or last_time_ms is None:
        raise ValueError(f"No valid vibration/sound records in {path.name}.")
    if not positive_time_deltas or not timestamp_run_lengths:
        raise ValueError(f"No positive timestamp intervals in {path.name}.")
    median_delta_ms = float(np.median(np.frombuffer(positive_time_deltas, dtype=np.int64)))
    median_samples_per_timestamp = float(
        np.median(np.frombuffer(timestamp_run_lengths, dtype=np.int64))
    )
    sampling_rate = (
        median_samples_per_timestamp * 1000.0 / median_delta_ms
        if median_delta_ms > 0
        else 0.0
    )
    if not np.isfinite(sampling_rate) or sampling_rate <= 0:
        raise ValueError(f"Could not measure a valid sampling rate from {path.name}.")

    time_array = np.frombuffer(time_values, dtype=np.int64)
    frame = pd.DataFrame({
        "Time": (time_array - time_array[0]).astype(np.float64) / 1000.0,
        "sample_index": np.frombuffer(sample_indices, dtype=np.int64),
        "Vx": np.frombuffer(channels[0], dtype=np.float64),
        "Vy": np.frombuffer(channels[1], dtype=np.float64),
        "Vz": np.frombuffer(channels[2], dtype=np.float64),
        "Sound": np.frombuffer(channels[3], dtype=np.float64),
    })
    frame.attrs["sampling_rate"] = sampling_rate
    frame.attrs["total_samples"] = total_samples
    frame.attrs["invalid_sample_indices"] = np.asarray(invalid_sample_indices, dtype=np.int64)
    frame.attrs["n_invalid_dropped"] = len(invalid_sample_indices)
    return frame


def read_vibration_file(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return _read_xlsx_signal(path)
    if path.suffix.lower() != ".csv":
        raise ValueError(f"Unsupported vibration file type: {path}")
    return _read_csv_signal(path)


def estimate_fs(time_values: np.ndarray) -> float:
    if time_values.size < 2:
        raise ValueError("Cannot estimate sampling rate from fewer than two timestamps.")
    values = np.asarray(time_values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size < 2:
        raise ValueError("Cannot estimate sampling rate from fewer than two valid timestamps.")
    delta_time = np.diff(values)
    positive = delta_time[delta_time > 0]
    span = float(values[-1] - values[0])
    if positive.size == 0 or span <= 0:
        raise ValueError("Time column does not contain a positive elapsed interval.")
    if np.any(delta_time == 0):
        # Coarse timestamp columns repeat the same millisecond for multiple signal samples.
        return float(values.size / (span + np.median(positive)))
    return float((values.size - 1) / span)


def compute_basic_stats(x: np.ndarray) -> Dict[str, float]:
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return {name: 0.0 for name in ["mean", "std", "rms", "peak", "peak_to_peak", "skewness", "kurtosis", "crest_factor"]}

    mean = float(np.mean(x))
    std = float(np.std(x, ddof=1)) if x.size > 1 else 0.0
    rms = float(np.sqrt(np.mean(x ** 2)))
    peak = float(np.max(np.abs(x)))
    pk2pk = float(np.max(x) - np.min(x))

    if std > 0:
        centered = x - mean
        skewness = float(np.mean(centered ** 3) / (std ** 3))
        kurtosis = float(np.mean(centered ** 4) / (std ** 4) - 3.0)
    else:
        skewness = 0.0
        kurtosis = 0.0

    crest_factor = float(peak / rms) if rms > 0 else 0.0
    return {
        "mean": mean,
        "std": std,
        "rms": rms,
        "peak": peak,
        "peak_to_peak": pk2pk,
        "skewness": skewness,
        "kurtosis": kurtosis,
        "crest_factor": crest_factor,
    }


def compute_spectral_features(x: np.ndarray, fs: float) -> Dict[str, float]:
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return {"spectral_centroid": 0.0, "bandwidth": 0.0, "spectral_entropy": 0.0}

    spec = np.abs(np.fft.rfft(x - np.mean(x)))
    freqs = np.fft.rfftfreq(x.size, d=1.0 / fs)
    if spec.size == 0:
        return {"spectral_centroid": 0.0, "bandwidth": 0.0, "spectral_entropy": 0.0}

    positive = spec > 0
    if not np.any(positive):
        return {"spectral_centroid": 0.0, "bandwidth": 0.0, "spectral_entropy": 0.0}

    mag = spec[positive]
    f = freqs[positive]
    power = mag ** 2
    denom = np.sum(power)
    if denom <= 0:
        return {"spectral_centroid": 0.0, "bandwidth": 0.0, "spectral_entropy": 0.0}

    centroid = float(np.sum(f * power) / denom)
    bandwidth = float(np.sqrt(np.sum(((f - centroid) ** 2) * power) / denom))
    p = power / denom
    p = p[p > 0]
    entropy = float(-np.sum(p * np.log(p + 1e-12)) / np.log(p.size + 1e-12)) if p.size > 1 else 0.0
    return {"spectral_centroid": centroid, "bandwidth": bandwidth, "spectral_entropy": entropy}


def log_band_energy(magnitude: np.ndarray, freqs: np.ndarray, low: float, high: float) -> float:
    mask = (freqs >= low) & (freqs < high)
    if not np.any(mask):
        return 0.0
    energy = float(np.sum(magnitude[mask] ** 2))
    return float(np.log10(energy + 1e-12))


def compute_harmonic_and_band_features(x: np.ndarray, fs: float) -> Dict[str, float]:
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        out = {}
        for k in range(1, 7):
            out[f"harmonic_{k}"] = 0.0
        for low, high in BAND_EDGES:
            out[f"band_{low}_{high}"] = 0.0
        return out

    centered = x - np.mean(x)
    spec = np.abs(np.fft.rfft(centered))
    freqs = np.fft.rfftfreq(x.size, d=1.0 / fs)
    out = {}
    for k in range(1, 7):
        center = 95.0 * k
        low = max(center - 10.0, 0.0)
        high = center + 10.0
        out[f"harmonic_{k}"] = log_band_energy(spec, freqs, low, high)
    nyquist = fs / 2.0
    for low, high in BAND_EDGES:
        effective_high = min(high, nyquist)
        out[f"band_{int(low)}_{int(high)}"] = log_band_energy(spec, freqs, low, effective_high)
    return out


def window_features_for_signal(
    signal: np.ndarray,
    fs: float,
    channel: str,
    sample_indices: np.ndarray | None = None,
    total_samples: int | None = None,
    invalid_indices: np.ndarray | None = None,
) -> List[Dict[str, float]]:
    signal = np.asarray(signal, dtype=float)
    window_samples = int(round(fs))
    if window_samples <= 0:
        raise ValueError(f"Invalid window size from sampling rate {fs}.")
    if sample_indices is None:
        sample_indices = np.arange(signal.size, dtype=np.int64)
    else:
        sample_indices = np.asarray(sample_indices, dtype=np.int64)
    if total_samples is None:
        total_samples = int(sample_indices[-1] + 1) if sample_indices.size else 0
    invalid_indices = (
        np.asarray(invalid_indices, dtype=np.int64)
        if invalid_indices is not None
        else np.empty(0, dtype=np.int64)
    )
    expected_windows = total_samples // window_samples
    if expected_windows == 0:
        return []

    rows: List[Dict[str, float]] = []
    for window_index in range(expected_windows):
        start = window_index * window_samples
        end = start + window_samples
        bad_start = np.searchsorted(invalid_indices, start, side="left")
        if bad_start < invalid_indices.size and invalid_indices[bad_start] < end:
            continue
        first = np.searchsorted(sample_indices, start, side="left")
        last = np.searchsorted(sample_indices, end, side="left")
        if last - first != window_samples:
            continue
        window = signal[first:last]
        if not np.isfinite(window).all():
            continue
        stat = compute_basic_stats(window)
        spectral = compute_spectral_features(window, fs)
        harmonic_band = compute_harmonic_and_band_features(window, fs)
        row = {"window_index": window_index}
        for key, value in stat.items():
            row[f"{channel}_{key}"] = value
        for key, value in spectral.items():
            row[f"{channel}_{key}"] = value
        for key, value in harmonic_band.items():
            row[f"{channel}_{key}"] = value
        rows.append(row)
    return rows


def _channel_window_map(
    signals: Dict[str, np.ndarray],
    fs: float,
    sample_indices: np.ndarray,
    total_samples: int,
    invalid_indices: np.ndarray,
) -> Dict[int, Dict[str, float]]:
    result: Dict[int, Dict[str, float]] = {}
    for channel, signal in signals.items():
        for row in window_features_for_signal(
            signal,
            fs,
            channel,
            sample_indices=sample_indices,
            total_samples=total_samples,
            invalid_indices=invalid_indices,
        ):
            window_index = int(row.pop("window_index"))
            result.setdefault(window_index, {}).update(row)
    return result


def build_cycle_features(
    force_df: pd.DataFrame,
    vib_df: pd.DataFrame | None,
    cycle: int,
    source_file: str,
    vibration_source_file: str | None,
) -> tuple[pd.DataFrame, dict]:
    fs_force = estimate_fs(force_df["Time"].to_numpy())
    force_duration = len(force_df) / fs_force
    force_sample_indices = np.arange(len(force_df), dtype=np.int64)
    force_windows = _channel_window_map(
        {channel: force_df[channel].to_numpy(dtype=float) for channel in FORCE_CHANNELS},
        fs_force,
        force_sample_indices,
        len(force_df),
        np.empty(0, dtype=np.int64),
    )
    vib_windows: Dict[int, Dict[str, float]] = {}
    vib_duration = 0.0
    vibration_total_windows = 0
    vibration_windows_discarded = 0
    n_invalid_dropped = 0
    if vib_df is not None:
        fs_vib = (
            float(vib_df.attrs["sampling_rate"])
            if "sampling_rate" in vib_df.attrs
            else estimate_fs(vib_df["Time"].to_numpy())
        )
        vib_total_samples = int(vib_df.attrs.get("total_samples", len(vib_df)))
        vib_sample_indices = vib_df["sample_index"].to_numpy(dtype=np.int64)
        invalid_indices = np.asarray(
            vib_df.attrs.get("invalid_sample_indices", np.empty(0, dtype=np.int64)),
            dtype=np.int64,
        )
        n_invalid_dropped = int(vib_df.attrs.get("n_invalid_dropped", len(invalid_indices)))
        vib_duration = vib_total_samples / fs_vib
        coverage = vib_duration / force_duration if force_duration else 0.0
        if coverage < VIBRATION_MINIMUM_COVERAGE:
            raise ValueError(
                f"Cycle {cycle} vibration coverage is {coverage:.3%}; "
                "under-50% recordings must be force-only."
            )
        window_samples = int(round(fs_vib))
        vibration_total_windows = vib_total_samples // window_samples
        complete_sample_count = vibration_total_windows * window_samples
        invalid_complete_windows = invalid_indices[invalid_indices < complete_sample_count]
        vibration_windows_discarded = len(
            np.unique(invalid_complete_windows // window_samples)
        )
        vib_windows = _channel_window_map(
            {channel: vib_df[channel].to_numpy(dtype=float) for channel in VIBRATION_CHANNELS},
            fs_vib,
            vib_sample_indices,
            vib_total_samples,
            invalid_indices,
        )

    force_ids = sorted(force_windows)
    vib_ids = sorted(vib_windows)
    difference = abs(vib_duration - force_duration) / force_duration if vib_df is not None else 0.0
    pairing = "none"
    pairs: list[tuple[int, int]] = []
    if vib_df is not None:
        if difference <= MISMATCH_TOLERANCE:
            pairing = "index"
            common = sorted(set(force_ids).intersection(vib_ids))
            pairs = [(idx, idx) for idx in common]
        else:
            pairing = "random"
            pair_count = min(len(force_ids), len(vib_ids))
            shuffled_vib_ids = np.random.default_rng(
                RANDOM_PAIRING_SEED + cycle
            ).permutation(vib_ids)
            pairs = list(zip(force_ids[:pair_count], map(int, shuffled_vib_ids[:pair_count])))

    paired_force = {force_idx for force_idx, _ in pairs}
    paired_vib = {vib_idx for _, vib_idx in pairs}
    records = []
    for force_idx, vib_idx in pairs:
        records.append({
            "cycle": cycle,
            "tool": "unknown",
            "window_index": force_idx,
            "window_index_force": force_idx,
            "window_index_vibration": vib_idx,
            "source_file": source_file,
            "vibration_source_file": vibration_source_file,
            "pairing": pairing,
            "truncated": cycle in TRUNCATED_CYCLES,
            "n_invalid_dropped": n_invalid_dropped,
            "corrupt_vib": n_invalid_dropped > 0,
            **force_windows[force_idx],
            **vib_windows[vib_idx],
        })
    for force_idx in force_ids:
        if force_idx not in paired_force:
            records.append({
                "cycle": cycle,
                "tool": "unknown",
                "window_index": force_idx,
                "window_index_force": force_idx,
                "window_index_vibration": np.nan,
                "source_file": source_file,
                "vibration_source_file": vibration_source_file,
                "pairing": "none",
                "truncated": cycle in TRUNCATED_CYCLES,
                "n_invalid_dropped": n_invalid_dropped,
                "corrupt_vib": n_invalid_dropped > 0,
                **force_windows[force_idx],
            })
    for vib_idx in vib_ids:
        if vib_idx not in paired_vib:
            records.append({
                "cycle": cycle,
                "tool": "unknown",
                "window_index": vib_idx,
                "window_index_force": np.nan,
                "window_index_vibration": vib_idx,
                "source_file": source_file,
                "vibration_source_file": vibration_source_file,
                "pairing": "none",
                "truncated": cycle in TRUNCATED_CYCLES,
                "n_invalid_dropped": n_invalid_dropped,
                "corrupt_vib": n_invalid_dropped > 0,
                **vib_windows[vib_idx],
            })

    frame = pd.DataFrame.from_records(records)
    feature_columns = [
        f"{channel}_{name}"
        for channel in CHANNELS
        for name in (
            list(compute_basic_stats(np.array([0.0])).keys())
            + list(compute_spectral_features(np.array([0.0]), 10000.0).keys())
            + list(compute_harmonic_and_band_features(np.array([0.0]), 10000.0).keys())
        )
    ]
    frame = frame.reindex(columns=[
        "cycle", "tool", "window_index", "window_index_force",
        "window_index_vibration", "source_file", "vibration_source_file",
        "pairing", "truncated", "n_invalid_dropped", "corrupt_vib",
        *feature_columns,
    ])
    frame[feature_columns] = frame[feature_columns].replace([np.inf, -np.inf], np.nan)
    stats = {
        "force_duration_s": force_duration,
        "force_windows": len(force_ids),
        "vibration_duration_s": vib_duration if vib_df is not None else None,
        "vibration_windows": len(vib_ids),
        "vibration_total_windows": vibration_total_windows,
        "vibration_windows_discarded": vibration_windows_discarded,
        "n_invalid_dropped": n_invalid_dropped,
        "corrupt_vib": n_invalid_dropped > 0,
        "paired_windows": len(pairs),
        "pairing": pairing,
    }
    return frame, stats


def determine_cycle_map(force_dir: Path, vib_dir: Path) -> Tuple[Dict[str, int], Dict[int, Path]]:
    force_files = sorted(force_dir.glob("*.txt"))
    vib_files = sorted(vib_dir.glob("*.csv")) + sorted(vib_dir.glob("*.xlsx")) + sorted(vib_dir.glob("*.xls"))
    force_map = {path.name: idx + 1 for idx, path in enumerate(force_files)}

    vibration_by_key = {}
    for vib_path in vib_files:
        parts = vib_path.stem.split("-")
        if len(parts) != 3:
            raise ValueError(f"Unexpected vibration filename format: {vib_path.name}")
        key = tuple(int(part) for part in parts)
        if key in vibration_by_key:
            raise ValueError(f"Duplicate vibration file mapping for {key}: {vib_path.name}")
        vibration_by_key[key] = vib_path

    vib_map: Dict[int, Path] = {}
    for cycle, force_path in enumerate(force_files, start=1):
        parts = force_path.stem.split("-")
        if len(parts) != 3:
            raise ValueError(f"Unexpected force filename format: {force_path.name}")
        key = tuple(int(part) for part in parts)
        vibration_path = vibration_by_key.get(key)
        if vibration_path is not None:
            vib_map[cycle] = vibration_path
    return force_map, vib_map


def extract_features(
    force_dir: Path,
    vib_dir: Path,
    output_path: Path,
    max_cycles: int | None = None,
    overwrite: bool = False,
) -> pd.DataFrame:
    force_files = sorted(force_dir.glob("*.txt"))
    _, vib_map = determine_cycle_map(force_dir, vib_dir)

    if output_path.exists() and not overwrite:
        raise FileExistsError(f"{output_path} already exists. Delete it or pass --overwrite to regenerate the parquet cache.")
    if output_path.exists() and overwrite:
        output_path.unlink()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    parts_dir = output_path.with_suffix(output_path.suffix + ".parts")
    parts_dir.mkdir(parents=True, exist_ok=True)
    validation_path = output_path.parent / "vibration_validation.json"
    if max_cycles is None and not validation_path.exists():
        raise FileNotFoundError(
            f"Full vibration validation is required before extraction: {validation_path}"
        )
    validation_rows = (
        json.loads(validation_path.read_text(encoding="utf-8"))
        if validation_path.exists()
        else []
    )
    validation_by_cycle = {int(row["cycle"]): row for row in validation_rows}
    selected_files = force_files[:max_cycles] if max_cycles is not None else force_files
    part_paths = []

    for idx, force_path in enumerate(tqdm(selected_files, desc="Cycles"), start=1):
        cycle = idx
        vib_path = None if cycle in FORCE_ONLY_CYCLES else vib_map.get(cycle)
        part_path = parts_dir / f"cycle_{cycle:03d}.parquet"
        manifest_path = parts_dir / f"cycle_{cycle:03d}.json"

        def file_signature(path: Path | None):
            if path is None:
                return None
            stat = path.stat()
            return {"path": str(path.resolve()), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}

        expected_manifest = {
            "cache_version": CACHE_VERSION,
            "cycle": cycle,
            "force": file_signature(force_path),
            "vibration": file_signature(vib_path),
        }
        validation = validation_by_cycle.get(cycle, {})
        invalid_sample_indices = np.asarray(
            validation.get("invalid_indexes", []),
            dtype=np.int64,
        )
        total_signal_samples = int(validation.get("total_records", 0))
        invalid_window_samples = int(round(float(validation.get("sampling_rate_hz", 10000.0))))
        invalid_complete_windows = invalid_sample_indices[
            invalid_sample_indices < (total_signal_samples // invalid_window_samples) * invalid_window_samples
        ]
        must_rebuild_for_invalid_windows = bool(vib_path is not None and invalid_complete_windows.size)
        if part_path.exists() and manifest_path.exists():
            try:
                saved_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                stats = saved_manifest.get("stats", {})
                invalid_count = (
                    int(validation.get("invalid_records", 0))
                    if vib_path is not None
                    else 0
                )
                expected_discarded_windows = len(
                    np.unique(invalid_complete_windows // invalid_window_samples)
                )
                integrity_matches = (
                    stats.get("n_invalid_dropped") == invalid_count
                    and stats.get("vibration_windows_discarded") == expected_discarded_windows
                )
                if (
                    saved_manifest.get("input") == expected_manifest
                    and (not must_rebuild_for_invalid_windows or integrity_matches)
                ):
                    cached_frame = pd.read_parquet(part_path)
                    cached_frame["n_invalid_dropped"] = invalid_count
                    cached_frame["corrupt_vib"] = invalid_count > 0
                    temporary_part = part_path.with_suffix(".parquet.tmp")
                    cached_frame.to_parquet(temporary_part, index=False)
                    os.replace(temporary_part, part_path)
                    stats["n_invalid_dropped"] = invalid_count
                    stats["corrupt_vib"] = invalid_count > 0
                    stats.setdefault("vibration_total_windows", stats.get("vibration_windows", 0))
                    stats.setdefault("vibration_windows_discarded", 0)
                    temporary_manifest = manifest_path.with_suffix(".json.tmp")
                    temporary_manifest.write_text(
                        json.dumps({"input": expected_manifest, "stats": stats}),
                        encoding="utf-8",
                    )
                    os.replace(temporary_manifest, manifest_path)
                    print(
                        f"CYCLE {cycle:02d}: force_duration={stats['force_duration_s']:.4f}s "
                        f"force_windows={stats['force_windows']} pairing={stats['pairing']} "
                        f"invalid_vibration_records={invalid_count} (resumed)",
                        flush=True,
                    )
                    part_paths.append(part_path)
                    continue
            except (OSError, json.JSONDecodeError):
                pass

        part_path.unlink(missing_ok=True)
        manifest_path.unlink(missing_ok=True)
        cycle_started = time.perf_counter()
        force_df = read_force_file(force_path)
        vib_df = read_vibration_file(vib_path) if vib_path is not None else None
        cycle_df, stats = build_cycle_features(
            force_df,
            vib_df,
            cycle,
            force_path.name,
            vib_path.name if vib_path is not None else None,
        )
        if cycle_df.empty:
            raise RuntimeError(f"No complete 1-second windows were produced for cycle {cycle}.")
        temporary_part = part_path.with_suffix(".parquet.tmp")
        cycle_df.to_parquet(temporary_part, index=False)
        os.replace(temporary_part, part_path)
        temporary_manifest = manifest_path.with_suffix(".json.tmp")
        temporary_manifest.write_text(
            json.dumps({
                "input": expected_manifest,
                "stats": stats,
            }),
            encoding="utf-8",
        )
        os.replace(temporary_manifest, manifest_path)
        part_paths.append(part_path)
        print(
            f"CYCLE {cycle:02d}: force_duration={stats['force_duration_s']:.4f}s "
            f"force_windows={stats['force_windows']} "
            f"vibration_duration={stats['vibration_duration_s']} "
            f"vibration_windows={stats['vibration_windows']}/"
            f"{stats['vibration_total_windows']} "
            f"discarded_vibration_windows={stats['vibration_windows_discarded']} "
            f"invalid_vibration_records={stats['n_invalid_dropped']} "
            f"paired={stats['paired_windows']} pairing={stats['pairing']} "
            f"elapsed={time.perf_counter() - cycle_started:.1f}s",
            flush=True,
        )

    if not part_paths:
        raise RuntimeError("No feature rows were produced. Check dataset paths and file format.")

    import pyarrow.parquet as pq

    temporary_output = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary_output.unlink(missing_ok=True)
    writer = None
    row_count = 0
    try:
        for part_path in part_paths:
            table = pq.read_table(part_path)
            if writer is None:
                writer = pq.ParquetWriter(temporary_output, table.schema)
            writer.write_table(table)
            row_count += table.num_rows
    finally:
        if writer is not None:
            writer.close()
    os.replace(temporary_output, output_path)
    if max_cycles is None or max_cycles >= len(force_files):
        import shutil
        shutil.rmtree(parts_dir)
    print(f"Saved features to {output_path} with {row_count} rows.", flush=True)
    return pd.DataFrame({"rows_written": [row_count]})


def main():
    parser = argparse.ArgumentParser(description="Extract 1-second-window sensor features from the QIT CEMC milling dataset.")
    parser.add_argument("--dataset-root", type=str, default=r"e:\27323346\Milling dataset from QIT", help="Path to the root folder containing raw data.")
    parser.add_argument("--output", type=str, default=r"e:\27323346\Milling dataset from QIT\project\data\features.parquet", help="Destination Parquet file.")
    parser.add_argument("--max-cycles", type=int, default=None, help="Optional limit for a quick debug run (e.g., 3 cycles).")
    parser.add_argument("--overwrite", action="store_true", help="Delete any existing output before writing a new parquet cache.")
    args = parser.parse_args()

    dataset_root = Path(args.dataset_root)
    force_dir = dataset_root / "Force and torque data"
    vib_dir = dataset_root / "Vibration and sound data"
    output_path = Path(args.output)

    if not force_dir.exists():
        raise FileNotFoundError(f"Force folder not found: {force_dir}")
    if not vib_dir.exists():
        raise FileNotFoundError(f"Vibration folder not found: {vib_dir}")

    print(f"Force files found: {len(list(force_dir.glob('*.txt')))}")
    print(f"Vibration files found: {len(list(vib_dir.glob('*.csv')) + list(vib_dir.glob('*.xlsx')) + list(vib_dir.glob('*.xls')))}")
    print("Checking sampling rate for 5 kHz band support...")

    sample_force = pd.read_csv(
        sorted(force_dir.glob("*.txt"))[0],
        sep="\t",
        usecols=["Time"],
        nrows=20001,
    )
    fs = estimate_fs(sample_force["Time"].to_numpy())
    print(f"Estimated sampling rate: {fs:.2f} Hz")
    if fs < 10000 and not np.isclose(fs, 10000, rtol=0, atol=1):
        print(f"Warning: fs={fs:.2f} Hz is below 10 kHz; the upper frequency band is clipped to Nyquist ({fs / 2.0:.2f} Hz).")
    elif np.isclose(fs, 10000, rtol=0, atol=1):
        print("Note: fs is 10 kHz, so 5 kHz is exactly Nyquist. The 2000-5000 Hz band is half-open and uses bins below 5 kHz; the Nyquist bin itself is excluded.")

    extract_features(force_dir, vib_dir, output_path, max_cycles=args.max_cycles, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
