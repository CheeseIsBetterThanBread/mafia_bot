.PHONY: run test coverage badge clean

# ---- Переменные ----
PYTHON=python3
COVERAGE_FILE=.coverage_value
BADGE_FILE=coverage_badge.md

# ---- Запуск ----
run:
	$(PYTHON) -m main

# ---- Тесты ----
test:
	pytest

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
