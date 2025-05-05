# Include a local .env file if it exists, ignoring errors if it doesn't
-include .env
# Export the variables from the .env file so sub-processes (like curl) can see them
export $(shell sed 's/=.*//' .env 2>/dev/null)

.PHONY: run env setup test-post-data-auth

# --- Default Variables (used if not set in .env or environment) ---
API_BASE_URL ?= http://127.0.0.1:5000
# Default Authentication Key (should be overridden in .env for security)
SECRET_AUTH_KEY ?= mysecretkey
# Default test data (can be overridden in .env)
TEST_ITEM_DATA ?= '{"message": "Default test data"}'

# --- Main Targets ---
default: run

env:
	@echo "Activating virtual environment and setting env vars..."
	@source venv/Scripts/activate && \
	export FLASK_APP=app.py && \
	export FLASK_ENV=development

run: env
	@echo "Starting Flask development server (ensure venv is active)..."
	# SECRET_AUTH_KEY を Flask アプリケーションに環境変数として渡す
	SECRET_AUTH_KEY=$(SECRET_AUTH_KEY) flask run --host=0.0.0.0 --port=5000 $(RUN_ARGS)

setup:
	pip install -r requirements.txt

# --- API Test Targets ---

# Target to send a POST request to /data with authentication
# Reads API_BASE_URL, SECRET_AUTH_KEY, and TEST_ITEM_DATA from .env or uses defaults
# Usage: make test-post-data-auth
test-post-data-auth:
	@echo "Sending POST request to $(API_BASE_URL)/data with auth key..."
	@echo "Data: $(TEST_ITEM_DATA)"
	# Check if API_BASE_URL is set
	# If not set, print an error message and exit
	curl -X POST \
	 -H "Content-Type: application/json" \
	 -H "X-Auth-Key: $(SECRET_AUTH_KEY)" \
	 -d $(TEST_ITEM_DATA) \
	 $(API_BASE_URL)/data
	@echo "" # Add a newline for better readability

