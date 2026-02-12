#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from typing import List, Set


def _run(cmd: List[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _active_image_version(service: str, region: str) -> str | None:
    image_ref = _run(
        [
            "gcloud",
            "run",
            "services",
            "describe",
            service,
            "--region",
            region,
            "--format=value(spec.template.spec.containers[0].image)",
        ]
    )
    if "@" not in image_ref:
        return None
    return image_ref.split("@", 1)[1]


def prune_revisions(service: str, region: str, keep: int) -> None:
    cmd = [
        "gcloud",
        "run",
        "revisions",
        "list",
        "--service",
        service,
        "--region",
        region,
        "--format",
        "value(metadata.name)",
        "--sort-by=~metadata.creationTimestamp",
    ]
    result = _run(cmd)
    if not result:
        return
    names = result.splitlines()
    remove = names[keep:]
    for name in remove:
        subprocess.run(
            ["gcloud", "run", "revisions", "delete", name, "--region", region, "--quiet"],
            check=True,
        )


def prune_images(package: str, keep: int, protected_versions: Set[str] | None = None) -> None:
    cmd = [
        "gcloud",
        "artifacts",
        "docker",
        "images",
        "list",
        package,
        "--include-tags",
        "--format=json",
    ]
    raw = _run(cmd)
    if not raw:
        return
    items = json.loads(raw)
    if not items:
        return
    protected = protected_versions or set()

    items.sort(
        key=lambda x: _parse_time(x.get("createTime") or x.get("updateTime")),
        reverse=True,
    )
    kept_count = 0
    remove: list[dict] = []
    for item in items:
        version = item.get("version")
        if isinstance(version, str) and version in protected:
            continue
        if kept_count < keep:
            kept_count += 1
            continue
        remove.append(item)

    for item in remove:
        image_ref = f"{item['package']}@{item['version']}"
        subprocess.run(
            ["gcloud", "artifacts", "docker", "images", "delete", image_ref, "--quiet"],
            check=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Prune Cloud Run revisions and images")
    parser.add_argument("--service", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--image", required=True, help="Artifact Registry package path")
    parser.add_argument("--keep", type=int, default=3)
    args = parser.parse_args()

    if args.keep < 1:
        raise SystemExit("--keep must be >= 1")

    prune_revisions(args.service, args.region, args.keep)
    protected_versions: Set[str] = set()
    active_version = _active_image_version(args.service, args.region)
    if active_version:
        protected_versions.add(active_version)
    prune_images(args.image, args.keep, protected_versions=protected_versions)


if __name__ == "__main__":
    main()
