"""
Automated CSI Data Collector - Records labeled data with timed intervals
User performs each activity during the countdown
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
SAMPLES_PER_LABEL = 150
RECORD_SECONDS = 30

ACTIVITIES = [
    ('empty_room',   'STAY STILL - Empty room, no movement'),
    ('walking',      'WALK around the room normally'),
    ('sitting',      'SIT DOWN and stay seated'),
    ('standing',     'STAND STILL in place'),
    ('door_open',    'OPEN the door and leave it open'),
    ('door_closed',  'CLOSE the door and stay inside'),
]


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


def collect():
    os.makedirs(DATA_DIR, exist_ok=True)

    print("=" * 60)
    print("  AUTOMATED CSI DATA COLLECTOR")
    print("=" * 60)
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

    for activity, instruction in ACTIVITIES:
        print()
        print(f"{'=' * 50}")
        print(f"  NEXT: {activity.upper()}")
        print(f"  {instruction}")
        print(f"  Recording for {RECORD_SECONDS} seconds...")
        print(f"{'=' * 50}")

        for i in range(3, 0, -1):
            print(f"  Starting in {i}...", end='\r')
            time.sleep(1)
        print("  GO!                    ")

        samples = []
        start = time.time()
        while time.time() - start < RECORD_SECONDS:
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
                            })
                else:
                    time.sleep(0.01)
            except Exception:
                time.sleep(0.1)

            elapsed = time.time() - start
            remaining = RECORD_SECONDS - elapsed
            if int(elapsed) % 3 == 0:
                print(f"  {remaining:.0f}s left | {len(samples)} samples", end='\r')

        print(f"  DONE: {len(samples)} samples for {activity}         ")
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
    for act, count in sorted(summary.items()):
        print(f"  {act}: {count} samples")


if __name__ == "__main__":
    collect()
