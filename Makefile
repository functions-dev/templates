.PHONY: test test-go test-node test-python test-quarkus test-rust test-springboot test-typescript

LOG := test-results.log
START_TIME := $(shell date +%s%3N)

# Skipped templates:
#   go/blog — Hugo theme is a broken submodule, func create doesn't fetch submodules
#   python/llamacpp, mcp, mcp-ollama, mcp-ollama-rag, ollama-client — need external services or have broken tests
GO_SKIP := blog
PYTHON_SKIP := llamacpp mcp mcp-ollama mcp-ollama-rag ollama-client

# Run tests for each template in a language directory.
# For each template: check skip list, run test command, print colored result with timing.
# Detailed output goes to LOG file; PASS/FAIL/SKIP printed to stdout.
# Args: $(1)=language dir  $(2)=space-separated skip list  $(3)=test command
define run_tests
	@for dir in $(1)/*/; do \
		t=$$(basename $$dir); \
		skip=false; for s in $(2); do [ "$$t" = "$$s" ] && skip=true && break; done; \
		if [ "$$skip" = "true" ]; then \
			printf "\033[33mSKIP\033[0m %s\n" "$$dir"; echo "SKIP $$dir" >> $(LOG); continue; \
		fi; \
		start=$$(date +%s%3N); \
		if (cd $$dir && $(3)) >> $(LOG) 2>&1; then \
			ms=$$(( $$(date +%s%3N) - $$start )); \
			printf "\033[32mPASS\033[0m %s (%d.%03ds)\n" "$$dir" "$$((ms/1000))" "$$((ms%1000))"; \
			echo "PASS $$dir ($${ms}ms)" >> $(LOG); \
		else \
			ms=$$(( $$(date +%s%3N) - $$start )); \
			printf "\033[31mFAIL\033[0m %s (%d.%03ds)\n" "$$dir" "$$((ms/1000))" "$$((ms%1000))"; \
			echo "FAIL $$dir ($${ms}ms)" >> $(LOG); \
		fi; \
	done
endef

test: clean-log test-go test-node test-python test-quarkus test-rust test-springboot test-typescript summary

clean-log:
	@rm -f $(LOG)
	@echo "Running tests..."

test-go:           ; $(call run_tests,go,$(GO_SKIP),go test -count=1 ./...)
test-node:         ; $(call run_tests,node,,npm install --silent && npm test && rm -rf node_modules)
test-python:       ; $(call run_tests,python,$(PYTHON_SKIP),python -m venv .venv && .venv/bin/pip install -q '.[dev]' && .venv/bin/python -m pytest tests/ && rm -rf .venv)
test-quarkus:      ; $(call run_tests,quarkus,,mvn test -q)
test-rust:         ; $(call run_tests,rust,,cargo test)
test-springboot:   ; $(call run_tests,springboot,,mvn test -q)
test-typescript:   ; $(call run_tests,typescript,,npm install --silent && npm test && rm -rf node_modules build)

summary:
	@echo ""
	@echo "=== Test Summary ==="
	@passed=$$(grep -c "^PASS" $(LOG) || true); \
	failed=$$(grep -c "^FAIL" $(LOG) || true); \
	skipped=$$(grep -c "^SKIP" $(LOG) || true); \
	ms=$$(( $$(date +%s%3N) - $(START_TIME) )); \
	printf "\033[32m$$passed passed\033[0m, \033[31m$$failed failed\033[0m, \033[33m$$skipped skipped\033[0m in %d.%03ds\n" "$$((ms/1000))" "$$((ms%1000))"; \
	echo "Full log: $(LOG)"; \
	if [ "$$failed" -gt 0 ]; then echo ""; echo "=== Failed ==="; grep "^FAIL" $(LOG); exit 1; fi

