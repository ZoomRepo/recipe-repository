.PHONY: setup run_app run_app_production run_scraper

setup:
	@if [ ! -d "venv" ]; then \
		echo "⚙️ Creating virtual environment..."; \
	python3 -m venv venv \
	echo "Activating environment..." \
	source ./venv/bin/activate \
	echo "Installing requirements..." \
	pip install -r requirements.txt \
	echo "Development environment has been successfully setup!" \
	else \
		echo "✅ venv already exists"; \
	fi

run_app:
	@if [ ! -d "venv" ]; then \
		echo "❌ venv not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@. venv/bin/activate && \
	python3 -m webapp

run_app_production:
	@if [ ! -d "venv" ]; then \
		echo "❌ venv not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@. venv/bin/activate && \
		export FLASK_ENV=production FLASK_DEBUG=0 && \
		python3 -m webapp

run_scraper:
	@if [ ! -d "venv" ]; then \
		echo "❌ venv not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@. venv/bin/activate && \
		export FLASK_DEBUG=1 && export FLASK_ENV=development && \
		python -m scraper.cli --config config/scraper_templates.json
