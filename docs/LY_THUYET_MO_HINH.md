# Cơ sở lý thuyết các mô hình sử dụng trong đề tài

Tài liệu giải thích lý thuyết của các mô hình **đang có trong mã nguồn**. Mỗi mục gồm: ý tưởng, công thức chính, cách đề tài cấu hình, ưu/nhược điểm. Mã mô hình (M-xx), bài toán (BT-xx), lần huấn luyện (R-xx) khớp với [PROJECT.md](../PROJECT.md). Số liệu lấy từ các lần chạy ngày 2026-11-01.

## Mục lục

1. [Bài toán và cách đánh giá](#1-bài-toán-và-cách-đánh-giá)
2. [Biểu diễn văn bản: TF-IDF](#2-biểu-diễn-văn-bản-tf-idf)
3. [Học máy cổ điển: Logistic Regression, SVM](#3-học-máy-cổ-điển-logistic-regression-svm)
4. [Học sâu: BiLSTM](#4-học-sâu-bilstm)
5. [Transformer: BERT, PhoBERT, ViSoBERT](#5-transformer-bert-phobert-visobert)
6. [Mô hình ngôn ngữ lớn (LLM) zero-shot / few-shot](#6-mô-hình-ngôn-ngữ-lớn-llm-zero-shot--few-shot)
7. [Phát hiện chủ đề: NMF, LDA, K-means](#7-phát-hiện-chủ-đề-nmf-lda-k-means)
8. [Phân loại xu hướng theo thời gian](#8-phân-loại-xu-hướng-theo-thời-gian)
9. [Học máy bảo toàn quyền riêng tư: DP-SGD](#9-học-máy-bảo-toàn-quyền-riêng-tư-dp-sgd)
10. [An toàn mô hình: đầu độc dữ liệu, độ bền, trôi dữ liệu](#10-an-toàn-mô-hình-đầu-độc-dữ-liệu-độ-bền-trôi-dữ-liệu)
11. [Tổng hợp](#11-tổng-hợp)

---

## 1. Bài toán và cách đánh giá

### 1.1. Các bài toán

| Mã | Bài toán | Dạng | Dữ liệu | Nhãn |
|---|---|---|---|---|
| BT-01 | Phân loại quan điểm | Phân loại văn bản, 3 lớp | UIT-VSFC (~16.000 câu phản hồi sinh viên) | Tích cực, Tiêu cực, Trung tính |
| BT-03 | Nhận diện cảm xúc | Phân loại văn bản, 7 lớp | UIT-VSMEC (~6.900 bình luận Facebook) | Vui vẻ, Buồn bã, Tức giận, Sợ hãi, Ghê tởm, Ngạc nhiên, Khác |
| BT-02 | Phát hiện chủ đề | Gom cụm không giám sát | Bình luận thu thập | Chủ đề do mô hình sinh |
| BT-04 | Phân loại xu hướng | Luật trên chuỗi thời gian | Số bài theo chủ đề/ngày | Mới nổi, Đang tăng, Đang giảm, Ổn định |

Phân loại văn bản có giám sát: cho tập huấn luyện $\{(x_i, y_i)\}_{i=1}^{N}$ với $x_i$ là câu, $y_i \in \{1,\dots,K\}$ là nhãn, cần học hàm $f(x) \to y$ sao cho dự đoán đúng trên câu chưa gặp.

### 1.2. Độ đo

Với mỗi lớp $c$: TP (dự đoán $c$ và đúng là $c$), FP (dự đoán $c$ nhưng sai), FN (là $c$ nhưng dự đoán khác).

$$
\text{Precision}_c = \frac{TP_c}{TP_c + FP_c}, \quad
\text{Recall}_c = \frac{TP_c}{TP_c + FN_c}, \quad
F1_c = \frac{2 \cdot P_c \cdot R_c}{P_c + R_c}
$$

$$
\text{F1-macro} = \frac{1}{K}\sum_{c=1}^{K} F1_c
$$

**Vì sao chọn F1-macro làm độ đo chính** thay vì Accuracy: dữ liệu lệch lớp mạnh — lớp Trung tính chỉ chiếm ~4% UIT-VSFC. Một mô hình không bao giờ đoán "Trung tính" vẫn đạt Accuracy cao, nhưng F1 lớp đó bằng 0 kéo F1-macro xuống. F1-macro coi mọi lớp quan trọng như nhau.

Quy trình chung cho mọi mô hình ([models/sentiment/train.py](../models/sentiment/train.py)):
- Chia train / validation / test; kiểm tra không có câu trùng giữa train và test (chống rò rỉ).
- Chọn siêu tham số hoặc epoch tốt nhất theo **F1-macro trên validation**.
- Báo kết quả cuối trên **test**, kèm ma trận nhầm lẫn và F1 từng lớp.
- Hệ thống tự chọn mô hình có F1-macro test cao nhất cho mỗi bài toán (quản trị có thể chọn tay).

---

## 2. Biểu diễn văn bản: TF-IDF

Máy học cổ điển cần đầu vào là vector số. TF-IDF biến mỗi câu thành một vector thưa, mỗi chiều ứng với một từ / cụm từ.

$$
\text{tf-idf}(t, d) = \text{tf}(t, d) \times \log\frac{1 + N}{1 + \text{df}(t)} + 1
$$

- $\text{tf}(t, d)$: số lần từ $t$ xuất hiện trong câu $d$. Đề tài dùng `sublinear_tf`, tức thay bằng $1 + \log(\text{tf})$ để từ lặp nhiều lần không áp đảo.
- $\text{df}(t)$: số câu chứa $t$; $N$: tổng số câu. Từ xuất hiện ở mọi câu ("là", "của") có IDF thấp → ít trọng số; từ đặc trưng ("tuyệt vời", "tệ") có IDF cao.
- Mỗi vector được chuẩn hóa L2.

**Cấu hình trong đề tài** — ghép hai loại đặc trưng (`FeatureUnion`):

| Đặc trưng | Mục đích |
|---|---|
| n-gram **từ** 1–2 | Bắt cụm như "không hay", "rất tốt" — giữ được phủ định |
| n-gram **ký tự** 2–5 (`char_wb`) | Chịu được lỗi gõ, teencode, biến thể ("hayyy", "đc") |
| Emoji → từ (`emoji_tags`) | Emoji mang cảm xúc mạnh, đổi thành token để mô hình dùng được |

**Hạn chế:** mô hình "túi từ" — bỏ qua thứ tự và ngữ cảnh. "Không phải tệ" và "phải không tệ" gần như cùng vector; không hiểu từ đồng nghĩa.

---

## 3. Học máy cổ điển: Logistic Regression, SVM

Cả hai đều là **bộ phân loại tuyến tính** trên vector TF-IDF $\mathbf{x}$: mỗi lớp $c$ có vector trọng số $\mathbf{w}_c$, điểm của lớp là $\mathbf{w}_c^\top \mathbf{x} + b_c$.

### 3.1. Logistic Regression (M-01)

Chuyển điểm thành xác suất bằng softmax và tối đa hóa log-likelihood:

$$
P(y = c \mid \mathbf{x}) = \frac{\exp(\mathbf{w}_c^\top \mathbf{x} + b_c)}{\sum_{k}\exp(\mathbf{w}_k^\top \mathbf{x} + b_k)}
$$

$$
\min_{\mathbf{W}} \; \frac{1}{2}\|\mathbf{W}\|^2 + C \sum_{i} \alpha_{y_i} \cdot \big(-\log P(y_i \mid \mathbf{x}_i)\big)
$$

- $C$: nghịch đảo độ mạnh chính quy hóa — $C$ nhỏ thì mô hình đơn giản hơn, ít quá khớp.
- $\alpha_{y}$: trọng số lớp (`class_weight="balanced"`, $\alpha_c = N / (K \cdot N_c)$) — phạt sai ở lớp hiếm nặng hơn, bù cho dữ liệu lệch.

### 3.2. Linear SVM (M-02)

Tìm siêu phẳng phân tách với **lề (margin) lớn nhất**, dùng hàm mất mát hinge:

$$
\min_{\mathbf{w}, b} \; \frac{1}{2}\|\mathbf{w}\|^2 + C \sum_{i} \alpha_{y_i} \max\big(0,\, 1 - y_i(\mathbf{w}^\top \mathbf{x}_i + b)\big)
$$

Nhiều lớp xử lý theo kiểu một-chọi-phần-còn-lại (one-vs-rest). SVM hợp với dữ liệu nhiều chiều, thưa như TF-IDF.

**Cấu hình:** thử $C \in \{0.25, 0.5, 1, 2, 4\}$, chọn theo F1-macro validation, rồi huấn luyện lại trên train + validation.

**Kết quả:** quan điểm F1-macro 0.763 (LR) / 0.762 (SVM); cảm xúc 0.595 / 0.588. Huấn luyện vài chục giây, dự đoán ~9.000 câu/giây trên CPU — làm **mốc cơ sở (baseline)** để đo mức lợi của mô hình phức tạp hơn.

---

## 4. Học sâu: BiLSTM

### 4.1. Ý tưởng

Mạng hồi quy (RNN) đọc câu **lần lượt từng token**, giữ một trạng thái ẩn $h_t$ tóm tắt phần đã đọc — nên nắm được **thứ tự từ**, điều TF-IDF bỏ qua. RNN thường bị *tiêu biến gradient* với câu dài; **LSTM** (Long Short-Term Memory) khắc phục bằng các cổng điều khiển dòng thông tin.

### 4.2. Công thức một ô LSTM

Tại bước $t$ với đầu vào $x_t$ (embedding của token):

$$
\begin{aligned}
f_t &= \sigma(W_f [h_{t-1}, x_t] + b_f) && \text{cổng quên: bỏ bớt gì từ bộ nhớ} \\
i_t &= \sigma(W_i [h_{t-1}, x_t] + b_i) && \text{cổng vào: ghi thêm gì} \\
\tilde{c}_t &= \tanh(W_c [h_{t-1}, x_t] + b_c) && \text{nội dung ứng viên} \\
c_t &= f_t \odot c_{t-1} + i_t \odot \tilde{c}_t && \text{cập nhật bộ nhớ} \\
o_t &= \sigma(W_o [h_{t-1}, x_t] + b_o) && \text{cổng ra} \\
h_t &= o_t \odot \tanh(c_t)
\end{aligned}
$$

Bộ nhớ $c_t$ được cập nhật bằng **phép cộng** nên gradient truyền ngược qua nhiều bước mà không tắt dần.

**Bi**LSTM chạy hai LSTM: một chiều trái → phải, một chiều phải → trái, rồi ghép $[\overrightarrow{h_t}; \overleftarrow{h_t}]$. Mỗi vị trí vì thế thấy được cả ngữ cảnh trước và sau ("không" đứng trước "hay" ảnh hưởng tới "hay").

### 4.3. Kiến trúc trong đề tài ([models/sentiment/bilstm.py](../models/sentiment/bilstm.py))

```
token (âm tiết / emoji / dấu câu)
  → Embedding 200 chiều (học từ đầu, không dùng word2vec ngoài)
  → Dropout 0.3
  → BiLSTM, 128 đơn vị mỗi chiều → 256 chiều mỗi vị trí
  → Max-pooling theo thời gian (lấy giá trị lớn nhất mỗi chiều trên toàn câu)
  → Dropout 0.3 → Linear → K lớp
```

- Từ điển tối đa 30.000 token xuất hiện ≥ 2 lần; câu cắt ở 128 token.
- Hàm mất mát Cross-Entropy có **trọng số lớp nghịch tần suất**; tối ưu Adam, lr $10^{-3}$, cắt gradient ở 5.0; 10 epoch, giữ epoch có F1 validation tốt nhất.

**Kết quả:** quan điểm 0.757, cảm xúc 0.503 — **không hơn TF-IDF**. Lý do: embedding học từ đầu cần nhiều dữ liệu, trong khi UIT-VSMEC chỉ ~5.500 câu huấn luyện. Đây là động lực để dùng mô hình **tiền huấn luyện** ở mục 5.

---

## 5. Transformer: BERT, PhoBERT, ViSoBERT

### 5.1. Cơ chế Self-Attention

Transformer bỏ hẳn cơ chế hồi quy. Mỗi token nhìn trực tiếp **mọi token khác** trong câu và tự quyết định cần chú ý vào đâu. Mỗi token được chiếu thành 3 vector: Query $Q$, Key $K$, Value $V$:

$$
\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{Q K^\top}{\sqrt{d_k}}\right) V
$$

- $QK^\top$: độ liên quan giữa từng cặp token; chia $\sqrt{d_k}$ để softmax không quá nhọn.
- **Multi-head**: chạy nhiều attention song song (12 head ở bản base), mỗi head học một kiểu quan hệ (cú pháp, phủ định, đồng tham chiếu…).
- Mỗi lớp Transformer = Multi-head Attention + mạng truyền thẳng, kèm kết nối tắt (residual) và LayerNorm. Bản *base* xếp chồng 12 lớp, ẩn 768 chiều, ~110–135 triệu tham số.
- Vì không có thứ tự tự nhiên, thêm **positional embedding** vào embedding token.

So với BiLSTM: mọi cặp token liên hệ trực tiếp (không phải truyền qua nhiều bước), và tính song song được trên GPU.

### 5.2. BERT: tiền huấn luyện rồi tinh chỉnh

BERT (Bidirectional Encoder Representations from Transformers) học theo hai pha:

1. **Tiền huấn luyện (pre-training)** trên kho văn bản khổng lồ không nhãn bằng *Masked Language Modeling*: che ngẫu nhiên ~15% token, bắt mô hình đoán lại từ ngữ cảnh hai phía. Qua đó mô hình học được ngữ pháp, nghĩa từ, kiến thức chung.
2. **Tinh chỉnh (fine-tuning)** trên bài toán cụ thể: thêm một lớp phân loại lên vector của token đặc biệt `<s>` / `[CLS]` (đại diện cả câu), rồi huấn luyện **toàn bộ** mạng với vài epoch trên dữ liệu có nhãn.

Đây là **học chuyển giao (transfer learning)** — giải thích vì sao Transformer vượt BiLSTM dù dùng cùng lượng dữ liệu có nhãn: phần lớn "hiểu ngôn ngữ" đã học sẵn ở pha 1.

**RoBERTa** là bản cải tiến của BERT: bỏ nhiệm vụ dự đoán câu kế tiếp, huấn luyện lâu hơn trên nhiều dữ liệu hơn, che token động. **XLM-R** là RoBERTa đa ngôn ngữ (100 ngôn ngữ). Cả PhoBERT và ViSoBERT đều theo kiến trúc RoBERTa.

### 5.3. PhoBERT-base-v2 (M-16) — mô hình được chọn cho quan điểm

- Do VinAI phát triển, tiền huấn luyện trên ~20GB văn bản tiếng Việt (Wikipedia + tin tức; bản v2 thêm dữ liệu OSCAR).
- Tiếng Việt viết tách theo âm tiết, nhưng một **từ** có thể gồm nhiều âm tiết ("sinh viên", "giảng viên"). PhoBERT được huấn luyện trên văn bản **đã tách từ**, nên đầu vào bắt buộc tách từ trước: `giảng viên dạy hay` → `giảng_viên dạy hay`. Đề tài dùng `underthesea.word_tokenize`, sau đó tách tiếp bằng BPE của mô hình.
- **Giấy phép AGPL-3.0** — lưu ý nếu phân phối phần mềm.

**Kết quả:** quan điểm **F1-macro 0.831** (Accuracy 0.938) — cao nhất; cảm xúc 0.590.

### 5.4. ViSoBERT (M-10) — mô hình được chọn cho cảm xúc

- Do nhóm UIT-NLP phát triển, tiền huấn luyện trên **văn bản mạng xã hội tiếng Việt** (Facebook, TikTok, YouTube) — nơi có teencode, emoji, viết không dấu, câu cụt.
- Dùng tokenizer **SentencePiece**, làm việc trực tiếp trên chuỗi thô, **không cần tách từ**, và có sẵn token cho emoji.
- Kho mô hình gốc thiếu cấu hình tokenizer; thư viện `transformers` 5.x đọc sai thành toàn `<unk>` mà không báo lỗi. Đề tài tự viết bộ đọc ([models/sentiment/spm_tokenizer.py](../models/sentiment/spm_tokenizer.py)) và chặn huấn luyện nếu tỉ lệ `<unk>` > 20%.

**Kết quả:** cảm xúc **F1-macro 0.665** — cao nhất, vì UIT-VSMEC chính là bình luận Facebook, đúng miền ViSoBERT được tiền huấn luyện; quan điểm 0.809. Trong thực nghiệm độ bền (mục 10.2), ViSoBERT cũng **ít bị ảnh hưởng nhất khi câu bị bỏ dấu**.

### 5.5. Cấu hình tinh chỉnh (dùng chung cho cả hai)

| Tham số | Giá trị | Ý nghĩa |
|---|---|---|
| Tối ưu | AdamW, lr $2 \times 10^{-5}$, weight decay 0.01 | lr nhỏ để không phá kiến thức đã tiền huấn luyện |
| Lịch lr | Warmup tuyến tính 10% bước đầu rồi giảm tuyến tính | Tránh cập nhật quá mạnh khi lớp phân loại còn ngẫu nhiên |
| Epoch / batch | 4 / 16 | |
| Độ dài tối đa | 128 token | Bình luận MXH thường ngắn |
| Cắt gradient | 1.0 | Ổn định huấn luyện |
| Dừng sớm | Giữ checkpoint có F1 validation cao nhất | |
| Seed | 42 | Tái lập kết quả |

---

## 6. Mô hình ngôn ngữ lớn (LLM) zero-shot / few-shot

### 6.1. Ý tưởng

LLM (Large Language Model) là Transformer dạng **decoder**, huấn luyện để đoán token tiếp theo trên lượng văn bản rất lớn, sau đó tinh chỉnh để làm theo chỉ dẫn (*instruction tuning*). Có thể phân loại **mà không cần huấn luyện thêm**, chỉ bằng cách viết câu lệnh (prompt):

- **Zero-shot:** chỉ mô tả nhiệm vụ và danh sách nhãn.
- **Few-shot (in-context learning):** thêm vài ví dụ có nhãn ngay trong prompt; mô hình "học" từ ví dụ trong lúc suy luận, không cập nhật trọng số.

### 6.2. Cách làm trong đề tài ([experiments/llm.py](../experiments/llm.py))

- Mô hình: **Qwen2.5-1.5B-Instruct** (Apache-2.0), chạy **cục bộ** trên GPU 4GB → không gửi dữ liệu ra dịch vụ ngoài (yêu cầu an ninh).
- Prompt hệ thống: *"Bạn là bộ phân loại … Chỉ trả lời đúng MỘT nhãn trong danh sách: … Không giải thích."*; few-shot lấy 1 ví dụ mỗi nhãn từ tập train.
- Đầu ra văn bản tự do được dò tìm nhãn (nhãn dài khớp trước).

**Kết quả** (trên mẫu cân bằng nhãn, so với mô hình fine-tune trên **cùng mẫu**):

| Bài toán | LLM tốt nhất | Mô hình fine-tune | Tốc độ LLM |
|---|---|---|---|
| Quan điểm | 0.748 (few-shot) | 0.800 | chậm hơn ~41 lần |
| Cảm xúc | 0.299 (zero-shot) | 0.681 | chậm hơn ~56 lần |

**Nhận xét:** LLM nhỏ khá tốt với quan điểm (nhiệm vụ đơn giản) nhưng kém xa với 7 cảm xúc (ranh giới giữa các nhãn khó định nghĩa bằng lời). LLM lớn hơn có thể tốt hơn nhưng cần phần cứng mạnh hoặc gửi dữ liệu ra ngoài — đánh đổi với quyền riêng tư.

---

## 7. Phát hiện chủ đề: NMF, LDA, K-means

Bài toán **không giám sát**: không có nhãn, cần tự tìm nhóm bình luận cùng nói về một việc. Đầu ra mỗi chủ đề là danh sách từ khóa đại diện.

### 7.1. NMF — Phân rã ma trận không âm (M-21, đang dùng trong pipeline)

Cho ma trận TF-IDF $X \in \mathbb{R}_{\ge 0}^{n \times m}$ ($n$ câu, $m$ từ), tìm hai ma trận **không âm**:

$$
X \approx W H, \quad W \in \mathbb{R}_{\ge 0}^{n \times k}, \; H \in \mathbb{R}_{\ge 0}^{k \times m}
\qquad \min_{W, H \ge 0} \|X - WH\|_F^2
$$

- Mỗi hàng của $H$ là một **chủ đề** — trọng số của từng từ; lấy 6 từ trọng số lớn nhất làm từ khóa.
- Mỗi hàng của $W$ cho biết câu thuộc từng chủ đề bao nhiêu; câu được gán vào chủ đề có trọng số lớn nhất.
- Ràng buộc không âm khiến mỗi câu là **tổng cộng** (không trừ) của các chủ đề → dễ diễn giải.

**Cấu hình** ([models/trend/trends.py](../models/trend/trends.py)): gom theo từng nhóm nguồn (từ khóa / video); TF-IDF 1–2 gram, bỏ từ dừng tiếng Việt và token ẩn danh (`xxsđt`, `xxemail`); số chủ đề $k \approx$ số bài / 40, trong khoảng 2–8; khởi tạo `nndsvda`.

### 7.2. LDA — Latent Dirichlet Allocation (M-12)

Mô hình **xác suất sinh văn bản**: mỗi văn bản là hỗn hợp các chủ đề, mỗi chủ đề là phân phối trên từ.

1. Với mỗi văn bản $d$: rút tỉ lệ chủ đề $\theta_d \sim \text{Dirichlet}(\alpha)$.
2. Với mỗi từ trong $d$: rút chủ đề $z \sim \text{Multinomial}(\theta_d)$, rồi rút từ $w \sim \text{Multinomial}(\beta_z)$.

Học ngược $\theta, \beta$ từ dữ liệu bằng suy luận biến phân. LDA làm việc trên **số đếm từ** (không phải TF-IDF) và hợp với văn bản dài; bình luận MXH quá ngắn nên mỗi câu có quá ít từ để ước lượng hỗn hợp chủ đề.

### 7.3. K-means trên embedding (M-13 + M-18)

1. Biến mỗi câu thành vector ngữ nghĩa bằng **ViSoBERT gốc** (không fine-tune): lấy trung bình vector đầu ra của các token ([experiments/embed.py](../experiments/embed.py)).
2. K-means: chọn $k$ tâm, lặp (gán mỗi điểm vào tâm gần nhất → cập nhật tâm = trung bình các điểm), tối thiểu

$$
\sum_{j=1}^{k} \sum_{\mathbf{x} \in S_j} \|\mathbf{x} - \boldsymbol{\mu}_j\|^2
$$

Ưu điểm: embedding hiểu **đồng nghĩa** — "thầy giảng dễ hiểu" và "giảng viên dạy rõ ràng" gần nhau dù không chung từ, điều TF-IDF không làm được.

### 7.4. Đánh giá và so sánh

UIT-VSFC có nhãn chủ đề do người gán (Giảng viên / Chương trình đào tạo / Cơ sở vật chất / Khác) nên dùng để đo khách quan:

- **NMI** (Normalized Mutual Information): lượng thông tin chung giữa cụm tìm được và nhãn thật, chuẩn hóa về [0, 1].
- **ARI** (Adjusted Rand Index): mức đồng ý giữa hai cách chia trên từng cặp điểm, đã trừ phần trùng ngẫu nhiên (0 ≈ ngẫu nhiên, 1 = khớp hoàn toàn).
- **Purity**: tỉ lệ điểm thuộc nhãn chiếm đa số trong cụm của nó. Dữ liệu lệch (Giảng viên 72%) nên purity tối thiểu đã là 0.72 → phải đọc kèm NMI/ARI.

| Phương pháp ($k = 4$) | NMI | ARI |
|---|---|---|
| TF-IDF + NMF (đang dùng) | 0.083 | — |
| LDA | 0.116 | 0.081 |
| K-means trên embedding ViSoBERT | **0.138** | **0.094** |

NMF đang dùng vì chạy nhanh, chỉ cần scikit-learn và dễ giải thích; đề xuất chuyển sang K-means trên embedding khi có dữ liệu thật. Các hướng mạnh hơn trong thuyết minh: **BERTopic** (embedding → giảm chiều UMAP → gom cụm HDBSCAN → c-TF-IDF lấy từ khóa) và **BERTrend** (BERTopic theo cửa sổ thời gian để bắt chủ đề nổi lên) — hiện chưa chạy được vì `umap`/`hdbscan` chưa có bản cho Python 3.14.

---

## 8. Phân loại xu hướng theo thời gian

Theo quyết định QD-05, "xu hướng" là xu hướng **chủ đề của cộng đồng** — chỉ đếm số bài theo chủ đề/ngày, **không theo dõi từng người**.

### 8.1. Luật phân loại

Với mỗi chủ đề, đếm số bài mỗi ngày, rồi so **3 ngày gần nhất** với **tối đa 7 ngày trước đó**:

$$
\bar{r} = \frac{\text{số bài 3 ngày gần nhất}}{3}, \quad
\bar{p} = \frac{\text{số bài giai đoạn trước}}{\text{số ngày giai đoạn trước}}, \quad
g = \frac{\bar{r} - \bar{p}}{\bar{p}}
$$

| Điều kiện | Nhãn |
|---|---|
| Dữ liệu < 2 ngày | Chưa đủ dữ liệu |
| Trước đó không có bài, gần đây ≥ 5 bài | **Mới nổi** |
| $g \ge 0.5$ (tăng ≥ 50%) | **Đang tăng** |
| $g \le -0.5$ (giảm ≥ 50%) | **Đang giảm** |
| Còn lại | **Ổn định** |

So sánh **trung bình mỗi ngày** chứ không phải tổng, để hai giai đoạn dài ngắn khác nhau vẫn so được.

### 8.2. Chiều thay đổi cảm xúc

Kết hợp với kết quả BT-01: tính độ phân cực ở mỗi giai đoạn

$$
\text{polarity} = \frac{\#\text{Tích cực} - \#\text{Tiêu cực}}{\#\text{bài có nhãn}}
$$

Chênh lệch giữa giai đoạn gần đây và trước đó > 0.15 → **Tích cực hóa**; < −0.15 → **Tiêu cực hóa**; còn lại Ổn định (cần ≥ 5 bài có nhãn mỗi giai đoạn). Ví dụ: một chủ đề "Đang tăng" + "Tiêu cực hóa" là dấu hiệu khủng hoảng truyền thông. Cùng luật được áp cho **hashtag**.

**Vì sao dùng luật thay vì mô hình học:** chưa có dữ liệu xu hướng có nhãn để huấn luyện; luật minh bạch, dễ giải thích, dễ chỉnh ngưỡng. Mốc so sánh đề xuất: phát hiện bùng nổ bằng **z-score** trên chuỗi thời gian (M-17) — đánh dấu ngày có số bài vượt trung bình quá $k$ độ lệch chuẩn. Phần này chưa được đánh giá vì cần dữ liệu YouTube thật trải ≥ 2 ngày.

---

## 9. Học máy bảo toàn quyền riêng tư: DP-SGD

### 9.1. Vấn đề

Mô hình có thể **ghi nhớ** dữ liệu huấn luyện. Kẻ tấn công có thể suy ra một bình luận cụ thể có nằm trong tập huấn luyện hay không (*membership inference*), thậm chí trích lại nội dung. Câu hỏi CH4: bảo vệ được dữ liệu mà vẫn giữ độ chính xác?

### 9.2. Differential Privacy (riêng tư vi phân)

Thuật toán $\mathcal{M}$ đạt $(\varepsilon, \delta)$-DP nếu với **mọi** cặp tập dữ liệu $D, D'$ chỉ khác nhau **một mẫu**, và mọi tập kết quả $S$:

$$
P[\mathcal{M}(D) \in S] \le e^{\varepsilon} \cdot P[\mathcal{M}(D') \in S] + \delta
$$

Nghĩa là: có hay không có bình luận của **bạn** trong dữ liệu, mô hình thu được gần như giống nhau → không ai suy ra được gì về riêng bạn. $\varepsilon$ càng **nhỏ** càng riêng tư (thường $\varepsilon \le 10$ được coi là có ý nghĩa, $\varepsilon \le 1$ là mạnh); $\delta$ là xác suất nhỏ cho phép vi phạm, thường chọn $< 1/N$.

### 9.3. DP-SGD

Biến thể của gradient descent, khác ở hai bước:

1. **Cắt gradient từng mẫu:** $\bar{g}_i = g_i / \max\left(1, \frac{\|g_i\|_2}{C}\right)$ — giới hạn ảnh hưởng tối đa của một mẫu bất kỳ ở mức $C$.
2. **Thêm nhiễu Gauss** vào tổng gradient của lô: $\tilde{g} = \frac{1}{B}\left(\sum_i \bar{g}_i + \mathcal{N}(0, \sigma^2 C^2 I)\right)$.

Một *bộ kế toán riêng tư* (RDP accountant) cộng dồn mức rò rỉ qua mọi bước để tính ra $\varepsilon$ cuối cùng; ngược lại, cho $\varepsilon$ mục tiêu thì tính ra hệ số nhiễu $\sigma$ cần dùng.

### 9.4. Thực nghiệm ([experiments/dp.py](../experiments/dp.py))

- Bộ trích đặc trưng: ViSoBERT gốc **đóng băng** (không học trên dữ liệu đề tài) → vector câu chuẩn hóa L2.
- Phần học trên dữ liệu đề tài: một lớp phân loại tuyến tính, huấn luyện bằng DP-SGD (thư viện Opacus), $C = 1$, $\delta = 1/N$, 30 epoch, 3 seed mỗi mức.

| Bài toán | Không DP ($\varepsilon = \infty$) | $\varepsilon = 8$ | $\varepsilon = 1$ | $\varepsilon = 0.5$ |
|---|---|---|---|---|
| Quan điểm | 0.752 | 0.664 | 0.606 | 0.590 |
| Cảm xúc | 0.604 | 0.389 | 0.259 | 0.163 |

**Nhận xét:** riêng tư càng mạnh, độ chính xác càng giảm; bài toán 7 lớp ít dữ liệu bị ảnh hưởng nặng hơn nhiều. Phần lớn khoảng cách so với fine-tune đầy đủ (0.809 / 0.665) đến từ việc **đóng băng** bộ trích đặc trưng, không phải từ DP — khi viết báo cáo cần tách hai yếu tố này. DP-SGD cho toàn bộ ViSoBERT cần GPU lớn hơn 4GB, để ở hướng phát triển. **Học liên kết (federated learning, M-20)** — mỗi bên huấn luyện tại chỗ, chỉ gửi trọng số — là hướng bổ sung, chưa thực hiện.

---

## 10. An toàn mô hình: đầu độc dữ liệu, độ bền, trôi dữ liệu

### 10.1. Tấn công đầu độc dữ liệu và phòng vệ ([experiments/poisoning.py](../experiments/poisoning.py))

**Tấn công lật nhãn (label flipping):** kẻ tấn công sửa nhãn của $p\%$ mẫu huấn luyện sang nhãn khác, làm mô hình học sai.

**Phòng vệ — kiểm tra dữ liệu (data validation):** dự đoán chéo 5-fold trên chính tập huấn luyện; mẫu nào mô hình gán xác suất < 0.15 cho **chính nhãn của nó** bị coi là đáng ngờ và loại trước khi huấn luyện lại. Cơ sở: mẫu bị lật nhãn thường mâu thuẫn với các mẫu tương tự.

| | Lật 40% nhãn, không phòng vệ | Có phòng vệ | Phát hiện đúng |
|---|---|---|---|
| Quan điểm | 0.751 → 0.547 | 0.562 | 31% mẫu bị lật |
| Cảm xúc | 0.595 → 0.422 | 0.503 | 71% mẫu bị lật |

Khi không bị tấn công, phòng vệ vẫn loại nhầm các mẫu khó/nhập nhằng → chỉ nên bật khi giám sát nghi ngờ dữ liệu bị nhiễm.

### 10.2. Độ bền trước cách viết thật trên MXH ([experiments/robustness.py](../experiments/robustness.py))

Biến đổi câu gốc của tập test rồi cho qua đúng chuỗi làm sạch → mô hình: **bỏ dấu**, **teencode hóa** ("không" → "ko", "được" → "đc"), **bỏ emoji**, **lỗi gõ** 10% từ.

- **Bỏ dấu là điểm yếu lớn nhất** của mọi mô hình: F1 giảm 0.10–0.38. Bền nhất là ViSoBERT ở bài quan điểm (0.809 → 0.712) nhờ được tiền huấn luyện trên văn bản MXH vốn hay không dấu.
- Bước chuẩn hóa teencode giúp nhiều nhất cho mô hình đơn giản (TF-IDF +0.04, BiLSTM +0.05 F1); Transformer gần như tự xử lý được.
- Câu có emoji khó hơn câu không emoji ở bài cảm xúc (ViSoBERT 0.558 so với 0.670) — emoji thường đi kèm mỉa mai.
- Đề xuất: thêm bước khôi phục dấu, hoặc tăng cường dữ liệu không dấu khi huấn luyện.

### 10.3. Giám sát trôi dữ liệu (data drift)

Mô hình học trên phân phối dữ liệu huấn luyện; khi dữ liệu thật khác đi (*trôi miền*), độ chính xác giảm mà không có nhãn để biết. Bước `monitor` ([pipeline/steps.py](../pipeline/steps.py)) so **phân phối nhãn dự đoán 7 ngày gần nhất** $P$ với **phân phối nhãn tập huấn luyện** $Q$ bằng **khoảng cách Jensen–Shannon**:

$$
M = \tfrac{1}{2}(P + Q), \qquad
\text{JS}(P, Q) = \sqrt{\tfrac{1}{2} \text{KL}(P \,\|\, M) + \tfrac{1}{2} \text{KL}(Q \,\|\, M)}, \qquad
\text{KL}(P \,\|\, M) = \sum_k P_k \log_2 \frac{P_k}{M_k}
$$

JS đối xứng, luôn hữu hạn và nằm trong [0, 1] (dùng log cơ số 2). JS > 0.3 → cảnh báo trôi miền. Trên dữ liệu thử đã đo được JS = 0.32: mô hình học trên phản hồi sinh viên đang chạy trên bình luận MXH — lý do cần gán nhãn dữ liệu YouTube thật (T-16). Bước này cũng theo dõi tỉ lệ dự đoán có độ tin cậy thấp.

---

## 11. Tổng hợp

### 11.1. Bảng so sánh phân loại (F1-macro trên tập test)

| Nhóm | Mô hình | Quan điểm (VSFC) | Cảm xúc (VSMEC) | Đặc điểm |
|---|---|---|---|---|
| Cổ điển | TF-IDF + LR | 0.763 | 0.595 | Nhanh nhất, dễ giải thích |
| Cổ điển | TF-IDF + SVM | 0.762 | 0.588 | |
| Học sâu | BiLSTM | 0.757 | 0.503 | Nắm thứ tự từ, cần nhiều dữ liệu |
| Transformer | ViSoBERT | 0.809 | **0.665** ✔ | Tiền huấn luyện trên MXH, bền với không dấu |
| Transformer | PhoBERT-base-v2 | **0.831** ✔ | 0.590 | Tiền huấn luyện trên văn bản chuẩn, cần tách từ |
| LLM | Qwen2.5-1.5B (few/zero-shot)* | 0.748 | 0.299 | Không cần huấn luyện, chậm |

\* Đo trên mẫu cân bằng nhãn, không so trực tiếp được với các dòng còn lại.

### 11.2. Rút ra

1. **Tiền huấn luyện quyết định:** hai Transformer vượt rõ các mô hình học từ đầu, nhất là khi dữ liệu có nhãn ít.
2. **Miền dữ liệu quan trọng:** PhoBERT thắng ở phản hồi sinh viên (văn phong chuẩn), ViSoBERT thắng ở bình luận Facebook (văn phong MXH). Với dữ liệu YouTube thật, ViSoBERT nhiều khả năng phù hợp hơn — cần kiểm chứng sau khi gán nhãn.
3. **Điểm khó chung:** lớp Trung tính (F1 45–58%), nhãn Tức giận và Ngạc nhiên, câu không dấu, câu mỉa mai.
4. **An ninh có giá:** DP-SGD giảm độ chính xác rõ rệt; phòng vệ đầu độc có ích nhưng cần dùng có điều kiện.

### 11.3. Tài liệu tham khảo chính

- Vaswani et al. (2017). *Attention Is All You Need*. NeurIPS.
- Devlin et al. (2019). *BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding*. NAACL.
- Liu et al. (2019). *RoBERTa: A Robustly Optimized BERT Pretraining Approach*. arXiv:1907.11692.
- Conneau et al. (2020). *Unsupervised Cross-lingual Representation Learning at Scale* (XLM-R). ACL.
- Nguyen & Nguyen (2020). *PhoBERT: Pre-trained language models for Vietnamese*. Findings of EMNLP.
- Nguyen et al. (2023). *ViSoBERT: A Pre-Trained Language Model for Vietnamese Social Media Text Processing*. EMNLP.
- Nguyen et al. (2018). *UIT-VSFC: Vietnamese Students' Feedback Corpus for Sentiment Analysis*. KSE.
- Ho et al. (2019). *Emotion Recognition for Vietnamese Social Media Text* (UIT-VSMEC). PACLING.
- Hochreiter & Schmidhuber (1997). *Long Short-Term Memory*. Neural Computation.
- Lee & Seung (1999). *Learning the parts of objects by non-negative matrix factorization*. Nature.
- Blei, Ng & Jordan (2003). *Latent Dirichlet Allocation*. JMLR.
- Grootendorst (2022). *BERTopic: Neural topic modeling with a class-based TF-IDF procedure*. arXiv:2203.05794.
- Dwork & Roth (2014). *The Algorithmic Foundations of Differential Privacy*.
- Abadi et al. (2016). *Deep Learning with Differential Privacy* (DP-SGD). ACM CCS.
- Qwen Team (2024). *Qwen2.5 Technical Report*. arXiv:2412.15115.
