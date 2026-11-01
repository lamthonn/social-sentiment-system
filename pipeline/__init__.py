"""Pipeline xử lý dữ liệu theo PROJECT.md: thu thập -> làm sạch -> dataset/gán nhãn -> lưu trữ ->
huấn luyện -> đánh giá -> dự đoán/ứng dụng -> giám sát. Chạy: python -m pipeline --help"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATASETS_DIR = DATA_DIR / "datasets"
MODELS_DIR = DATA_DIR / "models"
