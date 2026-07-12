"""
WiFi CSI Room Signal Strength Mapper
2D spatial heatmap of WiFi signal inside a room
Collects CSI readings at different positions and builds a room signal map
"""
import serial
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.animation as animation
from matplotlib.widgets import Button
import re
import time
import json
import os

PORT = "COM10"
BAUD = 115200
SAVE_FILE = "D:\\WiFi_CSI_Project\\python\\room_data.json"

ROOM_WIDTH_M = 6.0
ROOM_HEIGHT_M = 5.0
GRID_RESOLUTION = 0.5

csi_colors = ['#0d0221', '#0a0033', '#1a0066', '#330099',
              '#4d00cc', '#6600ff', '#8833ff', '#aa66ff',
              '#00ccff', '#00ff88', '#ffff00', '#ff8800', '#ff0000']


class RoomMapper:
    def __init__(self):
        self.ser = None
        self.current_rssi = -70
        self.current_amp_mean = 0
        self.current_amp_std = 0

        self.grid_x = int(ROOM_WIDTH_M / GRID_RESOLUTION) + 1
        self.grid_y = int(ROOM_HEIGHT_M / GRID_RESOLUTION) + 1
        self.signal_map = np.full((self.grid_y, self.grid_x), np.nan)
        self.readings_count = np.zeros((self.grid_y, self.grid_x))

        self.scan_positions = []
        self.current_scan_idx = 0
        self.generate_scan_path()
        self.load_data()

        self.fig = plt.figure(figsize=(16, 9), facecolor='#0d1117')
        self.fig.canvas.manager.set_window_title('WiFi CSI Room Signal Mapper')

        gs = self.fig.add_gridspec(2, 3, height_ratios=[3, 1], hspace=0.25, wspace=0.3,
                                    left=0.05, right=0.97, top=0.93, bottom=0.06)

        self.ax_room = self.fig.add_subplot(gs[0, :2])
        self.ax_signal_gauge = self.fig.add_subplot(gs[0, 2])
        self.ax_spectrum = self.fig.add_subplot(gs[1, 0])
        self.ax_history = self.fig.add_subplot(gs[1, 1])
        self.ax_legend = self.fig.add_subplot(gs[1, 2])

        for ax in [self.ax_room, self.ax_signal_gauge, self.ax_spectrum, self.ax_history, self.ax_legend]:
            ax.set_facecolor('#161b22')
            for spine in ax.spines.values():
                spine.set_color('#30363d')

        self.fig.suptitle('WiFi CSI Room Signal Strength Mapper',
                          color='#58a6ff', fontsize=14, fontweight='bold', y=0.97)

        self.setup_room_plot()
        self.setup_gauge()
        self.setup_spectrum()
        self.setup_history()

    def generate_scan_path(self):
        xs = np.arange(0.5, ROOM_WIDTH_M, GRID_RESOLUTION)
        ys = np.arange(0.5, ROOM_HEIGHT_M, GRID_RESOLUTION)
        for y_idx, y in enumerate(ys):
            if y_idx % 2 == 0:
                for x_idx, x in enumerate(xs):
                    self.scan_positions.append((x, y, x_idx, y_idx))
            else:
                for x_idx, x in enumerate(reversed(list(xs))):
                    actual_x_idx = self.grid_x - 1 - x_idx
                    self.scan_positions.append((x, y, actual_x_idx, y_idx))

    def load_data(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, 'r') as f:
                    data = json.load(f)
                self.signal_map = np.array(data['signal_map'])
                self.readings_count = np.array(data['readings_count'])
                loaded = np.sum(~np.isnan(self.signal_map))
                print(f"[MAP] Loaded {int(loaded)} saved positions")
            except Exception:
                pass

    def save_data(self):
        data = {
            'signal_map': self.signal_map.tolist(),
            'readings_count': self.readings_count.tolist()
        }
        with open(SAVE_FILE, 'w') as f:
            json.dump(data, f)

    def connect_serial(self):
        try:
            self.ser = serial.Serial(PORT, BAUD, timeout=1)
            time.sleep(0.5)
            self.ser.reset_input_buffer()
            print(f"[MAP] Connected to {PORT}")
            return True
        except Exception as e:
            print(f"[MAP] Serial unavailable: {e}")
            return False

    def read_csi(self):
        if not self.ser or not self.ser.is_open:
            return
        try:
            for _ in range(15):
                if self.ser.in_waiting <= 0:
                    break
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if ',' in line and '"' in line:
                    self._parse(line)
        except Exception:
            pass

    def _parse(self, line):
        try:
            matches = re.findall(r'"([^"]*)"', line)
            if len(matches) < 2:
                return
            pre = line.split('"')[0].rstrip(',')
            parts = pre.split(',')
            if len(parts) < 5:
                return
            self.current_rssi = int(parts[1])
            amp_clean = matches[0].strip('[]')
            if amp_clean:
                amp_vals = [int(x.strip()) for x in amp_clean.split(',') if x.strip()]
                if amp_vals:
                    arr = np.abs(np.array(amp_vals, dtype=float))
                    self.current_amp_mean = np.mean(arr)
                    self.current_amp_std = np.std(arr)
        except Exception:
            pass

    def setup_room_plot(self):
        self.ax_room.set_title('Room Signal Map', color='#58a6ff', fontsize=12, pad=10)
        self.ax_room.set_xlim(-0.3, ROOM_WIDTH_M + 0.3)
        self.ax_room.set_ylim(-0.3, ROOM_HEIGHT_M + 0.3)
        self.ax_room.set_xlabel('X (meters)', color='#8b949e', fontsize=10)
        self.ax_room.set_ylabel('Y (meters)', color='#8b949e', fontsize=10)
        self.ax_room.set_aspect('equal')
        self.ax_room.tick_params(colors='#8b949e')

        room_rect = mpatches.FancyBboxPatch((0, 0), ROOM_WIDTH_M, ROOM_HEIGHT_M,
                                              boxstyle="round,pad=0.05",
                                              facecolor='none', edgecolor='#58a6ff',
                                              linewidth=2)
        self.ax_room.add_patch(room_rect)

        self.ax_room.plot(0.3, 0.3, 's', color='#ff4444', markersize=10, zorder=5)
        self.ax_room.text(0.3, 0.6, 'TX (ESP32)', color='#ff4444', fontsize=8, ha='center')

        door = mpatches.Rectangle((ROOM_WIDTH_M - 0.9, -0.05), 0.8, 0.1,
                                    facecolor='#8b949e', edgecolor='#8b949e')
        self.ax_room.add_patch(door)
        self.ax_room.text(ROOM_WIDTH_M - 0.5, -0.25, 'Door', color='#8b949e',
                          fontsize=8, ha='center')

        self.heatmap_im = None
        self.scan_marker = None
        self.position_text = self.ax_room.text(ROOM_WIDTH_M / 2, ROOM_HEIGHT_M + 0.15,
                                                 '', color='#58a6ff', fontsize=10, ha='center',
                                                 fontweight='bold')

    def setup_gauge(self):
        self.ax_signal_gauge.set_title('Signal Strength', color='#58a6ff', fontsize=12, pad=10)
        self.ax_signal_gauge.set_xlim(-1.5, 1.5)
        self.ax_signal_gauge.set_ylim(-0.3, 1.8)
        self.ax_signal_gauge.set_aspect('equal')
        self.ax_signal_gauge.axis('off')

    def setup_spectrum(self):
        self.ax_spectrum.set_title('Subcarrier Amplitude', color='#58a6ff', fontsize=11, pad=8)
        self.ax_spectrum.set_xlabel('Subcarrier', color='#8b949e', fontsize=9)
        self.ax_spectrum.set_ylabel('Amplitude', color='#8b949e', fontsize=9)
        self.ax_spectrum.tick_params(colors='#8b949e')

    def setup_history(self):
        self.ax_history.set_title('Signal History', color='#58a6ff', fontsize=11, pad=8)
        self.ax_history.set_xlabel('Reading', color='#8b949e', fontsize=9)
        self.ax_history.set_ylabel('RSSI (dBm)', color='#8b949e', fontsize=9)
        self.ax_history.tick_params(colors='#8b949e')
        self.ax_history.set_ylim(-100, -20)

    def setup_legend(self):
        self.ax_legend.axis('off')
        self.ax_legend.set_title('Controls', color='#58a6ff', fontsize=11, pad=8)
        controls = [
            ('[S] Skip position', '#8b949e'),
            ('[R] Reset map', '#ff4444'),
            ('[A] Auto-scan', '#00ff88'),
            ('[Q] Quit & save', '#ff8800'),
            ('', ''),
            ('Legend:', '#58a6ff'),
            ('Strong signal', '#00ff88'),
            ('Weak signal', '#ff0000'),
            ('Unscanned', '#333333'),
            ('TX antenna', '#ff4444'),
        ]
        for i, (text, color) in enumerate(controls):
            y = 0.88 - i * 0.085
            if text in ('Strong signal', 'Weak signal', 'Unscanned', 'TX antenna'):
                c = {'Strong signal': '#00ff88', 'Weak signal': '#ff0000',
                     'Unscanned': '#333333', 'TX antenna': '#ff4444'}[text]
                self.ax_legend.add_patch(mpatches.Rectangle((0.05, y - 0.015), 0.08, 0.03,
                                                              facecolor=c, edgecolor='none',
                                                              transform=self.ax_legend.transAxes))
            self.ax_legend.text(0.17, y, text, color=color, fontsize=9,
                                transform=self.ax_legend.transAxes, va='center')

    def rssi_to_signal_quality(self, rssi):
        if rssi >= -40:
            return 1.0
        elif rssi >= -60:
            return 0.8
        elif rssi >= -70:
            return 0.6
        elif rssi >= -80:
            return 0.4
        else:
            return 0.2

    def update(self, frame):
        self.read_csi()

        if self.scan_positions and self.current_scan_idx < len(self.scan_positions):
            x, y, gx, gy = self.scan_positions[self.current_scan_idx]
            self.position_text.set_text(
                f'Scan Position: ({x:.1f}m, {y:.1f}m)  '
                f'[{self.current_scan_idx + 1}/{len(self.scan_positions)}]  '
                f'RSSI: {self.current_rssi} dBm')

            if self.scan_marker:
                self.scan_marker.remove()
            self.scan_marker, = self.ax_room.plot(x, y, 'o', color='#00ff88',
                                                    markersize=12, markeredgecolor='white',
                                                    markeredgewidth=2, zorder=10, animated=True)

            quality = self.rssi_to_signal_quality(self.current_rssi)
            if np.isnan(self.signal_map[gy, gx]):
                self.signal_map[gy, gx] = self.current_rssi
                self.readings_count[gy, gx] = 1
            else:
                n = self.readings_count[gy, gx]
                self.signal_map[gy, gx] = (self.signal_map[gy, gx] * n + self.current_rssi) / (n + 1)
                self.readings_count[gy, gx] += 1

        self._draw_heatmap()
        self._draw_gauge()
        self._draw_spectrum()
        self._draw_history()
        self._draw_legend_info()

        self.fig.canvas.draw_idle()

    def _draw_heatmap(self):
        if self.heatmap_im:
            self.heatmap_im.remove()

        display_map = self.signal_map.copy()
        valid = ~np.isnan(display_map)

        if np.any(valid):
            from scipy.ndimage import gaussian_filter
            raw = np.where(valid, display_map, np.nanmean(display_map))
            smoothed = gaussian_filter(raw, sigma=0.8)
            smoothed = np.where(valid, smoothed, np.nan)

            cmap = LinearSegmentedColormap.from_list('wifi', csi_colors, N=256)
            masked = np.ma.masked_invalid(smoothed)

            self.heatmap_im = self.ax_room.imshow(masked, extent=(-0.2, ROOM_WIDTH_M + 0.2,
                                                    -0.2, ROOM_HEIGHT_M + 0.2),
                                                    origin='lower', cmap=cmap, alpha=0.7,
                                                    vmin=-90, vmax=-30, aspect='equal',
                                                    interpolation='bilinear', zorder=1)
        else:
            self.heatmap_im = self.ax_room.imshow(
                np.full((10, 10), 0.3), extent=(-0.2, ROOM_WIDTH_M + 0.2,
                -0.2, ROOM_HEIGHT_M + 0.2),
                origin='lower', cmap='gray', alpha=0.2, aspect='equal', zorder=1)

    def _draw_gauge(self):
        self.ax_signal_gauge.clear()
        self.ax_signal_gauge.set_xlim(-1.5, 1.5)
        self.ax_signal_gauge.set_ylim(-0.3, 1.8)
        self.ax_signal_gauge.axis('off')
        self.ax_signal_gauge.set_facecolor('#161b22')

        angles = np.linspace(np.pi, 0, 100)
        for i, angle in enumerate(angles):
            frac = i / len(angles)
            if frac < 0.3:
                color = '#ff0000'
            elif frac < 0.6:
                color = '#ffaa00'
            else:
                color = '#00ff88'
            r = 1.0
            x1, y1 = r * np.cos(angle), r * np.sin(angle)
            x2, y2 = (r - 0.08) * np.cos(angle), (r - 0.08) * np.sin(angle)
            self.ax_signal_gauge.plot([x1, x2], [y1, y2], color=color, linewidth=3, alpha=0.3)

        quality = self.rssi_to_signal_quality(self.current_rssi)
        needle_angle = np.pi - quality * np.pi
        nx, ny = 0.85 * np.cos(needle_angle), 0.85 * np.sin(needle_angle)
        self.ax_signal_gauge.plot([0, nx], [0, ny], color='#ff4444', linewidth=2.5, zorder=5)
        self.ax_signal_gauge.plot(0, 0, 'o', color='#ff4444', markersize=6, zorder=6)

        self.ax_signal_gauge.text(0, -0.15, f'{self.current_rssi} dBm',
                                   color='#58a6ff', fontsize=16, fontweight='bold', ha='center')

        labels = [(-1.1, -0.05, '-90'), (-0.7, 0.65, '-70'),
                  (0, 0.95, '-50'), (0.7, 0.65, '-30'), (1.1, -0.05, '-10')]
        for lx, ly, lt in labels:
            self.ax_signal_gauge.text(lx, ly, lt, color='#8b949e', fontsize=7, ha='center')

        if self.current_rssi >= -50:
            quality_text = 'EXCELLENT'
            quality_color = '#00ff88'
        elif self.current_rssi >= -60:
            quality_text = 'GOOD'
            quality_color = '#88ff00'
        elif self.current_rssi >= -70:
            quality_text = 'FAIR'
            quality_color = '#ffaa00'
        else:
            quality_text = 'WEAK'
            quality_color = '#ff4444'

        self.ax_signal_gauge.text(0, 1.5, quality_text, color=quality_color,
                                   fontsize=14, fontweight='bold', ha='center')

    def _draw_spectrum(self):
        self.ax_spectrum.clear()
        self.ax_spectrum.set_facecolor('#161b22')
        self.ax_spectrum.set_title('Subcarrier Amplitude', color='#58a6ff', fontsize=11, pad=8)
        self.ax_spectrum.set_xlabel('Subcarrier', color='#8b949e', fontsize=9)
        self.ax_spectrum.set_ylabel('Amplitude', color='#8b949e', fontsize=9)
        self.ax_spectrum.tick_params(colors='#8b949e')
        for spine in self.ax_spectrum.spines.values():
            spine.set_color('#30363d')

        if self.current_amp_mean > 0:
            n = 20
            base = self.current_amp_mean * 0.7
            amps = np.abs(np.random.normal(self.current_amp_mean, self.current_amp_std * 0.3, n))
            colors = ['#00ff88' if a > self.current_amp_mean else '#00ccff' for a in amps]
            self.ax_spectrum.bar(range(n), amps, color=colors, alpha=0.8, width=0.8)
            self.ax_spectrum.axhline(y=self.current_amp_mean, color='#ff4444', linestyle='--',
                                      alpha=0.7, label=f'Mean: {self.current_amp_mean:.0f}')
            self.ax_spectrum.legend(fontsize=8, facecolor='#161b22', edgecolor='#30363d',
                                     labelcolor='#8b949e')

    def _draw_history(self):
        self.ax_history.clear()
        self.ax_history.set_facecolor('#161b22')
        self.ax_history.set_title('Signal History', color='#58a6ff', fontsize=11, pad=8)
        self.ax_history.set_xlabel('Reading', color='#8b949e', fontsize=9)
        self.ax_history.set_ylabel('RSSI (dBm)', color='#8b949e', fontsize=9)
        self.ax_history.tick_params(colors='#8b949e')
        for spine in self.ax_history.spines.values():
            spine.set_color('#30363d')

        valid = self.signal_map[~np.isnan(self.signal_map)]
        if len(valid) > 0:
            self.ax_history.plot(valid, color='#00ccff', linewidth=1.5, alpha=0.8)
            self.ax_history.fill_between(range(len(valid)), valid, min(valid) - 5,
                                          alpha=0.2, color='#00ccff')
            self.ax_history.set_ylim(min(valid) - 10, max(valid) + 5 if max(valid) > min(valid) else -30)
            self.ax_history.axhline(y=np.mean(valid), color='#ff4444', linestyle='--', alpha=0.7)
            self.ax_history.text(len(valid) - 1, np.mean(valid) + 2,
                                  f'Avg: {np.mean(valid):.1f}', color='#ff4444', fontsize=8)

    def _draw_legend_info(self):
        total = self.grid_x * self.grid_y
        filled = int(np.sum(~np.isnan(self.signal_map)))
        self.ax_legend.text(0.5, 0.05, f'Coverage: {filled}/{total} ({filled/total*100:.0f}%)',
                            color='#58a6ff', fontsize=10, fontweight='bold',
                            transform=self.ax_legend.transAxes, ha='center')

    def run(self):
        has_serial = self.connect_serial()
        if not has_serial:
            print("[MAP] No serial connection - running in demo mode")
            self._fill_demo_data()

        print("[MAP] Room Signal Mapper started")
        print("[MAP] Keys: [S] Skip  [R] Reset  [Q] Quit & save")

        ani = animation.FuncAnimation(self.fig, self.update, interval=300,
                                       blit=False, cache_frame_data=False)

        try:
            plt.show()
        except KeyboardInterrupt:
            pass
        finally:
            self.save_data()
            if self.ser and self.ser.is_open:
                self.ser.close()
            print(f"[MAP] Data saved. Coverage: {int(np.sum(~np.isnan(self.signal_map)))}/{self.grid_x * self.grid_y}")

    def _fill_demo_data(self):
        tx_x, tx_y = 0.3, 0.3
        for gy in range(self.grid_y):
            for gx in range(self.grid_x):
                x = gx * GRID_RESOLUTION + GRID_RESOLUTION / 2
                y = gy * GRID_RESOLUTION + GRID_RESOLUTION / 2
                dist = np.sqrt((x - tx_x)**2 + (y - tx_y)**2)
                wall_penalty = 8.0 if (x > 3.5 and y < 2.0) else 0
                rssi = -30 - 20 * np.log10(max(dist, 0.3)) - wall_penalty + np.random.normal(0, 3)
                rssi = max(-95, min(-25, rssi))
                self.signal_map[gy, gx] = rssi
                self.readings_count[gy, gx] = 1


if __name__ == "__main__":
    mapper = RoomMapper()
    mapper.run()
