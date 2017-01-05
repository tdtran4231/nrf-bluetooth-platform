#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "nordic_common.h"
#include "nrf.h"
#include "nrf_delay.h"
#include "nrf_gpio.h"
#include "nrf_gpiote.h"
#include "nrf_drv_gpiote.h" 
#include "nrf_sdm.h"
#include "ble.h"
#include "ble_hci.h"
#include "ble_db_discovery.h"
#include "ble_gattc.h"
#include "softdevice_handler.h"
#include "app_util.h"
#include "app_error.h"
#include "boards.h"
#include "pstorage.h"
#include "device_manager.h"
#include "app_trace.h"
#include "ble_hrs_c.h"
#include "app_util.h"
#include "app_timer.h"
#include "bsp.h"

#define UART_TX_BUF_SIZE 256                         
#define UART_RX_BUF_SIZE 1
#define APP_TIMER_PRESCALER        0                                 
#define APP_TIMER_OP_QUEUE_SIZE    2                                 
#define SEC_PARAM_BOND             1                                  
#define SEC_PARAM_MITM             1                                  
#define SEC_PARAM_IO_CAPABILITIES  BLE_GAP_IO_CAPS_NONE               
#define SEC_PARAM_OOB              0                                  
#define SEC_PARAM_MIN_KEY_SIZE     7                                  
#define SEC_PARAM_MAX_KEY_SIZE     16                                 
#define SCAN_INTERVAL              0x00A0 // scan interval in units of 0.625 millisec
#define SCAN_WINDOW                0x0050                            
#define MIN_CONNECTION_INTERVAL    MSEC_TO_UNITS(7.5, UNIT_1_25_MS)  
#define MAX_CONNECTION_INTERVAL    MSEC_TO_UNITS(30, UNIT_1_25_MS) 
#define SLAVE_LATENCY              0                                  
#define SUPERVISION_TIMEOUT        MSEC_TO_UNITS(4000, UNIT_10_MS)    

#define TARGET_UUID                0x152C                            
#define MAX_PEER_COUNT             1
#define UUID16_SIZE                2                                

// these are defined in the clock application, copied here for ease of experiments
#define BLE_UUID_OUR_BASE_UUID {0x23, 0xD1, 0x13, 0xEF, 0x5F, 0x78, 0x23, 0x15, 0xDE, 0xEF, 0x12, 0x12, 0x00, 0x00, 0x00, 0x00}
#define BLE_UUID_OUR_SERVICE 0x152C
#define CLOCK_READ_UUID 0x3907
#define CLOCK_READ_INDX 0
#define CLOCK_WRITE_UUID 0x3909
#define CLOCK_WRITE_INDX 1
#define NUMBER_OUR_ATTRIBUTES 2
uint32_t clock;
uint32_t setclock;
const uint16_t our_attribute_uuid_list[NUMBER_OUR_ATTRIBUTES] = {CLOCK_READ_UUID,CLOCK_WRITE_UUID};
const uint8_t our_attribute_lengths[NUMBER_OUR_ATTRIBUTES] = {4,4};
uint8_t* our_attribute_pointers[NUMBER_OUR_ATTRIBUTES] = {(uint8_t*)&clock,(uint8_t*)&setclock};

#define UUID16_EXTRACT(DST, SRC) \
    do                           \
    {                            \
        (*(DST))   = (SRC)[1];   \
        (*(DST)) <<= 8;          \
        (*(DST))  |= (SRC)[0];   \
    } while (0)

typedef struct {
  uint8_t  * p_data;  
  uint16_t data_len; 
  } data_t;

typedef enum {
  BLE_NO_SCAN,
  BLE_WHITELIST_SCAN, 
  BLE_FAST_SCAN,
  } ble_scan_mode_t;

typedef struct {
  uint16_t conn_handle;
  uint16_t clock_cccd_handle;
  uint16_t clock_handle; 
  uint16_t setclock_cccd_handle;
  uint16_t setclock_handle; 
  } m_clock_t; 

const uint8_t leds_list[5] = {18,19,20,21,22};
APP_TIMER_DEF(timer_id);
static ble_db_discovery_t           m_ble_db_discovery;
static ble_gap_scan_params_t        m_scan_param;      
static dm_application_instance_t    m_dm_app_id;     
static dm_handle_t                  m_dm_device_handle;    
static uint8_t                      m_peer_count = 0;     
static ble_scan_mode_t              m_scan_mode = BLE_FAST_SCAN;   
static uint16_t m_conn_handle = BLE_CONN_HANDLE_INVALID;
static volatile bool                m_whitelist_temporarily_disabled = false; 
static m_clock_t m_clock;

static bool m_memory_access_in_progress = false;

static const ble_gap_conn_params_t m_connection_param = {
    (uint16_t)MIN_CONNECTION_INTERVAL, 
    (uint16_t)MAX_CONNECTION_INTERVAL,  
    0,                              
    (uint16_t)SUPERVISION_TIMEOUT       
    };

static void scan_start(void);

static void gpioteHandler(nrf_drv_gpiote_pin_t p, nrf_gpiote_polarity_t d) {
  if (p != 16) return;
  }
static void gpioteInit() {
  nrf_drv_gpiote_in_config_t config16 = GPIOTE_CONFIG_IN_SENSE_HITOLO(false);
  config16.pull = NRF_GPIO_PIN_PULLUP;
  if (!nrf_drv_gpiote_is_init()) nrf_drv_gpiote_init();
  nrf_drv_gpiote_in_uninit(16);
  nrf_drv_gpiote_in_init(16,&config16,gpioteHandler);
  nrf_drv_gpiote_in_event_enable(16,true);
  }
static void gpioInit() {
  uint8_t i;
  for (i=0;i<5;i++) nrf_gpio_cfg_output(leds_list[i]);
  }
static void gpioOn(uint8_t pin) {
  nrf_gpio_pin_set(pin);
  }
static void gpioOff(uint8_t pin) {
  nrf_gpio_pin_clear(pin);
  }
static void gpioToggle(uint8_t pin) {
  nrf_gpio_pin_toggle(pin);
  }

static ret_code_t device_manager_event_handler(const dm_handle_t    * p_handle,
                                               const dm_event_t     * p_event,
                                               const ret_code_t     event_result) {
  uint32_t err_code;
  gpioToggle(20);
  switch (p_event->event_id) {
    case DM_EVT_CONNECTION:
      m_conn_handle = p_event->event_param.p_gap_param->conn_handle;
      m_dm_device_handle = (*p_handle);
      err_code = dm_security_setup_req(&m_dm_device_handle);
      APP_ERROR_CHECK(err_code);
      m_peer_count++;
      if (m_peer_count > MAX_PEER_COUNT) { scan_start(); }
      printf("Connection Made\r\n");
      break;

    case DM_EVT_DISCONNECTION:
      printf("Disconnecting\r\n");
      m_conn_handle = BLE_CONN_HANDLE_INVALID;
      memset(&m_ble_db_discovery, 0 , sizeof (m_ble_db_discovery));
      if (m_peer_count > 0) m_peer_count--;
      if (m_peer_count <= MAX_PEER_COUNT) { scan_start(); }
      break;

    case DM_EVT_SECURITY_SETUP:
      err_code = dm_security_setup_req(&m_dm_device_handle);
      APP_ERROR_CHECK(err_code);
      break;

    case DM_EVT_SECURITY_SETUP_COMPLETE:
      break;

    case DM_EVT_LINK_SECURED:
      err_code = ble_db_discovery_start(&m_ble_db_discovery,
                                              p_event->event_param.p_gap_param->conn_handle);
      APP_ERROR_CHECK(err_code);
      break;

    case DM_EVT_DEVICE_CONTEXT_LOADED:
      APP_ERROR_CHECK(event_result);
      break;

    case DM_EVT_DEVICE_CONTEXT_STORED:
      APP_ERROR_CHECK(event_result);
      break;

    case DM_EVT_DEVICE_CONTEXT_DELETED:
      APP_ERROR_CHECK(event_result);
      break;

    default:
      break;
    }

  return NRF_SUCCESS;
  }


static uint32_t adv_report_parse(uint8_t type, data_t * p_advdata, data_t * p_typedata) {
  uint32_t  index = 0;
  uint8_t * p_data;
  p_data = p_advdata->p_data;
  while (index < p_advdata->data_len) {
    uint8_t field_length = p_data[index];
    uint8_t field_type   = p_data[index+1];
    if (field_type == type) {
       p_typedata->p_data   = &p_data[index+2];
       p_typedata->data_len = field_length-1;
       return NRF_SUCCESS;
       }
    index += field_length + 1;
    }
  return NRF_ERROR_NOT_FOUND;
  }

static void sleep_mode_enter(void) {
  sd_power_system_off();
  }

static void on_ble_evt(ble_evt_t * p_ble_evt) {
  uint32_t                err_code;
  data_t adv_data;
  data_t type_data;
  const ble_gap_evt_t   * p_gap_evt = &p_ble_evt->evt.gap_evt;

  switch (p_ble_evt->header.evt_id) {
    case BLE_GAP_EVT_ADV_REPORT:
      gpioToggle(21);
      // Initialize advertisement report for parsing.
      adv_data.p_data = (uint8_t *)p_gap_evt->params.adv_report.data;
      adv_data.data_len = p_gap_evt->params.adv_report.dlen;
      err_code = adv_report_parse(BLE_GAP_AD_TYPE_16BIT_SERVICE_UUID_MORE_AVAILABLE,
                                        &adv_data,
                                        &type_data);
      if (err_code != NRF_SUCCESS) {
        err_code = adv_report_parse(BLE_GAP_AD_TYPE_16BIT_SERVICE_UUID_COMPLETE,
                                            &adv_data,
                                            &type_data);
        }
      if (err_code == NRF_SUCCESS) {
        uint16_t extracted_uuid;
        int8_t i;
        uint8_t len;
        uint8_t byte;
        // UUIDs found, look for matching UUID
        for (uint32_t u_index = 0; u_index < (type_data.data_len/UUID16_SIZE); u_index++) {
           UUID16_EXTRACT(&extracted_uuid,&type_data.p_data[u_index * UUID16_SIZE]);
           printf("* Extracted from Advertisement.");
           printf(" UUID %04x",extracted_uuid);
           printf(" RSSI %d",p_ble_evt->evt.gap_evt.params.adv_report.rssi);
           printf(" ADDR ");
           for (i=BLE_GAP_ADDR_LEN-1;i>=0;i--) {
              printf("%02x",p_ble_evt->evt.gap_evt.params.adv_report.peer_addr.addr[i]);
              if (i>0) printf(":");
              }
           printf(" ");
           len = 0x1f & p_ble_evt->evt.gap_evt.params.adv_report.dlen;
           for (i=0;i<len;i++) {
              byte = p_ble_evt->evt.gap_evt.params.adv_report.data[i];
              if (byte < ' ' || byte > '~') printf("_");
              else printf("%c",byte);
              }
           printf("\r\n");
           if (extracted_uuid == TARGET_UUID) {
              err_code = sd_ble_gap_scan_stop();
              m_scan_param.selective = 0; 
              m_scan_param.p_whitelist = NULL;
              err_code = sd_ble_gap_connect(&p_gap_evt->params.adv_report.peer_addr,
                                                      &m_scan_param,
                                                      &m_connection_param);
              m_whitelist_temporarily_disabled = false;
              break;
              } 
           } 
        }
        break;

    case BLE_GAP_EVT_TIMEOUT:
      if (p_gap_evt->params.timeout.src == BLE_GAP_TIMEOUT_SRC_SCAN) {
        scan_start();
        }
      else if (p_gap_evt->params.timeout.src == BLE_GAP_TIMEOUT_SRC_CONN) {
        }
      break;

    case BLE_GAP_EVT_CONN_PARAM_UPDATE_REQUEST:
      err_code = sd_ble_gap_conn_param_update(p_gap_evt->conn_handle,
                                      &p_gap_evt->params.conn_param_update_request.conn_params);
      APP_ERROR_CHECK(err_code);
      break;

    case BLE_GATTC_EVT_READ_RSP:
      {
      const ble_gattc_evt_read_rsp_t * p_response = &p_ble_evt->evt.gattc_evt.params.read_rsp;
      printf("got read response from handle %x\r\n",p_response->handle);
      memcpy((uint8_t*)&clock,p_response->data,4);  
      printf("clock = %d\r\n",(int)clock);
      }
      break;
    default:
      break;
    }
  }


static void on_sys_evt(uint32_t sys_evt) {
  switch (sys_evt) {
    case NRF_EVT_FLASH_OPERATION_SUCCESS:
    case NRF_EVT_FLASH_OPERATION_ERROR:
      if (m_memory_access_in_progress) {
         m_memory_access_in_progress = false;
         scan_start();
         }
      break;

    default:
      break;
    }
  }

static void ble_evt_dispatch(ble_evt_t * p_ble_evt) {
  dm_ble_evt_handler(p_ble_evt);
  ble_db_discovery_on_ble_evt(&m_ble_db_discovery, p_ble_evt);
  on_ble_evt(p_ble_evt);
  // Add service event here ....
  }
static void sys_evt_dispatch(uint32_t sys_evt) {
  pstorage_sys_event_handler(sys_evt);
  on_sys_evt(sys_evt);
  }

static void ble_stack_init(void) {
  uint32_t err_code;
  ble_enable_params_t ble_enable_params;
  memset(&ble_enable_params, 0, sizeof(ble_enable_params));
  ble_enable_params.gatts_enable_params.service_changed = false;
  ble_enable_params.gap_enable_params.role = BLE_GAP_ROLE_CENTRAL;

  err_code = sd_ble_enable(&ble_enable_params);
  APP_ERROR_CHECK(err_code);

  err_code = softdevice_ble_evt_handler_set(ble_evt_dispatch);
  APP_ERROR_CHECK(err_code);

  err_code = softdevice_sys_evt_handler_set(sys_evt_dispatch);
  APP_ERROR_CHECK(err_code);
  }


static void device_manager_init(bool erase_bonds) {
  uint32_t               err_code;
  dm_init_param_t        init_param = {.clear_persistent_data = erase_bonds};
  dm_application_param_t register_param;

  err_code = pstorage_init();
  APP_ERROR_CHECK(err_code);

  err_code = dm_init(&init_param);
  APP_ERROR_CHECK(err_code);

  memset(&register_param.sec_param, 0, sizeof (ble_gap_sec_params_t));

  // Event handler to be registered with the module.
  register_param.evt_handler            = device_manager_event_handler;

  // Service or protocol context for device manager to load, store and apply on behalf of application.
  // Here set to client as application is a GATT client.
  register_param.service_type           = DM_PROTOCOL_CNTXT_GATT_CLI_ID;

  // Secuirty parameters to be used for security procedures.
  register_param.sec_param.bond         = SEC_PARAM_BOND;
  register_param.sec_param.mitm         = SEC_PARAM_MITM;
  register_param.sec_param.io_caps      = SEC_PARAM_IO_CAPABILITIES;
  register_param.sec_param.oob          = SEC_PARAM_OOB;
  register_param.sec_param.min_key_size = SEC_PARAM_MIN_KEY_SIZE;
  register_param.sec_param.max_key_size = SEC_PARAM_MAX_KEY_SIZE;
  register_param.sec_param.kdist_periph.enc = 1;
  register_param.sec_param.kdist_periph.id  = 1;

  dm_register(&m_dm_app_id, &register_param);
  }


static void whitelist_disable(void) {
  uint32_t err_code;
  if ((m_scan_mode == BLE_WHITELIST_SCAN) && !m_whitelist_temporarily_disabled) {
    m_whitelist_temporarily_disabled = true;
    err_code = sd_ble_gap_scan_stop();
    if (err_code == NRF_SUCCESS) {
      scan_start(); }
    else if (err_code != NRF_ERROR_INVALID_STATE) {
      APP_ERROR_CHECK(err_code);
      }
    }
  m_whitelist_temporarily_disabled = true;
  }

static void db_discover_evt_handler(ble_db_discovery_evt_t * p_evt) {
  uint32_t i;
  if (p_evt->evt_type == BLE_DB_DISCOVERY_COMPLETE &&
      p_evt->params.discovered_db.srv_uuid.uuid == BLE_UUID_OUR_SERVICE &&
      p_evt->params.discovered_db.srv_uuid.type == BLE_UUID_TYPE_VENDOR_BEGIN) {
    m_clock.conn_handle = p_evt->conn_handle;
    for (i = 0; i < p_evt->params.discovered_db.char_count; i++) {
      if (p_evt->params.discovered_db.charateristics[i].characteristic.uuid.uuid == 
            CLOCK_READ_UUID) {
        printf("Got clock read handle\r\n");
        m_clock.clock_cccd_handle = p_evt->params.discovered_db.charateristics[i].cccd_handle;
        m_clock.clock_handle = p_evt->params.discovered_db.charateristics[i].characteristic.handle_value;
        }
      if (p_evt->params.discovered_db.charateristics[i].characteristic.uuid.uuid == 
            CLOCK_WRITE_UUID) {
        printf("Got clock write handle\r\n");
        m_clock.setclock_cccd_handle = p_evt->params.discovered_db.charateristics[i].cccd_handle;
        m_clock.setclock_handle = p_evt->params.discovered_db.charateristics[i].characteristic.handle_value;
        }
      } 
    }
  }

static void db_discovery_init(void) {
  uint32_t err_code = ble_db_discovery_init();
  APP_ERROR_CHECK(err_code);
  }

static void clockserv_init() {
  ble_uuid_t clock_uuid = { .uuid = BLE_UUID_OUR_SERVICE, .type = BLE_UUID_TYPE_BLE };
  ble_uuid128_t base_uuid = { BLE_UUID_OUR_BASE_UUID };
  memset(&m_clock,0, sizeof(m_clock));
  m_conn_handle = BLE_CONN_HANDLE_INVALID;
  m_clock.conn_handle = BLE_CONN_HANDLE_INVALID;
  m_clock.clock_cccd_handle = BLE_GATT_HANDLE_INVALID;
  m_clock.clock_handle = BLE_GATT_HANDLE_INVALID;
  m_clock.setclock_cccd_handle = BLE_GATT_HANDLE_INVALID;
  m_clock.setclock_handle = BLE_GATT_HANDLE_INVALID;
  sd_ble_uuid_vs_add(&base_uuid, &clock_uuid.type);
  ble_db_discovery_evt_register(&clock_uuid,db_discover_evt_handler);
  }

static void scan_start(void) {
  ble_gap_whitelist_t   whitelist;
  ble_gap_addr_t      * p_whitelist_addr[BLE_GAP_WHITELIST_ADDR_MAX_COUNT];
  ble_gap_irk_t       * p_whitelist_irk[BLE_GAP_WHITELIST_IRK_MAX_COUNT];
  uint32_t              err_code;
  uint32_t              count;

  err_code = pstorage_access_status_get(&count);
  APP_ERROR_CHECK(err_code);

  if (count != 0) {
    m_memory_access_in_progress = true;
    return;
    }

  // Initialize whitelist parameters.
  whitelist.addr_count = BLE_GAP_WHITELIST_ADDR_MAX_COUNT;
  whitelist.irk_count  = 0;
  whitelist.pp_addrs   = p_whitelist_addr;
  whitelist.pp_irks    = p_whitelist_irk;

  // Request creating of whitelist.
  err_code = dm_whitelist_create(&m_dm_app_id,&whitelist);
  APP_ERROR_CHECK(err_code);

  if (((whitelist.addr_count == 0) && (whitelist.irk_count == 0)) ||
    (m_scan_mode != BLE_WHITELIST_SCAN)                        ||
    (m_whitelist_temporarily_disabled)) {
    // No devices in whitelist, hence non selective performed.
    m_scan_param.active       = 0;            // Active scanning set.
    m_scan_param.selective    = 0;            // Selective scanning not set.
    m_scan_param.interval     = SCAN_INTERVAL;// Scan interval.
    m_scan_param.window       = SCAN_WINDOW;  // Scan window.
    m_scan_param.p_whitelist  = NULL;         // No whitelist provided.
    m_scan_param.timeout      = 0x0000;       // No timeout.
    }
  else {
    // Selective scanning based on whitelist first.
    m_scan_param.active       = 0;            // Active scanning set.
    m_scan_param.selective    = 1;            // Selective scanning not set.
    m_scan_param.interval     = SCAN_INTERVAL;// Scan interval.
    m_scan_param.window       = SCAN_WINDOW;  // Scan window.
    m_scan_param.p_whitelist  = &whitelist;   // Provide whitelist.
    m_scan_param.timeout      = 0x001E;       // 30 seconds timeout.
    }

  err_code = sd_ble_gap_scan_start(&m_scan_param);
  APP_ERROR_CHECK(err_code);
  }

static void uart_error_handler(app_uart_evt_t * p_event) {
  if (p_event->evt_type == APP_UART_COMMUNICATION_ERROR) {
    APP_ERROR_HANDLER(p_event->data.error_communication);
    }
  else if (p_event->evt_type == APP_UART_FIFO_ERROR) {
    APP_ERROR_HANDLER(p_event->data.error_code);
    }
  }

static void uart_init() {
  uint32_t err_code;
  const app_uart_comm_params_t comm_params = {
    RX_PIN_NUMBER,
    TX_PIN_NUMBER,
    RTS_PIN_NUMBER,
    CTS_PIN_NUMBER,
    APP_UART_FLOW_CONTROL_ENABLED,
    false,
    UART_BAUDRATE_BAUDRATE_Baud115200
    };
  APP_UART_FIFO_INIT(&comm_params,
    UART_RX_BUF_SIZE,
    UART_TX_BUF_SIZE,
    uart_error_handler,
    APP_IRQ_PRIORITY_LOW,
    err_code);
  APP_ERROR_CHECK(err_code);
  }

static void timer_handler(void * p_context) {
  UNUSED_PARAMETER(p_context);
  if (m_conn_handle != BLE_CONN_HANDLE_INVALID && m_clock.clock_handle != BLE_GATT_HANDLE_INVALID) {
     // try to read the clock handle
     uint32_t err_code;
     err_code = sd_ble_gattc_read(m_conn_handle,m_clock.clock_handle,0); 
     printf("Read request error code %d\r\n",(int)err_code);
     }
  // clock += 1;
  // gpioToggle(22);
  }
static void timers_init(void) {
  APP_TIMER_INIT(APP_TIMER_PRESCALER, APP_TIMER_OP_QUEUE_SIZE, false);
  app_timer_create(&timer_id, APP_TIMER_MODE_REPEATED, timer_handler);
  }
static void timers_start(void) {
  app_timer_start(timer_id,APP_TIMER_TICKS(1000,APP_TIMER_PRESCALER),NULL);
  }

static void power_manage(void) {
  uint32_t err_code = sd_app_evt_wait();
  APP_ERROR_CHECK(err_code);
  }

static void softdevice_init() {   
  uint8_t ison = false;
  sd_softdevice_is_enabled(&ison);
  if (ison) return;
  SOFTDEVICE_HANDLER_INIT(NRF_CLOCK_LFCLKSRC_SYNTH_250_PPM, false);
  }

int main(void) {
  uint8_t i;
  gpioInit();
  gpioOn(18);
  gpioteInit();
  for (i=0;i<10;i++) nrf_delay_ms(1000);
  uart_init();
  gpioOff(18);
  timers_init();
  softdevice_init();
  gpioOn(19);
  ble_stack_init();
  device_manager_init(false);
  db_discovery_init();
  timers_start();
  clockserv_init();
  scan_start();
  printf("\n\rScanning launched\n\r");
  for (;; )
    { power_manage(); }
  }
