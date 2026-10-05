# Báo cáo Day 19 - Flat RAG vs GraphRAG

**Họ tên:** Đinh Đức Long  **MSSV:** 2A202602633  **Ngày:** 05/10/2026

## 1. Chi phí (10 điểm)

Hai bảng kết quả trích trực tiếp từ file `ket_qua_benchmark_kg.txt`:

```
== Indexing (one-off)
pipeline  calls    in_tok  out_tok       USD  seconds
flat        176         0        0   0.00000    107.0
graph       196     34619     6151   0.00592    142.1

== Querying (mean per question)
pipeline  recall  judge   in_tok  out_tok       USD  seconds
flat        0.51   1.50      696       74   0.00010     1.56
graph       1.00   2.00     5622      146   0.00062    12.23
```

| Chỉ số | Flat | Graph | Graph / Flat |
| --- | --- | --- | --- |
| Indexing USD | $0.00000 | $0.00592 | Tăng thêm $0.00592 |
| Indexing giây | 107.0s | 142.1s | 1.33x |
| Mỗi câu: USD | $0.00010 | $0.00062 | 6.20x |
| Mỗi câu: giây | 1.56s | 12.23s | 7.84x |
| Mỗi câu: in_tok | 696 | 5622 | 8.08x |

**Chi phí tăng thêm đến từ đâu?**
Chi phí tăng thêm ở khâu indexing chủ yếu đến từ 20 lượt gọi LLM bóc tách thực thể từ 20 bài báo tin tức (tiêu tốn 34.619 input tokens và 6.151 output tokens, mất $0.00592, khoảng 150 đồng), trong khi 18 điều luật được em bóc tách bằng regex nên hoàn toàn miễn phí. Ở khâu truy vấn, chi phí tăng gấp 6.2 lần và input token tăng gấp 8 lần do prompt của GraphRAG phải gánh thêm danh sách các sự kiện trích từ đồ thị (trung bình 18 đến 23 facts mỗi câu) để LLM có đầy đủ căn cứ điều luật.

Về điểm hòa vốn: Xét thuần túy tiền API thì GraphRAG luôn tốn hơn Flat RAG $0.00052 cho mỗi câu hỏi, nên không có điểm hòa vốn theo nghĩa càng gọi nhiều càng rẻ. Nhưng nếu xét trên chất lượng câu trả lời thì ở các câu hỏi phức tạp (Q3, Q4, Q5, Q6), Flat RAG chỉ đạt recall từ 0.00 đến 0.40. Nếu muốn Flat RAG trả lời được bằng cách tăng top_k từ 3 lên 15 hoặc 20 chunk để vét thông tin, số lượng token đầu vào của Flat RAG sẽ vượt 4.000 tokens và chi phí sẽ xấp xỉ GraphRAG mà mô hình vẫn rất dễ bị loạn ngữ cảnh.

## 2. Từng câu hỏi (10 điểm)

| Câu | Loại | Flat recall / judge | Graph recall / judge | Thắng | Vì sao (1 câu) |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 | single-hop-law | 1.00 / 2 | 1.00 / 2 | Hòa | Khái niệm tiền chất nằm trọn trong Điều 2 Luật Phòng chống ma túy nên vector search lấy đúng chunk là trả lời chuẩn. |
| Q2 | single-hop-news | 1.00 / 2 | 1.00 / 2 | Hòa | Danh sách bị cáo nhận án tử hình nằm đầy đủ trong bài báo vụ 36kg ma túy nên Flat RAG tìm trúng thông tin. |
| Q3 | cross-kb | 0.33 / 1 | 1.00 / 2 | Graph | Mức án của Lê Minh Thành nằm ở báo nhưng Điều 251 và khung cơ bản nằm ở luật, Flat RAG không thể tự nối hai tài liệu rời nhau. |
| Q4 | cross-kb | 0.33 / 1 | 1.00 / 2 | Graph | Bài báo chỉ ghi hành vi tổ chức sử dụng ma túy, chỉ có GraphRAG mới nhảy sang Điều 255 BLHS để tìm ra mức án tối đa là tù chung thân. |
| Q5 | cross-kb-multi-hop | 0.40 / 1 | 1.00 / 2 | Graph | Flat RAG chịu thua trước câu hỏi khung hình phạt cho 9.6kg MDMA, trong khi đồ thị đối chiếu khối lượng sang điểm b khoản 4 Điều 250 để chỉ ra mức án tử hình. |
| Q6 | aggregation | 0.00 / 2 | 1.00 / 2 | Graph | Dữ liệu các vụ việc liên quan MDMA nằm rải rác ở nhiều bài báo, top-k vector search bị hụt từ khóa trong khi đồ thị gom đủ qua node Substance. |

**Quy luật rút ra giữa loại câu hỏi và bên thắng:**
Với câu hỏi đơn nguồn (single-hop), thông tin nằm gọn trong một văn bản thì Flat RAG và GraphRAG có kết quả ngang nhau. Với câu hỏi xuyên nguồn (cross-kb) hoặc gom nhóm phân tán (aggregation), GraphRAG thắng áp đảo vì đồ thị đã nối sẵn các mối quan hệ logic giữa sự việc ngoài đời với điều luật tương ứng.

## 3. Phân tích lỗi (20 điểm)

### Lỗi E2: Thiếu ngữ cảnh luật khi suy luận mức phạt (Flat RAG thất bại)

- **Hiện tượng:** Ở câu Q5, khi hỏi về vụ Cái Quang Huy vận chuyển hơn 9.6kg MDMA và khung hình phạt tương ứng, Flat RAG chỉ trả lời được tội danh từ bài báo nhưng đầu hàng trước khung hình phạt ("Khoản của điều luật và khung hình phạt: Ngữ cảnh không đủ thông tin"). Trong khi đó, GraphRAG chỉ ra chính xác điểm b khoản 4 Điều 250 BLHS với khung hình phạt cao nhất là 20 năm, tù chung thân hoặc tử hình.
- **Bằng chứng:**
  Câu trả lời của Flat RAG trong file `ket_qua_benchmark_kg.txt`:
  > "Dựa trên ngữ cảnh: Tội danh: Cái Quang Huy bị truy tố về tội 'vận chuyển trái phép chất ma túy'... Khoản của điều luật và khung hình phạt: Ngữ cảnh không đủ thông tin."
  
  Truy vấn Cypher kiểm tra đường nối và các khoản luật tương ứng trên đồ thị:
  ```cypher
  MATCH (p:Person {name: 'Cái Quang Huy'})-[:INVOLVED_IN]->(k:Case)-[:CHARGED_WITH]->(c:Crime)<-[:DEFINES]-(a:Article)-[:HAS_CLAUSE]->(cl:Clause)
  WHERE cl.number = 4
  RETURN p.name, k.name, c.name, a.id, cl.number, cl.penalty;
  ```
  Kết quả trả về trên Neo4j:
  ```
  p.name: "Cái Quang Huy"
  k.name: "Vụ vận chuyển trái phép chất ma túy qua sân bay Nội Bài do Cái Quang Huy thực hiện"
  c.name: "vận chuyển trái phép chất ma túy"
  a.id: "Điều 250 BLHS"
  cl.number: 4
  cl.penalty: "phạt tù 20 năm, tù chung thân hoặc tử hình"
  ```
- **Nguyên nhân:** Lỗi này nằm ở bước Retrieval của Flat RAG. Vector search tìm kiếm theo độ tương đồng ngữ nghĩa của câu hỏi. Câu hỏi nhắc tên "Cái Quang Huy" nên cả 3 chunk vector trả về đều thuộc bài báo. Chunk văn bản của Điều 250 BLHS không hề chứa cái tên "Cái Quang Huy", do đó điểm tương đồng vector rất thấp và bị văng ra khỏi top-k. GraphRAG xử lý được nhờ bước Thiết kế ontology: đưa tội danh "vận chuyển trái phép chất ma túy" làm node cầu nối `Crime`, cho phép nhảy từ vụ án sang Điều 250 và bóc các khoản tương ứng.
- **Đề xuất sửa:** Với văn bản pháp lý, không thể chỉ trông cậy vào vector search thuần túy. Nếu không có đồ thị, pipeline RAG bắt buộc phải có bước nhận diện thực thể tội danh bằng mô hình chuyên biệt rồi truy vấn thêm văn bản luật vào ngữ cảnh, hoặc chấp nhận dùng Knowledge Graph để định tuyến quan hệ có cấu trúc.

### Lỗi E5: Giới hạn truy xuất diện rộng ở câu hỏi tổng hợp (Aggregation Bottleneck)

- **Hiện tượng:** Ở câu Q6, Flat RAG có điểm recall bằng 0.00 vì chỉ nêu được 3 vụ trong phạm vi 3 chunk lấy về và không gọi đúng tên thực thể chính (bỏ sót Cái Quang Huy, Lê Minh Thành, Viện Pháp y tâm thần). GraphRAG đạt recall 1.00 tuyệt đối nhờ gom đủ các vụ việc dính dáng đến MDMA trong cơ sở dữ liệu.
- **Bằng chứng:**
  Câu trả lời Q6 của Flat RAG (trích từ `ket_qua_benchmark_kg.txt`):
  > "Dựa trên ngữ cảnh, cả 3 vụ việc đều có liên quan đến ma túy MDMA: 1. Vụ việc thứ nhất... liên quan đến các nhân vật như Đạt và Huy. 2. Vụ việc thứ hai: Công an bắt quả tang Thành... 3. Vụ việc thứ ba: Kết quả giám định..." (Bị thiếu tên đầy đủ của 3 thực thể bắt buộc trong must_include nên recall = 0.00).
  
  Truy vấn Cypher gom nhóm trực tiếp từ node Substance trên đồ thị của em:
  ```cypher
  MATCH (k:Case)-[r:INVOLVES]->(s:Substance)
  WHERE s.name = 'MDMA'
  RETURN k.name, r.amount;
  ```
  Kết quả trả về:
  ```
  k.name: "Vụ vận chuyển hơn 10kg ma túy từ Đức về Việt Nam qua sân bay Nội Bài", amount: "hơn 9,6kg"
  k.name: "Vụ mua bán trái phép chất ma túy do Lê Minh Thành và đồng phạm thực hiện tại Hà Nội", amount: "5 viên"
  k.name: "Vụ án sai phạm tại Viện Pháp y tâm thần Trung ương", amount: "0,686g"
  k.name: "Vụ triệt phá 8 đường dây ma túy liên quan đến Hoàng Nato tại TP.HCM", amount: "khoảng 100g ma túy tổng hợp"
  ```
- **Nguyên nhân:** Lỗi này nằm ở cả bước Retrieval (tham số top_k=3) và Thiết kế Ontology ban đầu. Dữ liệu về chất MDMA phân tán ở nhiều bài viết độc lập. Vector search chỉ lấy đúng 3 chunk điểm cao nhất nên không thể bao quát toàn bộ tài liệu. Mặt khác, nếu dùng ontology gợi ý một chiều (chỉ đi từ Case sang Luật), câu hỏi hỏi về Chất sẽ không biết đường tìm về Vụ án. Em đã khắc phục điểm này bằng cách thiết kế truy vấn hai chiều trong hàm `context()`, cho phép tìm kiếm các Case nối với node Substance được hỏi.
- **Đề xuất sửa:** Khi gặp các câu hỏi tổng hợp mang tính gom nhóm, Knowledge Graph cần được thiết kế hỗ trợ duyệt hai chiều từ thực thể trung gian (ở đây là Substance) ngược về các sự kiện (Case), kết hợp chuẩn hóa các từ lóng ("kẹo", "thuốc lắc" về "MDMA") ngay từ lúc nạp dữ liệu.

## 4. Kết luận (5 điểm)

Từ các số liệu thực tế đo được qua benchmark:

1. **Khi nào Flat RAG là đủ:**
   - Với các câu hỏi tra cứu dữ kiện đơn lẻ (single-hop) mà đáp án nằm trọn trong một đoạn văn bản (như Q1 tra cứu luật, Q2 tìm danh sách bị cáo trong một bài báo). Ở nhóm này, Flat RAG trả lời chính xác tương đương GraphRAG (recall 1.00, judge 2) nhưng chi phí rẻ hơn 6 lần (0.00010 USD so với 0.00062 USD) và thời gian phản hồi nhanh gấp 8 lần (1.56 giây so với 12.23 giây). Nếu dữ liệu đồng nhất và câu hỏi không đòi hỏi suy luận chéo, dùng Flat RAG là tối ưu và tiết kiệm nhất.

2. **Khi nào bắt buộc phải dùng Knowledge Graph (GraphRAG):**
   - Khi bài toán yêu cầu kết nối hai miền dữ liệu độc lập (cross-kb như Q3, Q4, Q5), ví dụ từ tên người và hành vi trong tin tức nhảy sang điều luật và khung hình phạt tương ứng.
   - Khi bài toán đòi hỏi gom nhóm toàn diện (aggregation như Q6) mà các mảnh thông tin nằm rải rác ở nhiều bài báo khác nhau.
   - Ở các trường hợp này, Flat RAG gần như thất bại hoàn toàn (recall tụt xuống 0.00 đến 0.40), trong khi GraphRAG duy trì độ chính xác tuyệt đối (recall 1.00, judge 2.00). Khoản chi phí bỏ ra ban đầu khoảng $0.00592 để nạp đồ thị là hoàn toàn xứng đáng với giá trị câu trả lời mang lại.

## 5. Tự kiểm (5 điểm)

Output kiểm tra test tự động:

```
$ pytest tests/ -q
................................................                         [100%]
48 passed in 0.13s
```

Output kiểm tra hợp đồng hệ thống:

```
$ python bench_kg.py --check
[OK] Dữ liệu: 18 điều luật, 20 bài báo
[OK] KG-1 link_entity
[OK] Neo4j kết nối được
[provider] chat = gemini:gemini-3.5-flash-lite | embedding = gemini:gemini-embedding-001
[OK] KG-2 build_graph: 148 node / 294 cạnh, đường xuyên 2 KB dài 2 cạnh
[OK] KG-3 context: 23 dữ kiện, có Điều 251
[OK] KG-4 GraphRAGAgent.answer
[OK] Chi phí check: 1 lần gọi LLM, $0.00054. Graph nhỏ (luật + 1 bài) vẫn còn trong Neo4j để bạn xem; chạy --judge để dựng graph đầy đủ.
```

3 ảnh chụp màn hình Neo4j Browser trong thư mục `report/img/`:
- `report/img/kg_count.png`: Bảng đếm 208 node theo 7 label trong đồ thị (thấy rõ ô nhập lệnh và bảng số lượng từng loại).
- `report/img/kg_cross_kb.png`: Đường đi xuyên 2 KB từ Person qua Case, Crime đến Article (thấy rõ ô nhập lệnh và cột Results overview).
- `report/img/kg_my_case.png`: Đường đi trọn vẹn cho nhân vật tự chọn Cái Quang Huy (kết nối vụ án vận chuyển ma túy qua sân bay Nội Bài đến Điều 250 BLHS, kèm địa điểm Hà Nội và các chất MDMA, Ketamine).

Người đã chọn cho `kg_my_case.png`: Cái Quang Huy

## Vấn đề gặp phải (không tính điểm)

- **Lỗi model Gemini mặc định bị quá hạn:** Ban đầu cấu hình trong repo để model chat mặc định là `gemini-2.5-flash-lite`. Khi chạy, Google API báo lỗi 404 vì model này đã đóng cho tài khoản mới. Em đã viết một đoạn script ngắn để liệt kê các model đang mở của tài khoản và đổi sang `gemini-3.5-flash-lite` trong `src/llm.py`, sau đó hệ thống gọi API bình thường.
- **Chạm trần Rate Limit ở gói Free Tier:** Khi chạy nhồi 176 chunk embedding một lúc cho Flat RAG, Google API trả về mã lỗi 429 vì gói miễn phí chỉ cho phép tối đa 100 requests/phút. Em đã bổ sung cơ chế retry kèm thời gian chờ theo cấp số nhân (exponential backoff) vào cả hàm `embed` và `chat` trong `src/llm.py`. Nhờ vậy, khi gặp mã 429 chương trình sẽ tự ngủ khoảng 5 đến 10 giây rồi gửi lại, giúp lệnh benchmark chạy trọn vẹn từ đầu đến cuối mà không bị dừng đột ngột.
