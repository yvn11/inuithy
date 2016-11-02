## Makefile for Inuithy
# Author: Zex Li <top_zlynch@yahoo.com>
#
PROJECT		           := Inuithy
VERSION		           := 0.0.1

include makefiles/predef.mk
include makefiles/pack.mk

#export PYTHONPATH=/opt/inuithy

.PHONY: $(VERSION_PATH) $(OUTPUT_TAR_PATH) $(BUILD) clean version sample_config traffic_config_chk run_controller run_tsh $(LOGBASE) install run_agent run_mosquitto

all: $(OUTPUT_TAR_PATH)

version: $(VERSION_PATH)

clean:
	$(ECHO) "-----------------Cleaning-------------------"
	$(FIND) . -name *.pyc -delete 
	$(FIND) . -name __pycache__ -exec rm -rf {} \;
	$(RM) $(VERSION_PATH)
	$(RM) $(BUILD)

sample_config: inuithy/util/config_manager.py
	$(PYTHON) $<

traffic_config_chk: inuithy/common/traffic.py
	$(PYTHON) $<

run_controller: inuithy/controller.py
	$(ECHO) "" > $(LOGPATH)
	$(PYTHON) $<

run_tsh: inuithy/controller.py
	$(ECHO) "" > $(LOGPATH)
	$(PYTHON) $<

run_agent: inuithy/agent.py
	$(PYTHON) $<

run_mosquitto:
	mosquitto -c $(MOSQUITTO_CONFIG)

run_mongod:
	mongod -f $(MONGODB_CONFIG)

logmon:
	$(TAILMON) $(LOGPATH)

run_all_agents:
	ssh root@127.0.0.1 "pushd $(PROJECT_PATH);nohup $(PYTHON) inuithy/agent.py" &

viewlog:
	vim $(LOGPATH)

sfood: $(BUILD_DOCS)
	$(SFOOD) --follow --internal inuithy | sfood-graph > $(BUILD_DOCS)/inuithy.dot
	$(DOT) -Tps $(BUILD_DOCS)/inuithy.dot > $(BUILD_DOCS)/inuithy.ps
	$(PS2PDF) $(BUILD_DOCS)/inuithy.ps $(BUILD_DOCS)/inuithy.pdf
	$(RM) $(BUILD_DOCS)/inuithy.dot $(BUILD_DOCS)/inuithy.ps

install: $(LOGPATH)
	

	
