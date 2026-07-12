"""
Wall Detection using CSI Signal Attenuation Analysis
Detects walls by analyzing RSSI drop and subcarrier amplitude changes
"""
import numpy as np
from collections import deque


class WallDetector:
    def __init__(self, room_w=7.0, room_h=5.0, grid_res=20):
        self.room_w = room_w
        self.room_h = room_h
        self.grid_res = grid_res
        self.no_wall_rssi = -45
        self.wall_attenuation = 12.0
        self.noise_std = 3.0

    def compute_attenuation_map(self, measured_rssi, measured_positions, ap_position):
        xi = np.linspace(0, self.room_w, self.grid_res)
        yi = np.linspace(0, self.room_h, self.grid_res)
        Xi, Yi = np.meshgrid(xi, yi)

        dist = np.sqrt((Xi - ap_position[0])**2 + (Yi - ap_position[1])**2)
        dist = np.clip(dist, 0.1, None)

        free_space_rssi = self.no_wall_rssi - 10 * 2.8 * np.log10(dist)

        attenuation_map = np.zeros_like(Xi)
        wall_probability = np.zeros_like(Xi)

        for gy in range(self.grid_res):
            for gx in range(self.grid_res):
                px, py = Xi[gy, gx], Yi[gy, gx]
                distances = np.sqrt((np.array(measured_positions)[:, 0] - px)**2 +
                                   (np.array(measured_positions)[:, 1] - py)**2)

                if len(distances) > 0:
                    closest_idx = np.argmin(distances)
                    closest_dist = distances[closest_idx]

                    if closest_dist < 1.0:
                        weight = 1.0 / (closest_dist + 0.1)
                        expected = free_space_rssi[gy, gx]
                        actual = measured_rssi[closest_idx]
                        attenuation_map[gy, gx] = expected - actual
                        wall_probability[gy, gx] = weight * max(0, attenuation_map[gy, gx]) / self.wall_attenuation

        wall_probability = np.clip(wall_probability, 0, 1)
        return Xi, Yi, wall_probability, attenuation_map

    def detect_walls_from_csi(self, rssi_history, amp_history, ap_position):
        if len(rssi_history) < 10:
            return None

        recent_rssi = list(rssi_history)[-50:]
        mean_rssi = np.mean(recent_rssi)
        std_rssi = np.std(recent_rssi)

        if len(amp_history) > 0:
            recent_amps = np.array(amp_history[-20:])
            amp_mean = np.mean(recent_amps, axis=0)
            amp_variance = np.var(recent_amps, axis=0)
        else:
            amp_mean = np.zeros(52)
            amp_variance = np.zeros(52)

        wall_likelihood = max(0, min(1, (-55 - mean_rssi) / self.wall_attenuation))
        reflection_indicator = np.mean(amp_variance) > 5.0

        return {
            'mean_rssi': mean_rssi,
            'std_rssi': std_rssi,
            'wall_likelihood': wall_likelihood,
            'reflection_indicator': reflection_indicator,
            'amp_mean': amp_mean,
            'amp_variance': amp_variance,
            'estimated_attenuation': max(0, self.no_wall_rssi - mean_rssi),
        }

    def generate_wall_map(self, num_walls=2):
        np.random.seed(123)
        walls = []

        wall_positions = [
            {'x1': 3.5, 'y1': 0, 'x2': 3.5, 'y2': 3.5, 'orient': 'v'},
            {'x1': 3.5, 'y1': 3.5, 'x2': 7.0, 'y2': 3.5, 'orient': 'h'},
        ]

        xi = np.linspace(0, self.room_w, self.grid_res * 2)
        yi = np.linspace(0, self.room_h, self.grid_res * 2)
        Xi, Yi = np.meshgrid(xi, yi)
        wall_map = np.zeros_like(Xi)

        for wall in wall_positions:
            if wall['orient'] == 'v':
                wx = wall['x1']
                dist_to_wall = np.abs(Xi - wx)
                wall_mask = np.exp(-dist_to_wall**2 / (2 * 0.3**2))
                wall_map += wall_mask
            else:
                wy = wall['y1']
                dist_to_wall = np.abs(Yi - wy)
                wall_mask = np.exp(-dist_to_wall**2 / (2 * 0.3**2))
                wall_map += wall_mask

        wall_map = np.clip(wall_map, 0, 1)
        return Xi, Yi, wall_map, wall_positions
