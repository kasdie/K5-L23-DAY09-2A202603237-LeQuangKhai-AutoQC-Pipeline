"""Đọc đúng tập ảnh/nhãn của export mà không dựng lại hoặc sửa dataset gốc."""
import hashlib
import json
from pathlib import Path

from pipeline.common import Dataset, IMG_EXTS


def sha1(path):
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()


class ExportDataset(Dataset):
    def __init__(self, export_dir, images_dir, classes):
        super().__init__(export_dir, classes)
        self.manifest_path = self.root / "manifest.json"
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        if manifest["classes"] != list(classes):
            raise ValueError("classes trong export không khớp cấu hình")
        names = manifest["images"]
        if len(names) != manifest["n_images"] or len({Path(n).stem for n in names}) != len(names):
            raise ValueError("manifest có số ảnh sai hoặc trùng stem")
        self.images_dir = Path(images_dir)
        self._selected_images = []
        for name in sorted(names):
            if Path(name).name != name or Path(name).suffix.lower() not in IMG_EXTS:
                raise ValueError("tên ảnh trong manifest không hợp lệ")
            image = self.images_dir / name
            label = self.label_path(image.stem)
            if not image.is_file() or not label.is_file():
                raise FileNotFoundError(f"thiếu ảnh/nhãn export: {image.stem}")
            if sha1(label)[:12] != manifest["label_sha1"][label.name]:
                raise ValueError(f"nhãn không khớp hash manifest: {label.name}")
            self._selected_images.append(image)

    def image_files(self):
        return list(self._selected_images)
