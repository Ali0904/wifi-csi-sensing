/**
 * @file csi_collector.h
 * @brief CSI Collector Header
 * 
 * Handles CSI data collection and processing
 */

#ifndef CSI_COLLECTOR_H
#define CSI_COLLECTOR_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

/* ─── Data Structures ─────────────────────────────────────────────────────── */

/**
 * @brief CSI Data Structure
 * Contains captured CSI information from WiFi packets
 */
typedef struct {
    int64_t timestamp;              // Timestamp in milliseconds
    int8_t *buf;                    // CSI data buffer
    uint16_t len;                   // Buffer length
    int8_t rssi;                    // Received Signal Strength Indicator
    uint8_t channel;                // WiFi channel
    uint8_t secondary_channel;      // Secondary channel (HT40)
    uint8_t bw;                     // Bandwidth (20/40 MHz)
    uint8_t bits_per_subcarrier;    // Bits per subcarrier
} csi_data_t;

/**
 * @brief CSI Collector Statistics
 */
typedef struct {
    uint32_t packets_received;      // Total packets received
    uint32_t packets_queued;        // Packets successfully queued
    uint32_t packets_dropped;       // Packets dropped (queue full)
    uint32_t queue_size;            // Current queue size
} csi_stats_t;

/* ─── Function Prototypes ─────────────────────────────────────────────────── */

/**
 * @brief Initialize CSI Collector
 * 
 * @return esp_err_t ESP_OK on success
 */
esp_err_t csi_collector_init(void);

/**
 * @brief Start CSI collection
 * 
 * @return esp_err_t ESP_OK on success
 */
esp_err_t csi_collector_start(void);

/**
 * @brief Stop CSI collection
 * 
 * @return esp_err_t ESP_OK on success
 */
esp_err_t csi_collector_stop(void);

/**
 * @brief Get CSI data from queue
 * 
 * @param data Pointer to store CSI data
 * @param timeout_ms Timeout in milliseconds
 * @return esp_err_t ESP_OK if data received, ESP_ERR_TIMEOUT on timeout
 */
esp_err_t csi_collector_get_data(csi_data_t *data, uint32_t timeout_ms);

/**
 * @brief Get collector statistics
 * 
 * @return csi_stats_t Statistics structure
 */
csi_stats_t csi_collector_get_stats(void);

/**
 * @brief Check if collector is running
 * 
 * @return true if running, false otherwise
 */
bool csi_collector_is_running(void);

#endif // CSI_COLLECTOR_H