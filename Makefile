APP_FILE = main
APP_INSTANCE = app
PORT = 8000

hello:
	echo "Hello, this is my first make command"

run:
	cd src && uv run uvicorn $(APP_FILE):$(APP_INSTANCE) --reload --host 0.0.0.0 --port $(PORT)

test_service:
	cd src && python3 tests/test_services.py