#include "nrf.h"
#include "nrf_gpio.h"
#include "nrf_drv_config.h"
#include "nrf_drv_rtc.h"
#include "nrf_drv_clock.h"
#include "boards.h"
#include <stdbool.h>
#include <stdint.h>

#define COMPARE_COUNTERTIME  (3UL)                                       

const uint8_t leds_list[5] = {18,19,20,21,22};
const nrf_drv_rtc_t rtc = NRF_DRV_RTC_INSTANCE(0);
static uint8_t counter = 0;
static uint8_t subcounter = 0;

static void lfclk_config() {
  nrf_drv_clock_init(NULL);
  nrf_drv_clock_lfclk_request();
  };
static void rtc_handler(nrf_drv_rtc_int_type_t int_type) {
  uint8_t i;
  uint32_t pins;
  if (int_type == NRF_DRV_RTC_INT_TICK) {
    subcounter++;
    if (subcounter % 8 != 0) return;
    counter++;
    pins = nrf_gpio_pin_read(16);     
    if (!pins) counter = 0;
    for (i=0;i<5;i++) {
      if (counter & (1<<i)) nrf_gpio_pin_set(leds_list[i]);
      else nrf_gpio_pin_clear(leds_list[i]);
      }
    }
  }
static void rtc_config() {
  nrf_drv_rtc_init(&rtc,NULL,rtc_handler);
  nrf_drv_rtc_tick_enable(&rtc,true);
  // Set compare channel to trigger interrupt after COMPARE_COUNTERTIME seconds
  nrf_drv_rtc_cc_set(&rtc,0,COMPARE_COUNTERTIME*RTC0_CONFIG_FREQUENCY,true);
  nrf_drv_rtc_enable(&rtc);
  }

int main(void) {
  uint8_t i;
  for (i=0;i<5;i++) nrf_gpio_cfg_output(leds_list[i]);  
  nrf_gpio_cfg_input(16,NRF_GPIO_PIN_NOPULL);
  lfclk_config();
  rtc_config();
  while (true) {
    __SEV();
    __WFE();
    __WFE();
    }
  }
