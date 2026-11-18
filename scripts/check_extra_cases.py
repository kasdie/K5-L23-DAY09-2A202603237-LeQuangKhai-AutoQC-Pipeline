#!/usr/bin/env python3
"""Các ca biên bổ sung, chạy trên dữ liệu tạm; không sửa tests/ hoặc data/."""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.checks import label_format, second_opinion
from pipeline.common import Dataset, Issue, load_config
from pipeline.steps import autofix, gate


def main():
    cfg = load_config()
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "images").mkdir()
        (root / "labels").mkdir()
        Image.new("RGB", (640, 480)).save(root / "images" / "sample.JPG")
        ds = Dataset(root, cfg["classes"])
        path = ds.label_path("sample")
        path.write_text("1 .95 .5 .2 .2\n\n1 .95 .5 .2 .2\ninf .5 .5 .2 .2\n", encoding="utf-8")
        issues = label_format.run(ds, cfg)
        assert {i.code for i in issues if i.line == 3} >= {"DUP_BOX", "BOX_OUT_OF_IMAGE"}
        assert any(i.code == "BAD_FORMAT" and i.line == 4 for i in issues)
        changes = autofix.fix(ds, issues, cfg)
        assert [(c["line"], c["action"]) for c in changes] == [
            (1, "clip_box"), (3, "drop_line"), (4, "drop_line")]
        assert label_format.run(ds, cfg) == []
        assert autofix.fix(ds, label_format.run(ds, cfg), cfg) == []
        print("PASS: hai lỗi cùng dòng, dòng trống, ID inf, clip/drop và chạy lại không đổi")

        path.write_text("0 .5 .5 .3 .4\n\nmalformed\n1 .1 .1 .1 .1\n", encoding="utf-8")
        before = path.read_bytes()
        predictions = {"sample": [[0, .95, .5, .5, .3, .4],
                                   [1, .95, .15, .7, .12, .3],
                                   [2, .95, .85, .7, .12, .3]]}
        issues = second_opinion.run(ds, cfg, predictions)
        assert [(i.code, i.line) for i in issues] == [
            ("POSSIBLE_MISSING", None), ("POSSIBLE_MISSING", None),
            ("POSSIBLE_FALSE_POS", 4)]
        assert path.read_bytes() == before
        print("PASS: nhiều dự đoán, dòng hỏng/trống, giữ thứ tự và số dòng, check chỉ đọc")

        # 1/11 < 0.1 dù hiển thị làm tròn có thể làm người đọc nhầm.
        warning = Issue("extra", "warn", "X", "a0", "test")
        stems = [f"a{i}" for i in range(11)]
        assert gate.decide([warning], stems, cfg)["decision"] == "Release"
        dataset_error = Issue("extra", "error", "BAD_CLASS_NAME", "data.yaml", "test")
        assert gate.decide([dataset_error], stems, cfg, reviewed={"data.yaml"})["decision"] == "Rework"
        print("PASS: gate dùng tỉ lệ thực, lỗi cấp dataset không bị bỏ qua khi đã duyệt")

    try:
        autofix.fix(Dataset(ROOT / "data/raw", cfg["classes"]), [], cfg)
    except ValueError:
        print("PASS: autofix từ chối sửa trực tiếp data/raw")
    else:
        raise AssertionError("thiếu chặn sửa raw")


if __name__ == "__main__":
    main()
