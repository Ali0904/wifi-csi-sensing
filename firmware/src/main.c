/**
 * @file main.c
 * @brief WiFi CSI Environmental Sensing System - Main Entry Point
 * 
 * This project captures WiFi Channel State Information (CSI) using ESP32-S3
 * for environmental sensing and wall detection applications.
 * 
 * @author Ali Haider
 * @date July 2026
 * @version 1.0.0
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_timer.h"

#include "config.h"
#include "wifi_manager.h"
#include "csi_collector.h"
#include "serial_manager.h"

/* ─── Private Variables ───────────────────────────────────────────────────── */

static const char *TAG = "Main";

/* ─── Private Function Prototypes ─────────────────────────────────────────── */

static void status_task(void *pvParameters);

/* ─── Main Application Entry Point ────────────────────────────────────────── */

void app_main(void)
{
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "WiFi CSI Environmental Sensing System");
    ESP_LOGI(TAG, "Version: 1.0.0");
    ESP_LOGI(TAG, "Author: Ali Haider");
    ESP_LOGI(TAG, "========================================");
    
    // Initialize Serial Manager first for debug output
    esp_err_t err = serial_manager_init();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize Serial Manager");
        return;
    }
    serial_send_status("System initializing...");
    
    // Initialize WiFi Manager
    err = wifi_manager_init(NULL);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize WiFi Manager");
        serial_send_error("WiFi initialization failed");
        return;
    }
    serial_send_status("WiFi initialized");
    
    // Initialize CSI Collector
    err = csi_collector_init();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize CSI Collector");
        serial_send_error("CSI collector initialization failed");
        return;
    }
    serial_send_status("CSI collector initialized");
    
    // Connect to WiFi
    serial_send_status("Connecting to WiFi...");
    err = wifi_manager_start();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to connect to WiFi");
        serial_send_error("WiFi connection failed");
        return;
    }
    serial_send_status("WiFi connected");
    
    // Start CSI Collection
    err = csi_collector_start();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to start CSI collection");
        serial_send_error("CSI collection start failed");
        return;
    }
    serial_send_status("CSI collection started");
    
    // Start Serial Manager (will send CSI data)
    err = serial_manager_start();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to start Serial Manager");
        serial_send_error("Serial manager start failed");
        return;
    }
    serial_send_status("System ready - streaming CSI data");
    
    // Create status task
    xTaskCreate(
        status_task,
        "Status_Task",
        STATUS_TASK_STACK_SIZE,
        NULL,
        STATUS_TASK_PRIORITY,
        NULL
    );
    
    ESP_LOGI(TAG, "System initialized successfully");
    
    // Keep main task alive - other tasks do the work
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

/* ─── Private Functions ───────────────────────────────────────────────────── */

static void status_task(void *pvParameters)
{
    ESP_LOGI(TAG, "Status task started");
    
    while (1) {
        // Print status
        if (wifi_manager_is_connected()) {
            csi_stats_t stats = csi_collector_get_stats();
            int8_t rssi = wifi_manager_get_rssi();
            
            ESP_LOGI(TAG, "Status: Connected | RSSI: %d dBm | CSI: %lu received, %lu queued, %lu dropped | Free heap: %lu bytes",
                     rssi,
                     stats.packets_received,
                     stats.packets_queued,
                     stats.packets_dropped,
                     esp_get_free_heap_size());
        } else {
            ESP_LOGW(TAG, "Status: WiFi not connected");
        }
        
        vTaskDelay(pdMS_TO_TICKS(STATUS_INTERVAL_MS));
    }
}