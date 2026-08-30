.PHONY: install up down initdb api dashboard

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

dashboard:
	streamlit run dashboard/app.py
