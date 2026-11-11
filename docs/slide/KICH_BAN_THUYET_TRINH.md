# Kịch bản thuyết trình

Đề tài: Máy học hiện đại kết hợp an ninh an toàn trong hệ thống thu thập, nhận diện cảm xúc và xu hướng mạng xã hội tiếng Việt.
Slide: [NCKH_thuyet_trinh.pptx](NCKH_thuyet_trinh.pptx) · 14 slide · khoảng 20–25 phút (mỗi slide 1,5–2 phút).

Cách dùng: đọc tự nhiên, không đọc nguyên văn. Phần **Ý chính** là những gì cần nhớ nếu quên lời. Phần *[Chuyển]* là câu nối sang slide sau.

---

## Slide 1. Tiêu đề

**Ý chính:** chào, nêu tên đề tài, nói đề tài gồm ba phần cộng an ninh.

Kính chào hội đồng và các thầy cô. Em xin trình bày kết quả nghiên cứu của nhóm với đề tài: *máy học hiện đại kết hợp an ninh an toàn trong hệ thống thu thập, nhận diện cảm xúc và xu hướng mạng xã hội tiếng Việt*.

Nói ngắn gọn, nhóm xây dựng một hệ thống thử nghiệm gồm ba phần: thu thập và lưu trữ bình luận mạng xã hội tự động, nhận diện cảm xúc của người dùng, và phát hiện xu hướng chủ đề. Xuyên suốt cả ba phần là lớp an ninh an toàn và bảo vệ quyền riêng tư. Đề tài do nhóm thực hiện dưới sự hướng dẫn của ThS. Lê Thanh Trà, khoa Điện toán và Công nghệ số năng lượng.

*[Chuyển]* Trước hết, vì sao nhóm chọn bài toán này?

---

## Slide 2. Bối cảnh và bài toán

**Ý chính:** ba khó khăn (dữ liệu nhiều, tiếng Việt khó, dữ liệu cá nhân) và điểm mới.

Có ba vấn đề nhóm muốn giải quyết.

Thứ nhất, người dùng để lại lượng bình luận rất lớn trên YouTube, TikTok. Đọc thủ công để biết mọi người nghĩ gì là không khả thi.

Thứ hai, tiếng Việt trên mạng xã hội rất khó với máy: teencode, viết tắt, gõ không dấu, emoji, mỉa mai. Các mô hình chuẩn thường giảm chất lượng rõ rệt khi gặp kiểu viết này. Phần thực nghiệm sau sẽ cho thấy con số cụ thể.

Thứ ba, đây là dữ liệu cá nhân. Luật 91/2025/QH15 yêu cầu bảo vệ danh tính người dùng, nên việc bảo vệ phải làm từ lúc thu thập, không phải làm sau.

Điểm mới của đề tài là gộp thu thập, phân tích cảm xúc, phân tích xu hướng và an ninh an toàn thành một hệ thống liền mạch cho tiếng Việt, thay vì làm rời từng phần.

*[Chuyển]* Từ đó nhóm đặt ra năm câu hỏi nghiên cứu.

---

## Slide 3. Mục tiêu và câu hỏi nghiên cứu

**Ý chính:** năm câu hỏi CH1–CH5, năm nhóm sản phẩm. Các slide sau lần lượt trả lời.

Đề tài trả lời năm câu hỏi. CH1: mô hình nào tốt nhất cho cảm xúc tiếng Việt trên mạng xã hội. CH2: phát hiện chủ đề và xu hướng theo thời gian thế nào. CH3: kiến trúc thu thập, lưu trữ nào chạy ổn định và mở rộng được. CH4: bảo vệ dữ liệu và mô hình mà vẫn giữ được độ chính xác không. CH5: ghép đủ các phần thành một hệ thống tích hợp được không.

Sản phẩm đầu ra gồm phần mềm hệ thống thử nghiệm kèm dashboard, bộ dữ liệu thô, đã làm sạch và chia train/validation/test, bảng so sánh các mô hình, và báo cáo tổng kết. Các slide tiếp theo sẽ lần lượt trả lời từng câu hỏi này.

*[Chuyển]* Em xin đi vào kiến trúc hệ thống.

---

## Slide 4. Kiến trúc hệ thống

**Ý chính:** sáu khối nối tiếp, ẩn danh nằm ngay sau thu thập, an ninh bao trùm tất cả.

Hệ thống có sáu khối. Dữ liệu được thu thập qua API YouTube theo lịch tự động. Ngay sau đó, định danh tác giả được băm một chiều, nên hệ thống không lưu ID gốc. Dữ liệu vào PostgreSQL, nội dung thô được mã hóa. Tiếp theo là tiền xử lý: làm sạch, chuẩn hóa teencode, che thông tin cá nhân. Rồi đến phân tích cảm xúc hai tầng và chủ đề, xu hướng. Kết quả hiển thị trên dashboard web có phân quyền ba vai trò.

Điểm cần nhấn mạnh là thanh dưới cùng: xác thực, phân quyền, nhật ký kiểm toán, cảnh báo bất thường và giám sát pipeline học máy chạy xuyên suốt, không phải một khối gắn thêm ở cuối. Toàn bộ thành phần dùng chung một cơ sở dữ liệu PostgreSQL, và mỗi bước pipeline đều được ghi nhật ký chạy.

*[Chuyển]* Em đi vào hai khối đầu: thu thập và lưu trữ.

---

## Slide 5. Thu thập và lưu trữ an toàn

**Ý chính:** chỉ dùng API chính thức; trung thực về TikTok; ba lớp bảo vệ.

Về thu thập, nhóm chỉ dùng API chính thức của nền tảng. YouTube đã chạy được: thu thập theo video hoặc theo từ khóa, bật tắt lịch từ giao diện, và chống trùng theo cặp nền tảng và mã bình luận. Về TikTok, em xin nói thẳng: phần code đã viết nhưng chưa thử với khóa thật, nên chưa thể khẳng định kết quả.

Có một ràng buộc thực tế là quota. YouTube cho 10.000 đơn vị mỗi ngày; một lần tìm kiếm tốn 100, đọc bình luận chỉ tốn 1. Vì vậy cấu hình chu kỳ và số từ khóa phải tính đến quota.

Về bảo vệ dữ liệu, có ba lớp. Một, băm định danh tác giả bằng SHA-256 kèm muối, không lưu ID gốc. Hai, mã hóa nội dung thô ở mức cột bằng Fernet. Ba, người dùng vai trò phân tích chỉ xem văn bản đã che thông tin cá nhân; nội dung gốc chỉ quản trị viên xem được.

*[Chuyển]* Dữ liệu sau đó được làm sạch trước khi vào mô hình.

---

## Slide 6. Tiền xử lý và bộ dữ liệu

**Ý chính:** một hàm làm sạch dùng cho cả huấn luyện và dữ liệu thật; hai bộ dữ liệu công khai.

Tiền xử lý gồm các bước: chuẩn hóa Unicode, che thông tin cá nhân, bỏ URL và gộp ký tự lặp, xử lý teencode và viết tắt, gắn cờ spam và ngôn ngữ. Điều quan trọng là cùng một hàm làm sạch được dùng cho cả dữ liệu huấn luyện lẫn bình luận thu thập, nên lúc huấn luyện và lúc dự đoán xử lý văn bản giống hệt nhau.

Vì chưa có dữ liệu thu thập đã gán nhãn, nhóm huấn luyện trên hai bộ công khai. UIT-VSFC là phản hồi của sinh viên, 3 lớp quan điểm, hơn 13 nghìn mẫu huấn luyện và hơn 3 nghìn mẫu kiểm thử. UIT-VSMEC là bình luận mạng xã hội với 7 nhãn cảm xúc, khoảng 6 nghìn mẫu huấn luyện và 693 mẫu kiểm thử.

*[Chuyển]* Trên hai bộ dữ liệu này nhóm so sánh năm mô hình.

---

## Slide 7. Phân tích cảm xúc hai tầng

**Ý chính:** hai tầng nhãn, ba họ mô hình.

Nhóm phân tích cảm xúc ở hai tầng. Tầng một là quan điểm ba lớp: tích cực, trung tính, tiêu cực. Tầng hai là cảm xúc bảy nhãn: vui vẻ, buồn bã, tức giận, ghê tởm, sợ hãi, ngạc nhiên và khác. Hai tầng trả lời hai nhu cầu khác nhau: biết thái độ chung, và biết sắc thái cảm xúc.

Nhóm so sánh ba họ mô hình: máy học cổ điển là TF-IDF kết hợp Logistic Regression và SVM; học sâu là BiLSTM; và Transformer là ViSoBERT và PhoBERT-base-v2. Mô hình có F1-macro cao nhất được hệ thống chọn tự động cho từng bài toán. Em dùng F1-macro thay vì độ chính xác vì dữ liệu mất cân bằng lớp.

*[Chuyển]* Kết quả như sau.

---

## Slide 8. Kết quả quan điểm ba lớp

**Ý chính:** PhoBERT 0,831 dẫn đầu; Transformer hơn rõ; lớp trung tính yếu.

Ở bài toán quan điểm ba lớp, PhoBERT-base-v2 tốt nhất với F1-macro 0,831 và độ chính xác 93,8%. ViSoBERT đứng sau với 0,809. Ba mô hình còn lại, TF-IDF với Logistic Regression, SVM và BiLSTM, chỉ quanh 0,76. Vậy Transformer tiếng Việt vượt rõ rệt các mô hình còn lại.

Có một điểm yếu chung của mọi mô hình: lớp trung tính. F1 của lớp này chỉ từ 45 đến 59%, trong khi hai lớp còn lại khoảng 95%. Nguyên nhân chủ yếu là dữ liệu mất cân bằng và ranh giới trung tính vốn mơ hồ.

*[Chuyển]* Với cảm xúc bảy nhãn, bức tranh có khác.

---

## Slide 9. Kết quả cảm xúc bảy nhãn

**Ý chính:** ViSoBERT thắng, PhoBERT không; không mô hình nào thắng mọi bài toán.

Ở bảy nhãn cảm xúc, ViSoBERT dẫn đầu với F1-macro 0,665 và độ chính xác 70,1%. Đáng chú ý là PhoBERT, tốt nhất ở bài toán trước, ở đây chỉ đạt 0,590, ngang với TF-IDF và Logistic Regression ở 0,595. BiLSTM thấp nhất với 0,503.

Kết luận cho câu hỏi CH1: không có mô hình nào thắng ở mọi bài toán, nên hệ thống chọn mô hình theo từng bài toán thay vì cố định một mô hình. Nhãn khó nhất là tức giận, F1 chỉ khoảng 49%.

*[Chuyển]* Kế tiếp, nhóm thử hai câu hỏi thực tế: dùng LLM được không, và mô hình có bền khi văn bản bẩn không.

---

## Slide 10. LLM và độ bền

**Ý chính:** LLM nhỏ thua fine-tune và chậm hơn nhiều; bỏ dấu là điểm yếu lớn nhất.

Bên trái là so sánh với LLM. Nhóm thử Qwen2.5 cỡ 1,5 tỷ tham số, vì phần cứng chỉ có GPU 4 GB. Ở quan điểm, LLM few-shot đạt 0,75 so với 0,80 của mô hình fine-tune. Ở cảm xúc, LLM zero-shot chỉ đạt 0,30 so với 0,68. Đồng thời LLM chậm hơn từ 41 đến 56 lần. Em xin lưu ý mẫu thử được lấy cân bằng và chỉ thử LLM nhỏ, nên không so trực tiếp với các con số F1 ở slide trước, và LLM lớn hơn có thể tốt hơn. Tuy vậy, gửi dữ liệu ra dịch vụ ngoài sẽ đặt ra rủi ro quyền riêng tư.

Bên phải là độ bền. Khi văn bản bị bỏ dấu, F1 của mọi mô hình giảm từ 0,10 đến 0,38; đây là điểm yếu lớn nhất. ViSoBERT bền nhất. Bước chuẩn hóa teencode giúp thêm từ 0,003 đến 0,05 F1, và câu có emoji khó hơn. Nhóm đề xuất khôi phục dấu hoặc tăng cường dữ liệu không dấu khi huấn luyện.

*[Chuyển]* Sau cảm xúc là xu hướng.

---

## Slide 11. Chủ đề và xu hướng

**Ý chính:** ba bước; chỉ cấp cộng đồng; nói thẳng chưa có dữ liệu thật để đánh giá xu hướng.

Việc phát hiện xu hướng gồm ba bước. Một, gom chủ đề bằng TF-IDF và NMF theo từng nhóm nội dung. Hai, so sánh tần suất chủ đề trong 3 ngày gần nhất với tối đa 7 ngày trước đó. Ba, gán nhãn xu hướng: mới nổi, tăng, giảm hoặc ổn định, và gắn với cảm xúc.

Một nguyên tắc thiết kế: xu hướng chỉ tính ở cấp cộng đồng, không bao giờ tổng hợp theo từng người dùng, để không xâm phạm quyền riêng tư.

Nhóm cũng so sánh các phương pháp gom chủ đề. Tốt nhất là K-means trên embedding ViSoBERT với NMI 0,138. Con số này còn thấp. Dữ liệu thử lệch mạnh, nhóm Giảng viên chiếm 72%, nên cần đọc kèm NMI và ARI. Và em xin thẳng thắn: phần phân loại xu hướng chưa đánh giá được đầy đủ vì chưa có dữ liệu YouTube thật theo chuỗi thời gian.

*[Chuyển]* Em xin sang phần an ninh, đóng góp đặc thù của đề tài.

---

## Slide 12. An ninh hệ thống và an toàn pipeline

**Ý chính:** bốn cơ chế, hai số đo, một hạn chế còn lại.

Hệ thống có bốn cơ chế. Phân quyền RBAC ba vai trò, và mọi đường dẫn chưa khai báo mặc định chỉ quản trị viên truy cập. Nhật ký kiểm toán ghi mọi thao tác ghi, thao tác xem dữ liệu và cả token sai. Cảnh báo bất thường theo luật cửa sổ trượt: dò mật khẩu, tải dữ liệu hàng loạt, token giả. Và phòng vệ đầu độc dữ liệu, phát hiện nhãn bị lật trước khi huấn luyện.

Nhóm đo hiệu quả bằng mô phỏng. Trong 5 tuần mô phỏng với người dùng bình thường, không có cảnh báo nhầm nào. Về đầu độc dữ liệu, khi kẻ tấn công lật 40% nhãn, F1 cảm xúc giảm từ 0,59 xuống 0,42; phòng vệ đưa lên 0,50, tức là cải thiện một phần chứ không khôi phục hoàn toàn. Khi không bị tấn công, phòng vệ cũng loại nhầm một số mẫu khó, nên chỉ bật khi giám sát nghi ngờ.

Hạn chế còn lại: kẻ tấn công tải dữ liệu thật chậm để né ngưỡng vẫn bị bỏ sót 22%. Hướng khắc phục là phát hiện bất thường theo hồ sơ từng người dùng.

*[Chuyển]* Cuối cùng là bài toán riêng tư trong chính mô hình.

---

## Slide 13. Quyền riêng tư và độ chính xác

**Ý chính:** riêng tư có giá; DP giảm F1 rõ; học liên kết chỉ là mô phỏng.

Câu hỏi CH4 là: bảo vệ riêng tư mà vẫn giữ độ chính xác được không? Biểu đồ cho thấy câu trả lời là có đánh đổi. Dùng differential privacy khi huấn luyện, ε càng nhỏ tức càng riêng tư thì F1 quan điểm càng thấp: từ 0,75 xuống 0,66 ở ε bằng 8, và 0,61 ở ε bằng 1. Ở cảm xúc bảy nhãn, sự sụt giảm mạnh hơn: từ 0,60 còn 0,26 ở ε bằng 1.

Cần lưu ý: thử nghiệm này chỉ huấn luyện lớp cuối trên đặc trưng ViSoBERT đóng băng, vì GPU 4 GB không đủ cho DP-SGD toàn bộ mô hình. Một phần chênh lệch với kết quả trước là do việc đóng băng, không phải do DP.

Nhóm cũng mô phỏng học liên kết FedAvg: các bên chỉ chia sẻ tham số, không chia sẻ dữ liệu thô. Khi dữ liệu lệch mạnh giữa các bên, học liên kết vẫn hơn từng bên tự học riêng khoảng 0,35 F1. Đây chỉ là mô phỏng trên một máy, và tham số vẫn có thể rò rỉ thông tin nên nên kết hợp với DP.

*[Chuyển]* Em xin tổng kết.

---

## Slide 14. Kết luận và hướng phát triển

**Ý chính:** ba kết luận, bốn bước tiếp theo, cảm ơn.

Em xin tóm tắt ba kết luận. Một, nhóm đã xây dựng được hệ thống tích hợp đủ chuỗi thu thập, ẩn danh, phân tích cảm xúc, xu hướng và dashboard phân quyền. Hai, Transformer tiếng Việt vượt rõ máy học cổ điển và BiLSTM, nhưng mô hình tốt nhất phụ thuộc vào bài toán. Ba, an ninh và riêng tư có chi phí đo được: DP làm giảm F1, và đầu độc nhãn có thể làm giảm F1 tới khoảng 0,20.

Hạn chế chính của nghiên cứu là chưa có dữ liệu thu thập thật được gán nhãn. Vì vậy các bước tiếp theo là thu thập dữ liệu YouTube thật và gán nhãn vàng, thử TikTok với khóa thật, bổ sung BERTopic và khôi phục dấu tiếng Việt, và mở rộng DP-SGD cho toàn bộ Transformer.

Em xin cảm ơn hội đồng đã lắng nghe và rất mong nhận được góp ý.

---

## Câu hỏi hội đồng có thể hỏi

**Vì sao dùng F1-macro mà không dùng độ chính xác?**
Dữ liệu mất cân bằng lớp. Lớp trung tính ít mẫu nên độ chính xác che mất lỗi ở lớp đó. F1-macro coi các lớp ngang nhau.

**Vì sao không dùng thẳng LLM?**
LLM nhỏ trong thử nghiệm thua mô hình fine-tune, chậm hơn 41–56 lần, và LLM lớn hoặc dịch vụ ngoài đặt ra rủi ro gửi dữ liệu cá nhân ra ngoài.

**Hệ thống đã chạy trên dữ liệu thật chưa?**
Chưa đủ. Mô hình được huấn luyện và đánh giá trên UIT-VSFC và UIT-VSMEC. Thu thập YouTube đã chạy nhưng chưa có bộ dữ liệu thu thập đủ lớn và được gán nhãn. TikTok chưa thử với khóa thật.

**Kết quả cảm xúc 7 nhãn 0,665 có tốt không?**
Đây là bài toán khó, nhãn tức giận và ngạc nhiên yếu. Con số cao hơn rõ so với TF-IDF (0,595) và BiLSTM (0,503), nhưng vẫn còn nhiều dư địa cải thiện.

**Học liên kết có thực sự được áp dụng không?**
Chỉ là mô phỏng trên một máy, lớp tuyến tính trên đặc trưng đóng băng. Học liên kết toàn bộ Transformer cần nhiều GPU hơn và tốn chi phí truyền tham số lớn.

**Vì sao xu hướng chỉ ở cấp cộng đồng?**
Để phù hợp yêu cầu bảo vệ dữ liệu cá nhân: không tổng hợp hay theo dõi theo từng người dùng.
