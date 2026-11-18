# Các bước còn lại — Lê Quang Khải, 2A202603237

Phần lõi và train đã hoàn thành: 4 module, hai sweep calibration, báo cáo lỗi, bản xuất có manifest, bốn lần train raw/clean × seed 0/1 và REPORT.md đã cập nhật kết quả. Kết luận QC vẫn là **Hold**; mAP50 trung bình clean thấp hơn raw 2,54 điểm phần trăm, không cần ép kết quả cải thiện để nộp. Các bước Colab bên dưới giữ làm hướng dẫn tái lập, không cần chạy lại để hoàn tất bài hiện tại. CVAT thưởng +2 chưa làm; chưa nộp LMS và chưa đẩy repo riêng.

## 1. Mở và chạy lại trên máy này

Trong Terminal:

```bash
cd /Users/phambaovy/Applications/vscode/vf/day09/lab
source .venv/bin/activate
python --version
make test
python scripts/check_extra_cases.py
make calibrate
make run
make check-core
```

Python hiện tại trong môi trường là **3.9.6**. `.venv` trỏ đến `.venv39`; không đưa cả hai lên GitHub. Không kích hoạt môi trường thì dùng `make check-core PY=.venv/bin/python`. Trên máy khác dùng Python 3.9–3.13, tạo venv mới và `pip install -r requirements.txt`; file `requirements-core-py39.lock.txt` ghi phiên bản đã kiểm chứng trên máy này.

`make run` trả thành công cho Hold; lệnh `python -m pipeline.run` trả **10** khi Hold. Đây là kết luận QC, không phải chương trình bị lỗi. Báo cáo chính ở `submission/reports`; thí nghiệm riêng luôn dùng `--reports work/...`, `--work work/...`, `--export-dir work/...` để giữ bằng chứng chính.

## 2. Tự đọc code và ảnh trước khi nộp

Quy tắc lớp yêu cầu học viên hiểu code AI tạo. Đọc docstring rồi lần theo:

- `pipeline/checks/label_format.py`: parse từng dòng; dừng ở lỗi cấu trúc/ID/diện tích; kiểm tràn, trùng, nhỏ/lớn; giữ số dòng gốc.
- `pipeline/steps/autofix.py`: chỉ ERROR; gom lỗi theo ảnh/dòng trước khi ghi; xóa dòng thắng cắt box; thiếu nhãn chuyển người; ghi mọi thay đổi; chặn sửa raw.
- `pipeline/checks/second_opinion.py`: dự đoán đủ conf/diện tích → thiếu, lỏng, sai lớp; false positive dùng ngưỡng riêng và số dòng gốc. Model chỉ đưa cảnh báo.
- `pipeline/steps/gate.py`: ERROR luôn Rework; nếu không có ERROR thì tính ảnh cảnh báo chưa duyệt/tổng ảnh, từ 10% trở lên là Hold.

Mở `submission/evidence/visual_inspection.jpg` và `phash_pairs.jpg`. Các nhận xét bằng mắt trong REPORT.md do trợ lý AI thực hiện; bạn cần tự đối chiếu. REPORT đã ghi rõ việc dùng AI, không khẳng định bạn đã tự xem hoặc tự viết toàn bộ code.

## 3. Đưa bài lên GitHub riêng và nộp phần lõi

1. Vào repo đề, chọn **Fork**. Đặt tên **K5-L23-DAY09-2A202603237-AutoQCPipeline**, để public. Fork giữ chung lịch sử với bản đang làm nên có thể push bình thường.
2. Thay địa chỉ remote bằng URL fork của bạn (không push vào repo giảng viên):

```bash
git remote set-url origin https://github.com/TAI_KHOAN_CUA_BAN/K5-L23-DAY09-2A202603237-AutoQCPipeline.git
git remote -v
git status --short
git log --oneline -6
git push -u origin main
```

Nếu đã tạo repo bằng **Use this template** thì lịch sử có thể khác: không force push. Clone repo mới sang thư mục khác, chép các file đã làm và `submission/` từ đây, rồi commit/push trong repo mới.

3. Kiểm tra trên GitHub có 4 module, `configs/pipeline.yaml`, `submission/REPORT.md`, `submission/calibration/`, `submission/reports/` và `submission/export/clean_v1/manifest.json`.
4. Nộp link repo public lên **https://aithucchien.vinuni.edu.vn** hoặc kênh lớp chỉ định. Không có train thì nộp phần lõi với `make check-core`, không khai đã hoàn thành 15 điểm train.

## 4. Train trên Colab — chọn một cách

### Cách A: dùng GitHub sau khi push

Mở notebook `notebooks/day09_train_compare.ipynb` của **repo bạn** trên Colab. Runtime → Change runtime type → **T4 GPU**. Sửa duy nhất `REPO_URL` sang repo public của bạn; giữ seed [0, 1], epoch 20 và variants ["raw", "clean"]. Chạy các ô theo thứ tự, cuối cùng tải `results.zip`. Không cần làm file ANALYSIS riêng trong notebook mẫu: hướng dẫn chính của lab yêu cầu cập nhật mục 5 REPORT.md.

### Cách B: tải ZIP bài đã làm, không phải chờ push

1. Mở **https://colab.research.google.com**, chọn Upload notebook, tải file `notebooks/day09_completed_colab.ipynb`.
2. Chọn runtime **T4 GPU**, chạy ô cài đặt.
3. Ở ô upload, chọn file **day09-lab-2A202603237.zip** nằm cạnh thư mục `lab/` trên máy này.
4. Run all để train raw/clean, seed 0/1, 20 epoch, rồi tải `results.zip`. Bốn lần train có thể mất khoảng 20 phút hoặc lâu hơn tùy GPU.

Notebook mới chỉ tự động hóa upload và gọi đúng các script gốc; không sửa script train, không tạo kết quả giả. Dữ liệu clean đang **Hold**, được dùng thử nghiệm dưới dạng bản nháp. Khi Colab ngắt giữa chừng, có thể chạy lại lệnh train với `--skip-existing` nếu các JSON còn trong phiên.

### Nhận và kiểm tra kết quả

Giải nén `results.zip`, chép các file trong `submission/results/` về đúng thư mục tương ứng của repo trên máy bạn; giữ nguyên tên và nội dung JSON. Sau đó:

```bash
python scripts/summarize_results.py
make check
```

Lệnh tổng hợp cần `matplotlib`: nếu máy chưa có, `pip install matplotlib` trong venv hoặc dùng luôn comparison.md đã sinh trên Colab. Giữ **bản export hiện tại** sau khi train; đổi manifest/cấu hình thì phải train lại để khớp hash.

Cập nhật REPORT.md mục 5: dán bảng comparison.md, nêu clean − raw so với độ lệch giữa seed, AP theo lớp và ít nhất hai giả thuyết. Nếu khác biệt nằm trong nhiễu, kết luận **chưa đủ bằng chứng**. Sau khi sửa báo cáo, commit/push theo quy trình lớp. Nếu không dùng Git CLI, có thể upload riêng các file kết quả/báo cáo qua giao diện GitHub.

## 5. CVAT — tùy chọn thưởng +2

Phần này cần bạn đăng nhập CVAT và tự thao tác/chụp bằng chứng:

1. Tạo project, nhập nhãn từ `cvat/labels.json`.
2. Tạo task với khoảng 20 ảnh đầu hàng đợi `05_review_queue.csv` từ `work/run/ds/images/`, nhập nhãn YOLO 1.1 theo `docs/CVAT_FILTER.md`.
3. Trong Filters đặt **width < 20** (có thể thêm height < 20); ghi tên ảnh, số box khớp và chụp màn hình bộ lọc.
4. So với `BOX_TINY` trong báo cáo: pipeline kiểm cạnh ngắn <12px, khác bộ lọc 20px nên không nhất thiết trùng số lượng. Không xóa hàng loạt chỉ vì box nhỏ.
5. Thêm kết quả thật vào REPORT.md mục 6; giải thích `can_review` đánh dấu đối tượng cần người xem lại, tương tự thông tin cảnh báo/hàng đợi của pipeline.

Nếu chưa thao tác và chưa có screenshot thì giữ trạng thái chưa làm CVAT; không khai điểm thưởng.
