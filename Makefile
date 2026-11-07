.PHONY: install up down initdb migrate api frontend-install frontend collect-schedule datasets train-baselines train-visobert train-more pipeline experiments backup test

install:
	pip install -r requirements.txt

up:
	docker compose up -d

down:
	docker compose down

initdb:
	python -c "from storage.database import init_db; init_db(); print('DB initialized')"

migrate:  # tạo bảng mới + nâng cấp bảng cũ (chạy lại nhiều lần không sao)
	python -m storage.migrate

api:
	uvicorn api.main:app --reload --host 127.0.0.1 --port 8000  # chỉ trong máy; trình duyệt đi qua Vite (https khi có data/certs)

frontend-install:
	npm install --prefix frontend

frontend:
	npm run dev --prefix frontend

collect-schedule:
	python -m collector schedule

# ===== Pipeline (xem PROJECT.md mục 4) =====
datasets:  # PL-03: tải + làm sạch UIT-VSFC, UIT-VSMEC
	python -m pipeline datasets

train-baselines:  # PL-05/06: TF-IDF + LR/SVM cho cả 2 bài toán (vài chục giây mỗi mô hình)
	python -m pipeline train --task sentiment --model tfidf-lr
	python -m pipeline train --task sentiment --model tfidf-svm
	python -m pipeline train --task emotion --model tfidf-lr
	python -m pipeline train --task emotion --model tfidf-svm

train-visobert:  # PL-05/06: fine-tune ViSoBERT (cần GPU, ~15-20 phút mỗi bài toán trên GTX 1050 Ti)
	python -m pipeline train --task sentiment --model visobert
	python -m pipeline train --task emotion --model visobert

train-more:  # BiLSTM (vài chục giây) + PhoBERT-base-v2 (cần GPU, tách từ bằng underthesea)
	python -m pipeline train --task sentiment --model bilstm
	python -m pipeline train --task emotion --model bilstm
	python -m pipeline train --task sentiment --model phobert
	python -m pipeline train --task emotion --model phobert

experiments:  # thực nghiệm bổ sung -> data/experiments/*.json (xem ở webapp, mục Mô hình)
	python -m experiments.poisoning
	python -m experiments.topics_eval
	python -m experiments.dp
	python -m experiments.robustness
	python -m experiments.llm
	python -m experiments.perf
	python -m experiments.federated
	python -m experiments.security_eval

backup:  # pg_dump -> data/backups/ (giữ 14 bản mới nhất)
	python -m storage.backup

pipeline:  # thu thập -> làm sạch -> dự đoán -> xu hướng -> giám sát
	python -m pipeline run

test:
	pytest tests preprocessing
