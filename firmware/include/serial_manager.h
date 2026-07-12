/**
 * @file serial_manager.h
 * @brief Serial Manager Header
 * 
 * Handles serial communication and data output
 */

#ifndef SERIAL_MANAGER_H
#define SERIAL_MANAGER_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
#include "csi_collector.h"

/* ─── Function Prototypes ─────────────────────────────────────────────────── */

/**
 * @brief Initialize Serial Manager
 * 
 * @return esp_err_t ESP_OK on success
 */
esp_err_t serial_manager_init(void);

/**
 * @brief Start Serial Manager task
 * 
 * @return esp_err_t ESP_OK on success
 */
esp_err_t serial_manager_start(void);

/**
 * @brief Stop Serial Manager task
 * 
 * @return esp_err_t ESP_OK on success
 */
esp_err_t serial_manager_stop(void);

/**
 * @brief Send CSI data via serial
 * 
 * @param data CSI data to send
 * @return esp_err_t ESP_OK on success
 */
esp_err_t serial_send_csi_data(const csi_data_t *data);

/**
 * @brief Send status message
 * 
 * @param message Status message
 * @return esp_err_t ESP_OK on success
 */
esp_err_t serial_send_status(const char *message);

/**
 * @brief Send error message
 * 
 * @param message Error message
 * @return esp_err_t ESP_OK on success
 */
esp_err_t serial_send_error(const char *message);

/**
 * @brief Check if serial manager is ready
 * 
 * @return true if ready, false otherwise
 */
bool serial_manager_is_ready(void);

#endif // SERIAL_MANAGER_H