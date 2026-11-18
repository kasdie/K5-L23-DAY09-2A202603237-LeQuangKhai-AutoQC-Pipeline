#!/usr/bin/env python3
"""Một lệnh chạy check bổ sung; giữ nguyên gate, export và kết quả train chính."""
import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.checks import class_balance
from pipeline.common import load_config
from pipeline.steps.report import write_report
from bonus_common import ExportDataset, sha1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", default="submission/export/clean_v1")
    parser.add_argument("--images", default="data/raw/images")
    parser.add_argument("--config", default="configs/bonus_qc.yaml")
    parser.add_argument("--out", default="submission/bonus_qc")
    args = parser.parse_args(argv)
    config_path = ROOT / args.config
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    ds = ExportDataset(ROOT / args.export, ROOT / args.images, load_config()["classes"])
    issues = class_balance.run(ds, cfg)
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    write_report(issues, out / "class_balance", "Bonus — lệch tỷ trọng lớp", len(ds.image_files()))
    counts = class_balance.class_counts(ds)
    summary = dict(n_images=len(ds.image_files()), total_boxes=sum(counts),
                   class_counts=dict(zip(ds.classes, counts)), n_warnings=len(issues),
                   config=cfg, bonus_config_sha1=sha1(config_path),
                   source_manifest_sha1=sha1(ds.manifest_path),
                   note="Cảnh báo bổ sung độc lập; không thay đổi gate/export/train. Ngưỡng 10% là heuristic, chưa calibration.")
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
