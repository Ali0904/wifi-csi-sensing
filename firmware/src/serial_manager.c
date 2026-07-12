/**
 * @file serial_manager.c
 * @brief Serial Manager Implementation
 * 
 * Handles serial communication and data output
 */

#include <string.h>
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_log.h"
#include "driver/uart.h"

#include "serial_manager.h"
#include "csi_collector.h"
#include "config.h"

/* ─── Private Variables ───────────────────────────────────────────────────── */

static const char *TAG = "Serial_Mgr";

static TaskHandle_t s_serial_task_handle = NULL;
static bool s_running = false;
static bool s_ready = false;

// UART configuration
#define UART_PORT       UART_NUM_0
#define UART_TX_PIN     UART_PIN_NO_CHANGE
#define UART_RX_PIN     UART_PIN_NO_CHANGE
#define UART_BUF_SIZE   2048

/* ─── Private Function Prototypes ─────────────────────────────────────────── */

static void serial_task(void *pvParameters);
static void format_amplitude_string(char *buf, size_t buf_size, const int8_t *data, uint16_t len);
static void format_phase_string(char *buf, size_t buf_size, const int8_t *data, uint16_t len);

/* ─── Public Functions ────────────────────────────────────────────────────── */

esp_err_t serial_manager_init(void)
{
    ESP_LOGI(TAG, "Initializing Serial Manager");
    
    // Configure UART
    uart_config_t uart_config = {
        .baud_rate = SERIAL_BAUDRATE,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    
    // Install UART driver
    esp_err_t err = uart_driver_install(UART_PORT, UART_BUF_SIZE * 2, 0, 0, NULL, 0);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to install UART driver: %s", esp_err_to_name(err));
        return err;
    }
    
    // Set UART parameters
    err = uart_param_config(UART_PORT, &uart_config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to configure UART: %s", esp_err_to_name(err));
        return err;
    }
    
    s_ready = true;
    ESP_LOGI(TAG, "Serial Manager initialized (baudrate: %d)", SERIAL_BAUDRATE);
    
    return ESP_OK;
}

esp_err_t serial_manager_start(void)
{
    if (s_running) {
        ESP_LOGW(TAG, "Serial Manager already running");
        return ESP_OK;
    }
    
    if (!s_ready) {
        ESP_LOGE(TAG, "Serial Manager not initialized");
        return ESP_ERR_INVALID_STATE;
    }
    
    ESP_LOGI(TAG, "Starting Serial Manager");
    
    s_running = true;
    
    // Create serial task
    BaseType_t ret = xTaskCreate(
        serial_task,
        "Serial_Task",
        SERIAL_TASK_STACK_SIZE,
        NULL,
        SERIAL_TASK_PRIORITY,
        &s_serial_task_handle
    );
    
    if (ret != pdPASS) {
        s_running = false;
        ESP_LOGE(TAG, "Failed to create Serial task");
        return ESP_FAIL;
    }
    ESP_LOGI(TAG, "Serial Manager started");
    
    return ESP_OK;
}

esp_err_t serial_manager_stop(void)
{
    if (!s_running) {
        ESP_LOGW(TAG, "Serial Manager not running");
        return ESP_OK;
    }
    
    ESP_LOGI(TAG, "Stopping Serial Manager");
    
    s_running = false;
    
    // Delete task
    if (s_serial_task_handle != NULL) {
        vTaskDelete(s_serial_task_handle);
        s_serial_task_handle = NULL;
    }
    
    ESP_LOGI(TAG, "Serial Manager stopped");
    
    return ESP_OK;
}

esp_err_t serial_send_csi_data(const csi_data_t *data)
{
    if (data == NULL || !s_ready) {
        return ESP_ERR_INVALID_ARG;
    }
    
    char amplitude_str[CSI_BUF_SIZE * 4];
    char phase_str[CSI_BUF_SIZE * 4];
    
    format_amplitude_string(amplitude_str, sizeof(amplitude_str), data->buf, data->len);
    format_phase_string(phase_str, sizeof(phase_str), data->buf, data->len);
    
    char buffer[2048];
    
#if DATA_FORMAT == DATA_FORMAT_CSV
    int len = snprintf(buffer, sizeof(buffer),
        "%lld,%d,%d,%d,%d,\"%s\",\"%s\"\n",
        data->timestamp,
        data->rssi,
        data->channel,
        data->secondary_channel,
        data->bw,
        amplitude_str,
        phase_str
    );
#elif DATA_FORMAT == DATA_FORMAT_JSON
    int len = snprintf(buffer, sizeof(buffer),
        "{\"timestamp\":%lld,\"rssi\":%d,\"channel\":%d,\"secondary_channel\":%d,"
        "\"bw\":%d,\"amplitude\":\"%s\",\"phase\":\"%s\"}\n",
        data->timestamp,
        data->rssi,
        data->channel,
        data->secondary_channel,
        data->bw,
        amplitude_str,
        phase_str
    );
#endif
    
    // Send via UART
    int written = uart_write_bytes(UART_PORT, buffer, len);
    
    if (written == len) {
        return ESP_OK;
    } else {
        return ESP_FAIL;
    }
}

esp_err_t serial_send_status(const char *message)
{
    if (message == NULL || !s_ready) {
        return ESP_ERR_INVALID_ARG;
    }
    
    char buffer[512];
    int len = snprintf(buffer, sizeof(buffer), "[STATUS] %s\n", message);
    
    int written = uart_write_bytes(UART_PORT, buffer, len);
    
    return (written == len) ? ESP_OK : ESP_FAIL;
}

esp_err_t serial_send_error(const char *message)
{
    if (message == NULL || !s_ready) {
        return ESP_ERR_INVALID_ARG;
    }
    
    char buffer[512];
    int len = snprintf(buffer, sizeof(buffer), "[ERROR] %s\n", message);
    
    int written = uart_write_bytes(UART_PORT, buffer, len);
    
    return (written == len) ? ESP_OK : ESP_FAIL;
}

bool serial_manager_is_ready(void)
{
    return s_ready;
}

/* ─── Private Functions ───────────────────────────────────────────────────── */

static void serial_task(void *pvParameters)
{
    ESP_LOGI(TAG, "Serial task started");
    
    csi_data_t csi;
    
    while (s_running) {
        // Get CSI data from collector
        if (csi_collector_get_data(&csi, pdMS_TO_TICKS(100)) == ESP_OK) {
            // Send via serial
            serial_send_csi_data(&csi);
        }
    }
    
    ESP_LOGI(TAG, "Serial task stopped");
    vTaskDelete(NULL);
}

static void format_amplitude_string(char *buf, size_t buf_size, const int8_t *data, uint16_t len)
{
    if (!buf || buf_size == 0 || !data) {
        if (buf && buf_size > 0) {
            buf[0] = '\0';
        }
        return;
    }
    
    buf[0] = '[';
    size_t pos = 1;
    
    for (int i = 0; i < len && pos < buf_size - 2; i++) {
        int written = snprintf(buf + pos, buf_size - pos, "%d", data[i]);
        if (written > 0) {
            pos += written;
            if (i < len - 1 && pos < buf_size - 2) {
                buf[pos++] = ',';
            }
        }
    }
    
    if (pos < buf_size) {
        buf[pos++] = ']';
        buf[pos] = '\0';
    }
}

static void format_phase_string(char *buf, size_t buf_size, const int8_t *data, uint16_t len)
{
    if (!buf || buf_size == 0 || !data) {
        if (buf && buf_size > 0) {
            buf[0] = '\0';
        }
        return;
    }
    
    buf[0] = '[';
    size_t pos = 1;
    
    // Phase data is in the second half of the buffer
    int phase_offset = len / 2;
    
    for (int i = 0; i < len / 2 && pos < buf_size - 2; i++) {
        int written = snprintf(buf + pos, buf_size - pos, "%d", data[phase_offset + i]);
        if (written > 0) {
            pos += written;
            if (i < len / 2 - 1 && pos < buf_size - 2) {
                buf[pos++] = ',';
            }
        }
    }
    
    if (pos < buf_size) {
        buf[pos++] = ']';
        buf[pos] = '\0';
    }
}