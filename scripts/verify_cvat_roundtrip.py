#!/usr/bin/env python3
"""Đối chiếu bản YOLO xuất từ CVAT, đo sai số theo pixel thay vì đòi byte giống nhau."""
import argparse
import json
import sys
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bonus_common import ExportDataset
from pipeline.common import load_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", default="submission/cvat/exported_yolo11.zip")
    parser.add_argument("--out", default="submission/cvat/export_verification.json")
    args = parser.parse_args()
    ds = ExportDataset(ROOT / "submission/export/clean_v1", ROOT / "data/raw/images", load_config()["classes"])
    expected = json.loads((ROOT / "submission/cvat/preparation.json").read_text())
    compared, images, max_delta = 0, 0, 0.0
    with ZipFile(ROOT / args.zip) as archive:
        assert archive.testzip() is None
        names = archive.read(next(n for n in archive.namelist() if n.endswith("obj.names"))).decode().splitlines()
        for filename in archive.namelist():
            stem = Path(filename).stem
            if not filename.endswith(".txt") or not ds.label_path(stem).exists():
                continue
            width, height = ds.image_size(stem)

            def corners(row):
                x, y, w, h = map(float, row[1:])
                return ((x - w / 2) * width, (y - h / 2) * height,
                        (x + w / 2) * width, (y + h / 2) * height)

            source = [text.split() for _, text in ds.read_label_lines(stem)]
            rows = [line.split() for line in archive.read(filename).decode().splitlines() if line.strip()]
            if len(source) != len(rows):
                raise ValueError(f"số box khác ở {stem}")
            pending = [(names[int(row[0])], corners(row)) for row in rows]
            for row in source:
                label, box = ds.classes[int(row[0])], corners(row)
                candidates = [(max(abs(a - b) for a, b in zip(box, other)), index)
                              for index, (name, other) in enumerate(pending) if name == label]
                if not candidates:
                    raise ValueError(f"lớp box không khớp ở {stem}")
                difference, index = min(candidates)
                max_delta = max(max_delta, difference)
                pending.pop(index)
                compared += 1
            images += 1
    if (images, compared) != (expected["n_images"], expected["n_boxes"]):
        raise ValueError("bản xuất CVAT thiếu/thừa ảnh hoặc box")
    result = dict(format="YOLO 1.1", n_images=images, boxes_compared=compared,
                  same_classes_and_counts=True, max_corner_delta_px=max_delta,
                  pixel_tolerance=0.01, within_pixel_tolerance=max_delta <= 0.01,
                  byte_identical_claim=False,
                  note="Có sai số số thực khi chuyển đổi qua CVAT/YOLO; không ghi đè dataset train. YOLO 1.1 không lưu thuộc tính can_review.")
    (ROOT / args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if max_delta > 0.01:
        raise SystemExit("sai số vượt 0.01 pixel, cần kiểm tra trước khi chấp nhận")


if __name__ == "__main__":
    main()
