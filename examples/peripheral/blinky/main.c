#include <stdbool.h>
#include <stdint.h>
#include "nrf_delay.h"
#include "nrf_gpio.h"
#include "boards.h"

const uint8_t leds_list[5] = {18,19,20,21,22};

/*

define LEDS_OFF(leds_mask) do {  NRF_GPIO->OUTSET = (leds_mask) & (LEDS_MASK & LEDS_INV_MASK); \
                            NRF_GPIO->OUTCLR = (leds_mask) & (LEDS_MASK & ~LEDS_INV_MASK); } while (0)

define LEDS_ON(leds_mask) do {  NRF_GPIO->OUTCLR = (leds_mask) & (LEDS_MASK & LEDS_INV_MASK); \
                           NRF_GPIO->OUTSET = (leds_mask) & (LEDS_MASK & ~LEDS_INV_MASK); } while (0)

define LED_IS_ON(leds_mask) ((leds_mask) & (NRF_GPIO->OUT ^ LEDS_INV_MASK) )

define LEDS_INVERT(leds_mask) do { uint32_t gpio_state = NRF_GPIO->OUT;      \
                              NRF_GPIO->OUTSET = ((leds_mask) & ~gpio_state); \
                              NRF_GPIO->OUTCLR = ((leds_mask) & gpio_state); } while (0)

define LEDS_CONFIGURE(leds_mask) do { uint32_t pin;                  \
                                  for (pin = 0; pin < 32; pin++) \
                                      if ( (leds_mask) & (1 << pin) )   \
                                          nrf_gpio_cfg_output(pin); } while (0)

*/


int main(void) {
  uint8_t i;
  uint8_t counter = 0;
  uint32_t pins;
  for (i=0;i<5;i++) nrf_gpio_cfg_output(leds_list[i]);  
  while (true) {
    nrf_delay_ms(1000);
    counter++;
    for (i=0;i<5;i++) {
      pins = NRF_GPIO->OUT; 
      if (counter & (1<<i)) {
         pins = ~pins;
         NRF_GPIO->OUTCLR = 1 << leds_list[i]; 
         NRF_GPIO->OUTSET = 0; 
         }
      else {
         NRF_GPIO->OUTSET = 1 << leds_list[i];
         NRF_GPIO->OUTCLR = 0;
         }
      }
    }
  }
