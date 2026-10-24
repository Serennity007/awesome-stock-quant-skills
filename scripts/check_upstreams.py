#!/usr/bin/env python3
"""Read upstream metadata; never download or replace third-party skill code."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def fetch_json(url):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "awesome-stock-quant-skills-upstream-check"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(url, headers=headers), timeout=20) as response:
        return json.load(response)


def discover_sources(root):
    sources = []
    for source in sorted((root / "skills").glob("*/SOURCE.md")):
        text = source.read_text(encoding="utf-8-sig")
        match = re.search(r"https://github\.com/([\w.-]+/[\w.-]+)", text)
        license_match = re.search(r"^- License:\s*(.+)$", text, re.MULTILINE)
        if not match or not license_match:
            raise ValueError(f"Missing repository or declared license in {source}")
        pinned = re.search(r"\b[0-9a-f]{40}\b", text)
        sources.append({"directory": source.parent.name, "repository": match[1].removesuffix(".git"),
                        "declared_license": license_match[1].strip(),
                        "mirrored_commit": pinned[0] if pinned else None})
    if not sources:
        raise ValueError("No SOURCE.md files found")
    return sources


def inspect_source(source, previous, fetch=fetch_json):
    result = dict(source)
    old = previous.get(source["directory"], {})
    previous_head = old.get("head_sha") or old.get("last_success_head_sha")
    try:
        url = f"https://api.github.com/repos/{source['repository']}"
        repo = fetch(url)
        # /commits defaults to the default branch; pushed_at also changes for other branches.
        commits = fetch(url + "/commits?per_page=1")
        head = commits[0]["sha"]
        license_id = (repo.get("license") or {}).get("spdx_id")
        flags = []
        if not source["mirrored_commit"]:
            flags.append("snapshot-unpinned")
        elif head != source["mirrored_commit"]:
            flags.append("snapshot-behind-head")
        if previous_head and previous_head != head:
            flags.append("head-changed-since-check")
        if license_id != source["declared_license"]:
            flags.append("license-needs-review")
        if repo.get("archived"):
            flags.append("archived")
        result.update(status="ok", head_sha=head, upstream_license=license_id,
                      archived=bool(repo.get("archived")), stars=repo.get("stargazers_count"),
                      url=repo["html_url"], flags=flags)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        # Do not include response bodies or request headers (tokens) in published reports.
        result.update(status="error", error_type=type(exc).__name__, flags=["fetch-failed"])
        result["last_success_head_sha"] = previous_head
        if isinstance(exc, HTTPError):
            result["http_status"] = exc.code
    return result


def markdown(report):
    lines = ["# 上游巡检 / Upstream check", "", f"检查时间（UTC）：{report['checked_at_utc']}", "",
             "仅核对远程元数据，未更新或执行第三方代码；head 变化不等于兼容性验证通过。",
             "`snapshot-unpinned` 表示历史 SOURCE.md 未记载 40 位提交号，无法确认镜像是否最新。",
             "`license-needs-review` 是元数据差异提示，须人工检查许可证文件。", "",
             "| 本地目录 | 上游 | 默认分支 head | 状态 / 复核项 |", "|---|---|---|---|"]
    for item in report["sources"]:
        repo = item["repository"]
        head = item.get("head_sha")
        commit = f"[{head[:12]}](https://github.com/{repo}/commit/{head})" if head else "—"
        flags = ", ".join(item["flags"]) or "no-metadata-flags"
        if item.get("http_status"):
            flags += f" (HTTP {item['http_status']})"
        lines.append(f"| `{item['directory']}` | [{repo}](https://github.com/{repo}) | {commit} | {item['status']}: {flags} |")
    dependency = report["akshare"]
    lines += ["", f"AKShare PyPI version: `{dependency.get('version', 'unavailable')}` ({dependency['status']}).",
              "版本号来自 PyPI 查询，不代表已验证本仓库全部行情接口。", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous", type=Path, help="Previous JSON report; default: reuse out-dir snapshot if present")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "reports/upstreams")
    args = parser.parse_args()
    previous_path = args.previous or args.out_dir / "latest.json"
    old = json.loads(previous_path.read_text(encoding="utf-8")) if previous_path.exists() else {}
    previous = {item["directory"]: item for item in old.get("sources", [])}
    sources = [inspect_source(source, previous) for source in discover_sources(ROOT)]
    try:
        version = fetch_json("https://pypi.org/pypi/akshare/json")["info"]["version"]
        dependency = {"status": "ok", "version": version, "url": "https://pypi.org/project/akshare/"}
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError, TypeError) as exc:
        dependency = {"status": "error", "error_type": type(exc).__name__}
    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "sources": sources, "akshare": dependency}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out_dir / "latest.md").write_text(markdown(report), encoding="utf-8")
    errors = sum(item["status"] == "error" for item in sources) + (dependency["status"] == "error")
    print(f"Checked {len(sources)} upstreams + AKShare: {errors} fetch errors; reports: {args.out_dir}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
