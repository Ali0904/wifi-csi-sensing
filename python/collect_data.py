"""
CSI Data Collector - Collect labeled activity data from ESP32
Press keys to label activities while recording CSI data
"""
import serial
import numpy as np
import time
import json
import re
import os

PORT = "COM10"
BAUD = 115200
DATA_DIR = "D:\\WiFi_CSI_Project\\data"
SAMPLES_PER_LABEL = 200

ACTIVITIES = {
    '1': 'empty_room',
    '2': 'walking',
    '3': 'sitting',
    '4': 'standing',
    '5': 'door_open',
    '6': 'door_closed',
    '7': 'wall_present',
    '8': 'no_wall',
}


def parse_csi_line(line):
    try:
        matches = re.findall(r'"([^"]*)"', line)
        if len(matches) < 1:
            return None, None
        pre = line.split('"')[0].rstrip(',')
        parts = pre.split(',')
        if len(parts) < 5:
            return None, None
        rssi = int(parts[1])
        amp_str = matches[0].strip('[]')
        amp_vals = [int(x.strip()) for x in amp_str.split(',') if x.strip()] if amp_str else []
        if len(amp_vals) < 10:
            return None, None
        return rssi, amp_vals
    except Exception:
        return None, None


def collect_labeled_data():
    os.makedirs(DATA_DIR, exist_ok=True)

    print("=" * 60)
    print("  CSI DATA COLLECTOR")
    print("=" * 60)
    print()
    print("Activities:")
    for key, name in ACTIVITIES.items():
        print(f"  [{key}] {name}")
    print()
    print(f"Need {SAMPLES_PER_LABEL} samples per activity")
    print()

    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
        time.sleep(1)
        ser.reset_input_buffer()
        print(f"[OK] Connected to {PORT}")
    except Exception as e:
        print(f"[!] Cannot connect: {e}")
        return

    dataset = []

    for key, activity in ACTIVITIES.items():
        print()
        print(f"--- Recording: {activity} ---")
        print(f"Press ENTER to start, then ENTER again to stop")
        input(">> ")

        samples = []
        print(f"  Recording {activity}... (press ENTER to stop)")

        start_time = time.time()
        while len(samples) < SAMPLES_PER_LABEL:
            try:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if ',' in line and '"' in line:
                        rssi, amps = parse_csi_line(line)
                        if rssi is not None and amps is not None:
                            samples.append({
                                'rssi': rssi,
                                'amplitude': amps,
                                'activity': activity,
                                'timestamp': time.time() - start_time
                            })
                            if len(samples) % 20 == 0:
                                print(f"    {len(samples)}/{SAMPLES_PER_LABEL} samples", end='\r')
                else:
                    time.sleep(0.01)

                if ser.in_waiting == 0 and len(samples) > 0:
                    pass

            except KeyboardInterrupt:
                break
            except Exception:
                time.sleep(0.1)

        print(f"  Collected {len(samples)} samples for {activity}")
        dataset.extend(samples)

    ser.close()

    out_file = os.path.join(DATA_DIR, "labeled_csi.json")
    with open(out_file, 'w') as f:
        json.dump(dataset, f, indent=2)
    print()
    print(f"[OK] Saved {len(dataset)} total samples to {out_file}")

    summary = {}
    for s in dataset:
        act = s['activity']
        summary[act] = summary.get(act, 0) + 1
    print("Summary:")
    for act, count in summary.items():
        print(f"  {act}: {count} samples")


if __name__ == "__main__":
    collect_labeled_data()
