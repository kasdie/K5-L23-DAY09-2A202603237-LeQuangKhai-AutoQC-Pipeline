#!/usr/bin/env python3
"""Tạo task bonus trong CVAT local từ hai ZIP đã chuẩn bị, kiểm số box nhập.

Thông tin đăng nhập đọc từ file riêng (không commit) hoặc hỏi bằng getpass.
Không in token/mật khẩu, không thay thế task có nhãn khác nội dung dự kiến.
"""
import argparse
import csv
import getpass
import json
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse, quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


class API:
    def __init__(self, base, account):
        self.base = base.rstrip("/")
        self.token = None
        self.token = self.call("POST", "/api/auth/login", account)["key"]
        who = self.call("GET", "/api/users/self")
        if who["username"] != account["username"]:
            raise RuntimeError("CVAT trả về tài khoản khác yêu cầu")

    def call(self, method, path, data=None, content_type=None):
        headers = {}
        if self.token:
            headers["Authorization"] = "Token " + self.token
        if data is not None and not isinstance(data, bytes):
            data = json.dumps(data).encode()
            content_type = "application/json"
        if content_type:
            headers["Content-Type"] = content_type
        req = Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=120) as response:
                body = response.read()
                return json.loads(body) if body else {}
        except HTTPError as exc:
            # Nội dung nghiệp vụ có thể hữu ích; token/header không được in.
            body = exc.read().decode(errors="replace")[:500]
            raise RuntimeError(f"CVAT HTTP {exc.code} {path}: {body}") from None

    def upload(self, path, fields, filename, field_name):
        boundary = "Day09" + uuid.uuid4().hex
        parts = []
        for key, value in fields.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        parts.extend([
            f'--{boundary}\r\nContent-Disposition: form-data; name="{field_name}"; filename="{filename.name}"\r\nContent-Type: application/zip\r\n\r\n'.encode(),
            filename.read_bytes(), f"\r\n--{boundary}--\r\n".encode(),
        ])
        return self.call("POST", path, b"".join(parts), "multipart/form-data; boundary=" + boundary)

    def wait(self, result):
        rq_id = result.get("rq_id")
        if not rq_id:
            return
        until = time.monotonic() + 240
        last_status = None
        while time.monotonic() < until:
            state = self.call("GET", "/api/requests/" + quote(rq_id, safe=""))
            status = state["status"]
            if status != last_status:
                print("CVAT background:", status, flush=True)
                last_status = status
            if status == "finished":
                return
            if status == "failed":
                raise RuntimeError("CVAT background failed: " + state.get("message", ""))
            time.sleep(2)
        raise TimeoutError("CVAT chưa hoàn tất sau 240 giây; task được giữ để kiểm tra")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8080")
    parser.add_argument("--credentials-file", type=Path)
    parser.add_argument("--out", type=Path, default=ROOT / "submission/cvat")
    args = parser.parse_args()
    if urlparse(args.url).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("script này chỉ dành cho CVAT local")
    account = (json.loads(args.credentials_file.read_text()) if args.credentials_file else
               {"username": input("CVAT username: "), "password": getpass.getpass("CVAT password: ")})
    api = API(args.url, account)
    out = args.out
    expected = list(csv.DictReader((out / "expected_frames.csv").open(encoding="utf-8")))
    project_name, task_name = "Day09 AutoQC Bonus - 2A202603237", "Bonus width lt 20 - 25 images - 2A202603237"
    projects = api.call("GET", "/api/projects?" + urlencode({"search": project_name}))["results"]
    projects = [p for p in projects if p["name"] == project_name]
    if len(projects) > 1:
        raise RuntimeError("có nhiều project trùng tên; không tự chọn/ghi đè")
    project = projects[0] if projects else api.call("POST", "/api/projects", {
        "name": project_name, "labels": json.loads((out / "project_labels.json").read_text())})
    tasks = api.call("GET", "/api/tasks?" + urlencode({"search": task_name}))["results"]
    tasks = [t for t in tasks if t["name"] == task_name and t["project_id"] == project["id"]]
    if len(tasks) > 1:
        raise RuntimeError("có nhiều task trùng tên; không tự chọn/ghi đè")
    task = tasks[0] if tasks else api.call("POST", "/api/tasks", {
        "name": task_name, "project_id": project["id"], "segment_size": 100})
    task_id = task["id"]
    print(f"Project {project['id']}; task {task_id}", flush=True)
    task = api.call("GET", f"/api/tasks/{task_id}")
    if not task.get("size", 0):
        api.wait(api.upload(f"/api/tasks/{task_id}/data",
                            {"image_quality": 100, "sorting_method": "lexicographical"},
                            out / "images.zip", "client_files[0]"))
    meta = api.call("GET", f"/api/tasks/{task_id}/data/meta")
    assert [x["name"] for x in meta["frames"]] == [r["filename"] for r in expected]
    annotations = api.call("GET", f"/api/tasks/{task_id}/annotations")
    if not annotations["shapes"] and not annotations["tracks"] and not annotations["tags"]:
        api.wait(api.upload(f"/api/tasks/{task_id}/annotations?" + urlencode({"format": "YOLO 1.1"}),
                            {}, out / "annotations_yolo11.zip", "annotation_file"))
        annotations = api.call("GET", f"/api/tasks/{task_id}/annotations")
    if len(annotations["shapes"]) != sum(int(r["n_boxes"]) for r in expected):
        raise RuntimeError("số box CVAT khác dữ liệu chuẩn bị; giữ task và không ghi đè")
    labels = api.call("GET", "/api/labels?" + urlencode({"project_id": project["id"]}))["results"]
    attr_ids = {label["id"]: next(a["id"] for a in label["attributes"] if a["name"] == "can_review") for label in labels}
    updates = []
    observed = []
    for frame, row in enumerate(expected):
        shapes = [s for s in annotations["shapes"] if s["frame"] == frame]
        selected = [s for s in shapes if abs(s["points"][2] - s["points"][0]) < 20]
        assert len(shapes) == int(row["n_boxes"])
        assert len(selected) == int(row["width_lt_20"]), row["image"]
        observed.append(dict(image=row["image"], frame=frame, n_boxes=len(shapes),
                             width_lt_20=len(selected), box_tiny=int(row["box_tiny"])))
        for shape in selected:
            attr_id = attr_ids[shape["label_id"]]
            shape["attributes"] = [a for a in shape["attributes"] if a["spec_id"] != attr_id] + [{"spec_id": attr_id, "value": "true"}]
            updates.append(shape)
    if updates:
        api.call("PATCH", f"/api/tasks/{task_id}/annotations?action=update", {
            "version": annotations["version"], "shapes": updates, "tracks": [], "tags": []})
    annotations = api.call("GET", f"/api/tasks/{task_id}/annotations")
    jobs = api.call("GET", "/api/jobs?" + urlencode({"task_id": task_id}))["results"]
    about = api.call("GET", "/api/server/about")
    result = dict(status="imported_and_verified", cvat_version=about["version"],
                  project_id=project["id"], task_id=task_id, job_id=jobs[0]["id"],
                  url=f"{args.url}/tasks/{task_id}/jobs/{jobs[0]['id']}",
                  n_images=len(expected), n_boxes=len(annotations["shapes"]),
                  width_lt_20_boxes=sum(r["width_lt_20"] for r in observed),
                  width_lt_20_images=sum(r["width_lt_20"] > 0 for r in observed),
                  can_review_true=len(updates), screenshot_status="pending",
                  source_manifest_sha1=json.loads((out / "preparation.json").read_text())["source_manifest_sha1"])
    (out / "session.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "annotations_snapshot.json").write_text(json.dumps(annotations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (out / "verified_counts.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["image", "frame", "n_boxes", "width_lt_20", "box_tiny"])
        writer.writeheader(); writer.writerows(observed)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
