.PHONY: run test coverage badge clean

# ---- Переменные ----
PYTHON=python3
COVERAGE_FILE=.coverage_value
BADGE_FILE=coverage_badge.md

# ---- Генерация ролей ----
generate:
	$(PYTHON) tools/generate_roles.py

# ---- Форматирование ----
format:
	black adapters
	black config
	black connection
	black engine
	black game_info
	black tests
	black tools
	black utils

# ---- Запуск ----
run:
	$(PYTHON) -m main

# ---- Тесты ----
test:
	pytest

test-infra:
	pytest tests/test_connection
	pytest tests/test_utils

test-frontend:
	pytest tests/test_adapters

test-backend:
	pytest tests/test_dispatcher
	pytest tests/test_engine

test-core:
	pytest tests/test_dispatcher/test_night_action.py
	pytest tests/test_engine/test_phases/test_night.py
	pytest tests/test_engine/test_services/test_night_resolution.py
	pytest tests/test_engine/test_services/test_victory.py

# ---- Coverage (всё сразу) ----
coverage:
	coverage run -m pytest
	coverage report -m
	coverage html
	$(MAKE) badge


# ---- Генерация бейджа ----
badge:
	@coverage report | grep TOTAL | awk '{print $$4}' | sed 's/%//' > $(COVERAGE_FILE)
	@COV=$$(cat $(COVERAGE_FILE)); \
	if [ $$COV -ge 95 ]; then COLOR=brightgreen; \
	elif [ $$COV -ge 90 ]; then COLOR=green; \
	elif [ $$COV -ge 80 ]; then COLOR=yellowgreen; \
	elif [ $$COV -ge 70 ]; then COLOR=yellow; \
	elif [ $$COV -ge 50 ]; then COLOR=orange; \
	else COLOR=red; fi; \
	BADGE="![Coverage](https://img.shields.io/badge/coverage-$$COV%25-$$COLOR)"; \
	echo $$BADGE > $(BADGE_FILE); \
	sed -i '/COVERAGE_BADGE_START/,/COVERAGE_BADGE_END/c\
<!-- COVERAGE_BADGE_START -->\
'$$BADGE'\
<!-- COVERAGE_BADGE_END -->' README.md

# ---- Очистка ----
clean:
	rm -rf htmlcov .coverage $(COVERAGE_FILE) $(BADGE_FILE)
