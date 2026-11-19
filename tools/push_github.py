# -*- coding: utf-8 -*-
"""把本地 git 仓库通过 GitHub API 推送到 GitHub（本机 git push 的 443 被阻断时使用）。

用法（cwd = CampusEvent 根目录）：
    python tools/push_github.py            # 推送当前 HEAD 到 main
    python tools/push_github.py --tag baseline-v1    # 推送后再给该提交打标签

原理：用本地 git 计算每个文件的 blob sha，先 POST /git/blobs 上传，再建 tree、commit，
最后 PATCH /git/refs/heads/main。仓库不存在时先用 /user/repos 创建（auto_init=True）。
网络抖动会重试；同名 blob/tree 会被 GitHub 直接复用。
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys
import time

GH = r"C:\Users\alice\AppData\Local\Temp\ghcli\bin\gh.exe"
OWNER = "adadada231rdsf"
REPO = "CampusEvent"
BRANCH = "main"
TRIES = 5


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, **kw)


def git(*args, binary=False):
    out = subprocess.run(["git", *args], capture_output=True, check=True).stdout
    return out if binary else out.decode("utf-8", "replace").strip()


def gh_api(path, method="GET", payload=None, absolute=False):
    """absolute=True 时 path 以 / 开头，表示 /user/repos 这类根路径。"""
    url = path.lstrip("/") if absolute else f"repos/{OWNER}/{REPO}/{path}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else b""
    last = ""
    for attempt in range(1, TRIES + 1):
        proc = run([GH, "api", "-X", method, url, "--input", "-"], input=body)
        if proc.returncode == 0:
            out = proc.stdout.decode("utf-8", "replace").strip()
            return json.loads(out) if out else {}
        last = proc.stderr.decode("utf-8", "replace").strip()
        low = last.lower()
        if "timeout" in low or "eof" in low or "connection" in low or "502" in low or "503" in low:
            wait = 2 * attempt
            print(f"  retry {attempt}/{TRIES} in {wait}s: {last.splitlines()[0][:90]}")
            time.sleep(wait)
            continue
        raise SystemExit(f"gh api {url} failed: {last}")
    raise SystemExit(f"gh api {url} failed after {TRIES} tries: {last}")


def ensure_repo():
    proc = run([GH, "repo", "view", f"{OWNER}/{REPO}", "--json", "name"])
    if proc.returncode == 0:
        print(f"repo exists: {OWNER}/{REPO}")
        return
    print(f"creating repo {OWNER}/{REPO} ...")
    res = gh_api("/user/repos", "POST", {
        "name": REPO,
        "private": False,
        "auto_init": True,
        "description": "CampusEvent 校园活动报名系统 —— 软件工程实验二（策略模式 + 观察者模式）",
    }, absolute=True)
    print("created:", res.get("html_url"))
    time.sleep(2)


def main():
    ensure_repo()

    head = git("rev-parse", "HEAD")
    message = git("log", "-1", "--pretty=%B")

    tree_map, blobs = {}, {}
    # 必须用 -z + quotepath=false：否则中文文件名会被 git 输出成 "\344\275\240..." 这类转义串，
    # 传到 GitHub 上就成了带引号和反斜杠的怪文件名。
    raw = git("-c", "core.quotepath=false", "ls-tree", "-r", "-z", "HEAD", binary=True)
    for entry in raw.split(b"\x00"):
        if not entry:
            continue
        meta, path_bytes = entry.split(b"\t", 1)
        path = path_bytes.decode("utf-8")
        mode, kind, sha = meta.decode("ascii").split()
        if kind != "blob" or mode == "120000":
            continue
        tree_map[path] = {
            "path": path,
            "mode": "100755" if mode == "100755" else "100644",
            "type": "blob",
            "sha": sha,
        }
        blobs.setdefault(sha, path)

    print(f"commit {head}  files={len(tree_map)}  unique blobs={len(blobs)}")
    for i, (sha, path) in enumerate(sorted(blobs.items()), 1):
        content = base64.b64encode(git("cat-file", "blob", sha, binary=True)).decode("ascii")
        res = gh_api("git/blobs", "POST", {"content": content, "encoding": "base64"})
        if res["sha"] != sha:
            raise SystemExit(f"blob sha mismatch for {path}: {res['sha']} != {sha}")
        if i % 20 == 0 or i == len(blobs):
            print(f"  uploaded {i}/{len(blobs)}")

    remote = gh_api(f"git/ref/heads/{BRANCH}")
    remote_sha = remote["object"]["sha"]
    base_tree = gh_api(f"git/commits/{remote_sha}")["tree"]["sha"]
    print("remote head:", remote_sha, "base_tree:", base_tree)

    tree = gh_api("git/trees", "POST", {"base_tree": base_tree, "tree": list(tree_map.values())})
    print("tree:", tree["sha"])

    commit = gh_api("git/commits", "POST", {
        "message": message,
        "tree": tree["sha"],
        "parents": [remote_sha],
    })
    print("commit:", commit["sha"])

    gh_api(f"git/refs/heads/{BRANCH}", "PATCH", {"sha": commit["sha"], "force": True})
    print("ref updated:", BRANCH, "->", commit["sha"])

    if "--tag" in sys.argv:
        tag = sys.argv[sys.argv.index("--tag") + 1]
        # 新建 ref 的接口是 POST /git/refs，ref 名放在 body 里；
        # 已有同名 tag 时该接口返回 422，改用 PATCH /git/refs/tags/{tag} 强移。
        try:
            gh_api("git/refs", "POST", {"ref": f"refs/tags/{tag}", "sha": commit["sha"]})
            print("tag created:", tag, "->", commit["sha"])
        except SystemExit as exc:
            if "422" in str(exc) or "already exists" in str(exc):
                gh_api(f"git/refs/tags/{tag}", "PATCH", {"sha": commit["sha"], "force": True})
                print("tag moved:", tag, "->", commit["sha"])
            else:
                raise

    run(["git", "update-ref", f"refs/remotes/origin/{BRANCH}", head])
    print(f"refs/remotes/origin/{BRANCH} ->", head)
    print(f"https://github.com/{OWNER}/{REPO}")


if __name__ == "__main__":
    main()
