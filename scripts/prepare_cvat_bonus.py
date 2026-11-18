#!/usr/bin/env python3
"""Đóng gói ảnh/YOLO 1.1 và tính số box dự kiến cho bộ lọc CVAT width < 20.

Đây là bước chuẩn bị, không thay thế việc chạy CVAT và chụp screenshot thật.
"""
import argparse
import csv
import json
import shutil
import sys
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.checks import label_format
from pipeline.common import load_config, parse_yolo_line
from bonus_common import ExportDataset, sha1


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def zip_entry(archive, name, content):
    info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, content)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", default="submission/export/clean_v1")
    parser.add_argument("--images", default="data/raw/images")
    parser.add_argument("--queue", default="submission/reports/05_review_queue.csv")
    parser.add_argument("--out", default="submission/cvat")
    args = parser.parse_args(argv)
    cfg = load_config()
    ds = ExportDataset(ROOT / args.export, ROOT / args.images, cfg["classes"])
    images = {p.stem: p for p in ds.image_files()}
    tiny = {}
    for issue in label_format.run(ds, cfg):
        if issue.code == "BOX_TINY":
            tiny.setdefault(issue.image, []).append(issue.line)
    with (ROOT / args.queue).open(encoding="utf-8") as f:
        selected = [r["image"] for r in csv.DictReader(f) if r["image"] in images][:20]
    # Thêm 5 ảnh có BOX_TINY để đối chiếu rõ ngưỡng 12px và bộ lọc 20px.
    selected = sorted(set(selected) | set(sorted(tiny)[:5]))
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    matches, frames = [], []
    for frame, stem in enumerate(selected):
        width, height = ds.image_size(stem)
        all_lines = ds.read_label_lines(stem) or []
        for line, text in all_lines:
            cls, _, _, w, h = parse_yolo_line(text)
            if w * width < 20:
                matches.append(dict(image=stem, frame=frame, line=line, label=ds.classes[cls],
                                    width_px=round(w * width, 6), height_px=round(h * height, 6),
                                    box_tiny=line in tiny.get(stem, [])))
        own = [r for r in matches if r["image"] == stem]
        frames.append(dict(image=stem, filename=images[stem].name, frame=frame,
                           n_boxes=len(all_lines), width_lt_20=len(own),
                           box_tiny=len(tiny.get(stem, [])),
                           width_lt_20_lines=";".join(str(r["line"]) for r in own),
                           box_tiny_lines=";".join(map(str, tiny.get(stem, [])))))
    with ZipFile(out / "images.zip", "w") as archive:
        for stem in selected:
            zip_entry(archive, images[stem].name, images[stem].read_bytes())
    with ZipFile(out / "annotations_yolo11.zip", "w") as archive:
        zip_entry(archive, "obj.names", ("\n".join(ds.classes) + "\n").encode())
        zip_entry(archive, "obj.data", f"classes = {len(ds.classes)}\ntrain = train.txt\nnames = obj.names\nbackup = backup/\n".encode())
        zip_entry(archive, "train.txt", "".join(f"obj_train_data/{images[s].name}\n" for s in selected).encode())
        for stem in selected:
            zip_entry(archive, f"obj_train_data/{stem}.txt", ds.label_path(stem).read_bytes())
    shutil.copy2(ROOT / "cvat/labels.json", out / "project_labels.json")
    write_csv(out / "expected_frames.csv", frames,
              ["image", "filename", "frame", "n_boxes", "width_lt_20", "box_tiny", "width_lt_20_lines", "box_tiny_lines"])
    write_csv(out / "expected_matches.csv", matches,
              ["image", "frame", "line", "label", "width_px", "height_px", "box_tiny"])
    summary = dict(status="prepared", n_images=len(selected), n_boxes=sum(r["n_boxes"] for r in frames),
                   width_filter="width < 20", width_lt_20_boxes=len(matches),
                   width_lt_20_images=sum(r["width_lt_20"] > 0 for r in frames),
                   box_tiny_boxes=sum(r["box_tiny"] for r in frames),
                   source_manifest_sha1=sha1(ds.manifest_path),
                   images_zip_sha1=sha1(out / "images.zip"),
                   annotations_zip_sha1=sha1(out / "annotations_yolo11.zip"),
                   selection="20 ảnh đầu hàng đợi + 5 ảnh BOX_TINY, khử trùng, xếp theo tên",
                   note="Số dự kiến tính từ export; chỉ xác nhận bonus CVAT sau khi thao tác và có screenshot thật.")
    (out / "preparation.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
