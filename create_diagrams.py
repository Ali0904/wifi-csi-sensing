import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import os

# Create images directory if it doesn't exist
os.makedirs('images', exist_ok=True)

def create_system_architecture():
    """Create system architecture diagram"""
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.axis('off')
    ax.set_facecolor('#f8f9fa')
    fig.patch.set_facecolor('#f8f9fa')
    
    # Title
    ax.text(7, 7.5, 'WiFi CSI Environmental Sensing System Architecture', 
            fontsize=16, fontweight='bold', ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#3498db', alpha=0.8),
            color='white')
    
    # WiFi Router box
    router_box = FancyBboxPatch((1, 5.5), 2.5, 1.2, 
                               boxstyle="round,pad=0.1", 
                               facecolor='#e74c3c', alpha=0.8)
    ax.add_patch(router_box)
    ax.text(2.25, 6.1, 'WiFi Router\n(2.4 GHz)', fontsize=10, 
            ha='center', va='center', fontweight='bold', color='white')
    
    # ESP32 box
    esp32_box = FancyBboxPatch((5, 5.5), 2.5, 1.2, 
                              boxstyle="round,pad=0.1", 
                              facecolor='#2ecc71', alpha=0.8)
    ax.add_patch(esp32_box)
    ax.text(6.25, 6.1, 'ESP32-S3\n(CSI Capture)', fontsize=10, 
            ha='center', va='center', fontweight='bold', color='white')
    
    # Laptop box
    laptop_box = FancyBboxPatch((9, 5.5), 2.5, 1.2, 
                               boxstyle="round,pad=0.1", 
                               facecolor='#9b59b6', alpha=0.8)
    ax.add_patch(laptop_box)
    ax.text(10.25, 6.1, 'Laptop/PC\n(Processing)', fontsize=10, 
            ha='center', va='center', fontweight='bold', color='white')
    
    # Arrows
    arrow1 = FancyArrowPatch((3.5, 6.1), (5, 6.1), 
                            arrowstyle='->', mutation_scale=20, 
                            color='#2c3e50', linewidth=2)
    ax.add_patch(arrow1)
    ax.text(4.25, 6.4, 'WiFi Signal', fontsize=8, ha='center', color='#2c3e50')
    
    arrow2 = FancyArrowPatch((7.5, 6.1), (9, 6.1), 
                            arrowstyle='->', mutation_scale=20, 
                            color='#2c3e50', linewidth=2)
    ax.add_patch(arrow2)
    ax.text(8.25, 6.4, 'USB Serial', fontsize=8, ha='center', color='#2c3e50')
    
    # Wall/Obstacle
    wall_box = FancyBboxPatch((3.8, 4.5), 0.4, 1.5, 
                             boxstyle="round,pad=0.05", 
                             facecolor='#95a5a6', alpha=0.8)
    ax.add_patch(wall_box)
    ax.text(4, 4.0, 'Wall', fontsize=8, ha='center', color='#2c3e50')
    
    # Signal waves through wall
    for i in range(3):
        y = 5.5 + i * 0.2
        ax.annotate('', xy=(5, y), xytext=(3.5, y),
                   arrowprops=dict(arrowstyle='->', color='#e74c3c', alpha=0.3-i*0.1))
    
    # Processing pipeline boxes
    pipeline_y = 3.0
    
    # Data Parser
    parser_box = FancyBboxPatch((1, pipeline_y), 2, 0.8, 
                               boxstyle="round,pad=0.1", 
                               facecolor='#f39c12', alpha=0.8)
    ax.add_patch(parser_box)
    ax.text(2, pipeline_y+0.4, 'Data Parser', fontsize=9, 
            ha='center', va='center', fontweight='bold', color='white')
    
    # Preprocessor
    preproc_box = FancyBboxPatch((4, pipeline_y), 2, 0.8, 
                                boxstyle="round,pad=0.1", 
                                facecolor='#f39c12', alpha=0.8)
    ax.add_patch(preproc_box)
    ax.text(5, pipeline_y+0.4, 'Preprocessor', fontsize=9, 
            ha='center', va='center', fontweight='bold', color='white')
    
    # Feature Extractor
    feature_box = FancyBboxPatch((7, pipeline_y), 2, 0.8, 
                                boxstyle="round,pad=0.1", 
                                facecolor='#f39c12', alpha=0.8)
    ax.add_patch(feature_box)
    ax.text(8, pipeline_y+0.4, 'Feature Extractor', fontsize=9, 
            ha='center', va='center', fontweight='bold', color='white')
    
    # ML Classifier
    ml_box = FancyBboxPatch((10, pipeline_y), 2, 0.8, 
                           boxstyle="round,pad=0.1", 
                           facecolor='#f39c12', alpha=0.8)
    ax.add_patch(ml_box)
    ax.text(11, pipeline_y+0.4, 'ML Classifier', fontsize=9, 
            ha='center', va='center', fontweight='bold', color='white')
    
    # Arrows in pipeline
    for x in [3, 6, 9]:
        arrow = FancyArrowPatch((x, pipeline_y+0.4), (x+1, pipeline_y+0.4), 
                               arrowstyle='->', mutation_scale=15, 
                               color='#2c3e50', linewidth=1.5)
        ax.add_patch(arrow)
    
    # Dashboard
    dashboard_box = FancyBboxPatch((4, 1.5), 6, 1, 
                                  boxstyle="round,pad=0.1", 
                                  facecolor='#1abc9c', alpha=0.8)
    ax.add_patch(dashboard_box)
    ax.text(7, 2, 'Real-time Dashboard\n(Activity Detection + Wall Mapping)', 
            fontsize=10, ha='center', va='center', fontweight='bold', color='white')
    
    # Arrow from ML to Dashboard
    arrow_dashboard = FancyArrowPatch((11, pipeline_y), (7, 2.5), 
                                     arrowstyle='->', mutation_scale=20, 
                                     color='#2c3e50', linewidth=2)
    ax.add_patch(arrow_dashboard)
    
    plt.tight_layout()
    plt.savefig('images/system_architecture.png', dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()

def create_wifi_propagation():
    """Create WiFi signal propagation diagram"""
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis('off')
    ax.set_facecolor('#f8f9fa')
    fig.patch.set_facecolor('#f8f9fa')
    
    # Title
    ax.text(6, 5.5, 'WiFi Signal Propagation Through Walls', 
            fontsize=14, fontweight='bold', ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#3498db', alpha=0.8),
            color='white')
    
    # Router
    router = FancyBboxPatch((0.5, 4), 1.5, 1, 
                           boxstyle="round,pad=0.1", 
                           facecolor='#e74c3c', alpha=0.8)
    ax.add_patch(router)
    ax.text(1.25, 4.5, 'WiFi\nRouter', fontsize=10, 
            ha='center', va='center', fontweight='bold', color='white')
    
    # Signal waves (strong)
    for i in range(5):
        x = 2.5 + i * 0.3
        ax.plot([x, x], [4.2, 4.8], color='#e74c3c', linewidth=3-i*0.5, alpha=0.8-i*0.15)
    
    # Wall
    wall = FancyBboxPatch((4, 3), 0.5, 2, 
                         boxstyle="round,pad=0.05", 
                         facecolor='#95a5a6', alpha=0.8)
    ax.add_patch(wall)
    ax.text(4.25, 2.5, 'Wall\n(Attenuation)', fontsize=9, 
            ha='center', va='center', color='#2c3e50')
    
    # Signal waves (weaker after wall)
    for i in range(5):
        x = 5 + i * 0.3
        ax.plot([x, x], [4.2, 4.8], color='#e74c3c', linewidth=(2-i*0.3), alpha=0.6-i*0.1)
    
    # ESP32
    esp32 = FancyBboxPatch((7, 4), 1.5, 1, 
                          boxstyle="round,pad=0.1", 
                          facecolor='#2ecc71', alpha=0.8)
    ax.add_patch(esp32)
    ax.text(7.75, 4.5, 'ESP32\n(Receiver)', fontsize=10, 
            ha='center', va='center', fontweight='bold', color='white')
    
    # CSI Data visualization
    ax.text(6, 3.5, 'CSI Amplitude\nHigh → Low', fontsize=9, 
            ha='center', va='center', color='#2c3e50')
    
    # Bar chart showing signal strength
    x_pos = [8.5, 9.5, 10.5, 11.5]
    heights = [0.8, 0.6, 0.4, 0.3]
    colors = ['#2ecc71', '#f39c12', '#e74c3c', '#c0392b']
    
    for x, h, c in zip(x_pos, heights, colors):
        ax.bar(x, h, 0.6, color=c, alpha=0.8)
    
    ax.text(10, 2.5, 'Signal Strength\n(Through Wall)', fontsize=9, 
            ha='center', va='center', color='#2c3e50')
    
    plt.tight_layout()
    plt.savefig('images/wifi_propagation.png', dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()

def create_csi_waveform():
    """Create CSI waveform visualization"""
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle('CSI Data Visualization', fontsize=14, fontweight='bold')
    
    # Generate sample CSI data
    subcarriers = np.arange(64)
    amplitude_empty = 20 + 5 * np.random.randn(64)
    amplitude_walking = 25 + 10 * np.sin(subcarriers * 0.2) + 8 * np.random.randn(64)
    
    # Plot 1: CSI Amplitude
    ax1 = axes[0, 0]
    ax1.plot(subcarriers, amplitude_empty, 'b-', label='Empty Room', linewidth=2)
    ax1.plot(subcarriers, amplitude_walking, 'r-', label='Walking', linewidth=2)
    ax1.set_xlabel('Subcarrier Index')
    ax1.set_ylabel('Amplitude')
    ax1.set_title('CSI Amplitude Across Subcarriers')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: RSSI over time
    ax2 = axes[0, 1]
    time = np.arange(100)
    rssi = -45 + 5 * np.sin(time * 0.1) + 2 * np.random.randn(100)
    ax2.plot(time, rssi, 'g-', linewidth=2)
    ax2.set_xlabel('Time (samples)')
    ax2.set_ylabel('RSSI (dBm)')
    ax2.set_title('RSSI Over Time')
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Heatmap
    ax3 = axes[1, 0]
    heatmap_data = np.random.randn(20, 64)
    im = ax3.imshow(heatmap_data, aspect='auto', cmap='viridis')
    ax3.set_xlabel('Subcarrier Index')
    ax3.set_ylabel('Time (samples)')
    ax3.set_title('CSI Heatmap')
    plt.colorbar(im, ax=ax3)
    
    # Plot 4: Phase plot
    ax4 = axes[1, 1]
    phase = np.angle(np.exp(1j * subcarriers * 0.1)) + 0.2 * np.random.randn(64)
    ax4.scatter(subcarriers, phase, c=phase, cmap='hsv', s=50)
    ax4.set_xlabel('Subcarrier Index')
    ax4.set_ylabel('Phase (radians)')
    ax4.set_title('CSI Phase Distribution')
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('images/csi_waveform.png', dpi=150, bbox_inches='tight')
    plt.close()

def create_wall_detection():
    """Create wall detection concept diagram"""
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis('off')
    ax.set_facecolor('#f8f9fa')
    fig.patch.set_facecolor('#f8f9fa')
    
    # Title
    ax.text(6, 5.5, 'WiFi CSI Wall Detection Concept', 
            fontsize=14, fontweight='bold', ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#3498db', alpha=0.8),
            color='white')
    
    # Room layout
    room = FancyBboxPatch((1, 1), 10, 4, 
                         boxstyle="round,pad=0.1", 
                         facecolor='#ecf0f1', alpha=0.5)
    ax.add_patch(room)
    ax.text(6, 5.2, 'Room Layout', fontsize=10, ha='center', color='#2c3e50')
    
    # Wall
    wall = FancyBboxPatch((5, 1), 0.5, 4, 
                         boxstyle="round,pad=0.05", 
                         facecolor='#95a5a6', alpha=0.8)
    ax.add_patch(wall)
    ax.text(5.25, 0.5, 'Wall', fontsize=10, ha='center', color='#2c3e50')
    
    # Router
    router = FancyBboxPatch((1.5, 3), 1.5, 1, 
                           boxstyle="round,pad=0.1", 
                           facecolor='#e74c3c', alpha=0.8)
    ax.add_patch(router)
    ax.text(2.25, 3.5, 'Router', fontsize=10, 
            ha='center', va='center', fontweight='bold', color='white')
    
    # ESP32
    esp32 = FancyBboxPatch((9, 3), 1.5, 1, 
                          boxstyle="round,pad=0.1", 
                          facecolor='#2ecc71', alpha=0.8)
    ax.add_patch(esp32)
    ax.text(9.75, 3.5, 'ESP32', fontsize=10, 
            ha='center', va='center', fontweight='bold', color='white')
    
    # Signal paths
    # Direct line of sight
    ax.annotate('', xy=(5, 3.5), xytext=(3, 3.5),
               arrowprops=dict(arrowstyle='->', color='#3498db', linewidth=2, alpha=0.7))
    ax.annotate('', xy=(9, 3.5), xytext=(5.5, 3.5),
               arrowprops=dict(arrowstyle='->', color='#3498db', linewidth=2, alpha=0.7))
    
    # Reflected paths
    ax.annotate('', xy=(5, 2), xytext=(3, 3),
               arrowprops=dict(arrowstyle='->', color='#e67e22', linewidth=1.5, alpha=0.6))
    ax.annotate('', xy=(9, 2), xytext=(5.5, 3),
               arrowprops=dict(arrowstyle='->', color='#e67e22', linewidth=1.5, alpha=0.6))
    
    # Labels
    ax.text(4, 3.7, 'Direct Path', fontsize=8, ha='center', color='#3498db')
    ax.text(4, 2.3, 'Reflected Path', fontsize=8, ha='center', color='#e67e22')
    
    # Detection zones
    zone1 = FancyBboxPatch((2, 1.5), 2.5, 1, 
                          boxstyle="round,pad=0.1", 
                          facecolor='#2ecc71', alpha=0.3)
    ax.add_patch(zone1)
    ax.text(3.25, 2, 'Zone 1\n(No Wall)', fontsize=8, ha='center', color='#2c3e50')
    
    zone2 = FancyBboxPatch((6.5, 1.5), 2.5, 1, 
                          boxstyle="round,pad=0.1", 
                          facecolor='#e74c3c', alpha=0.3)
    ax.add_patch(zone2)
    ax.text(7.75, 2, 'Zone 2\n(Through Wall)', fontsize=8, ha='center', color='#2c3e50')
    
    # Signal strength indicators
    ax.text(4, 4.5, 'Signal: -35 dBm', fontsize=9, ha='center', 
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#2ecc71', alpha=0.7))
    ax.text(8, 4.5, 'Signal: -55 dBm', fontsize=9, ha='center', 
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#e74c3c', alpha=0.7))
    
    plt.tight_layout()
    plt.savefig('images/wall_detection.png', dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()

def create_ml_pipeline():
    """Create ML pipeline diagram"""
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 6)
    ax.axis('off')
    ax.set_facecolor('#f8f9fa')
    fig.patch.set_facecolor('#f8f9fa')
    
    # Title
    ax.text(7, 5.5, 'Machine Learning Classification Pipeline', 
            fontsize=14, fontweight='bold', ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#3498db', alpha=0.8),
            color='white')
    
    # Pipeline stages
    stages = [
        ('CSI Data\n(Raw)', 1, '#e74c3c'),
        ('Preprocessing\n(Clean)', 3.5, '#f39c12'),
        ('Feature\nExtraction', 6, '#2ecc71'),
        ('ML Model\n(Classify)', 8.5, '#9b59b6'),
        ('Prediction\n(Result)', 11, '#1abc9c')
    ]
    
    for label, x, color in stages:
        box = FancyBboxPatch((x, 3.5), 2, 1.2, 
                            boxstyle="round,pad=0.1", 
                            facecolor=color, alpha=0.8)
        ax.add_patch(box)
        ax.text(x+1, 4.1, label, fontsize=10, 
                ha='center', va='center', fontweight='bold', color='white')
    
    # Arrows between stages
    for i in range(len(stages)-1):
        x_start = stages[i][1] + 2
        x_end = stages[i+1][1]
        arrow = FancyArrowPatch((x_start, 4.1), (x_end, 4.1), 
                               arrowstyle='->', mutation_scale=20, 
                               color='#2c3e50', linewidth=2)
        ax.add_patch(arrow)
    
    # Data flow annotations
    annotations = [
        (2, 4.5, 'Amplitude\nPhase'),
        (4.5, 4.5, 'Filtered\nNormalized'),
        (7, 4.5, 'Time/Freq\nDomain'),
        (9.5, 4.5, 'RF/SVM\nCNN/LSTM'),
    ]
    
    for x, y, text in annotations:
        ax.text(x, y, text, fontsize=8, ha='center', color='#2c3e50', style='italic')
    
    # Training data
    ax.text(7, 2, 'Training Data: Labeled CSI Datasets', fontsize=10, 
            ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#34495e', alpha=0.7),
            color='white')
    
    # Model output
    outputs = ['Walking', 'Sitting', 'Standing', 'Empty', 'Door Open']
    for i, output in enumerate(outputs):
        x = 8 + i * 1.2
        ax.text(x, 1.5, output, fontsize=8, ha='center', 
                bbox=dict(boxstyle='round,pad=0.2', facecolor='#2ecc71', alpha=0.7))
    
    ax.text(10, 1, 'Output Classes', fontsize=9, ha='center', color='#2c3e50')
    
    plt.tight_layout()
    plt.savefig('images/ml_pipeline.png', dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()

if __name__ == '__main__':
    print("Generating diagrams...")
    create_system_architecture()
    print("[OK] System architecture diagram created")
    create_wifi_propagation()
    print("[OK] WiFi propagation diagram created")
    create_csi_waveform()
    print("[OK] CSI waveform diagram created")
    create_wall_detection()
    print("[OK] Wall detection diagram created")
    create_ml_pipeline()
    print("[OK] ML pipeline diagram created")
    print("All diagrams generated successfully!")