import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from call_llm import translate


_HAS_ASCII_LETTER_RE = re.compile(r"[A-Za-z]")
TRANSLATE_BATCH_SIZE = 30
TRANSLATE_RETRY_ATTEMPTS = 10


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


def _translate_with_retry(s: str) -> tuple[str, Exception | None, int]:
    last_err: Exception | None = None
    for attempt in range(1, TRANSLATE_RETRY_ATTEMPTS + 1):
        try:
            return translate(s), None, attempt
        except Exception as e:
            last_err = e
            if attempt < TRANSLATE_RETRY_ATTEMPTS:
                time.sleep(min(4, 2 ** (attempt - 1)))
    return s, last_err, TRANSLATE_RETRY_ATTEMPTS


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
    translatable_leaves = [(p, s) for p, s in leaves if _should_translate(s)]
    cache: dict[str, str] = {}
    total = len(translatable_leaves)
    done = 0
    changed = 0
    skipped = len(leaves) - total
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
                "failed": 0,
            }
        )

    with ThreadPoolExecutor(max_workers=TRANSLATE_BATCH_SIZE) as executor:
        for i in range(0, total, TRANSLATE_BATCH_SIZE):
            batch = translatable_leaves[i : i + TRANSLATE_BATCH_SIZE]
            future_to_text: dict = {}
            text_to_entries: dict[str, list[tuple[tuple[str, ...], str]]] = {}

            for p, s in batch:
                path_str = "/".join(p)
                if s in cache:
                    done += 1
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
                                "failed": failed,
                                "cached": True,
                                "src": _clip_text(s),
                                "dst": _clip_text(cache[s]),
                            }
                        )
                    continue

                if s not in text_to_entries:
                    text_to_entries[s] = []
                    future = executor.submit(_translate_with_retry, s)
                    future_to_text[future] = s
                text_to_entries[s].append((p, path_str))

            for future in as_completed(future_to_text):
                s = future_to_text[future]
                dst, err, attempts = future.result()
                if err is None:
                    cache[s] = dst

                for p, path_str in text_to_entries[s]:
                    done += 1
                    if err is not None:
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
                                    "attempts": attempts,
                                    "message": str(err),
                                }
                            )
                        continue

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
                                "attempts": attempts,
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
