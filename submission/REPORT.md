# Báo cáo Day 09 — Lê Quang Khải, 2A202603237

## 1. Kết luận trước

**Hold.** Quét 224 ảnh, loại 19 ở intake, nhận và xuất 205 ảnh thành **bản nháp** `clean_v1`. Sau 80 lượt người duyệt **mô phỏng**, không còn lỗi bắt buộc; còn **38/205 ảnh chưa duyệt có cảnh báo = 18,54% ≥ 10%**, nên chưa phát hành. Nguồn: `reports/08_summary.json`, `export/clean_v1/manifest.json`.

## 2. Lỗi và phân việc

`02_error_list_v1.csv`: **208 lượt cờ** = 19 intake + 189 QC (36 lỗi bắt buộc, 153 cảnh báo). Một ảnh/dòng có thể nhận nhiều cờ. Bảng ghi **lượt cờ / ảnh khác nhau**; mẫu số 224 ảnh cho intake (*), 205 cho QC; cấu hình/thống kê tính riêng cấp dataset.

| Mã lỗi | Lượt / ảnh | Ai xử lý, lý do |
|---|---:|---|
| CORRUPT_IMAGE (*) | 2 / 2 | Máy loại ảnh không đọc được |
| BAD_SIZE (*) | 3 / 3 | Máy loại ảnh dưới kích thước quy định |
| DUP_IMAGE_EXACT (*) | 8 / 8 | Máy loại bản sao byte |
| DUP_IMAGE_NEAR (*) | 2 / 2 | Máy loại bản gần trùng theo pHash |
| LEAK_TEST (*) | 4 / 4 | Máy loại ảnh trùng kho test/val |
| MISSING_LABEL_FILE | 6 / 6 | Người gán; máy không bịa nhãn |
| EMPTY_LABEL | 12 / 12 | Người phân biệt ảnh nền với thiếu vật |
| BAD_FORMAT | 3 / 3 | Máy bỏ dòng sai; người kiểm lại vật bị mất |
| BAD_CLASS_ID | 6 / 6 | Máy bỏ ID ngoài danh mục; người gán lại |
| BOX_ZERO | 4 / 4 | Máy bỏ box không có diện tích |
| BOX_OUT_OF_IMAGE | 8 / 8 | Máy cắt về biên; người kiểm ý nghĩa |
| DUP_BOX | 7 / 7 | Máy bỏ dòng sau cùng lớp có IoU cao |
| BAD_CLASS_NAME | 2 / cấu hình | Máy chuẩn hóa tên lớp |
| BOX_TINY | 6 / 4 | Người kiểm vật nhỏ và guideline |
| BOX_HUGE | 3 / 3 | Người kiểm độ ôm vật |
| CLASS_RARE | 4 / dataset | Người xem phân bố lớp |
| POSSIBLE_MISSING | 53 / 52 | Người xác nhận vật thiếu |
| POSSIBLE_LOOSE_BOX | 28 / 24 | Người chỉnh box |
| POSSIBLE_WRONG_CLASS | 18 / 18 | Người xác định lớp |
| POSSIBLE_FALSE_POS | 29 / 27 | Người xác nhận box thừa |

`03_fixes.csv` ghi **35 hành động**: 20 bỏ dòng, 8 cắt box, 1 sửa tên lớp, 6 chuyển người gán. Hàng đợi **125 ảnh**: `img_0020` đầu tiên (11,524 điểm), cộng cảnh báo thiếu/sai lớp và dòng bị bỏ; tiếp theo 6 ảnh chưa có nhãn (10 điểm/ảnh). Trọng số và confidence quyết định thứ tự. Người mô phỏng xem 80/125 ảnh, bao phủ **98/128 lượt cờ ngữ nghĩa v1**, trên 74/104 ảnh có cờ ngữ nghĩa; không đồng nghĩa 98 lỗi đã được chứng minh. Sau duyệt còn 71 cờ trên 63 ảnh, trong đó 25 ảnh đã duyệt; gate đếm 38 ảnh chưa duyệt.

## 3. Calibration (2 ngưỡng)

Đã chạy hai sweep trên 39 ảnh calib; `calibration/calibration.json` được sinh lại với cấu hình cuối. P/R lấy từ các hàng sweep, có làm tròn.

| Tham số | Khởi đầu → chọn | Precision / Recall trước → sau | Lý do |
|---|---|---|---|
| `duplicates.phash_dist` | 2 → **4** | NEAR: 1,00/0,50 → 1,00/0,67; EXACT giữ 1,00/1,00 | Bắt thêm 1/6 ca near, không thêm FP; ngưỡng nhỏ nhất trên plateau 4–14, tránh loại nhầm ảnh |
| `second_opinion.conf` | 0,25 → **0,60** | WRONG: 0,556/0,833 → 0,625/0,833; MISSING: 0,50/1,00 → 0,571/1,00 | Giảm FP, giữ recall thiếu vật/sai lớp; 0,7–0,8 mất recall thiếu vật |

Đánh đổi: LOOSE giảm P/R từ 0,286/0,40 xuống 0,20/0,20; FALSE_POS giữ 0,312/1,00 vì dùng `fp_conf` riêng. Không nâng conf để ép Release.

**Bẫy calibration:** pHash 16 đạt recall near 5/6 trên calib nhưng báo `img_0011` trùng `img_0008` (cách 16): ảnh raw thực tế là tennis và trượt tuyết, khác nhau. Trong khi `img_0074/img_0084` thật sự cùng cảnh cũng cách 16. Xem `evidence/phash_pairs.jpg`; không dùng nhãn test chọn ngưỡng. Calib nhỏ không đại diện mọi cặp raw.

## 4. Cửa chặn và điểm mù

**Chặn thật:** chạy `python -m pipeline.run --budget 0 --work work/gate_demo --reports work/rep_nb --export-dir work/exp_nb`: còn 6/205 ảnh thiếu nhãn → **Rework**, mã thoát **20**, không xuất `work/exp_nb/clean_v1`. Log: `evidence/gate_no_review.txt`.

Đã mở 10 ảnh raw vẽ nhãn (`evidence/visual_inspection.jpg`): `img_0001` thiếu box người bên phải; `img_0050` có box người thành đường thẳng (w=0); `img_0070` có box car bao người bên trái. Đây là quan sát của trợ lý AI, học viên cần tự mở và đối chiếu trước khi nộp.

Hai điểm mù: (1) pHash 4 bỏ lọt `img_0077/img_0223` cùng cảnh nhưng cách 6; (2) checker bỏ sót 4/5 box lỏng trên calib (`calib_002/006/012/024`) và 1/6 sai lớp (`calib_009`). Hai model cùng bỏ sót/nhầm có thể không tạo cảnh báo. Ca biên bổ sung trong `scripts/check_extra_cases.py` kiểm ID inf, dòng trống, hai lỗi cùng dòng, nhiều dự đoán, gate và chặn sửa raw; đều qua.

## 5. Train: raw vs clean (tùy chọn, chấm riêng)

Đã chạy **4 thí nghiệm trên Colab T4**: raw/clean × seed 0/1, cùng `yolo26n.pt`, 20 epoch, batch 16, imgsz 640, cùng gold_val (40 ảnh) và test (100 ảnh) theo script gốc. Các JSON có `config_sha1` khớp cấu hình hiện tại; cả hai lần clean có `manifest_sha1` khớp bản xuất Hold. Bảng dưới do `scripts/summarize_results.py` sinh, độ lệch là độ lệch chuẩn mẫu giữa hai seed.

| biến thể | #ảnh train | số seed | map50 (TB ± độ lệch) | map50_95 (TB ± độ lệch) | precision (TB ± độ lệch) | recall (TB ± độ lệch) |
|---|---|---|---|---|---|---|
| raw | 224 | 2 | 0.726 ± 0.000 | 0.512 ± 0.004 | 0.764 ± 0.061 | 0.649 ± 0.028 |
| clean | 205 | 2 | 0.700 ± 0.030 | 0.486 ± 0.013 | 0.715 ± 0.073 | 0.615 ± 0.017 |

**Clean − raw: mAP50 = −0,0254 (−2,54 điểm phần trăm)**; mAP50-95 cũng giảm khoảng 2,55 điểm phần trăm. Độ lệch chuẩn mAP50 của clean là **0,0305**, lớn hơn độ lớn chênh lệch trung bình; của raw là 0,000212 (bảng làm tròn thành 0,000, không phải bằng 0). Chênh mAP50 theo cặp seed 0/1 lần lượt là −0,0468 và −0,0040. **Raw cao hơn ở cả hai seed đã chạy; chưa có bằng chứng clean tốt hơn raw**, và hai seed chưa đủ để khẳng định mức giảm ổn định khi khái quát sang lần train khác. Trung bình AP50 theo lớp: car tăng 1,10; person tăng 0,53; truck giảm 8,97; bus giảm 2,83 điểm phần trăm.

Hai giả thuyết cần kiểm: (1) raw có 4 cờ rò rỉ test/val cùng ảnh trùng, có thể làm điểm raw tăng giả; log intake chưa chứng minh mức ảnh hưởng, cần phép so sánh loại riêng các ảnh này khi giữ nguyên test. (2) clean vẫn Hold, còn 38/205 ảnh cảnh báo chưa duyệt, lại có ít box truck/bus (42/33 so với 576 person), có thể gây dao động và giảm AP ở hai lớp này; cần kiểm nhãn theo lớp, dự đoán sai và thử nhiều seed hơn, giữ cùng thiết lập. Không chọn ngưỡng hoặc sửa nhãn theo tập test. `train_images=224/205` là số file ảnh được dựng trước khi trainer kiểm dữ liệu; không khẳng định raw thật sự dùng đủ 224 ảnh vì Ultralytics có thể bỏ ảnh/nhãn hỏng, cần log train để xác nhận. Bước tiếp theo: kiểm tra các giả thuyết trên và thêm ít nhất 3 seed, không kết luận cải thiện từ riêng hai seed.

## 6. Quyết định và ghi chú AI

Giữ **Hold**, chỉ dùng bản xuất cho thử nghiệm. Với 205 ảnh, muốn dưới 10% cần giảm cảnh báo chưa xử lý từ 38 xuống ≤20 (ít nhất 18 ảnh), không còn lỗi bắt buộc. Cần vòng duyệt/lô tiếp theo được dự án cho phép; giữ nguyên ngân sách 80 và gate của bài. Đã hoàn thành train so sánh và bổ sung bằng chứng cho cả hai bonus: check QC mới (+3), CVAT (+2), chi tiết ở 6(a)–6(b).

- **Prompt/đặc tả AI:** Codex triển khai theo docstring + test: vào YOLO 5 cột/cache, quy tắc từ cfg, ra Issue/log/verdict; checks chỉ đọc, autofix sửa bản sao, không bịa nhãn.
- **Kiểm chứng:** trợ lý chạy 79 test gốc và 14 test bonus, calibration có lỗi chèn, ca biên, xem ảnh raw và thử Rework không xuất; không sửa test/dữ liệu/file mẫu bảo vệ. Học viên cần đọc và hiểu bốn module theo RULES.md.
- **Một lỗi AI:** ban đầu tạo môi trường bằng Python mặc định 3.14, ngoài dải 3.9–3.13 của đề; đã phát hiện và chuyển sang 3.9.6 trước khi kiểm chứng chính thức.

### 6(a). Bonus check QC mới (+3)

Đã thêm `pipeline/checks/class_balance.py` với mã `CLASS_IMBALANCE` (WARN cấp dataset). Khác `CLASS_RARE` đếm số box tuyệt đối, check mới đo tỷ trọng từng lớp trong tổng box parse được, có ID hợp lệ và kích thước dương; lớp vắng mặt cũng được kiểm. Ngưỡng 10% nằm riêng trong `configs/bonus_qc.yaml`, là heuristic chưa calibration, khác ngưỡng 10% ảnh cảnh báo của gate. Trên clean có **753 box**: car 102 (13,55%), person 576 (76,49%), truck **42 (5,58%)**, bus **33 (4,38%)**; hai lớp cuối được cảnh báo. Cần đánh giá guideline và dữ liệu bổ sung, không tự xóa/nhân bản box.

Check chạy bằng `python scripts/run_bonus_qc.py`; báo cáo ở [bonus_qc/summary.json](bonus_qc/summary.json) và [bonus_qc/class_balance.csv](bonus_qc/class_balance.csv). **14 test mới** tại `bonus_tests/test_class_balance.py` kiểm ranh giới ngưỡng, lớp vắng, ID/dòng hỏng, cấu hình và tính chỉ đọc/tái lập; cùng 79 test gốc đạt **93 test**. Chạy riêng để giữ nguyên registry, cấu hình cố định, báo cáo chính và hash dataset đã train.

### 6(b). Bonus CVAT (+2)

Đã thực hành trên **CVAT Community v2.83.0 local**, project 4, task 39, job 38: [mở job trên máy đã dựng](http://localhost:8080/tasks/39/jobs/38). Nhập nhãn YOLO 1.1 cho **25 ảnh / 164 box** (20 ảnh đầu hàng đợi + 5 ảnh có BOX_TINY). Bộ lọc **Width < 20** cho **24 box / 9 ảnh**, được kiểm chứng bằng API; đã trực tiếp xem giao diện và chụp **5 ảnh** dưới đây:

| Ảnh | Frame CVAT (từ 0) | Box sau lọc width < 20 | BOX_TINY trong pipeline | Screenshot |
|---|---:|---:|---:|---|
| img_0026 | 2 | 6 | 1 | [Ảnh](cvat/screenshots/img_0026.png) |
| img_0051 | 6 | 3 | 1 | [Ảnh](cvat/screenshots/img_0051.png) |
| img_0069 | 8 | 2 | 1 | [Ảnh](cvat/screenshots/img_0069.png) |
| img_0161 | 19 | 3 | 3 | [Ảnh](cvat/screenshots/img_0161.png) |
| img_0183 | 21 | 1 | 1 | [Ảnh](cvat/screenshots/img_0183.png) |

[Bộ lọc đang hiển thị](cvat/screenshots/filter_width_lt_20.png); [bảng kiểm từ CVAT](cvat/verified_counts.csv). Hai phép kiểm khác nhau: CVAT xét **chiều rộng <20px**, BOX_TINY xét **cạnh ngắn <12px**; box khớp filter chưa chắc là lỗi. `can_review=true` đánh dấu 24 box cần người xem lại, tương tự cờ/hàng đợi duyệt của pipeline ([screenshot thuộc tính](cvat/screenshots/can_review.png)); không có nghĩa đã xử lý lỗi.

Đã xuất lại YOLO 1.1: đủ **164 box, cùng lớp**, sai số góc box tối đa **0,00512px** so với bản clean ([kiểm chứng](cvat/export_verification.json)); không khẳng định file giống từng byte. Không sửa hình học thủ công hay ghi đè dataset train. Việc xem bonus không cộng vào 80 ảnh duyệt chính và không đổi quyết định **Hold**.
