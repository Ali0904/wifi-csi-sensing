/**
 * @file csi_collector.c
 * @brief CSI Collector Implementation
 * 
 * Handles CSI data collection and processing
 */

#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_timer.h"

#include "csi_collector.h"
#include "wifi_manager.h"
#include "config.h"

/* ─── Private Variables ───────────────────────────────────────────────────── */

static const char *TAG = "CSI_Collect";

static QueueHandle_t s_csi_queue = NULL;
static TaskHandle_t s_csi_task_handle = NULL;
static bool s_running = false;
static csi_stats_t s_stats = {0};

/* ─── Private Function Prototypes ─────────────────────────────────────────── */

static void csi_rx_callback(void *ctx, wifi_csi_info_t *info);
static void csi_task(void *pvParameters);
static int64_t get_timestamp_ms(void);

/* ─── Public Functions ────────────────────────────────────────────────────── */

esp_err_t csi_collector_init(void)
{
    ESP_LOGI(TAG, "Initializing CSI Collector");
    
    // Create CSI queue
    s_csi_queue = xQueueCreate(CSI_QUEUE_SIZE, sizeof(csi_data_t));
    if (s_csi_queue == NULL) {
        ESP_LOGE(TAG, "Failed to create CSI queue");
        return ESP_ERR_NO_MEM;
    }
    
    // Reset statistics
    memset(&s_stats, 0, sizeof(csi_stats_t));
    
    ESP_LOGI(TAG, "CSI Collector initialized (queue size: %d)", CSI_QUEUE_SIZE);
    
    return ESP_OK;
}

esp_err_t csi_collector_start(void)
{
    if (s_running) {
        ESP_LOGW(TAG, "CSI Collector already running");
        return ESP_OK;
    }
    
    ESP_LOGI(TAG, "Starting CSI Collector");
    
    // Register CSI callback FIRST (before config)
    esp_err_t err = esp_wifi_set_csi_rx_cb(csi_rx_callback, NULL);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to register CSI callback: %s", esp_err_to_name(err));
        return err;
    }
    
    // Wait for WiFi to be fully stable
    vTaskDelay(pdMS_TO_TICKS(1000));
    
    // Enable CSI on WiFi (config + enable)
    err = wifi_manager_enable_csi();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to enable CSI: %s", esp_err_to_name(err));
        return err;
    }
    
    s_running = true;
    
    // Create CSI task
    BaseType_t ret = xTaskCreate(
        csi_task,
        "CSI_Task",
        CSI_TASK_STACK_SIZE,
        NULL,
        CSI_TASK_PRIORITY,
        &s_csi_task_handle
    );
    
    if (ret != pdPASS) {
        s_running = false;
        ESP_LOGE(TAG, "Failed to create CSI task");
        return ESP_FAIL;
    }
    ESP_LOGI(TAG, "CSI Collector started");
    
    return ESP_OK;
}

esp_err_t csi_collector_stop(void)
{
    if (!s_running) {
        ESP_LOGW(TAG, "CSI Collector not running");
        return ESP_OK;
    }
    
    ESP_LOGI(TAG, "Stopping CSI Collector");
    
    s_running = false;
    
    // Disable CSI
    wifi_manager_disable_csi();
    
    // Unregister callback
    esp_wifi_set_csi_rx_cb(NULL, NULL);
    
    // Delete task
    if (s_csi_task_handle != NULL) {
        vTaskDelete(s_csi_task_handle);
        s_csi_task_handle = NULL;
    }
    
    ESP_LOGI(TAG, "CSI Collector stopped");
    ESP_LOGI(TAG, "Statistics - Received: %lu, Queued: %lu, Dropped: %lu",
             s_stats.packets_received, s_stats.packets_queued, s_stats.packets_dropped);
    
    return ESP_OK;
}

esp_err_t csi_collector_get_data(csi_data_t *data, uint32_t timeout_ms)
{
    if (data == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    
    if (xQueueReceive(s_csi_queue, data, pdMS_TO_TICKS(timeout_ms)) == pdTRUE) {
        return ESP_OK;
    }
    
    return ESP_ERR_TIMEOUT;
}

csi_stats_t csi_collector_get_stats(void)
{
    s_stats.queue_size = uxQueueMessagesWaiting(s_csi_queue);
    return s_stats;
}

bool csi_collector_is_running(void)
{
    return s_running;
}

/* ─── Private Functions ───────────────────────────────────────────────────── */

static void csi_rx_callback(void *ctx, wifi_csi_info_t *info)
{
    if (!info || !info->buf) {
        ESP_LOGW(TAG, "Invalid CSI data received");
        return;
    }
    
    s_stats.packets_received++;
    
    // Create CSI data structure
    csi_data_t csi;
    csi.timestamp = get_timestamp_ms();
    csi.buf = info->buf;
    csi.len = info->len;
    csi.rssi = info->rx_ctrl.rssi;
    csi.channel = info->rx_ctrl.channel;
    csi.secondary_channel = info->rx_ctrl.secondary_channel;
    csi.bw = info->rx_ctrl.cwb ? 40 : 20;
    csi.bits_per_subcarrier = info->rx_ctrl.stbc ? 2 : 1;
    
    // Send to queue
    if (xQueueSend(s_csi_queue, &csi, 0) == pdTRUE) {
        s_stats.packets_queued++;
    } else {
        s_stats.packets_dropped++;
    }
}

static void csi_task(void *pvParameters)
{
    ESP_LOGI(TAG, "CSI task started");
    
    while (s_running) {
        // Just wait - actual data comes via callback
        vTaskDelay(pdMS_TO_TICKS(100));
    }
    
    ESP_LOGI(TAG, "CSI task stopped");
    vTaskDelete(NULL);
}

static int64_t get_timestamp_ms(void)
{
    return esp_timer_get_time() / 1000;
}