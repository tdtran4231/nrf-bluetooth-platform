PROJECT_NAME := pca10028

NORDIC_PATH = /opt/nordic

export OUTPUT_FILENAME
#MAKEFILE_NAME := $(CURDIR)/$(word $(words $(MAKEFILE_LIST)),$(MAKEFILE_LIST))
MAKEFILE_NAME := $(MAKEFILE_LIST)
MAKEFILE_DIR := $(dir $(MAKEFILE_NAME) ) 

TEMPLATE_PATH = $(NORDIC_PATH)/components/toolchain/gcc
include $(TEMPLATE_PATH)/Makefile.posix

MK := mkdir
RM := rm -rf

#echo suspend
ifeq ("$(VERBOSE)","1")
NO_ECHO := 
else
NO_ECHO := @
endif

# Toolchain commands
CC              := '$(GNU_INSTALL_ROOT)/bin/$(GNU_PREFIX)-gcc'
AS              := '$(GNU_INSTALL_ROOT)/bin/$(GNU_PREFIX)-as'
AR              := '$(GNU_INSTALL_ROOT)/bin/$(GNU_PREFIX)-ar' -r
LD              := '$(GNU_INSTALL_ROOT)/bin/$(GNU_PREFIX)-ld'
NM              := '$(GNU_INSTALL_ROOT)/bin/$(GNU_PREFIX)-nm'
OBJDUMP         := '$(GNU_INSTALL_ROOT)/bin/$(GNU_PREFIX)-objdump'
OBJCOPY         := '$(GNU_INSTALL_ROOT)/bin/$(GNU_PREFIX)-objcopy'
SIZE            := '$(GNU_INSTALL_ROOT)/bin/$(GNU_PREFIX)-size'

#function for removing duplicates in a list
remduplicates = $(strip $(if $1,$(firstword $1) $(call remduplicates,$(filter-out $(firstword $1),$1))))

#source common to all targets
C_SOURCE_FILES += \
/opt/nordic/components/drivers_nrf/nrf_soc_nosd/nrf_soc.c \
/opt/nordic/components/libraries/fifo/app_fifo.c \
/opt/nordic/components/drivers_nrf/common/nrf_drv_common.c \
/opt/nordic/components/libraries/uart/app_uart_fifo.c \
/opt/nordic/components/drivers_nrf/twi_master/nrf_drv_twi.c \
/opt/nordic/components/libraries/util/app_util_platform.c \
/opt/nordic/components/toolchain/system_nrf51.c \
/opt/nordic/components/libraries/uart/retarget.c \
/opt/nordic/components/libraries/util/nrf_assert.c \
/opt/nordic/components/drivers_nrf/delay/nrf_delay.c \
/opt/nordic/components/drivers_nrf/uart/nrf_drv_uart.c \
/opt/nordic/components/libraries/util/app_error.c \
demo.c
#assembly files common to all targets
ASM_SOURCE_FILES  = $(NORDIC_PATH)/components/toolchain/gcc/gcc_startup_nrf51.s

#includes common to all targets
INC_PATHS  = -Iconfig
INC_PATHS += -I/opt/nordic/examples/bsp 
INC_PATHS += -I/opt/nordic/components/drivers_nrf/common 
INC_PATHS += -I/opt/nordic/components/device 
INC_PATHS += -I/opt/nordic/components/toolchain/gcc 
INC_PATHS += -I/opt/nordic/components/drivers_nrf/hal 
INC_PATHS += -I/opt/nordic/components/libraries/fifo 
INC_PATHS += -I/opt/nordic/components/drivers_nrf/delay 
INC_PATHS += -I/opt/nordic/components/drivers_nrf/uart 
INC_PATHS += -I/opt/nordic/components/libraries/uart 
INC_PATHS += -I/opt/nordic/components/drivers_nrf/twi_master 
INC_PATHS += -I/opt/nordic/components/drivers_nrf/config 
INC_PATHS += -I/opt/nordic/components/drivers_nrf/nrf_soc_nosd 
INC_PATHS += -I/opt/nordic/components/libraries/util 
INC_PATHS += -I/opt/nordic/components/toolchain 

OBJECT_DIRECTORY = _build
LISTING_DIRECTORY = $(OBJECT_DIRECTORY)
OUTPUT_BINARY_DIRECTORY = $(OBJECT_DIRECTORY)

# Sorting removes duplicates
BUILD_DIRECTORIES := $(sort $(OBJECT_DIRECTORY) $(OUTPUT_BINARY_DIRECTORY) $(LISTING_DIRECTORY) )

#flags common to all targets
CFLAGS  = -DBOARD_PCA10028
CFLAGS += -DNRF51
CFLAGS += -DSWI_DISABLE0
CFLAGS += -mcpu=cortex-m0
CFLAGS += -mthumb -mabi=aapcs --std=gnu99
CFLAGS += -Wall -Werror -O3
CFLAGS += -mfloat-abi=soft
# keep every function in separate section. This will allow linker to dump unused functions
CFLAGS += -ffunction-sections -fdata-sections -fno-strict-aliasing
CFLAGS += -fno-builtin --short-enums

# keep every function in separate section. This will allow linker to dump unused functions
LDFLAGS += -Xlinker -Map=$(LISTING_DIRECTORY)/$(OUTPUT_FILENAME).map
LDFLAGS += -mthumb -mabi=aapcs -L$(TEMPLATE_PATH) -T$(LINKER_SCRIPT)
LDFLAGS += -mcpu=cortex-m0
# let linker to dump unused sections
LDFLAGS += -Wl,--gc-sections
# use newlib in nano version
LDFLAGS += --specs=nano.specs -lc -lnosys

# Assembler flags
ASMFLAGS += -x assembler-with-cpp
ASMFLAGS += -DBOARD_PCA10028
ASMFLAGS += -DNRF51
ASMFLAGS += -DSWI_DISABLE0
#default target - first one defined
default: clean nrf51422

#building all targets
all: clean
	$(NO_ECHO)$(MAKE) -f $(MAKEFILE_NAME) -C $(MAKEFILE_DIR) -e cleanobj
	$(NO_ECHO)$(MAKE) -f $(MAKEFILE_NAME) -C $(MAKEFILE_DIR) -e nrf51422

#target for printing all targets
help:
	@echo following targets are available:
	@echo 	nrf51422
	@echo 	flash_softdevice


C_SOURCE_FILE_NAMES = $(notdir $(C_SOURCE_FILES))
C_PATHS = $(call remduplicates, $(dir $(C_SOURCE_FILES) ) )
C_OBJECTS = $(addprefix $(OBJECT_DIRECTORY)/, $(C_SOURCE_FILE_NAMES:.c=.o) )

ASM_SOURCE_FILE_NAMES = $(notdir $(ASM_SOURCE_FILES))
ASM_PATHS = $(call remduplicates, $(dir $(ASM_SOURCE_FILES) ))
ASM_OBJECTS = $(addprefix $(OBJECT_DIRECTORY)/, $(ASM_SOURCE_FILE_NAMES:.s=.o) )

vpath %.c $(C_PATHS)
vpath %.s $(ASM_PATHS)

OBJECTS = $(C_OBJECTS) $(ASM_OBJECTS)

nrf51422: OUTPUT_FILENAME := nrf51422_xxaa
nrf51422: LINKER_SCRIPT=blank.ld
nrf51422: $(BUILD_DIRECTORIES) $(OBJECTS)
	@echo Linking target: $(OUTPUT_FILENAME).out
	$(NO_ECHO)$(CC) $(LDFLAGS) $(OBJECTS) $(LIBS) -o $(OUTPUT_BINARY_DIRECTORY)/$(OUTPUT_FILENAME).out
	$(NO_ECHO)$(MAKE) -f $(MAKEFILE_NAME) -C $(MAKEFILE_DIR) -e finalize

## Create build directories
$(BUILD_DIRECTORIES):
	echo $(MAKEFILE_NAME)
	$(MK) $@

# Create objects from C SRC files
$(OBJECT_DIRECTORY)/%.o: %.c
	@echo Compiling file: $(notdir $<)
	$(NO_ECHO)$(CC) $(CFLAGS) $(INC_PATHS) -c -o $@ $<

# Assemble files
$(OBJECT_DIRECTORY)/%.o: %.s
	@echo Compiling file: $(notdir $<)
	$(NO_ECHO)$(CC) $(ASMFLAGS) $(INC_PATHS) -c -o $@ $<


# Link
$(OUTPUT_BINARY_DIRECTORY)/$(OUTPUT_FILENAME).out: $(BUILD_DIRECTORIES) $(OBJECTS)
	@echo Linking target: $(OUTPUT_FILENAME).out
	$(NO_ECHO)$(CC) $(LDFLAGS) $(OBJECTS) $(LIBS) -o $(OUTPUT_BINARY_DIRECTORY)/$(OUTPUT_FILENAME).out


## Create binary .bin file from the .out file
$(OUTPUT_BINARY_DIRECTORY)/$(OUTPUT_FILENAME).bin: $(OUTPUT_BINARY_DIRECTORY)/$(OUTPUT_FILENAME).out
	@echo Preparing: $(OUTPUT_FILENAME).bin
	$(NO_ECHO)$(OBJCOPY) -O binary $(OUTPUT_BINARY_DIRECTORY)/$(OUTPUT_FILENAME).out $(OUTPUT_BINARY_DIRECTORY)/$(OUTPUT_FILENAME).bin

## Create binary .hex file from the .out file
$(OUTPUT_BINARY_DIRECTORY)/$(OUTPUT_FILENAME).hex: $(OUTPUT_BINARY_DIRECTORY)/$(OUTPUT_FILENAME).out
	@echo Preparing: $(OUTPUT_FILENAME).hex
	$(NO_ECHO)$(OBJCOPY) -O ihex $(OUTPUT_BINARY_DIRECTORY)/$(OUTPUT_FILENAME).out $(OUTPUT_BINARY_DIRECTORY)/$(OUTPUT_FILENAME).hex

finalize: genbin genhex echosize

genbin:
	@echo Preparing: $(OUTPUT_FILENAME).bin
	$(NO_ECHO)$(OBJCOPY) -O binary $(OUTPUT_BINARY_DIRECTORY)/$(OUTPUT_FILENAME).out $(OUTPUT_BINARY_DIRECTORY)/$(OUTPUT_FILENAME).bin

## Create binary .hex file from the .out file
genhex: 
	@echo Preparing: $(OUTPUT_FILENAME).hex
	$(NO_ECHO)$(OBJCOPY) -O ihex $(OUTPUT_BINARY_DIRECTORY)/$(OUTPUT_FILENAME).out $(OUTPUT_BINARY_DIRECTORY)/$(OUTPUT_FILENAME).hex

echosize:
	-@echo ''
	$(NO_ECHO)$(SIZE) $(OUTPUT_BINARY_DIRECTORY)/$(OUTPUT_FILENAME).out
	-@echo ''

clean:
	$(RM) $(BUILD_DIRECTORIES)

cleanobj:
	$(RM) $(BUILD_DIRECTORIES)/*.o

flash: $(MAKECMDGOALS)
	@echo Flashing: $(OUTPUT_BINARY_DIRECTORY)/$<.hex
	nrfjprog --program $(OUTPUT_BINARY_DIRECTORY)/$<.hex -f nrf51  --sectorerase
	nrfjprog --reset

## Flash softdevice
flash_softdevice:
	@echo Flashing: nrf51_8.0.0_softdevice.hex
	nrfjprog --program ../../../../../../components/softdevice/s110/hex/s110_nrf51_8.0.0_softdevice.hex -f nrf51 --chiperase
	nrfjprog --reset
