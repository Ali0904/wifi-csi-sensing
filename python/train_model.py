"""
ML Training Pipeline - Train activity classifier on CSI data
Generates synthetic data if no real data available, trains model, saves it
"""
import numpy as np
import json
import os
import pickle
from collections import defaultdict
from preprocessor import extract_features, extract_window_features

DATA_DIR = "D:\\WiFi_CSI_Project\\data"
MODEL_DIR = "D:\\WiFi_CSI_Project\\model"

ACTIVITIES = ['empty_room', 'walking', 'sitting', 'standing', 'door_open', 'door_closed']
WINDOW_SIZE = 5
NUM_SUBCARRIERS = 52


def generate_synthetic_data():
    np.random.seed(42)
    samples = []

    profiles = {
        'empty_room':  {'rssi': -55, 'amp_base': 12, 'amp_noise': 1.5, 'motion': 0.2},
        'walking':     {'rssi': -58, 'amp_base': 14, 'amp_noise': 5.0, 'motion': 3.0},
        'sitting':     {'rssi': -56, 'amp_base': 13, 'amp_noise': 2.0, 'motion': 0.5},
        'standing':    {'rssi': -57, 'amp_base': 13, 'amp_noise': 2.5, 'motion': 0.8},
        'door_open':   {'rssi': -50, 'amp_base': 15, 'amp_noise': 2.0, 'motion': 0.3},
        'door_closed': {'rssi': -62, 'amp_base': 10, 'amp_noise': 1.8, 'motion': 0.2},
    }

    for activity in ACTIVITIES:
        p = profiles[activity]
        for _ in range(300):
            base = p['amp_base'] + 3 * np.sin(np.linspace(0, 2 * np.pi, NUM_SUBCARRIERS))
            noise = np.random.randn(NUM_SUBCARRIERS) * p['amp_noise']
            motion = np.random.randn(NUM_SUBCARRIERS) * p['motion']
            amp = np.abs(base + noise + motion).tolist()
            rssi = p['rssi'] + np.random.randn() * 2
            samples.append({
                'rssi': round(rssi, 1),
                'amplitude': [int(v) for v in amp],
                'activity': activity
            })

    return samples


def load_or_generate_data():
    real_file = os.path.join(DATA_DIR, "labeled_csi.json")
    if os.path.exists(real_file):
        print(f"[OK] Loading real data from {real_file}")
        with open(real_file, 'r') as f:
            return json.load(f)

    print("[!] No real data found, generating synthetic data...")
    data = generate_synthetic_data()
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "synthetic_csi.json"), 'w') as f:
        json.dump(data, f, indent=2)
    print(f"[OK] Generated {len(data)} synthetic samples")
    return data


def create_windows(data):
    by_activity = defaultdict(list)
    for s in data:
        by_activity[s['activity']].append(s)

    windows = []
    labels = []
    for activity, samples in by_activity.items():
        for i in range(0, len(samples) - WINDOW_SIZE, WINDOW_SIZE // 2):
            window = samples[i:i + WINDOW_SIZE]
            features = extract_window_features(window)
            if features is not None:
                windows.append(features)
                labels.append(activity)
    return windows, labels


class NearestCentroid:
    def __init__(self):
        self.centroids = {}
        self.stds = {}
        self.feature_names = None
        self.classes = None

    def fit(self, X, y):
        X = np.array(X)
        self.feature_names = list(range(X.shape[1]))
        self.classes = list(set(y))
        for cls in self.classes:
            idx = [i for i, label in enumerate(y) if label == cls]
            self.centroids[cls] = np.mean(X[idx], axis=0)
            self.stds[cls] = np.std(X[idx], axis=0) + 1e-6

    def predict(self, X):
        X = np.array(X)
        predictions = []
        for x in X:
            best_cls = None
            best_dist = float('inf')
            for cls in self.classes:
                dist = np.sum(((x - self.centroids[cls]) / self.stds[cls]) ** 2)
                if dist < best_dist:
                    best_dist = dist
                    best_cls = cls
            predictions.append(best_cls)
        return predictions

    def score(self, X, y):
        preds = self.predict(X)
        return sum(1 for p, t in zip(preds, y) if p == t) / len(y)


class RandomForest:
    def __init__(self, n_trees=50, max_depth=10):
        self.n_trees = n_trees
        self.max_depth = max_depth
        self.trees = []
        self.feature_indices = []

    def fit(self, X, y):
        X = np.array(X)
        y = np.array(y)
        self.classes = list(set(y))
        n_features = X.shape[1]

        for _ in range(self.n_trees):
            n_cols = max(1, int(np.sqrt(n_features)))
            feat_idx = np.random.choice(n_features, n_cols, replace=False)
            self.feature_indices.append(feat_idx)

            boot_idx = np.random.choice(len(X), len(X), replace=True)
            X_boot = X[boot_idx][:, feat_idx]
            y_boot = y[boot_idx]

            tree = self._build_tree(X_boot, y_boot, 0)
            self.trees.append(tree)

    def _build_tree(self, X, y, depth):
        if depth >= self.max_depth or len(set(y)) == 1 or len(y) < 2:
            counts = {}
            for label in y:
                counts[label] = counts.get(label, 0) + 1
            leaf = max(counts, key=counts.get)
            return {'leaf': True, 'class': leaf}

        best_feat = 0
        best_thresh = 0
        best_score = -1

        for f in range(X.shape[1]):
            vals = X[:, f]
            thresholds = np.percentile(vals, [25, 50, 75])
            for t in thresholds:
                left_mask = vals <= t
                right_mask = ~left_mask
                if sum(left_mask) < 2 or sum(right_mask) < 2:
                    continue
                left_labels = y[left_mask]
                right_labels = y[right_mask]
                score = self._gini(y) - (
                    sum(left_mask) / len(y) * self._gini(left_labels) +
                    sum(right_mask) / len(y) * self._gini(right_labels)
                )
                if score > best_score:
                    best_score = score
                    best_feat = f
                    best_thresh = t

        if best_score <= 0:
            counts = {}
            for label in y:
                counts[label] = counts.get(label, 0) + 1
            return {'leaf': True, 'class': max(counts, key=counts.get)}

        left_mask = X[:, best_feat] <= best_thresh
        return {
            'leaf': False,
            'feature': best_feat,
            'threshold': best_thresh,
            'left': self._build_tree(X[left_mask], y[left_mask], depth + 1),
            'right': self._build_tree(X[~left_mask], y[~left_mask], depth + 1),
        }

    def _gini(self, y):
        counts = {}
        for label in y:
            counts[label] = counts.get(label, 0) + 1
        impurity = 1.0
        for count in counts.values():
            impurity -= (count / len(y)) ** 2
        return impurity

    def _predict_tree(self, tree, x):
        if tree['leaf']:
            return tree['class']
        if x[tree['feature']] <= tree['threshold']:
            return self._predict_tree(tree['left'], x)
        return self._predict_tree(tree['right'], x)

    def predict(self, X):
        X = np.array(X)
        predictions = []
        for x in X:
            votes = []
            for tree, feat_idx in zip(self.trees, self.feature_indices):
                x_sub = x[feat_idx]
                votes.append(self._predict_tree(tree, x_sub))
            counts = {}
            for v in votes:
                counts[v] = counts.get(v, 0) + 1
            predictions.append(max(counts, key=counts.get))
        return predictions

    def score(self, X, y):
        preds = self.predict(X)
        return sum(1 for p, t in zip(preds, y) if p == t) / len(y)


def train():
    os.makedirs(MODEL_DIR, exist_ok=True)

    data = load_or_generate_data()
    print(f"[OK] Total samples: {len(data)}")

    activity_counts = defaultdict(int)
    for s in data:
        activity_counts[s['activity']] += 1
    for act, count in sorted(activity_counts.items()):
        print(f"  {act}: {count}")

    print("[...] Creating feature windows...")
    windows, labels = create_windows(data)
    print(f"[OK] {len(windows)} windows, {len(set(labels))} classes")

    feature_keys = sorted(windows[0].keys())
    X = np.array([[w[k] for k in feature_keys] for w in windows])
    y = np.array(labels)

    perm = np.random.permutation(len(X))
    X, y = X[perm], y[perm]
    split = int(0.8 * len(X))
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    print(f"[...] Training Random Forest ({len(X_train)} train, {len(X_test)} test)...")
    rf = RandomForest(n_trees=50, max_depth=10)
    rf.fit(X_train, y_train)
    acc = rf.score(X_test, y_test)
    print(f"[OK] Random Forest accuracy: {acc:.1%}")

    print("[...] Training Nearest Centroid...")
    nc = NearestCentroid()
    nc.fit(X_train, y_train)
    acc_nc = nc.score(X_test, y_test)
    print(f"[OK] Nearest Centroid accuracy: {acc_nc:.1%}")

    model = {
        'classifier': rf,
        'feature_names': feature_keys,
        'activities': ACTIVITIES,
        'window_size': WINDOW_SIZE,
        'accuracy': acc,
    }

    model_file = os.path.join(MODEL_DIR, "activity_model.pkl")
    with open(model_file, 'wb') as f:
        pickle.dump(model, f)
    print(f"[OK] Model saved to {model_file}")

    from collections import Counter
    y_pred = rf.predict(X_test)
    print("\n[OK] Classification Report:")
    print(f"{'Activity':<15} {'Precision':>10} {'Recall':>10} {'F1':>10}")
    print("-" * 50)
    for act in ACTIVITIES:
        tp = sum(1 for p, t in zip(y_pred, y_test) if p == act and t == act)
        fp = sum(1 for p, t in zip(y_pred, y_test) if p == act and t != act)
        fn = sum(1 for p, t in zip(y_pred, y_test) if p != act and t == act)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        print(f"{act:<15} {precision:>10.1%} {recall:>10.1%} {f1:>10.1%}")

    return model


if __name__ == "__main__":
    train()
