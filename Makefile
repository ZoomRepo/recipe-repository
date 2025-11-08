.PHONY: env run_app run_app_production run_scraper migrate rerun_failures

env:
	@if [ ! -d "venv" ]; then \
		echo "⚙️ Creating virtual environment..."; \
		python3 -m venv venv; \
	else \
		echo "✅ venv already exists"; \
	fi
	@. venv/bin/activate && \
		echo "Installing requirements..." && \
		pip install -r requirements.txt 
	export FLASK_ENV=development FLASK_DEBUG=1
	export TEMP_LOGIN_ENABLED=true
	export NEXT_PUBLIC_TEMP_LOGIN_ENABLED=true
	export LOGIN_EMAIL_SENDER=no.reply@findmyflavour.com
	export LOGIN_SESSION_SECRET=f!ndmyZ@m61@nCh3f
	export SMTP_HOST=smtp.zoho.eu 
	export SMTP_PORT=465 
	export SMTP_USERNAME=no.reply@findmyflavour.com 
	export SMTP_PASSWORD=xul98qVUK%$uluJu 
	export SMTP_SECURE=true 
	echo "Development environment has been successfully setup!"

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
		PORT=$${PORT:-8000} && \
		waitress-serve --listen=0.0.0.0:$${PORT} webapp.wsgi:app

run_scraper:
	@if [ ! -d "venv" ]; then \
			echo "❌ venv not found. Run 'make setup' first."; \
			exit 1; \
	fi
	@. venv/bin/activate && \
			export FLASK_DEBUG=1 && export FLASK_ENV=development && \
			python -m scraper.cli --config config/scraper_templates.json

migrate:
	@if [ ! -d "venv" ]; then \
			echo "❌ venv not found. Run 'make setup' first."; \
			exit 1; \
	fi
	@. venv/bin/activate && \
			python -m scraper.cli --migrate-only

rerun_failures:
	@if [ ! -d "venv" ]; then \
			echo "❌ venv not found. Run 'make setup' first."; \
			exit 1; \
	fi
	@. venv/bin/activate && \
			export FLASK_DEBUG=1 && export FLASK_ENV=development && \
			python -m scraper.cli --config config/scraper_templates.json --rerun-failures

compile_scraping_failures:
	python3 scraper/scripts/compile_scraping_failures.py

run_production:
	@if [ ! -d "venv" ]; then \
		echo "❌ venv not found. Run 'make setup' first."; \
		exit 1; \
	fi
	cd findmyrecipe-web-app && npm run build && \
	npm run start -- -p 3232