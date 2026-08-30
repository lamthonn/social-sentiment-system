"""Khung dashboard Streamlit (Giai đoạn 0)."""
import streamlit as st

st.set_page_config(page_title="Social Sentiment Dashboard", layout="wide")
st.title("Hệ thống phân tích cảm xúc & xu hướng mạng xã hội")
st.caption("Bản khung (Giai đoạn 0) - biểu đồ sẽ được bổ sung ở giai đoạn sau.")

col1, col2, col3 = st.columns(3)
col1.metric("Tổng bài thu thập", 0)
col2.metric("Đã phân tích", 0)
col3.metric("Chủ đề nổi", 0)

st.info("Kết nối dữ liệu thật sẽ được thêm ở Giai đoạn 3-4.")
