#include <stdbool.h>
#include <stdint.h>
#include "nrf_delay.h"
#include "nrf_gpio.h"
#include "boards.h"
#include "app_error.h"
#include "sdk_errors.h"
#include "app_timer.h"
#include "app_util_platform.h"
#include "softdevice_handler.h"
#include "bsp.h"

/*Timer initalization parameters*/   
#define OP_QUEUE_SIZE  3
#define APP_TIMER_PRESCALER 0 

const uint8_t leds_list[5] = {18,19,20,21,22};
static uint8_t counter = 0;
// static uint8_t subcounter = 0;
APP_TIMER_DEF(timer_id);

void bsp_evt_handler(bsp_event_t evt) {
  bool result;
  bsp_button_is_pressed(BUTTON_1,&result);
  switch (evt) {
    case BSP_EVENT_KEY_1:
      counter = 0;
      break;
    default: return; 
      }
    // bsp_indication_text_set(actual_state, indications_list[actual_state]);
    }
void bsp_configuration() {
  bsp_init(BSP_INIT_BUTTONS,APP_TIMER_TICKS(100, APP_TIMER_PRESCALER),bsp_evt_handler);
  bsp_buttons_enable();
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
  bsp_configuration();
  app_timer_create(&timer_id,APP_TIMER_MODE_REPEATED,timer_handler);
  app_timer_start(timer_id,APP_TIMER_TICKS(10000,APP_TIMER_PRESCALER),NULL);
  while (true) {
    __WFE();
    }
  }
