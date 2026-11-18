"""Test bonus mới; không chỉnh sửa bộ test gốc của đề."""
from copy import deepcopy

import pytest
from PIL import Image

from pipeline.checks import class_balance
from pipeline.common import Dataset


@pytest.fixture
def cfg():
    return {"class_balance": {"min_fraction": 0.10}}


@pytest.fixture
def dataset(tmp_path):
    def make(counts=None, lines=None, classes=None):
        classes = classes or ["car", "person", "truck", "bus"]
        (tmp_path / "images").mkdir(exist_ok=True)
        (tmp_path / "labels").mkdir(exist_ok=True)
        Image.new("RGB", (64, 48)).save(tmp_path / "images/arbitrary_name.JPG")
        text = lines if lines is not None else [
            f"{cls} .5 .5 .2 .2" for cls, count in enumerate(counts or []) for _ in range(count)]
        (tmp_path / "labels/arbitrary_name.txt").write_text("\n".join(text) + "\n", encoding="utf-8")
        return Dataset(tmp_path, classes)
    return make


def test_balanced_classes_are_silent(dataset, cfg):
    assert class_balance.run(dataset([10, 10, 10, 10]), cfg) == []


def test_relative_imbalance_even_when_absolute_counts_are_not_rare(dataset, cfg):
    ds = dataset([102, 576, 42, 33])
    issues = class_balance.run(ds, cfg)
    assert [i.extra["class_name"] for i in issues] == ["truck", "bus"]
    assert all(i.code == "CLASS_IMBALANCE" and i.severity == "warn" for i in issues)
    assert issues[0].extra["total_boxes"] == 753
    assert issues[0].extra["fraction"] == pytest.approx(42 / 753)
    assert all(i.image == "<dataset>" and i.line is None for i in issues)


def test_exact_threshold_does_not_warn(dataset, cfg):
    assert class_balance.run(dataset([10, 70, 10, 10]), cfg) == []


def test_missing_class_is_included(dataset, cfg):
    issues = class_balance.run(dataset([10, 10, 10, 0]), cfg)
    assert [(i.extra["class_name"], i.extra["boxes"]) for i in issues] == [("bus", 0)]


def test_empty_dataset_has_no_distribution_claim(dataset, cfg):
    assert class_balance.run(dataset([]), cfg) == []


def test_malformed_invalid_class_and_empty_boxes_do_not_affect_distribution(dataset, cfg):
    ds = dataset(lines=["0 .5 .5 .2 .2", "", "garbage", "inf .5 .5 .2 .2",
                        "93 .5 .5 .2 .2", "-1 .5 .5 .2 .2", "1 nan .5 .2 .2",
                        "1 .5 .5 0 .2", "1 .5 .5 .2 -.2"])
    assert class_balance.class_counts(ds) == [1, 0, 0, 0]
    assert len(class_balance.run(ds, cfg)) == 3


def test_missing_label_file_and_orphan_label_are_not_counted(dataset, cfg):
    ds = dataset([10, 10, 10, 10])
    Image.new("RGB", (64, 48)).save(ds.images_dir / "no_label.png")
    (ds.labels_dir / "orphan.txt").write_text("0 .5 .5 .2 .2\n" * 100, encoding="utf-8")
    assert class_balance.run(ds, cfg) == []
    assert class_balance.class_counts(ds) == [10, 10, 10, 10]


def test_class_names_are_supplied_by_dataset(dataset, cfg):
    ds = dataset([9, 1, 0], classes=["apple", "pear", "plum"])
    assert [i.extra["class_name"] for i in class_balance.run(ds, cfg)] == ["plum"]


def test_threshold_is_read_from_configuration(dataset, cfg):
    ds = dataset([10, 70, 10, 10])
    cfg["class_balance"]["min_fraction"] = 0.11
    assert len(class_balance.run(ds, cfg)) == 3


@pytest.mark.parametrize("threshold", [0, 1, float("nan"), float("inf")])
def test_invalid_threshold_is_rejected(dataset, cfg, threshold):
    cfg["class_balance"]["min_fraction"] = threshold
    with pytest.raises(ValueError):
        class_balance.run(dataset([10, 10, 10, 10]), cfg)


def test_read_only_repeatable_and_configuration_unchanged(dataset, cfg):
    ds = dataset([9, 1, 0, 0])
    before = {p: p.read_bytes() for p in ds.root.rglob("*") if p.is_file()}
    original_cfg = deepcopy(cfg)
    assert class_balance.run(ds, cfg) == class_balance.run(ds, cfg)
    assert cfg == original_cfg
    assert before == {p: p.read_bytes() for p in ds.root.rglob("*") if p.is_file()}
