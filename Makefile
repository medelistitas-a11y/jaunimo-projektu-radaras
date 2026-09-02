.PHONY: up down migrate scrape scrape-source test lint format backup restore seed logs shell

up: ## Paleisti visą programą (db + web + worker) per Docker Compose
	docker compose up --build -d
	@echo "Programa pasiekiama: http://localhost:8000"

down: ## Sustabdyti ir pašalinti konteinerius
	docker compose down

migrate: ## Pritaikyti duomenų bazės migracijas
	docker compose exec web alembic upgrade head

seed: ## Įkelti/atnaujinti šaltinių registrą iš sources.yaml
	docker compose exec web python -m app.seed.sources_seed

scrape: ## Rankinis visų įjungtų šaltinių tikrinimas
	docker compose exec web python -m app.scripts.manual_scrape

scrape-source: ## Rankinis vieno šaltinio tikrinimas: make scrape-source SOURCE=kaunas_naujienos
	docker compose exec web python -m app.scripts.manual_scrape --source $(SOURCE)

test: ## Paleisti testus (be Docker, naudoja SQLite)
	. .venv/bin/activate && python -m pytest tests/ -v

test-docker: ## Paleisti testus Docker konteineryje
	docker compose exec web pytest tests/ -v

lint: ## Ruff patikra ir formatavimo patikra
	. .venv/bin/activate && ruff check app tests && ruff format --check app tests

format: ## Automatiškai suformatuoti kodą
	. .venv/bin/activate && ruff format app tests && ruff check app tests --fix

backup: ## Sukurti PostgreSQL atsarginę kopiją į backups/
	./scripts/backup.sh

restore: ## Atkurti PostgreSQL iš kopijos: make restore FILE=backups/xxx.sql.gz
	./scripts/restore.sh $(FILE)

logs: ## Rodyti web serviso logus
	docker compose logs -f web

shell: ## Interaktyvus shell web konteineryje
	docker compose exec web bash

admin-password: ## Sugeneruoti bcrypt hash administratoriaus slaptažodžiui
	. .venv/bin/activate && python -m app.scripts.hash_password
