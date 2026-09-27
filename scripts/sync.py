import hashlib
import json
import shutil
import tempfile
import urllib.request
from urllib.parse import quote
import zipfile
from pathlib import Path


UPSTREAM_URL = ( 
    "https://gitee.com/PizazzXS/another-d/raw/master/"
                + quote("单线路.zip") 
)

OUTPUT_FILE = Path("www/api.json")
HASH_FILE = Path("www/.source_sha256")


def log(message):
    print(f"[tvbox-sync] {message}", flush=True)


def download(url, target):
    log(f"下载上游文件：{url}")

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "tvbox-sync/1.0"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=120
    ) as response:

        with open(target, "wb") as f:
            shutil.copyfileobj(response, f)

    size = target.stat().st_size

    log(f"下载完成：{size} bytes")

    if size < 100:
        raise RuntimeError(
            "下载文件异常，文件太小"
        )


def sha256(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            data = f.read(1024 * 1024)

            if not data:
                break

            h.update(data)

    return h.hexdigest()


def find_api_json(directory):
    files = list(directory.rglob("api.json"))

    if not files:
        raise RuntimeError(
            "单线路.zip 中没有找到 api.json"
        )

    log("找到以下 api.json：")

    for file in files:
        log(f"  {file}")

    # 优先使用 TVBoxOSC/tvbox/api.json
    for file in files:
        normalized = str(file).replace("\\", "/")

        if normalized.endswith(
            "TVBoxOSC/tvbox/api.json"
        ):
            return file

    return files[0]


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

    log("JSON 验证成功")

    return data


def main():

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with tempfile.TemporaryDirectory() as temp:

        temp = Path(temp)

        zip_file = temp / "source.zip"
        extract_dir = temp / "extract"

        extract_dir.mkdir()

        # 1. 下载
        download(
            UPSTREAM_URL,
            zip_file
        )

        # 2. 计算文件 SHA256
        current_hash = sha256(zip_file)

        log(
            f"SHA256: {current_hash}"
        )

        # 3. 判断是否有更新
        if HASH_FILE.exists():

            old_hash = HASH_FILE.read_text(
                encoding="utf-8"
            ).strip()

            if old_hash == current_hash:

                log(
                    "上游文件没有变化"
                )

                return

        # 4. 检查 ZIP
        if not zipfile.is_zipfile(zip_file):
            raise RuntimeError(
                "下载的文件不是有效 ZIP"
            )

        # 5. 解压
        log("开始解压")

        with zipfile.ZipFile(
            zip_file,
            "r"
        ) as z:

            z.extractall(extract_dir)

        # 6. 找 api.json
        api_file = find_api_json(
            extract_dir
        )

        # 7. 验证 JSON
        validate_json(api_file)

        # 8. 更新自己的 api.json
        shutil.copy2(
            api_file,
            OUTPUT_FILE
        )

        # 9. 保存 SHA256
        HASH_FILE.write_text(
            current_hash + "\n",
            encoding="utf-8"
        )

        log(
            f"同步成功：{OUTPUT_FILE}"
        )


if __name__ == "__main__":
    main()
