.PHONY: install up down initdb api frontend-install frontend

install:
	pip install -r requirements.txt

up:
	docker compose up -d

down:
	docker compose down

initdb:
	python -c "from storage.database import init_db; init_db(); print('DB initialized')"

api:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

frontend-install:
	npm install --prefix frontend

frontend:
	npm run dev --prefix frontend
