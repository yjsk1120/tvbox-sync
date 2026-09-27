```python
#!/usr/bin/env python3

import hashlib
import json
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


# ============================================================
# 配置
# ============================================================

UPSTREAM_URL = (
    "https://gitee.com/PizazzXS/another-d/raw/master/"
    "单线路.zip"
)

OUTPUT_FILE = Path("www/api.json")
STATE_FILE = Path("www/.source_sha256")

USER_AGENT = "tvbox-sync/1.0"


# ============================================================
# 日志
# ============================================================

def log(message):
    print(f"[tvbox-sync] {message}", flush=True)


# ============================================================
# 下载
# ============================================================

def download(url, target):
    log(f"正在下载：{url}")

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=120
    ) as response:

        status = getattr(response, "status", 200)

        if status < 200 or status >= 300:
            raise RuntimeError(
                f"下载失败，HTTP 状态码：{status}"
            )

        with open(target, "wb") as f:
            shutil.copyfileobj(response, f)

    size = target.stat().st_size

    if size < 100:
        raise RuntimeError(
            f"下载文件异常，大小只有 {size} bytes"
        )

    log(f"下载完成：{size} bytes")


# ============================================================
# SHA256
# ============================================================

def sha256_file(path):
    sha256 = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            block = f.read(1024 * 1024)

            if not block:
                break

            sha256.update(block)

    return sha256.hexdigest()


# ============================================================
# 查找 api.json
# ============================================================

def find_api_json(directory):
    matches = []

    for path in directory.rglob("api.json"):
        if path.is_file():
            matches.append(path)

    if not matches:
        raise RuntimeError(
            "ZIP 中没有找到 api.json"
        )

    if len(matches) > 1:
        log("发现多个 api.json：")

        for path in matches:
            log(f"  {path}")

        # 优先寻找 TVBoxOSC/tvbox/api.json
        for path in matches:
            normalized = str(path).replace("\\", "/")

            if normalized.endswith(
                "TVBoxOSC/tvbox/api.json"
            ):
                return path

    return matches[0]


# ============================================================
# 验证 JSON
# ============================================================

def validate_json(path):
    log(f"验证 JSON：{path}")

    with open(
        path,
        "r",
        encoding="utf-8-sig"
    ) as f:

        data = json.load(f)

    if not isinstance(data, dict):
        raise RuntimeError(
            "api.json 不是 JSON 对象"
        )

    log(
        "JSON 验证成功，"
        f"字段数量：{len(data)}"
    )

    return data


# ============================================================
# 主程序
# ============================================================

def main():

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with tempfile.TemporaryDirectory() as tmp:

        tmp_path = Path(tmp)

        zip_file = tmp_path / "source.zip"

        extract_dir = tmp_path / "extracted"

        extract_dir.mkdir()

        # ----------------------------------------------------
        # 1. 下载
        # ----------------------------------------------------

        download(
            UPSTREAM_URL,
            zip_file
        )

        # ----------------------------------------------------
        # 2. 计算 ZIP SHA256
        # ----------------------------------------------------

        source_hash = sha256_file(zip_file)

        log(
            f"上游 ZIP SHA256：{source_hash}"
        )

        # ----------------------------------------------------
        # 3. 检查是否和上一次一样
        # ----------------------------------------------------

        if STATE_FILE.exists():

            old_hash = (
                STATE_FILE
                .read_text(
                    encoding="utf-8"
                )
                .strip()
            )

            if old_hash == source_hash:

                log(
                    "上游文件没有变化，"
                    "无需更新。"
                )

                return 0

        # ----------------------------------------------------
        # 4. 验证 ZIP
        # ----------------------------------------------------

        log("检查 ZIP 文件")

        if not zipfile.is_zipfile(zip_file):

            raise RuntimeError(
                "下载的文件不是有效 ZIP"
            )

        # ----------------------------------------------------
        # 5. 解压
        # ----------------------------------------------------

        log("开始解压")

        with zipfile.ZipFile(
            zip_file,
            "r"
        ) as z:

            z.extractall(extract_dir)

        # ----------------------------------------------------
        # 6. 查找 api.json
        # ----------------------------------------------------

        api_file = find_api_json(
            extract_dir
        )

        log(
            f"找到 api.json：{api_file}"
        )

        # ----------------------------------------------------
        # 7. 验证 JSON
        # ----------------------------------------------------

        validate_json(api_file)

        # ----------------------------------------------------
        # 8. 复制到自己的仓库
        # ----------------------------------------------------

        log(
            f"更新：{OUTPUT_FILE}"
        )

        shutil.copy2(
            api_file,
            OUTPUT_FILE
        )

        # ----------------------------------------------------
        # 9. 保存上游 SHA256
        # ----------------------------------------------------

        STATE_FILE.write_text(
            source_hash + "\n",
            encoding="utf-8"
        )

        log("同步完成")

    return 0


if __name__ == "__main__":

    try:
        sys.exit(main())

    except Exception as e:

        log(
            f"ERROR: {e}"
        )

        sys.exit(1)
```
