import serial
import serial.tools.list_ports
import time
import sys

def main():
    print("=" * 60)
    print("  WiFi CSI Live Data Stream")
    print("  ESP32-S3 on COM10 @ 115200 baud")
    print("=" * 60)
    print()
    
    ports = serial.tools.list_ports.comports()
    print("Available ports:")
    for p in ports:
        print(f"  {p.device} - {p.description}")
    print()
    
    port = "COM10"
    print(f"Connecting to {port}...")
    
    try:
        ser = serial.Serial(port, 115200, timeout=2)
        time.sleep(0.5)
        ser.reset_input_buffer()
        print(f"Connected! Waiting for CSI data...\n")
        print(f"{'RSSI':>6} {'CH':>4} {'BW':>4} {'Subcarriers':>12} {'Amplitude (first 10)':>22}")
        print("-" * 60)
        
        count = 0
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                    
                # Skip log/status lines
                if line.startswith('[') or line.startswith('I ') or line.startswith('D ') or line.startswith('V ') or line.startswith('W ') or line.startswith('E '):
                    continue
                    
                # Try to parse CSI CSV: timestamp,rssi,ch,sec_ch,bw,"amp","phase"
                if ',' in line and '"' in line:
                    try:
                        import re
                        matches = re.findall(r'"([^"]*)"', line)
                        if len(matches) >= 2:
                            amp_str = matches[0]
                            phase_str = matches[1]
                            
                            # Get numeric parts before first quote
                            pre = line.split('"')[0].rstrip(',')
                            parts = pre.split(',')
                            
                            if len(parts) >= 5:
                                timestamp = parts[0]
                                rssi = parts[1]
                                channel = parts[2]
                                sec_ch = parts[3]
                                bw = parts[4]
                                
                                # Parse amplitude
                                amp_clean = amp_str.strip('[]')
                                amp_vals = [int(x.strip()) for x in amp_clean.split(',') if x.strip()] if amp_clean else []
                                
                                # Show first 10 subcarrier amplitudes
                                amp_preview = amp_vals[:10]
                                amp_str_display = str(amp_preview) if amp_vals else "[]"
                                
                                count += 1
                                print(f"#{count:>5}  RSSI={rssi:>4}  CH={channel:>2}  BW={bw:>2}  "
                                      f"Subcarriers={len(amp_vals):>4}  Amp={amp_str_display}")
                    except Exception:
                        pass
                else:
                    # Print non-CSI lines (status messages etc) with a different prefix
                    if line.strip():
                        print(f"  [SYS] {line}")
            else:
                time.sleep(0.01)
                
    except serial.SerialException as e:
        print(f"\nSerial error: {e}")
        print("Make sure no other program is using the port.")
    except KeyboardInterrupt:
        print(f"\n\nStopped. Total CSI packets received: {count}")
    finally:
        if 'ser' in dir() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()
