/**
 * @file wifi_manager.c
 * @brief WiFi Manager Implementation
 * 
 * Handles WiFi initialization, connection, and CSI configuration
 */

#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"

#include "wifi_manager.h"
#include "config.h"

/* ─── Private Variables ───────────────────────────────────────────────────── */

static const char *TAG = "WiFi_Mgr";

// Event group bits
#define WIFI_CONNECTED_BIT  BIT0
#define WIFI_FAIL_BIT       BIT1

static EventGroupHandle_t s_wifi_event_group;
static wifi_mgr_state_t s_state = WIFI_MGR_STATE_IDLE;
static int s_retry_count = 0;
static bool s_csi_enabled = false;

// Default configuration
static wifi_mgr_config_t s_config = {
    .ssid = WIFI_SSID,
    .password = WIFI_PASSWORD,
    .channel = WIFI_CHANNEL,
    .max_retry = WIFI_MAX_RETRY
};

/* ─── Private Function Prototypes ─────────────────────────────────────────── */

static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                              int32_t event_id, void *event_data);

/* ─── Public Functions ────────────────────────────────────────────────────── */

esp_err_t wifi_manager_init(const wifi_mgr_config_t *config)
{
    ESP_LOGI(TAG, "Initializing WiFi Manager");
    
    // Use custom config if provided
    if (config != NULL) {
        memcpy(&s_config, config, sizeof(wifi_mgr_config_t));
    }
    
    // Create event group
    s_wifi_event_group = xEventGroupCreate();
    if (s_wifi_event_group == NULL) {
        ESP_LOGE(TAG, "Failed to create event group");
        return ESP_ERR_NO_MEM;
    }
    
    // Initialize NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGW(TAG, "Erasing NVS flash");
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    
    // Initialize TCP/IP and event loop
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();
    
    // Initialize WiFi
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    
    // Register event handlers
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID,
                    &wifi_event_handler, NULL, NULL));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP,
                    &wifi_event_handler, NULL, NULL));
    
    s_state = WIFI_MGR_STATE_INIT;
    ESP_LOGI(TAG, "WiFi Manager initialized");
    
    return ESP_OK;
}

esp_err_t wifi_manager_start(void)
{
    ESP_LOGI(TAG, "Starting WiFi connection");
    
    s_state = WIFI_MGR_STATE_CONNECTING;
    
    // Configure WiFi
    wifi_config_t wifi_config = {
        .sta = {
            .threshold.authmode = WIFI_AUTH_WPA2_PSK,
            .pmf_cfg = {
                .capable = true,
                .required = false
            },
        },
    };
    
    // Copy SSID and password
    strncpy((char *)wifi_config.sta.ssid, s_config.ssid, sizeof(wifi_config.sta.ssid) - 1);
    strncpy((char *)wifi_config.sta.password, s_config.password, sizeof(wifi_config.sta.password) - 1);
    
    // Set WiFi mode and start
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());
    
    // Configure CSI right after WiFi start (before connect)
    wifi_csi_config_t csi_config;
    memset(&csi_config, 0, sizeof(wifi_csi_config_t));
    csi_config.lltf_en = true;
    csi_config.htltf_en = true;
    csi_config.ltf_merge_en = true;
    
    esp_err_t csi_err = esp_wifi_set_csi_config(&csi_config);
    if (csi_err != ESP_OK) {
        ESP_LOGW(TAG, "CSI config deferred: %s", esp_err_to_name(csi_err));
    } else {
        ESP_LOGI(TAG, "CSI config set successfully");
    }
    
    ESP_LOGI(TAG, "WiFi started, connecting to %s...", s_config.ssid);
    
    // Wait for connection
    EventBits_t bits = xEventGroupWaitBits(s_wifi_event_group,
            WIFI_CONNECTED_BIT | WIFI_FAIL_BIT,
            pdFALSE,
            pdFALSE,
            pdMS_TO_TICKS(WIFI_CONNECT_TIMEOUT_MS));
    
    if (bits & WIFI_CONNECTED_BIT) {
        s_state = WIFI_MGR_STATE_CONNECTED;
        ESP_LOGI(TAG, "Connected to WiFi");
        return ESP_OK;
    } else if (bits & WIFI_FAIL_BIT) {
        s_state = WIFI_MGR_STATE_ERROR;
        ESP_LOGE(TAG, "Failed to connect to WiFi");
        return ESP_FAIL;
    } else {
        s_state = WIFI_MGR_STATE_ERROR;
        ESP_LOGE(TAG, "WiFi connection timeout");
        return ESP_ERR_TIMEOUT;
    }
}

esp_err_t wifi_manager_stop(void)
{
    ESP_LOGI(TAG, "Stopping WiFi");
    
    // Disable CSI if enabled
    if (s_csi_enabled) {
        wifi_manager_disable_csi();
    }
    
    // Disconnect and stop
    esp_wifi_disconnect();
    esp_wifi_stop();
    
    s_state = WIFI_MGR_STATE_IDLE;
    
    return ESP_OK;
}

bool wifi_manager_is_connected(void)
{
    return (s_state == WIFI_MGR_STATE_CONNECTED);
}

wifi_mgr_state_t wifi_manager_get_state(void)
{
    return s_state;
}

int8_t wifi_manager_get_rssi(void)
{
    wifi_ap_record_t ap_info;
    if (esp_wifi_sta_get_ap_info(&ap_info) == ESP_OK) {
        return ap_info.rssi;
    }
    return -100;  // Default low value
}

uint8_t wifi_manager_get_channel(void)
{
    uint8_t primary;
    wifi_second_chan_t second;
    
    if (esp_wifi_get_channel(&primary, &second) == ESP_OK) {
        return primary;
    }
    return WIFI_CHANNEL;
}

esp_err_t wifi_manager_enable_csi(void)
{
    if (s_csi_enabled) {
        ESP_LOGW(TAG, "CSI already enabled");
        return ESP_OK;
    }
    
    ESP_LOGI(TAG, "Enabling CSI collection");
    
    // CSI config already set in wifi_manager_start
    // Just enable CSI
    esp_err_t err = esp_wifi_set_csi(true);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to enable CSI: %s", esp_err_to_name(err));
        return err;
    }
    
    s_csi_enabled = true;
    ESP_LOGI(TAG, "CSI collection enabled");
    
    return ESP_OK;
}

esp_err_t wifi_manager_disable_csi(void)
{
    if (!s_csi_enabled) {
        ESP_LOGW(TAG, "CSI already disabled");
        return ESP_OK;
    }
    
    ESP_LOGI(TAG, "Disabling CSI collection");
    
    esp_err_t err = esp_wifi_set_csi(false);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to disable CSI: %s", esp_err_to_name(err));
        return err;
    }
    
    s_csi_enabled = false;
    ESP_LOGI(TAG, "CSI collection disabled");
    
    return ESP_OK;
}

/* ─── Private Functions ───────────────────────────────────────────────────── */

static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                              int32_t event_id, void *event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        ESP_LOGI(TAG, "WiFi STA started");
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        s_state = WIFI_MGR_STATE_CONNECTING;
        
        if (s_retry_count < s_config.max_retry) {
            esp_wifi_connect();
            s_retry_count++;
            ESP_LOGI(TAG, "Retrying WiFi connection (%d/%d)", s_retry_count, s_config.max_retry);
        } else {
            xEventGroupSetBits(s_wifi_event_group, WIFI_FAIL_BIT);
            s_state = WIFI_MGR_STATE_ERROR;
            ESP_LOGE(TAG, "Failed to connect to WiFi after %d attempts", s_config.max_retry);
        }
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
        ESP_LOGI(TAG, "Connected - IP: " IPSTR, IP2STR(&event->ip_info.ip));
        s_state = WIFI_MGR_STATE_CONNECTED;
        s_retry_count = 0;
        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
    }
}