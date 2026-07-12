/**
 * @file config.h
 * @brief Configuration Header for WiFi CSI Environmental Sensing System
 * 
 * Contains all configuration parameters and constants
 */

#ifndef CONFIG_H
#define CONFIG_H

/* ─── WiFi Configuration ──────────────────────────────────────────────────── */

// WiFi Credentials - CHANGE THESE TO YOUR WIFI
#define WIFI_SSID               "Haider-2.4GHz"
#define WIFI_PASSWORD           "Ali@1234"

// WiFi Settings
#define WIFI_CHANNEL            6
#define WIFI_MAX_RETRY          10
#define WIFI_CONNECT_TIMEOUT_MS 10000

/* ─── CSI Configuration ───────────────────────────────────────────────────── */

// CSI Buffer Settings
#define CSI_BUF_SIZE            128
#define CSI_MAX_SUBCARRIERS     64

// CSI Task Settings
#define CSI_TASK_STACK_SIZE     8192
#define CSI_TASK_PRIORITY       5

// CSI Collection Settings
#define CSI_COLLECTION_INTERVAL_MS  10  // 100 Hz collection rate

/* ─── Serial Configuration ────────────────────────────────────────────────── */

// Serial Settings
#define SERIAL_BAUDRATE         115200
#define SERIAL_TASK_STACK_SIZE  8192
#define SERIAL_TASK_PRIORITY    4

// Data Format (0 = CSV, 1 = JSON)
#define DATA_FORMAT_CSV         0
#define DATA_FORMAT_JSON        1
#define DATA_FORMAT             DATA_FORMAT_CSV

/* ─── Queue Configuration ─────────────────────────────────────────────────── */

// Queue Settings
#define CSI_QUEUE_SIZE          100

/* ─── Task Configuration ──────────────────────────────────────────────────── */

// Status Task Settings
#define STATUS_TASK_STACK_SIZE  2048
#define STATUS_TASK_PRIORITY    1
#define STATUS_INTERVAL_MS      5000  // Status print interval

/* ─── Pin Configuration ───────────────────────────────────────────────────── */

// Onboard LED (for status indication)
#define LED_GPIO                GPIO_NUM_48  // ESP32-S3 onboard LED

/* ─── Debug Configuration ─────────────────────────────────────────────────── */

// Debug Output
#define ENABLE_DEBUG_OUTPUT     1
#define DEBUG_TAG               "WiFi_CSI"

/* ─── Data Validation ─────────────────────────────────────────────────────── */

// Validation Settings
#define MIN_RSSI               -100
#define MAX_RSSI               -20
#define MIN_CHANNEL            1
#define MAX_CHANNEL            14

#endif // CONFIG_H