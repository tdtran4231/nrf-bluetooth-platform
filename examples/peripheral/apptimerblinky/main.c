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

static void lfclk_config() {
  nrf_drv_clock_init(NULL);
  nrf_drv_clock_lfclk_request();
  };
static void rtc_handler(nrf_drv_rtc_int_type_t int_type) {
  uint8_t i;
  uint32_t pins;
  counter++;
  if (int_type == NRF_DRV_RTC_INT_TICK) {
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

/***************************************
#include "nrf.h"
#include "nrf_gpio.h"
#include "nrf_drv_config.h"
#include "nrf_drv_rtc.h"
#include "nrf_drv_clock.h"
#include "boards.h"
#include "app_error.h"
#include <stdint.h>
#include <stdbool.h>

#define COMPARE_COUNTERTIME  (3UL)                                       

#ifdef BSP_LED_0
    #define TICK_EVENT_OUTPUT     BSP_LED_0                        
#endif
#ifndef TICK_EVENT_OUTPUT
    #error "Please indicate output pin"
#endif
#ifdef BSP_LED_1
    #define COMPARE_EVENT_OUTPUT   BSP_LED_1                 
#endif
#ifndef COMPARE_EVENT_OUTPUT
    #error "Please indicate output pin"
#endif

const nrf_drv_rtc_t rtc = NRF_DRV_RTC_INSTANCE(0); 

static void rtc_handler(nrf_drv_rtc_int_type_t int_type)
{
    if (int_type == NRF_DRV_RTC_INT_COMPARE0)
    {
        nrf_gpio_pin_toggle(COMPARE_EVENT_OUTPUT);
    }
    else if (int_type == NRF_DRV_RTC_INT_TICK)
    {
        nrf_gpio_pin_toggle(TICK_EVENT_OUTPUT);
    }
}

static void leds_config(void)
{
    LEDS_CONFIGURE(((1<<COMPARE_EVENT_OUTPUT) | (1<<TICK_EVENT_OUTPUT)));
    LEDS_OFF((1<<COMPARE_EVENT_OUTPUT) | (1<<TICK_EVENT_OUTPUT));
}

static void lfclk_config(void)
{
    ret_code_t err_code = nrf_drv_clock_init(NULL);
    APP_ERROR_CHECK(err_code);

    nrf_drv_clock_lfclk_request();
}

static void rtc_config(void)
{
    uint32_t err_code;

    //Initialize RTC instance
    err_code = nrf_drv_rtc_init(&rtc, NULL, rtc_handler);
    APP_ERROR_CHECK(err_code);

    //Enable tick event & interrupt
    nrf_drv_rtc_tick_enable(&rtc,true);

    //Set compare channel to trigger interrupt after COMPARE_COUNTERTIME seconds
    err_code = nrf_drv_rtc_cc_set(&rtc,0,COMPARE_COUNTERTIME*RTC0_CONFIG_FREQUENCY,true);
    APP_ERROR_CHECK(err_code);

    //Power on RTC instance
    nrf_drv_rtc_enable(&rtc);
}

int main(void)
{
    leds_config();

    lfclk_config();

    rtc_config();

    while (true)
    {
        __SEV();
        __WFE();
        __WFE();
    }
}
*****************/
