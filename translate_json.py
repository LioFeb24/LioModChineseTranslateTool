import json
import os
import re
import time
from typing import Callable

from call_llm import translate


_HAS_ASCII_LETTER_RE = re.compile(r"[A-Za-z]")


def _should_translate(s: str) -> bool:
    if not s:
        return False
    return bool(_HAS_ASCII_LETTER_RE.search(s))


def _iter_string_leaves(obj, path=()):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _iter_string_leaves(v, path + (str(k),))
        return
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _iter_string_leaves(v, path + (str(i),))
        return
    if isinstance(obj, str):
        yield path, obj


def _set_by_path(root, path, value):
    cur = root
    for p in path[:-1]:
        if isinstance(cur, list):
            cur = cur[int(p)]
        else:
            cur = cur[p]
    last = path[-1]
    if isinstance(cur, list):
        cur[int(last)] = value
    else:
        cur[last] = value


def _clip_text(s: str) -> str:
    if s is None:
        return ""
    return s


def _cleanup_sibling_json_files(dst_path: str) -> None:
    folder = os.path.dirname(dst_path)
    dst_name = os.path.basename(dst_path).lower()
    for name in os.listdir(folder):
        if not name.lower().endswith(".json"):
            continue
        if name.lower() == dst_name:
            continue
        os.remove(os.path.join(folder, name))


def translate_json(
    json_path: str,
    *,
    progress_callback: Callable[[dict], None] | None = None,
) -> dict:
    """
    将 json 文件中的所有字符串值翻译为中文，并输出为同目录下的 zh_cn.json。

    返回：
    - 翻译后的对象（dict / list）
    """
    src_path = os.path.abspath(json_path)
    dst_path = os.path.join(os.path.dirname(src_path), "zh_cn.json")

    with open(src_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    leaves = list(_iter_string_leaves(data))
    cache: dict[str, str] = {}
    total = sum(1 for _, s in leaves if _should_translate(s))
    done = 0
    changed = 0
    skipped = 0
    failed = 0
    t0 = time.time()

    if progress_callback:
        progress_callback(
            {
                "type": "start",
                "json_path": dst_path,
                "source_json_path": src_path,
                "total": total,
                "done": 0,
                "changed": 0,
                "skipped": 0,
            }
        )

    for p, s in leaves:
        if not _should_translate(s):
            skipped += 1
            continue
        done += 1
        path_str = "/".join(p)
        if s in cache:
            _set_by_path(data, p, cache[s])
            if progress_callback:
                progress_callback(
                    {
                        "type": "progress",
                        "json_path": dst_path,
                        "source_json_path": src_path,
                        "path": path_str,
                        "total": total,
                        "done": done,
                        "changed": changed,
                        "skipped": skipped,
                        "cached": True,
                        "src": _clip_text(s),
                        "dst": _clip_text(cache[s]),
                    }
                )
            continue
        try:
            dst = translate(s)
        except Exception as e:
            failed += 1
            _set_by_path(data, p, s)
            if progress_callback:
                progress_callback(
                    {
                        "type": "warning",
                        "json_path": dst_path,
                        "source_json_path": src_path,
                        "path": path_str,
                        "total": total,
                        "done": done,
                        "changed": changed,
                        "skipped": skipped,
                        "failed": failed,
                        "src": _clip_text(s),
                        "dst": _clip_text(s),
                        "message": str(e),
                    }
                )
            continue
        cache[s] = dst
        _set_by_path(data, p, dst)
        changed += 1
        if progress_callback:
            progress_callback(
                {
                    "type": "progress",
                    "json_path": dst_path,
                    "source_json_path": src_path,
                    "path": path_str,
                    "total": total,
                    "done": done,
                    "changed": changed,
                    "skipped": skipped,
                    "failed": failed,
                    "cached": False,
                    "src": _clip_text(s),
                    "dst": _clip_text(dst),
                }
            )

    with open(dst_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    _cleanup_sibling_json_files(dst_path)
    elapsed = time.time() - t0
    rate = changed / elapsed if elapsed > 0 else 0
    if progress_callback:
        progress_callback(
            {
                "type": "done",
                "json_path": dst_path,
                "source_json_path": src_path,
                "total": total,
                "done": done,
                "changed": changed,
                "skipped": skipped,
                "failed": failed,
                "rate": rate,
            }
        )

    return data
