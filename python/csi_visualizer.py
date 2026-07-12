"""
WiFi CSI 2D Signal Strength Visualizer
Real-time heatmap + RSSI + amplitude spectrum from ESP32-S3
"""
import serial
import serial.tools.list_ports
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import re
import time
import sys

PORT = "COM10"
BAUD = 115200
MAX_HISTORY = 100
ANIMATION_INTERVAL_MS = 200

class CSIVisualizer:
    def __init__(self):
        self.rssi_history = deque(maxlen=MAX_HISTORY)
        self.amp_history = deque(maxlen=MAX_HISTORY)
        self.phase_history = deque(maxlen=MAX_HISTORY)
        self.timestamps = deque(maxlen=MAX_HISTORY)
        self.packet_count = 0
        self.ser = None
        self.last_rssi = -80
        self.last_channel = 0
        self.last_bw = 20

        self.fig = plt.figure(figsize=(14, 8), facecolor='#1a1a2e')
        self.fig.canvas.manager.set_window_title('WiFi CSI Signal Strength - 2D Visualization')

        gs = self.fig.add_gridspec(2, 2, hspace=0.35, wspace=0.3,
                                    left=0.07, right=0.95, top=0.92, bottom=0.08)

        self.ax_heatmap = self.fig.add_subplot(gs[0, :])
        self.ax_rssi = self.fig.add_subplot(gs[1, 0])
        self.ax_spectrum = self.fig.add_subplot(gs[1, 1])

        for ax in [self.ax_heatmap, self.ax_rssi, self.ax_spectrum]:
            ax.set_facecolor('#16213e')
            ax.tick_params(colors='#a0a0a0')
            for spine in ax.spines.values():
                spine.set_color('#333')

        self.fig.suptitle('WiFi CSI Environmental Sensing', color='#00ff88',
                          fontsize=14, fontweight='bold', y=0.97)

        self.setup_plots()

    def setup_plots(self):
        self.ax_heatmap.set_title('CSI Amplitude Heatmap (Subcarriers vs Time)',
                                   color='#00ccff', fontsize=11, pad=10)
        self.ax_heatmap.set_xlabel('Subcarrier Index', color='#a0a0a0', fontsize=9)
        self.ax_heatmap.set_ylabel('Time (packets)', color='#a0a0a0', fontsize=9)

        self.ax_rssi.set_title('RSSI Over Time', color='#00ccff', fontsize=11, pad=10)
        self.ax_rssi.set_xlabel('Time (packets)', color='#a0a0a0', fontsize=9)
        self.ax_rssi.set_ylabel('RSSI (dBm)', color='#a0a0a0', fontsize=9)
        self.ax_rssi.set_ylim(-100, -20)

        self.ax_spectrum.set_title('Current Amplitude Spectrum', color='#00ccff', fontsize=11, pad=10)
        self.ax_spectrum.set_xlabel('Subcarrier Index', color='#a0a0a0', fontsize=9)
        self.ax_spectrum.set_ylabel('Amplitude', color='#a0a0a0', fontsize=9)

    def connect(self):
        try:
            self.ser = serial.Serial(PORT, BAUD, timeout=2)
            time.sleep(0.5)
            self.ser.reset_input_buffer()
            print(f"[VIZ] Connected to {PORT}")
            return True
        except Exception as e:
            print(f"[VIZ] Connection failed: {e}")
            return False

    def read_serial(self):
        if not self.ser or not self.ser.is_open:
            return
        try:
            for _ in range(20):
                if self.ser.in_waiting <= 0:
                    break
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                if ',' in line and '"' in line:
                    self.parse_csi(line)
        except Exception:
            pass

    def parse_csi(self, line):
        try:
            matches = re.findall(r'"([^"]*)"', line)
            if len(matches) < 2:
                return
            amp_str = matches[0]
            phase_str = matches[1]
            pre = line.split('"')[0].rstrip(',')
            parts = pre.split(',')
            if len(parts) < 5:
                return

            self.last_rssi = int(parts[1])
            self.last_channel = int(parts[2])
            self.last_bw = int(parts[4])

            amp_clean = amp_str.strip('[]')
            amp_vals = [int(x.strip()) for x in amp_clean.split(',') if x.strip()] if amp_clean else []

            phase_clean = phase_str.strip('[]')
            phase_vals = [int(x.strip()) for x in phase_clean.split(',') if x.strip()] if phase_clean else []

            if amp_vals:
                self.amp_history.append(np.array(amp_vals, dtype=float))
                self.phase_history.append(np.array(phase_vals, dtype=float))
                self.rssi_history.append(self.last_rssi)
                self.timestamps.append(time.time())
                self.packet_count += 1
        except Exception:
            pass

    def update(self, frame):
        self.read_serial()

        if not self.amp_history:
            self.ax_heatmap.text(0.5, 0.5, f'Waiting for CSI data... (0 packets)\nConnect phone to same WiFi\nand browse/stream to generate traffic',
                                  transform=self.ax_heatmap.transAxes, ha='center', va='center',
                                  color='#ff8800', fontsize=12,
                                  bbox=dict(boxstyle='round,pad=0.5', facecolor='#16213e', edgecolor='#ff8800'))
            self.ax_rssi.text(0.5, 0.5, f'RSSI: {self.last_rssi} dBm',
                              transform=self.ax_rssi.transAxes, ha='center', va='center',
                              color='#00ff88', fontsize=16, fontweight='bold')
            self.ax_spectrum.text(0.5, 0.5, 'No data',
                                   transform=self.ax_spectrum.transAxes, ha='center', va='center',
                                   color='#a0a0a0', fontsize=12)
            return self.ax_heatmap, self.ax_rssi, self.ax_spectrum

        self.fig.suptitle(f'WiFi CSI Environmental Sensing  |  CH {self.last_channel}  |  BW {self.last_bw}MHz  |  Packets: {self.packet_count}',
                          color='#00ff88', fontsize=13, fontweight='bold', y=0.97)

        for ax in [self.ax_heatmap, self.ax_rssi, self.ax_spectrum]:
            ax.clear()
        self.setup_plots()

        amp_data = list(self.amp_history)
        max_cols = max(len(a) for a in amp_data)
        padded = np.zeros((len(amp_data), max_cols))
        for i, a in enumerate(amp_data):
            padded[i, :len(a)] = np.abs(a)

        if padded.shape[0] > 1:
            im = self.ax_heatmap.imshow(padded, aspect='auto', cmap='viridis',
                                         interpolation='nearest', origin='lower')
            self.ax_heatmap.set_ylabel('Time (newest top)', color='#a0a0a0', fontsize=9)
            cbar = self.fig.colorbar(im, ax=self.ax_heatmap, fraction=0.02, pad=0.02)
            cbar.ax.yaxis.set_tick_params(color='#a0a0a0')
            cbar.ax.set_ylabel('Amplitude', color='#a0a0a0', fontsize=9)
            plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='#a0a0a0')
        else:
            self.ax_heatmap.plot(padded[0], color='#00ccff', linewidth=1.5)

        rssi_data = list(self.rssi_history)
        self.ax_rssi.plot(rssi_data, color='#00ff88', linewidth=2)
        self.ax_rssi.fill_between(range(len(rssi_data)), rssi_data, min(rssi_data) - 5,
                                   alpha=0.3, color='#00ff88')
        self.ax_rssi.set_ylim(min(rssi_data) - 10, max(rssi_data) + 5 if max(rssi_data) > min(rssi_data) else -30)
        self.ax_rssi.axhline(y=np.mean(rssi_data), color='#ff4444', linestyle='--', alpha=0.7,
                              label=f'Avg: {np.mean(rssi_data):.1f} dBm')
        self.ax_rssi.legend(loc='upper right', fontsize=8, facecolor='#16213e', edgecolor='#333',
                             labelcolor='#a0a0a0')

        current_amp = np.abs(amp_data[-1])
        self.ax_spectrum.bar(range(len(current_amp)), current_amp, color='#00ccff', alpha=0.8, width=0.8)
        self.ax_spectrum.set_xlim(-1, len(current_amp))

        return self.ax_heatmap, self.ax_rssi, self.ax_spectrum

    def run(self):
        if not self.connect():
            print("[VIZ] Cannot connect. Exiting.")
            return

        print("[VIZ] Starting visualization... Close window to stop.")
        print("[VIZ] TIP: Connect your phone to 'Haider-2.4GHz' and browse/play video for more CSI data.")

        ani = animation.FuncAnimation(self.fig, self.update, interval=ANIMATION_INTERVAL_MS,
                                       blit=False, cache_frame_data=False)

        try:
            plt.show()
        except KeyboardInterrupt:
            pass
        finally:
            if self.ser and self.ser.is_open:
                self.ser.close()
            print(f"[VIZ] Stopped. Total packets: {self.packet_count}")


if __name__ == "__main__":
    viz = CSIVisualizer()
    viz.run()
