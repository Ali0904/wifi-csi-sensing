"""
CSI Data Parser Module
Handles serial communication and data parsing from ESP32

@author: Ali Haider
@date: July 2026
"""

import serial
import serial.tools.list_ports
import pandas as pd
import numpy as np
from datetime import datetime
import time
import json
import re
import threading
from queue import Queue


class CSIDataParser:
    """
    Parse CSI data from ESP32 serial output
    """
    
    # Data format constants
    FORMAT_CSV = 'csv'
    FORMAT_JSON = 'json'
    
    def __init__(self, port=None, baudrate=115200, timeout=1):
        """
        Initialize CSI Data Parser
        
        Args:
            port: Serial port (auto-detect if None)
            baudrate: Serial baudrate (default: 115200)
            timeout: Serial timeout in seconds
        """
        self.port = port or self._auto_detect_port()
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn = None
        self.data_queue = Queue()
        self.is_running = False
        self.thread = None
        
        # Statistics
        self.stats = {
            'packets_received': 0,
            'packets_parsed': 0,
            'packets_error': 0,
            'start_time': None,
            'last_timestamp': None
        }
        
        print(f"[Parser] Initialized - Port: {self.port}, Baudrate: {self.baudrate}")
    
    def _auto_detect_port(self):
        """
        Auto-detect ESP32 serial port
        
        Returns:
            str: Detected port name or None
        """
        ports = serial.tools.list_ports.comports()
        esp32_ports = []
        
        for port in ports:
            # Check for common ESP32 identifiers
            if any(identifier in port.description.lower() for identifier in 
                   ['cp210', 'ch340', 'ftdi', 'silicon labs', 'usb-serial']):
                esp32_ports.append(port.device)
                print(f"[Parser] Found potential ESP32 port: {port.device} ({port.description})")
        
        if esp32_ports:
            return esp32_ports[0]
        elif ports:
            print(f"[Parser] Using first available port: {ports[0].device}")
            return ports[0].device
        else:
            print("[Parser] WARNING: No serial ports found")
            return None
    
    def connect(self):
        """
        Establish serial connection
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.port is None:
                print("[Parser] ERROR: No serial port available")
                return False
            
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            
            # Reset input buffer
            self.serial_conn.reset_input_buffer()
            
            print(f"[Parser] Connected to {self.port}")
            return True
            
        except serial.SerialException as e:
            print(f"[Parser] Connection error: {e}")
            return False
    
    def disconnect(self):
        """Close serial connection"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print("[Parser] Disconnected")
    
    def start_parsing(self, callback=None):
        """
        Start parsing CSI data in background thread
        
        Args:
            callback: Function to call with parsed data
        """
        if self.is_running:
            print("[Parser] Already running")
            return
        
        if not self.serial_conn or not self.serial_conn.is_open:
            if not self.connect():
                return
        
        self.is_running = True
        self.stats['start_time'] = datetime.now()
        
        # Start parsing thread
        self.thread = threading.Thread(
            target=self._parse_loop,
            args=(callback,),
            daemon=True
        )
        self.thread.start()
        
        print("[Parser] Started parsing")
    
    def stop_parsing(self):
        """Stop parsing CSI data"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
        print("[Parser] Stopped parsing")
    
    def _parse_loop(self, callback):
        """
        Main parsing loop
        
        Args:
            callback: Function to call with parsed data
        """
        while self.is_running:
            try:
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    
                    if line:
                        self.stats['packets_received'] += 1
                        parsed_data = self._parse_line(line)
                        
                        if parsed_data:
                            self.stats['packets_parsed'] += 1
                            self.data_queue.put(parsed_data)
                            
                            if callback:
                                callback(parsed_data)
                        else:
                            self.stats['packets_error'] += 1
                else:
                    time.sleep(0.001)  # Small delay to prevent CPU spinning
                    
            except serial.SerialException as e:
                print(f"[Parser] Serial error: {e}")
                time.sleep(1)
                self.connect()
                
            except Exception as e:
                print(f"[Parser] Parse error: {e}")
                self.stats['packets_error'] += 1
    
    def _parse_line(self, line):
        """
        Parse a single line of CSI data
        
        Args:
            line: Raw string from serial
            
        Returns:
            dict: Parsed CSI data or None
        """
        try:
            # Try CSV format first
            if ',' in line and '"' in line:
                return self._parse_csv(line)
            # Try JSON format
            elif line.startswith('{'):
                return self._parse_json(line)
            else:
                return None
        except Exception as e:
            return None
    
    def _parse_csv(self, line):
        """
        Parse CSV format data
        
        Format: timestamp,rssi,channel,secondary_channel,bw,nr,"amplitude","phase"
        """
        try:
            # Extract quoted strings
            matches = re.findall(r'"([^"]*)"', line)
            if len(matches) < 2:
                return None
            
            amplitude_str = matches[0]
            phase_str = matches[1]
            
            # Remove quoted strings and parse remaining CSV
            remaining = line.split('"')[0].rstrip(',') + line.split('"')[-1].lstrip(',')
            parts = remaining.split(',')
            
            if len(parts) < 6:
                return None
            
            # Parse numeric values
            timestamp = int(parts[0])
            rssi = int(parts[1])
            channel = int(parts[2])
            secondary_channel = int(parts[3])
            bw = int(parts[4])
            nr = int(parts[5])
            
            # Parse amplitude and phase arrays
            amplitude = self._parse_array(amplitude_str)
            phase = self._parse_array(phase_str)
            
            self.stats['last_timestamp'] = datetime.now()
            
            return {
                'timestamp': timestamp,
                'rssi': rssi,
                'channel': channel,
                'secondary_channel': secondary_channel,
                'bandwidth': bw,
                'nr': nr,
                'amplitude': amplitude,
                'phase': phase,
                'parsed_time': datetime.now()
            }
            
        except Exception as e:
            return None
    
    def _parse_json(self, line):
        """
        Parse JSON format data
        """
        try:
            data = json.loads(line)
            
            # Parse amplitude and phase arrays
            amplitude = self._parse_array(data.get('amplitude', '[]'))
            phase = self._parse_array(data.get('phase', '[]'))
            
            self.stats['last_timestamp'] = datetime.now()
            
            return {
                'timestamp': data.get('timestamp', 0),
                'rssi': data.get('rssi', 0),
                'channel': data.get('channel', 0),
                'secondary_channel': data.get('secondary_channel', 0),
                'bandwidth': data.get('bw', 20),
                'nr': data.get('nr', 1),
                'amplitude': amplitude,
                'phase': phase,
                'parsed_time': datetime.now()
            }
            
        except json.JSONDecodeError:
            return None
    
    def _parse_array(self, array_str):
        """
        Parse array string like "[1,2,3,...]"
        
        Args:
            array_str: String representation of array
            
        Returns:
            list: Parsed array of integers
        """
        try:
            # Remove brackets and split by comma
            cleaned = array_str.strip('[]')
            if not cleaned:
                return []
            
            return [int(x.strip()) for x in cleaned.split(',') if x.strip()]
        except:
            return []
    
    def get_statistics(self):
        """
        Get parsing statistics
        
        Returns:
            dict: Statistics dictionary
        """
        stats = self.stats.copy()
        if stats['start_time']:
            elapsed = (datetime.now() - stats['start_time']).total_seconds()
            stats['elapsed_seconds'] = elapsed
            stats['packets_per_second'] = stats['packets_received'] / elapsed if elapsed > 0 else 0
        return stats
    
    def read_single(self):
        """
        Read and parse a single CSI packet (blocking)
        
        Returns:
            dict: Parsed CSI data or None
        """
        try:
            if not self.serial_conn or not self.serial_conn.is_open:
                return None
            
            line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
            if line:
                self.stats['packets_received'] += 1
                parsed = self._parse_line(line)
                if parsed:
                    self.stats['packets_parsed'] += 1
                    return parsed
                else:
                    self.stats['packets_error'] += 1
            
            return None
            
        except Exception as e:
            return None


def list_available_ports():
    """List all available serial ports"""
    ports = serial.tools.list_ports.comports()
    print("\nAvailable Serial Ports:")
    print("-" * 50)
    for i, port in enumerate(ports, 1):
        print(f"{i}. {port.device} - {port.description}")
        print(f"   Manufacturer: {port.manufacturer}")
    print("-" * 50)
    return ports


if __name__ == "__main__":
    # Example usage
    print("=== CSI Data Parser Test ===\n")
    
    # List available ports
    ports = list_available_ports()
    
    if ports:
        # Create parser with auto-detected port
        parser = CSIDataParser()
        
        # Connect
        if parser.connect():
            print("\nConnected! Waiting for CSI data...\n")
            
            try:
                # Read and display data
                for _ in range(10):  # Read 10 packets
                    data = parser.read_single()
                    if data:
                        print(f"RSSI: {data['rssi']} dBm | "
                              f"Channel: {data['channel']} | "
                              f"Amplitude samples: {len(data['amplitude'])}")
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("\nStopped by user")
            finally:
                parser.disconnect()
    else:
        print("No serial ports found!")