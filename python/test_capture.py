import serial, time
s = serial.Serial('COM10', 115200, timeout=3)
time.sleep(0.5)
s.reset_input_buffer()
for i in range(60):
    line = s.readline().decode('utf-8', errors='ignore').strip()
    if line:
        print(line)
s.close()
