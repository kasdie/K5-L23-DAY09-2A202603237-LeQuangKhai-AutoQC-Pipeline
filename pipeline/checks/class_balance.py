"""Bonus QC: cảnh báo lớp chiếm ít box hợp lệ so với toàn bộ dataset.

Khác CLASS_RARE (đếm tuyệt đối), CLASS_IMBALANCE xét tỷ trọng từng lớp,
kể cả lớp không có box. Chỉ đọc dữ liệu, chỉ WARN, không tự cân bằng hay sửa nhãn.
Ngưỡng cfg['class_balance']['min_fraction'] là heuristic cần người diễn giải.
"""
import math

from ..common import WARN, Issue, parse_yolo_line


def class_counts(ds):
    counts = [0] * len(ds.classes)
    for image in ds.image_files():
        for _, text in ds.read_label_lines(image.stem) or []:
            try:
                cls, _, _, width, height = parse_yolo_line(text)
            except (ValueError, OverflowError):
                continue
            if 0 <= cls < len(counts) and width > 0 and height > 0:
                counts[cls] += 1
    return counts


def run(ds, cfg):
    threshold = float(cfg["class_balance"]["min_fraction"])
    if not math.isfinite(threshold) or not 0 < threshold < 1:
        raise ValueError("class_balance.min_fraction phải hữu hạn và nằm trong (0, 1)")
    counts = class_counts(ds)
    total = sum(counts)
    if total == 0:
        return []  # Không có mẫu số: không suy luận phân bố lớp.
    return [
        Issue("class_balance", WARN, "CLASS_IMBALANCE", "<dataset>",
              f"lớp {name}: {count}/{total} box ({count / total:.2%}) < {threshold:.2%}; cần người đánh giá",
              extra={"class_id": cls, "class_name": name, "boxes": count,
                     "total_boxes": total, "fraction": count / total,
                     "min_fraction": threshold})
        for cls, (name, count) in enumerate(zip(ds.classes, counts))
        if count / total < threshold
    ]
