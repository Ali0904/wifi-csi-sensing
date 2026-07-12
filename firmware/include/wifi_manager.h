/**
 * @file wifi_manager.h
 * @brief WiFi Manager Header
 * 
 * Handles WiFi initialization, connection, and CSI configuration
 */

#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
#include "esp_wifi_types.h"

/* ─── Data Structures ─────────────────────────────────────────────────────── */

/**
 * @brief WiFi Manager State
 */
typedef enum {
    WIFI_MGR_STATE_IDLE = 0,
    WIFI_MGR_STATE_INIT,
    WIFI_MGR_STATE_CONNECTING,
    WIFI_MGR_STATE_CONNECTED,
    WIFI_MGR_STATE_ERROR
} wifi_mgr_state_t;

/**
 * @brief WiFi Manager Configuration
 */
typedef struct {
    char ssid[32];
    char password[64];
    uint8_t channel;
    uint8_t max_retry;
} wifi_mgr_config_t;

/* ─── Function Prototypes ─────────────────────────────────────────────────── */

/**
 * @brief Initialize WiFi Manager
 * 
 * @param config WiFi configuration (NULL for defaults)
 * @return esp_err_t ESP_OK on success
 */
esp_err_t wifi_manager_init(const wifi_mgr_config_t *config);

/**
 * @brief Start WiFi connection
 * 
 * @return esp_err_t ESP_OK on success
 */
esp_err_t wifi_manager_start(void);

/**
 * @brief Stop WiFi
 * 
 * @return esp_err_t ESP_OK on success
 */
esp_err_t wifi_manager_stop(void);

/**
 * @brief Get WiFi connection status
 * 
 * @return true if connected, false otherwise
 */
bool wifi_manager_is_connected(void);

/**
 * @brief Get current WiFi state
 * 
 * @return wifi_mgr_state_t Current state
 */
wifi_mgr_state_t wifi_manager_get_state(void);

/**
 * @brief Get RSSI value
 * 
 * @return int8_t RSSI value in dBm
 */
int8_t wifi_manager_get_rssi(void);

/**
 * @brief Get WiFi channel
 * 
 * @return uint8_t Current WiFi channel
 */
uint8_t wifi_manager_get_channel(void);

/**
 * @brief Enable CSI collection
 * 
 * @return esp_err_t ESP_OK on success
 */
esp_err_t wifi_manager_enable_csi(void);

/**
 * @brief Disable CSI collection
 * 
 * @return esp_err_t ESP_OK on success
 */
esp_err_t wifi_manager_disable_csi(void);

#endif // WIFI_MANAGER_H