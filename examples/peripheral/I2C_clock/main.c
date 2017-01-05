#include <stdio.h>
#include "boards.h"
#include "app_util_platform.h"
#include "app_uart.h"
#include "app_error.h"
#include "nrf_drv_twi.h"
#include "nrf_delay.h"

/*UART buffer size. */
#define UART_TX_BUF_SIZE 256
#define UART_RX_BUF_SIZE 1

#define AT24C32_ADDR        (0xAEU >> 1)
#define DS3231_ADDR         (0xD0U >> 1)

static const nrf_drv_twi_t m_twi_port = NRF_DRV_TWI_INSTANCE(0);
static char buffer[8];
static uint8_t clockvalue[7];
static volatile bool xfer_pending;
static volatile bool clockmode;

/* UART events handler */
static void uart_events_handler(app_uart_evt_t * p_event) {
  switch (p_event->evt_type) {
    case APP_UART_COMMUNICATION_ERROR:
      APP_ERROR_HANDLER(p_event->data.error_communication);
      break;
    case APP_UART_FIFO_ERROR:
      APP_ERROR_HANDLER(p_event->data.error_code);
      break;
    default:
      break;
    }
  }

/* UART initialization */
static void uart_config(void) {
  uint32_t err_code;
  const app_uart_comm_params_t comm_params = {
    RX_PIN_NUMBER,
    TX_PIN_NUMBER,
    RTS_PIN_NUMBER,
    CTS_PIN_NUMBER,
    APP_UART_FLOW_CONTROL_DISABLED,
    false,
    UART_BAUDRATE_BAUDRATE_Baud115200
    };
  APP_UART_FIFO_INIT(&comm_params,
    UART_RX_BUF_SIZE,
    UART_TX_BUF_SIZE,
    uart_events_handler,
    APP_IRQ_PRIORITY_LOW,
    err_code);
  APP_ERROR_CHECK(err_code);
  }

void AT24C32_setaddr() {
  ret_code_t err_code;
  uint8_t setaddr[2] = { 0x0f, 0x20 };
  err_code = nrf_drv_twi_tx(&m_twi_port,AT24C32_ADDR,setaddr,2,true);  
  APP_ERROR_CHECK(err_code);
  }
void AT24C32_read() {
  ret_code_t err_code;
  buffer[5] = 0x00;
  err_code = nrf_drv_twi_rx(&m_twi_port,AT24C32_ADDR,(uint8_t*)buffer,5,false);  
  APP_ERROR_CHECK(err_code);
  }
void DS3231_setaddr() {
  ret_code_t err_code;
  uint8_t setaddr[1] = { 0x00 };
  err_code = nrf_drv_twi_tx(&m_twi_port,DS3231_ADDR,setaddr,1,true);  
  APP_ERROR_CHECK(err_code);
  }
void DS3231_read() {
  ret_code_t err_code;
  err_code = nrf_drv_twi_rx(&m_twi_port,DS3231_ADDR,clockvalue,7,false);  
  APP_ERROR_CHECK(err_code);
  }

/* TWI events handler */
void twi_handler(nrf_drv_twi_evt_t const * p_event, void * p_context) {   
  if (!clockmode) {
    switch(p_event->type) {
      case NRF_DRV_TWI_RX_DONE:
        xfer_pending = false;
        break;
      case NRF_DRV_TWI_TX_DONE:
        AT24C32_read();
        break;
      default:
        break;        
      }   
    }
  if (clockmode) {
    switch(p_event->type) {
      case NRF_DRV_TWI_RX_DONE:
        xfer_pending = false;
        break;
      case NRF_DRV_TWI_TX_DONE:
        DS3231_read();
        break;
      default:
        break;        
      }   
    }
  }

/* TWI initialization */
void twi_init (void) {
  ret_code_t err_code;
  const nrf_drv_twi_config_t twi_AT24C32_config = {
    .scl                = 0x01,
    .sda                = 0x00,
    .frequency          = NRF_TWI_FREQ_400K,
    .interrupt_priority = APP_IRQ_PRIORITY_HIGH
    };
  err_code = nrf_drv_twi_init(&m_twi_AT24C32, &twi_AT24C32_config,twi_handler,NULL);
  APP_ERROR_CHECK(err_code);
  nrf_drv_twi_enable(&m_twi_AT24C32);
  }

void printclock() {
  uint8_t h;
  uint8_t m;
  uint8_t s;
  uint8_t D;
  uint8_t M;
  uint16_t Y;
  s = 10*(clockvalue[0]>>4) + (clockvalue[0]&0x0f); 
  m = 10*(clockvalue[1]>>4) + (clockvalue[1]&0x0f); 
  h = 10*((clockvalue[2]>>4)&0x03) + (clockvalue[2]&0x0f); 
  D = 10*(clockvalue[4]>>4) + (clockvalue[4]&0x0f);
  M = 10*((clockvalue[5]>>4)&0x07) + (clockvalue[5]&0x0f);
  Y = 2000 + 10*(clockvalue[6]>>4) + (clockvalue[6]&0x0f);
  printf("%d/%d/%d %d:%d:%d\n",D,M,Y,h,m,s);
  }

int main(void) {
  uart_config();
  printf("TWI AT24C32 example\n");
  twi_init();
  while(true) {
    nrf_delay_ms(1000);
    xfer_pending = true;
    clockmode = false;
    AT24C32_setaddr();
    do { __WFE(); } while (xfer_pending);        
    xfer_pending = true;
    clockmode = true;
    DS3231_setaddr();
    do { __WFE(); } while (xfer_pending);        
    printf("%s\n",buffer);
    printclock();
    }
  }
