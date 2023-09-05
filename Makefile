TOPLEVEL_LANG ?= verilog
# GUI ?= 1
# WAVES?=1
SIM ?= icarus #icarus #questa
PWD=$(shell pwd)


ifeq ($(TOPLEVEL_LANG),verilog)
    VERILOG_SOURCES = $(PWD)/DUT.sv #* for all files

else ifeq ($(TOPLEVEL_LANG),vhdl)
    VHDL_SOURCES = $(PWD)/or_gate.vhdl
else
    $(error A valid value (verilog or vhdl) was not provided for TOPLEVEL_LANG=$(TOPLEVEL_LANG))
endif

TOPLEVEL := tinyalu #Module_NAME
MODULE   := main #File_Python_Name

include $(shell cocotb-config --makefiles)/Makefile.sim