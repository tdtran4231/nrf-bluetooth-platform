#include <stdbool.h>
#include <stdint.h>
#include "nrf_delay.h"
#include "nrf_gpio.h"
#include "nrf_gpiote.h"
#include "nrf_drv_gpiote.h"
#include "boards.h"
#include "app_error.h"
#include "sdk_errors.h"
#include "app_timer.h"
#include "app_util_platform.h"
#include "softdevice_handler.h"

/*Timer initalization parameters*/   
#define OP_QUEUE_SIZE  3
#define APP_TIMER_PRESCALER 0 

const uint8_t leds_list[5] = {18,19,20,21,22};
static uint8_t counter = 0;
// static uint8_t subcounter = 0;
APP_TIMER_DEF(timer_id);

static void gpioteHandler(nrf_drv_gpiote_pin_t p, nrf_gpiote_polarity_t d) {
  if (p != 16) return;
  counter = 0; 
  }

static void gpioteInit() {
  nrf_drv_gpiote_in_config_t config16 = GPIOTE_CONFIG_IN_SENSE_HITOLO(false);
  config16.pull = NRF_GPIO_PIN_PULLUP;
  if (!nrf_drv_gpiote_is_init()) nrf_drv_gpiote_init();
  nrf_drv_gpiote_in_uninit(16);
  nrf_drv_gpiote_in_init(16,&config16,gpioteHandler);
  nrf_drv_gpiote_in_event_enable(16,true);
  }  

static void timer_handler(void * p_context) {
  uint8_t i;
  UNUSED_PARAMETER(p_context);
  // subcounter++;
  // if (subcounter % 8 != 0) return;
  counter++;
  for (i=0;i<5;i++) {
    if (counter & (1<<i)) nrf_gpio_pin_set(leds_list[i]);
    else nrf_gpio_pin_clear(leds_list[i]);
    }
  }

int main(void) {
  uint8_t i;
  for (i=0;i<5;i++) nrf_gpio_cfg_output(leds_list[i]);  
  nrf_gpio_cfg_input(16,NRF_GPIO_PIN_NOPULL);
  SOFTDEVICE_HANDLER_INIT(NRF_CLOCK_LFCLKSRC_SYNTH_250_PPM, false);
  APP_TIMER_INIT(APP_TIMER_PRESCALER,OP_QUEUE_SIZE,false);
  app_timer_create(&timer_id,APP_TIMER_MODE_REPEATED,timer_handler);
  app_timer_start(timer_id,APP_TIMER_TICKS(1000,APP_TIMER_PRESCALER),NULL);
  gpioteInit();
  while (true) {
    __WFE();
    }
  }
