"""
CSI Data Preprocessor Module
Handles data cleaning, filtering, and normalization

@author: Ali Haider
@date: July 2026
"""

import numpy as np
from collections import deque


class CSIPreprocessor:
    """
    Preprocess CSI data for analysis and machine learning
    """
    
    def __init__(self, window_size=5, filter_type='moving_average'):
        """
        Initialize preprocessor
        
        Args:
            window_size: Size of moving average window
            filter_type: Type of filter ('moving_average', 'median', 'none')
        """
        self.window_size = window_size
        self.filter_type = filter_type
        
        # Buffer for temporal filtering
        self.amplitude_buffer = deque(maxlen=window_size)
        self.phase_buffer = deque(maxlen=window_size)
        
        # Normalization parameters
        self.amplitude_min = None
        self.amplitude_max = None
        self.phase_min = None
        self.phase_max = None
        
        # Statistics
        self.stats = {
            'packets_processed': 0,
            'packets_filtered': 0,
            'packets_normalized': 0
        }
        
        print(f"[Preprocessor] Initialized - Window: {window_size}, Filter: {filter_type}")
    
    def process(self, data):
        """
        Process a single CSI data packet
        
        Args:
            data: Raw CSI data dictionary
            
        Returns:
            dict: Processed data dictionary
        """
        processed = data.copy()
        
        # Step 1: Remove invalid packets
        if not self._validate_data(data):
            return None
        
        # Step 2: Apply filtering
        if self.filter_type != 'none':
            processed['amplitude'] = self._apply_filter(data['amplitude'])
            processed['phase'] = self._apply_filter(data['phase'])
        
        # Step 3: Normalize if needed
        if self.amplitude_min is not None:
            processed['amplitude'] = self._normalize(data['amplitude'], 
                                                     self.amplitude_min, 
                                                     self.amplitude_max)
            processed['phase'] = self._normalize(data['phase'],
                                                 self.phase_min,
                                                 self.phase_max)
        
        self.stats['packets_processed'] += 1
        
        return processed
    
    def process_batch(self, data_list):
        """
        Process a batch of CSI data packets
        
        Args:
            data_list: List of raw CSI data dictionaries
            
        Returns:
            list: List of processed data dictionaries
        """
        processed_list = []
        
        for data in data_list:
            processed = self.process(data)
            if processed is not None:
                processed_list.append(processed)
        
        return processed_list
    
    def _validate_data(self, data):
        """
        Validate CSI data
        
        Args:
            data: CSI data dictionary
            
        Returns:
            bool: True if valid, False otherwise
        """
        # Check if amplitude exists and has data
        if 'amplitude' not in data or not data['amplitude']:
            return False
        
        # Check if phase exists
        if 'phase' not in data:
            return False
        
        # Check amplitude values
        amplitude = np.array(data['amplitude'])
        if np.any(np.isnan(amplitude)) or np.any(np.isinf(amplitude)):
            return False
        
        return True
    
    def _apply_filter(self, data):
        """
        Apply filter to data
        
        Args:
            data: Input data array
            
        Returns:
            numpy.ndarray: Filtered data
        """
        data_array = np.array(data, dtype=np.float64)
        
        if self.filter_type == 'moving_average':
            return self._moving_average(data_array)
        elif self.filter_type == 'median':
            return self._median_filter(data_array)
        else:
            return data_array
    
    def _moving_average(self, data):
        """
        Apply moving average filter
        
        Args:
            data: Input data array
            
        Returns:
            numpy.ndarray: Filtered data
        """
        if len(data) < self.window_size:
            return data
        
        # Calculate moving average
        kernel = np.ones(self.window_size) / self.window_size
        filtered = np.convolve(data, kernel, mode='valid')
        
        self.stats['packets_filtered'] += 1
        
        return filtered
    
    def _median_filter(self, data):
        """
        Apply median filter
        
        Args:
            data: Input data array
            
        Returns:
            numpy.ndarray: Filtered data
        """
        if len(data) < self.window_size:
            return data
        
        # Apply median filter
        filtered = np.copy(data)
        half_window = self.window_size // 2
        
        for i in range(half_window, len(data) - half_window):
            window = data[i - half_window:i + half_window + 1]
            filtered[i] = np.median(window)
        
        self.stats['packets_filtered'] += 1
        
        return filtered
    
    def _normalize(self, data, min_val, max_val):
        """
        Normalize data to 0-1 range
        
        Args:
            data: Input data array
            min_val: Minimum value
            max_val: Maximum value
            
        Returns:
            numpy.ndarray: Normalized data
        """
        data_array = np.array(data, dtype=np.float64)
        
        if max_val - min_val == 0:
            return np.zeros_like(data_array)
        
        normalized = (data_array - min_val) / (max_val - min_val)
        
        # Clip to 0-1 range
        normalized = np.clip(normalized, 0, 1)
        
        self.stats['packets_normalized'] += 1
        
        return normalized
    
    def update_normalization_params(self, data_list):
        """
        Update normalization parameters from data batch
        
        Args:
            data_list: List of CSI data dictionaries
        """
        all_amplitudes = []
        all_phases = []
        
        for data in data_list:
            if data['amplitude'] is not None:
                all_amplitudes.extend(data['amplitude'])
            if data['phase'] is not None:
                all_phases.extend(data['phase'])
        
        if all_amplitudes:
            self.amplitude_min = np.min(all_amplitudes)
            self.amplitude_max = np.max(all_amplitudes)
        
        if all_phases:
            self.phase_min = np.min(all_phases)
            self.phase_max = np.max(all_phases)
        
        print(f"[Preprocessor] Updated normalization params")
        print(f"  Amplitude: [{self.amplitude_min}, {self.amplitude_max}]")
        print(f"  Phase: [{self.phase_min}, {self.phase_max}]")
    
    def remove_outliers(self, data, threshold=3.0):
        """
        Remove outliers using z-score method
        
        Args:
            data: Input data array
            threshold: Z-score threshold
            
        Returns:
            numpy.ndarray: Data without outliers
        """
        data_array = np.array(data, dtype=np.float64)
        
        if len(data_array) < 3:
            return data_array
        
        # Calculate z-scores
        mean = np.mean(data_array)
        std = np.std(data_array)
        
        if std == 0:
            return data_array
        
        z_scores = np.abs((data_array - mean) / std)
        
        # Remove outliers
        mask = z_scores < threshold
        cleaned = data_array[mask]
        
        return cleaned
    
    def interpolate_missing(self, data):
        """
        Interpolate missing values (NaN)
        
        Args:
            data: Input data array
            
        Returns:
            numpy.ndarray: Data with interpolated values
        """
        data_array = np.array(data, dtype=np.float64)
        
        # Find NaN indices
        nan_mask = np.isnan(data_array)
        
        if not np.any(nan_mask):
            return data_array
        
        # Interpolate
        valid_indices = np.where(~nan_mask)[0]
        nan_indices = np.where(nan_mask)[0]
        
        if len(valid_indices) == 0:
            return np.zeros_like(data_array)
        
        # Linear interpolation
        interpolated = np.interp(nan_indices, valid_indices, data_array[valid_indices])
        data_array[nan_indices] = interpolated
        
        return data_array
    
    def get_statistics(self):
        """Get preprocessing statistics"""
        return self.stats.copy()


class CSIAdvancedPreprocessor(CSIPreprocessor):
    """
    Advanced preprocessing with additional techniques
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Kalman filter parameters
        self.kalman_gain = 0.1
        self.estimated_value = None
        self.estimated_error = 1.0
        
        # Exponential moving average
        self.ema_alpha = 0.3
        self.ema_value = None
    
    def kalman_filter(self, measurement):
        """
        Apply Kalman filter to single measurement
        
        Args:
            measurement: New measurement value
            
        Returns:
            float: Filtered value
        """
        if self.estimated_value is None:
            self.estimated_value = measurement
            return measurement
        
        # Prediction
        predicted_value = self.estimated_value
        predicted_error = self.estimated_error + 0.1  # Process noise
        
        # Update
        kalman_gain = predicted_error / (predicted_error + 1.0)  # Measurement noise
        self.estimated_value = predicted_value + kalman_gain * (measurement - predicted_value)
        self.estimated_error = (1 - kalman_gain) * predicted_error
        
        return self.estimated_value
    
    def exponential_moving_average(self, measurement):
        """
        Apply exponential moving average
        
        Args:
            measurement: New measurement value
            
        Returns:
            float: Filtered value
        """
        if self.ema_value is None:
            self.ema_value = measurement
            return measurement
        
        self.ema_value = self.ema_alpha * measurement + (1 - self.ema_alpha) * self.ema_value
        
        return self.ema_value
    
    def butterworth_filter(self, data, cutoff_freq, sample_freq, order=4):
        """
        Apply Butterworth low-pass filter
        
        Args:
            data: Input data array
            cutoff_freq: Cutoff frequency
            sample_freq: Sampling frequency
            order: Filter order
            
        Returns:
            numpy.ndarray: Filtered data
        """
        from scipy.signal import butter, filtfilt
        
        nyquist = sample_freq / 2
        normalized_cutoff = cutoff_freq / nyquist
        
        # Design filter
        b, a = butter(order, normalized_cutoff, btype='low')
        
        # Apply filter
        filtered = filtfilt(b, a, data)
        
        return filtered


if __name__ == "__main__":
    # Example usage
    print("=== CSI Preprocessor Test ===\n")
    
    # Create preprocessor
    preprocessor = CSIPreprocessor(window_size=5, filter_type='moving_average')
    
    # Generate test data
    test_data = {
        'timestamp': 1234567890,
        'rssi': -45,
        'channel': 6,
        'amplitude': list(np.random.randint(0, 100, 64)),
        'phase': list(np.random.uniform(-np.pi, np.pi, 64))
    }
    
    print(f"Input amplitude samples: {len(test_data['amplitude'])}")
    
    # Process data
    processed = preprocessor.process(test_data)
    
    if processed:
        print(f"Output amplitude samples: {len(processed['amplitude'])}")
        print(f"Amplitude range: [{np.min(processed['amplitude']):.2f}, {np.max(processed['amplitude']):.2f}]")
    
    print(f"\nStatistics: {preprocessor.get_statistics()}")