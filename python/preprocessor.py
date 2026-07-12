"""
CSI Feature Extraction Pipeline
Extracts features from raw CSI amplitude data for ML classification
"""
import numpy as np
from scipy import stats


def extract_features(amplitude, rssi):
    amp = np.array(amplitude, dtype=float)
    if len(amp) == 0:
        return None

    features = {}

    features['rssi'] = rssi
    features['amp_mean'] = np.mean(amp)
    features['amp_std'] = np.std(amp)
    features['amp_max'] = np.max(amp)
    features['amp_min'] = np.min(amp)
    features['amp_median'] = np.median(amp)
    features['amp_range'] = np.ptp(amp)
    features['amp_q25'] = np.percentile(amp, 25)
    features['amp_q75'] = np.percentile(amp, 75)
    features['amp_iqr'] = features['amp_q75'] - features['amp_q25']

    features['amp_skew'] = float(stats.skew(amp)) if len(amp) > 2 else 0
    features['amp_kurtosis'] = float(stats.kurtosis(amp)) if len(amp) > 3 else 0

    diff = np.diff(amp)
    features['diff_mean'] = np.mean(np.abs(diff))
    features['diff_std'] = np.std(diff)
    features['diff_max'] = np.max(np.abs(diff))

    fft_vals = np.abs(np.fft.rfft(amp))
    features['fft_peak'] = np.max(fft_vals)
    features['fft_mean'] = np.mean(fft_vals)
    features['fft_std'] = np.std(fft_vals)

    n_bands = min(4, len(fft_vals) // 4)
    if n_bands > 0:
        band_size = len(fft_vals) // n_bands
        for i in range(n_bands):
            band = fft_vals[i * band_size:(i + 1) * band_size]
            features[f'fft_band_{i}'] = np.mean(band)

    low = amp[:len(amp) // 3]
    mid = amp[len(amp) // 3:2 * len(amp) // 3]
    high = amp[2 * len(amp) // 3:]
    features['sub_low_mean'] = np.mean(low) if len(low) > 0 else 0
    features['sub_mid_mean'] = np.mean(mid) if len(mid) > 0 else 0
    features['sub_high_mean'] = np.mean(high) if len(high) > 0 else 0
    features['sub_low_high_ratio'] = features['sub_low_mean'] / max(features['sub_high_mean'], 0.01)

    return features


def extract_window_features(window_data):
    if not window_data:
        return None

    all_features = {}
    rssis = [d['rssi'] for d in window_data]
    amplitudes = [d['amplitude'] for d in window_data]

    all_features['rssi_mean'] = np.mean(rssis)
    all_features['rssi_std'] = np.std(rssis)
    all_features['rssi_range'] = np.ptp(rssis)

    max_len = max(len(a) for a in amplitudes)
    padded = [a + [0] * (max_len - len(a)) for a in amplitudes]
    amp_matrix = np.array(padded, dtype=float)
    all_features['amp_temporal_mean'] = np.mean(amp_matrix)
    all_features['amp_temporal_std'] = np.std(amp_matrix)
    all_features['amp_temporal_max'] = np.max(amp_matrix)
    all_features['amp_temporal_min'] = np.min(amp_matrix)

    subcarrier_std = np.std(amp_matrix, axis=0)
    all_features['subcarrier_var_mean'] = np.mean(subcarrier_std)
    all_features['subcarrier_var_max'] = np.max(subcarrier_std)

    frame_diff = np.diff(amp_matrix, axis=0)
    all_features['motion_mean'] = np.mean(np.abs(frame_diff))
    all_features['motion_max'] = np.max(np.abs(frame_diff))
    all_features['motion_std'] = np.std(frame_diff)

    entropy_vals = []
    for row in amp_matrix:
        hist, _ = np.histogram(row, bins=10, density=True)
        hist = hist[hist > 0]
        entropy_vals.append(-np.sum(hist * np.log2(hist + 1e-10)))
    all_features['entropy_mean'] = np.mean(entropy_vals)
    all_features['entropy_std'] = np.std(entropy_vals)

    peak_changes = []
    for i in range(1, len(amp_matrix)):
        peak_changes.append(np.max(np.abs(amp_matrix[i] - amp_matrix[i - 1])))
    all_features['peak_change_mean'] = np.mean(peak_changes) if peak_changes else 0
    all_features['peak_change_max'] = np.max(peak_changes) if peak_changes else 0

    return all_features
