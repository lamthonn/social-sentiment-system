# Module tiền xử lý NLP tiếng Việt - Giai đoạn 1

Chuẩn hoá text thô (nội dung bài đăng/bình luận trong bảng `raw_posts`) thành dạng sẵn
sàng cho fine-tune/suy luận mô hình cảm xúc (PhoBERT/ViSoBERT ở bước tiếp theo).

## Pipeline (thứ tự bắt buộc)

```
raw text
  -> clean_text()          làm sạch: gỡ HTML entity, chuẩn hoá Unicode (NFC), bỏ URL,
                            rút gọn ký tự/dấu câu lặp quá mức (VD "đẹppppp" -> "đẹp")
  -> normalize_teencode()   thay teencode/viết tắt phổ biến bằng từ chuẩn (VD "dc" -> "được")
  -> split_sentences()      tách câu (dùng underthesea)
  -> tokenize()             tách từ - ghép từ nhiều âm tiết bằng "_" (VD "học_sinh"),
                            đúng định dạng input mà PhoBERT/ViSoBERT cần
```

Đảo thứ tự sẽ cho kết quả sai - VD tách từ trước khi chuẩn hoá teencode sẽ khiến "ko" bị
coi là 1 từ độc lập thay vì được thay bằng "không" trước.

## Dùng thử

```python
from preprocessing import preprocess

result = preprocess("mik thấy sp này dc lắm, giá hơi caooo nhưng chất lượng oke!!!")
result.normalized_text     # "mình thấy sp này được lắm, giá hơi cao nhưng chất lượng oke!"
result.sentences           # đã tách câu
result.tokenized_text      # "mình thấy sp này được lắm , giá hơi cao nhưng chất_lượng oke !"
```

Chạy thử nhanh nhiều câu mẫu:
```bash
python -c "
from preprocessing import preprocess
print(preprocess('Ko biết sao dạo này giá vàng tăng dữ vậy').tokenized_text)
"
```

## Các file

- `cleaner.py` - làm sạch text thô (HTML entity, URL, Unicode NFC, ký tự/dấu câu lặp).
- `teencode.py` - từ điển + hàm chuẩn hoá teencode/viết tắt phổ biến (`TEENCODE_MAP`).
- `tokenizer.py` - tách câu & tách từ bằng `underthesea` (`sent_tokenize`/`word_tokenize`).
- `pipeline.py` - ghép 3 bước trên thành 1 hàm `preprocess()` duy nhất.

## Giới hạn đã biết

- `TEENCODE_MAP` không thể phủ hết mọi từ lóng MXH (biến đổi liên tục theo thời gian/trend
  - xem `docs/crawling_qna_design.md` mục 12 & 14) - mở rộng dần khi phát hiện từ mới xuất
  hiện nhiều trong dữ liệu thực tế thu thập được.
- Một số mục viết tắt 1 ký tự (`t`, `h`, `r`, `z`, `j`, `k`) có thể khớp nhầm trong ngữ
  cảnh không phải chat MXH (tên biến, đơn vị đo, chữ cái đơn lẻ...) - chấp nhận được cho
  dữ liệu bình luận MXH nhưng cần lưu ý nếu tái sử dụng module này cho loại văn bản khác.
- Emoji/icon cảm xúc (`<3`, `=))`, 😂...) được giữ nguyên, không bị `clean_text` chỉnh sửa
  - vì mang tín hiệu cảm xúc quan trọng cho mô hình sentiment ở bước sau.

## Bước tiếp theo (chưa làm)

- Tải bộ dữ liệu UIT-VSMEC/UIT-VSFC, áp `preprocess()` lên tập train.
- Viết pipeline fine-tune PhoBERT/ViSoBERT trong `models/sentiment/` dùng dữ liệu đã qua
  bước tiền xử lý này.
