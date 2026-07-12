"""
WiFi CSI Environmental Sensing System - Main Application

This application receives, processes, and visualizes CSI data from ESP32-S3
for environmental sensing and wall detection applications.

@author: Ali Haider
@date: July 2026
@version: 1.0.0
"""

import os
import sys
import time
import argparse
import threading
from datetime import datetime
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_parser import CSIDataParser, list_available_ports
from preprocessor import CSIPreprocessor
from feature_extractor import CSIFeatureExtractor
from ml_models import CSIActivityClassifier
from visualizer import CSIVisualizer


class WiFiCSISystem:
    """
    Main WiFi CSI Environmental Sensing System
    """
    
    def __init__(self, port=None, baudrate=115200):
        """
        Initialize the WiFi CSI System
        
        Args:
            port: Serial port (auto-detect if None)
            baudrate: Serial baudrate
        """
        print("=" * 60)
        print("WiFi CSI Environmental Sensing System")
        print("Version: 1.0.0")
        print("Author: Ali Haider")
        print("=" * 60)
        
        # Initialize components
        self.parser = CSIDataParser(port=port, baudrate=baudrate)
        self.preprocessor = CSIPreprocessor()
        self.feature_extractor = CSIFeatureExtractor()
        self.classifier = CSIActivityClassifier()
        self.visualizer = CSIVisualizer()
        
        # Data storage
        self.raw_data = []
        self.processed_data = []
        self.predictions = []
        
        # Configuration
        self.config = {
            'auto_preprocess': True,
            'auto_extract_features': True,
            'auto_classify': True,
            'visualization_enabled': True,
            'save_raw_data': True,
            'max_buffer_size': 10000
        }
        
        # State
        self.is_running = False
        self.start_time = None
        
        print("[System] Initialized successfully")
    
    def start(self):
        """Start the WiFi CSI system"""
        print("\n[System] Starting...")
        
        # Connect to ESP32
        if not self.parser.connect():
            print("[System] ERROR: Failed to connect to ESP32")
            return False
        
        # Start parsing
        self.parser.start_parsing(callback=self._on_data_received)
        
        # Start visualization if enabled
        if self.config['visualization_enabled']:
            self.visualizer.start()
        
        self.is_running = True
        self.start_time = datetime.now()
        
        print("[System] Started successfully")
        print("[System] Press Ctrl+C to stop\n")
        
        return True
    
    def stop(self):
        """Stop the WiFi CSI system"""
        print("\n[System] Stopping...")
        
        self.is_running = False
        self.parser.stop_parsing()
        self.visualizer.stop()
        self.parser.disconnect()
        
        # Save data if enabled
        if self.config['save_raw_data'] and self.raw_data:
            self._save_session_data()
        
        # Print statistics
        self._print_statistics()
        
        print("[System] Stopped")
    
    def _on_data_received(self, data):
        """
        Callback for received CSI data
        
        Args:
            data: Parsed CSI data dictionary
        """
        # Store raw data
        self.raw_data.append(data)
        
        # Limit buffer size
        if len(self.raw_data) > self.config['max_buffer_size']:
            self.raw_data.pop(0)
        
        # Preprocess if enabled
        if self.config['auto_preprocess']:
            processed = self.preprocessor.process(data)
            self.processed_data.append(processed)
        else:
            processed = data
        
        # Extract features if enabled
        if self.config['auto_extract_features']:
            features = self.feature_extractor.extract(processed)
        else:
            features = None
        
        # Classify if enabled
        if self.config['auto_classify'] and features:
            prediction = self.classifier.predict(features)
            self.predictions.append(prediction)
            
            # Update visualizer
            if self.config['visualization_enabled']:
                self.visualizer.update(data, prediction)
    
    def _save_session_data(self):
        """Save session data to CSV file"""
        import pandas as pd
        
        # Create data directory if it doesn't exist
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = data_dir / f"csi_session_{timestamp}.csv"
        
        # Convert to DataFrame
        df_data = []
        for data in self.raw_data:
            df_data.append({
                'timestamp': data['timestamp'],
                'rssi': data['rssi'],
                'channel': data['channel'],
                'amplitude': str(data['amplitude']),
                'phase': str(data['phase'])
            })
        
        df = pd.DataFrame(df_data)
        df.to_csv(filename, index=False)
        
        print(f"[System] Session data saved to {filename}")
    
    def _print_statistics(self):
        """Print session statistics"""
        print("\n" + "=" * 60)
        print("Session Statistics")
        print("=" * 60)
        
        # Parser statistics
        parser_stats = self.parser.get_statistics()
        print(f"Packets received: {parser_stats['packets_received']}")
        print(f"Packets parsed: {parser_stats['packets_parsed']}")
        print(f"Parse errors: {parser_stats['packets_error']}")
        
        if 'elapsed_seconds' in parser_stats:
            print(f"Duration: {parser_stats['elapsed_seconds']:.1f} seconds")
            print(f"Packets/second: {parser_stats['packets_per_second']:.1f}")
        
        # System statistics
        print(f"\nRaw data points: {len(self.raw_data)}")
        print(f"Processed data points: {len(self.processed_data)}")
        print(f"Predictions made: {len(self.predictions)}")
        
        # Classification statistics
        if self.predictions:
            from collections import Counter
            pred_counts = Counter([p['prediction'] for p in self.predictions])
            print("\nPredictions breakdown:")
            for pred, count in pred_counts.most_common():
                print(f"  {pred}: {count} ({count/len(self.predictions)*100:.1f}%)")
        
        print("=" * 60)
    
    def manual_collect(self, duration=30, label="unknown"):
        """
        Manually collect labeled data
        
        Args:
            duration: Collection duration in seconds
            label: Label for the collected data
        """
        print(f"\n[Collection] Starting {duration}s collection for '{label}'")
        print("[Collection] Press Enter when ready...")
        input()
        
        # Clear buffers
        self.raw_data.clear()
        self.processed_data.clear()
        self.predictions.clear()
        
        # Collect data
        start_time = time.time()
        while time.time() - start_time < duration:
            elapsed = time.time() - start_time
            remaining = duration - elapsed
            print(f"\r[Collection] {remaining:.1f}s remaining", end="", flush=True)
            time.sleep(0.1)
        
        print(f"\n[Collection] Complete! Collected {len(self.raw_data)} packets")
        
        # Save labeled data
        self._save_labeled_data(label)
    
    def _save_labeled_data(self, label):
        """Save labeled data to dataset directory"""
        import pandas as pd
        
        # Create dataset directory
        dataset_dir = Path("datasets") / label
        dataset_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = dataset_dir / f"{label}_{timestamp}.csv"
        
        # Save data
        df_data = []
        for data in self.raw_data:
            df_data.append({
                'timestamp': data['timestamp'],
                'rssi': data['rssi'],
                'channel': data['channel'],
                'amplitude': str(data['amplitude']),
                'phase': str(data['phase']),
                'label': label
            })
        
        df = pd.DataFrame(df_data)
        df.to_csv(filename, index=False)
        
        print(f"[Collection] Data saved to {filename}")
    
    def test_connection(self):
        """Test ESP32 connection and CSI capture"""
        print("\n[Test] Testing connection...")
        
        if not self.parser.connect():
            print("[Test] FAILED: Could not connect to ESP32")
            return False
        
        print("[Test] Connected! Waiting for CSI data...")
        
        # Wait for data
        data_received = False
        start_time = time.time()
        timeout = 10  # seconds
        
        while time.time() - start_time < timeout:
            data = self.parser.read_single()
            if data:
                data_received = True
                print(f"\n[Test] SUCCESS: Received CSI data")
                print(f"  RSSI: {data['rssi']} dBm")
                print(f"  Channel: {data['channel']}")
                print(f"  Amplitude samples: {len(data['amplitude'])}")
                print(f"  Phase samples: {len(data['phase'])}")
                break
            time.sleep(0.1)
        
        self.parser.disconnect()
        
        if not data_received:
            print(f"\n[Test] FAILED: No data received within {timeout}s")
            print("[Test] Check:")
            print("  1. ESP32 is powered and connected")
            print("  2. Correct serial port selected")
            print("  3. Firmware is running")
            print("  4. WiFi is connected")
        
        return data_received


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="WiFi CSI Environmental Sensing System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Auto-detect port and start
  python main.py --port COM3        # Use specific port
  python main.py --test             # Test connection only
  python main.py --collect walking  # Collect labeled data
        """
    )
    
    parser.add_argument('--port', '-p', type=str, default=None,
                       help='Serial port (auto-detect if not specified)')
    parser.add_argument('--baudrate', '-b', type=int, default=115200,
                       help='Serial baudrate (default: 115200)')
    parser.add_argument('--test', '-t', action='store_true',
                       help='Test connection only')
    parser.add_argument('--collect', '-c', type=str, default=None,
                       help='Collect labeled data (specify label)')
    parser.add_argument('--duration', '-d', type=int, default=30,
                       help='Collection duration in seconds (default: 30)')
    parser.add_argument('--list-ports', '-l', action='store_true',
                       help='List available serial ports')
    parser.add_argument('--no-viz', action='store_true',
                       help='Disable visualization')
    
    args = parser.parse_args()
    
    # List ports if requested
    if args.list_ports:
        list_available_ports()
        return
    
    # Create system
    system = WiFiCSISystem(port=args.port, baudrate=args.baudrate)
    
    # Disable visualization if requested
    if args.no_viz:
        system.config['visualization_enabled'] = False
    
    # Test mode
    if args.test:
        system.test_connection()
        return
    
    # Collection mode
    if args.collect:
        if system.start():
            system.manual_collect(duration=args.duration, label=args.collect)
            system.stop()
        return
    
    # Normal mode
    try:
        if system.start():
            # Wait for user to stop
            while system.is_running:
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        system.stop()


if __name__ == "__main__":
    main()