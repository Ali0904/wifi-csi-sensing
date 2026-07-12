"""
WiFi CSI Real-Time Signal Strength Monitor
Static room visualization with live RSSI and CSI data from ESP32
"""
import serial
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import LinearSegmentedColormap
from matplotlib import patheffects
import matplotlib.animation as animation
import re
import time
import threading
from collections import deque

PORT = "COM10"
BAUD = 115200

ROOM_W = 7.0
ROOM_H = 5.0
AP_X = 0.3
AP_Y = 4.7

SIGNAL_DBM_AT_1M = -30
PATH_LOSS_EXP = 2.8
NOISE_FLOOR = -95

wifi_cmap_colors = [
    (0.0,  '#050510'), (0.08, '#10002a'), (0.18, '#2d0066'),
    (0.28, '#5500aa'), (0.38, '#7700cc'), (0.48, '#9933dd'),
    (0.58, '#bb55ee'), (0.68, '#dd77ff'), (0.78, '#ff6600'),
    (0.86, '#ff9933'), (0.93, '#ffcc00'), (0.97, '#ffee66'),
    (1.0,  '#ffffff'),
]

GRID_RES = 80
xi = np.linspace(0, ROOM_W, GRID_RES)
yi = np.linspace(0, ROOM_H, GRID_RES)
Xi, Yi = np.meshgrid(xi, yi)
DIST = np.sqrt((Xi - AP_X)**2 + (Yi - AP_Y)**2)
DIST = np.clip(DIST, 0.1, None)

MASK = np.zeros_like(DIST, dtype=bool)


class WiFiStrengthMonitor:
    def __init__(self):
        self.ser = None
        self.lock = threading.Lock()
        self.current_rssi = -80
        self.current_amp = []
        self.connected = False
        self.rssi_history = deque(maxlen=200)
        self.amp_avg = []
        self.frame_count = 0

        self.cmap = LinearSegmentedColormap.from_list('wifi', wifi_cmap_colors, N=512)

        self.fig = plt.figure(figsize=(14, 8), facecolor='#050510')
        self.fig.canvas.manager.set_window_title('WiFi Signal Strength - Real Time')

        gs = self.fig.add_gridspec(2, 3, height_ratios=[3, 1.2], hspace=0.3, wspace=0.3,
                                    left=0.05, right=0.95, top=0.92, bottom=0.08)

        self.ax_room = self.fig.add_subplot(gs[0, :2])
        self.ax_gauge = self.fig.add_subplot(gs[0, 2])
        self.ax_spectrum = self.fig.add_subplot(gs[1, 0])
        self.ax_rssi = self.fig.add_subplot(gs[1, 1])
        self.ax_status = self.fig.add_subplot(gs[1, 2])

        for ax in [self.ax_gauge, self.ax_spectrum, self.ax_rssi, self.ax_status]:
            ax.set_facecolor('#0a0a1a')
            for spine in ax.spines.values():
                spine.set_color('#222244')

        self._init_room_static()
        self._init_gauge_static()

    def _init_room_static(self):
        ax = self.ax_room
        ax.set_facecolor('#060614')
        ax.set_xlim(-0.3, ROOM_W + 0.3)
        ax.set_ylim(-0.3, ROOM_H + 0.3)
        ax.set_aspect('equal')
        ax.set_title('Room WiFi Coverage', color='#5588ff', fontsize=13, pad=12, fontweight='bold')
        ax.set_xlabel('X (m)', color='#556677', fontsize=9)
        ax.set_ylabel('Y (m)', color='#556677', fontsize=9)
        ax.tick_params(colors='#445566', labelsize=8)
        for s in ax.spines.values():
            s.set_color('#1a1a3a')

    def _init_gauge_static(self):
        ax = self.ax_gauge
        ax.set_xlim(-1.5, 1.5)
        ax.set_ylim(-0.4, 1.8)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_facecolor('#0a0a1a')
        angles = np.linspace(np.pi, 0, 100)
        for i, angle in enumerate(angles):
            frac = i / len(angles)
            c = '#ff2222' if frac < 0.3 else '#ffaa00' if frac < 0.6 else '#00ff88'
            x1, y1 = np.cos(angle), np.sin(angle)
            x2, y2 = 0.88 * np.cos(angle), 0.88 * np.sin(angle)
            ax.plot([x1, x2], [y1, y2], color=c, linewidth=3, alpha=0.3)
        ax.plot(0, 0, 'o', color='#ff3333', markersize=6, zorder=6)
        ax.text(0, -0.4, 'dBm', color='#445566', fontsize=10, ha='center')

    def connect_serial(self):
        try:
            self.ser = serial.Serial(PORT, BAUD, timeout=1)
            time.sleep(1)
            self.ser.reset_input_buffer()
            self.connected = True
            print(f"[OK] Connected to {PORT}")
            return True
        except Exception as e:
            print(f"[!] No ESP32: {e}")
            return False

    def serial_thread(self):
        while self.connected:
            try:
                if self.ser and self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if ',' in line and '"' in line:
                        self._parse(line)
                else:
                    time.sleep(0.01)
            except Exception:
                time.sleep(0.1)

    def _parse(self, line):
        try:
            matches = re.findall(r'"([^"]*)"', line)
            if len(matches) < 1:
                return
            pre = line.split('"')[0].rstrip(',')
            parts = pre.split(',')
            if len(parts) < 5:
                return
            rssi = int(parts[1])
            amp_str = matches[0].strip('[]')
            amp_vals = [int(x.strip()) for x in amp_str.split(',') if x.strip()] if amp_str else []
            with self.lock:
                self.current_rssi = rssi
                self.current_amp = amp_vals
                self.rssi_history.append(rssi)
                if amp_vals:
                    self.amp_avg = list(np.abs(np.array(amp_vals, dtype=float)))
        except Exception:
            pass

    def update(self, frame):
        self.frame_count += 1
        self._update_room()
        self._update_gauge()
        self._update_spectrum()
        self._update_rssi_graph()
        self._update_status()

    def _update_room(self):
        ax = self.ax_room
        ax.clear()
        ax.set_facecolor('#060614')
        ax.set_xlim(-0.3, ROOM_W + 0.3)
        ax.set_ylim(-0.3, ROOM_H + 0.3)
        ax.set_aspect('equal')
        ax.set_title('Room WiFi Coverage', color='#5588ff', fontsize=13, pad=12, fontweight='bold')
        ax.set_xlabel('X (m)', color='#556677', fontsize=9)
        ax.set_ylabel('Y (m)', color='#556677', fontsize=9)
        ax.tick_params(colors='#445566', labelsize=8)
        for s in ax.spines.values():
            s.set_color('#1a1a3a')

        with self.lock:
            rssi = self.current_rssi

        signal_db = SIGNAL_DBM_AT_1M + (-10 * PATH_LOSS_EXP) * np.log10(DIST)
        signal_db = np.clip(signal_db, NOISE_FLOOR, -25)

        ax.imshow(signal_db, extent=(0, ROOM_W, 0, ROOM_H),
                  origin='lower', cmap=self.cmap, vmin=NOISE_FLOOR, vmax=-25,
                  aspect='equal', interpolation='bilinear', alpha=0.85, zorder=1)

        room = patches.Rectangle((0, 0), ROOM_W, ROOM_H, linewidth=3,
                                  edgecolor='#4488ff', facecolor='none', zorder=5)
        ax.add_patch(room)

        ax.plot([3.0, 4.0], [0, 0], color='#060614', linewidth=6, zorder=6)
        ax.text(3.5, -0.25, 'door', color='#334455', fontsize=7, ha='center', zorder=6)

        ax.plot([3.5, 3.5], [0, 3.5], color='#334466', linewidth=2, zorder=5)
        ax.plot([3.5, 7.0], [3.5, 3.5], color='#334466', linewidth=2, zorder=5)

        ax.text(1.75, 1.75, 'Living Room', color='#334466', fontsize=8, ha='center',
                fontfamily='monospace', alpha=0.6, zorder=6)
        ax.text(5.25, 1.75, 'Kitchen', color='#334466', fontsize=8, ha='center',
                fontfamily='monospace', alpha=0.6, zorder=6)
        ax.text(5.25, 5.25, 'Bedroom', color='#334466', fontsize=8, ha='center',
                fontfamily='monospace', alpha=0.6, zorder=6)

        pulse = 1.0 + 0.1 * np.sin(self.frame_count * 0.1)
        ax.plot(AP_X, AP_Y, 'o', color='#ffffff', markersize=14 * pulse, zorder=10,
                markeredgecolor='#4488ff', markeredgewidth=2)
        for r in [0.6, 1.2, 1.8]:
            c = plt.Circle((AP_X, AP_Y), r, fill=False,
                           edgecolor='#4466aa', linewidth=0.6, linestyle='--',
                           alpha=0.25, zorder=3)
            ax.add_patch(c)
        ax.text(AP_X, AP_Y + 0.45, 'WiFi Router', color='#88aaff', fontsize=8,
                ha='center', fontweight='bold', zorder=10,
                path_effects=[patheffects.withStroke(linewidth=2, foreground='#060614')])

        if rssi >= -50:
            sc, sl = '#00ff88', 'EXCELLENT'
        elif rssi >= -60:
            sc, sl = '#88ff00', 'GOOD'
        elif rssi >= -70:
            sc, sl = '#ffaa00', 'FAIR'
        else:
            sc, sl = '#ff4444', 'WEAK'
        ax.text(ROOM_W / 2, ROOM_H + 0.2, f'{rssi} dBm  [{sl}]', color=sc, fontsize=14,
                ha='center', fontweight='bold', fontfamily='monospace', zorder=10)

    def _update_gauge(self):
        ax = self.ax_gauge
        ax.clear()
        ax.set_xlim(-1.5, 1.5)
        ax.set_ylim(-0.4, 1.8)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_facecolor('#0a0a1a')

        angles = np.linspace(np.pi, 0, 100)
        for i, angle in enumerate(angles):
            frac = i / len(angles)
            c = '#ff2222' if frac < 0.3 else '#ffaa00' if frac < 0.6 else '#00ff88'
            x1, y1 = np.cos(angle), np.sin(angle)
            x2, y2 = 0.88 * np.cos(angle), 0.88 * np.sin(angle)
            ax.plot([x1, x2], [y1, y2], color=c, linewidth=3, alpha=0.3)

        with self.lock:
            rssi = self.current_rssi
        quality = np.clip((rssi + 95) / 65, 0, 1)
        na = np.pi - quality * np.pi
        ax.plot([0, 0.82 * np.cos(na)], [0, 0.82 * np.sin(na)],
                color='#ff3333', linewidth=2.5, zorder=5)
        ax.plot(0, 0, 'o', color='#ff3333', markersize=6, zorder=6)
        ax.text(0, -0.2, f'{rssi}', color='#5588ff', fontsize=22,
                fontweight='bold', ha='center', fontfamily='monospace')
        ax.text(0, -0.4, 'dBm', color='#445566', fontsize=10, ha='center')
        if rssi >= -50:
            qt, qc = 'EXCELLENT', '#00ff88'
        elif rssi >= -60:
            qt, qc = 'GOOD', '#88ff00'
        elif rssi >= -70:
            qt, qc = 'FAIR', '#ffaa00'
        else:
            qt, qc = 'WEAK', '#ff4444'
        ax.text(0, 1.55, qt, color=qc, fontsize=14, fontweight='bold', ha='center')

    def _update_spectrum(self):
        ax = self.ax_spectrum
        ax.clear()
        ax.set_facecolor('#0a0a1a')
        ax.set_title('CSI Subcarrier Amplitude', color='#5588ff', fontsize=11, pad=8)
        ax.set_xlabel('Subcarrier', color='#556677', fontsize=8)
        ax.set_ylabel('Amplitude', color='#556677', fontsize=8)
        ax.tick_params(colors='#445566', labelsize=7)
        for s in ax.spines.values():
            s.set_color('#1a1a3a')

        with self.lock:
            amp = list(self.amp_avg)
        if amp:
            vals = np.array(amp, dtype=float)
            mean_v = np.mean(vals)
            colors = ['#00ccff' if v > mean_v else '#2a3355' for v in vals]
            ax.bar(range(len(vals)), vals, color=colors, alpha=0.9, width=0.8)
            ax.axhline(y=mean_v, color='#ff4444', linestyle='--', alpha=0.5, linewidth=0.8)
            ax.set_xlim(-0.5, len(vals) - 0.5)
        else:
            ax.text(0.5, 0.5, 'Waiting for CSI...', transform=ax.transAxes,
                    ha='center', va='center', color='#334455', fontsize=10)

    def _update_rssi_graph(self):
        ax = self.ax_rssi
        ax.clear()
        ax.set_facecolor('#0a0a1a')
        ax.set_title('RSSI Over Time', color='#5588ff', fontsize=11, pad=8)
        ax.set_xlabel('Samples', color='#556677', fontsize=8)
        ax.set_ylabel('RSSI (dBm)', color='#556677', fontsize=8)
        ax.tick_params(colors='#445566', labelsize=7)
        for s in ax.spines.values():
            s.set_color('#1a1a3a')

        with self.lock:
            d = list(self.rssi_history)
        if len(d) > 1:
            ax.plot(d, color='#00ff88', linewidth=1.2)
            ax.fill_between(range(len(d)), d, min(d) - 5, alpha=0.15, color='#00ff88')
            lo = min(d) - 8
            hi = max(d) + 5 if max(d) > min(d) else -30
            ax.set_ylim(lo, hi)
            ax.axhline(y=np.mean(d), color='#ff4444', linestyle='--', alpha=0.4, linewidth=0.8)
            ax.set_xlim(0, max(len(d), 20))
        else:
            ax.text(0.5, 0.5, 'Collecting...', transform=ax.transAxes,
                    ha='center', va='center', color='#334455', fontsize=10)

    def _update_status(self):
        ax = self.ax_status
        ax.clear()
        ax.axis('off')
        ax.set_facecolor('#0a0a1a')

        status = 'CONNECTED' if self.connected else 'DISCONNECTED'
        sc = '#00ff88' if self.connected else '#ff4444'
        with self.lock:
            rssi = self.current_rssi
            n_samples = len(self.rssi_history)
            n_sub = len(self.amp_avg)

        avg_rssi = np.mean(list(self.rssi_history)) if self.rssi_history else rssi
        min_rssi = min(self.rssi_history) if self.rssi_history else rssi
        max_rssi = max(self.rssi_history) if self.rssi_history else rssi

        lines = [
            (f'ESP32: {status}', sc, 12),
            (f'Port: {PORT}', '#445566', 9),
            ('', '#0a0a1a', 6),
            (f'Current:  {rssi} dBm', '#ffcc00', 16),
            (f'Average:  {avg_rssi:.1f} dBm', '#88aaff', 11),
            (f'Min:      {min_rssi} dBm', '#ff6666', 9),
            (f'Max:      {max_rssi} dBm', '#66ff66', 9),
            ('', '#0a0a1a', 6),
            (f'Samples:  {n_samples}', '#556677', 9),
            (f'Subcarriers: {n_sub}', '#556677', 9),
        ]
        for i, (text, color, size) in enumerate(lines):
            ax.text(0.05, 0.92 - i * 0.085, text, color=color, fontsize=size,
                    transform=ax.transAxes, fontfamily='monospace')

    def run(self):
        has_serial = self.connect_serial()
        if has_serial:
            t = threading.Thread(target=self.serial_thread, daemon=True)
            t.start()
        else:
            print("[!] No ESP32 - showing UI without live data")

        print("[OK] Real-time WiFi strength monitor")
        print("[OK] Close window to exit")

        ani = animation.FuncAnimation(self.fig, self.update, interval=500,
                                       blit=False, cache_frame_data=False)
        try:
            plt.show()
        except KeyboardInterrupt:
            pass
        finally:
            self.connected = False
            if self.ser:
                self.ser.close()
            print("[OK] Stopped")


if __name__ == "__main__":
    mon = WiFiStrengthMonitor()
    mon.run()
