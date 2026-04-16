import os
import tempfile


LANGUAGE_LIST = ["en", "zh", "ja", "ko", "es", "fr", "de", "ru", "pt"]
REGION_LIST = ["us", "cn", "jp", "kr", "br", "ru", "de", "fr", "es", "419"]


def _is_locale_json(filename: str) -> bool:
    if not filename.lower().endswith(".json"):
        return False
    base = filename[:-5]
    sep = "_" if "_" in base else "-" if "-" in base else None
    if not sep:
        return False
    parts = base.split(sep)
    if len(parts) != 2:
        return False
    lang, region = parts[0].lower(), parts[1].lower()
    return (lang in LANGUAGE_LIST) and (region in REGION_LIST)


def find_json(folder: str) -> list[str]:
    """
    在指定文件夹 folder 中递归查找符合 Locale Identifier 命名规则的 json 文件。

    命名规则示例：
    - en_us.json / en-us.json
    - zh_cn.json / zh-cn.json

    匹配规则：
    - 语言代码在 LANGUAGE_LIST
    - 地区代码在 REGION_LIST

    返回：
    - list[str]：绝对路径列表
    """
    if not folder:
        return []
    if not os.path.isdir(folder):
        return []

    root = os.path.abspath(folder)
    results: list[str] = []

    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if not _is_locale_json(name):
                continue
            abs_path = os.path.join(dirpath, name)
            results.append(os.path.abspath(abs_path))

    results.sort()
    return results


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "a", "b"), exist_ok=True)
        keep = [
            os.path.join(d, "en_us.json"),
            os.path.join(d, "a", "zh_cn.json"),
            os.path.join(d, "a", "b", "pt-BR.json"),
            os.path.join(d, "a", "b", "es_419.json"),
        ]
        drop = [
            os.path.join(d, "enus.json"),
            os.path.join(d, "en_us.txt"),
            os.path.join(d, "a", "b", "en_us.json.bak"),
            os.path.join(d, "a", "b", "e_us.json"),
            os.path.join(d, "a", "b", "en_usa.json"),
        ]
        for p in keep + drop:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write("{}")

        got = find_json(d)
        expected = sorted([os.path.abspath(p) for p in keep])
        assert got == expected, (got, expected)
