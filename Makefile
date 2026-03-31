PYTHON ?= python3
GAME_PATH ?=
UNKNOWN_POLICY ?= prompt
ASSET_MODE ?= manifest
RENDER_MODE ?= png
PYTHON_DEPS ?= .python_packages
RUN_PYTHONPATH := $(abspath src):$(abspath $(PYTHON_DEPS))

.PHONY: install check-update update validate

install:
	$(PYTHON) -m pip install --target "$(PYTHON_DEPS)" --upgrade vdf vpk

check-update:
	PYTHONPATH="$(RUN_PYTHONPATH):$${PYTHONPATH:-}" CS2_GAME_PATH="$(GAME_PATH)" $(PYTHON) -m cs2_skins_api check-update

update:
	PYTHONPATH="$(RUN_PYTHONPATH):$${PYTHONPATH:-}" CS2_GAME_PATH="$(GAME_PATH)" CS2_UNKNOWN_POLICY="$(UNKNOWN_POLICY)" CS2_ASSET_MODE="$(ASSET_MODE)" CS2_RENDER_MODE="$(RENDER_MODE)" $(PYTHON) -m cs2_skins_api update

validate:
	PYTHONPATH="$(RUN_PYTHONPATH):$${PYTHONPATH:-}" $(PYTHON) -m unittest discover -s tests -q
