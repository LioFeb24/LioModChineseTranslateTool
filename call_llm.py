import time
from openai import OpenAI, APIConnectionError, APITimeoutError, RateLimitError
import json
import ast
import re
from config import DEFAULT_BASE_URL, get_config
json_path = R'C:\Users\30848\Desktop\autoChinese\files\DH\assets\distanthorizons\lang\en_us.json'


def _get_llm_settings() -> tuple[str, str]:
    config = get_config()
    api_key = config.get("api_key", "")
    base_url = config.get("base_url") or DEFAULT_BASE_URL
    return api_key, base_url


def _build_client(api_key: str, base_url: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=base_url)


def validate_api_key(api_key: str, base_url: str) -> tuple[bool, str]:
    api_key = (api_key or "").strip()
    base_url = (base_url or DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL
    if not api_key:
        return False, "请先填写 API Key"

    client = _build_client(api_key, base_url)
    try:
        client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
            stream=False,
            timeout=20,
        )
        return True, "API Key 鉴权成功"
    except Exception as e:
        return False, f"API Key 鉴权失败：{e}"


def call_llm(msg:str,sys_prompt:str)->str:
    api_key, base_url = _get_llm_settings()
    if not api_key:
        raise RuntimeError("未设置 API Key：请在界面中手动填写 API Key")
    client = _build_client(api_key, base_url)

    last_err: Exception | None = None
    for attempt in range(6):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": msg},
                ],
                stream=False,
                timeout=60,
            )
            return (response.choices[0].message.content or "").strip()
        except (APIConnectionError, APITimeoutError, RateLimitError) as e:
            last_err = e
            if attempt == 5:
                break
            time.sleep(min(8, 2 ** attempt))
        except Exception as e:
            last_err = e
            break
    raise RuntimeError(f"LLM 调用失败：base_url={base_url}") from last_err

_FENCE_RE = re.compile(r"^\s*```(?:json|JSON)?\s*([\s\S]*?)\s*```\s*$")

def _strip_code_fences(s: str) -> str:
    m = _FENCE_RE.match(s)
    return m.group(1).strip() if m else s.strip()

def _extract_first_braced_object(s: str) -> str | None:
    start = s.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == "\"":
                in_string = False
            continue
        if ch == "\"":
            in_string = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return None

def clear_dict(dict_str: str) -> dict:
    if isinstance(dict_str, dict):
        return dict_str
    if not isinstance(dict_str, str):
        raise TypeError(f"clear_dict 需要 str，但收到 {type(dict_str)}")

    s = _strip_code_fences(dict_str)
    candidate = _extract_first_braced_object(s)
    candidates = [s]
    if candidate and candidate != s:
        candidates.insert(0, candidate)

    for c in candidates:
        c = c.strip()
        if not c:
            continue
        try:
            obj = json.loads(c)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
        try:
            obj = ast.literal_eval(c)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
        try:
            fixed = re.sub(r",\s*([}\]])", r"\1", c)
            obj = json.loads(fixed)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    raise ValueError(f"无法从 LLM 输出解析出 dict：{dict_str[:300]}")

_PRINTF_PLACEHOLDER_RE = re.compile(r"%(?:[-+#0 ]?\d*(?:\.\d+)?)?[a-zA-Z]")
_BRACE_PLACEHOLDER_RE = re.compile(r"\{[^{}\n]+\}")
_ESCAPE_RE = re.compile(r"\\[nrt\"']")
_MC_COLOR_RE = re.compile(r"\u00A7.")


def _extract_placeholders(text: str) -> list[str]:
    if not text:
        return []
    holders: list[str] = []
    holders.extend(_PRINTF_PLACEHOLDER_RE.findall(text))
    holders.extend(_BRACE_PLACEHOLDER_RE.findall(text))
    holders.extend(_ESCAPE_RE.findall(text))
    holders.extend(_MC_COLOR_RE.findall(text))
    return sorted(holders)


def _has_matching_placeholders(src: str, dst: str) -> bool:
    return _extract_placeholders(src) == _extract_placeholders(dst)


DEFAULT_TRANSLATE_PROMPT = '''# Role
你是一位精通简体中文翻译的资深翻译专家，拥有卓越的文学修养和地道的表达能力。

# Task
将用户提供的文本翻译为简体中文。

# Response Format
必须严格遵守 JSON 格式输出，不得包含任何开场白或解释说明。结构如下：
{"result": "翻译结果"}

# Translation Guidelines
1. **信达雅**：译文需准确传达原意，逻辑通顺，符合简体中文表达习惯（避免翻译腔）。
2. **上下文适配**：根据语境灵活调整词义，确保专业术语翻译准确。
3. **排版规范**：简体中文与原文、数字之间保持一个空格的距离；正确使用中文全角标点符号。
4. **占位符保留**：必须原样保留所有占位符、格式符和转义符，绝不能改写、删除或新增。

# Constraints
- 严禁输出 JSON 块以外的内容。
- 若英文原文包含敏感词，请在保持原意的前提下进行委婉翻译，确保输出合法合规。
- 必须原样保留这类内容：`%s`、`%d`、`%.2f`、`{name}`、`{0}`、`\\n`、`\\t`、`§a` 等。'''


STRICT_PLACEHOLDER_PROMPT = '''# Role
你是一位软件本地化翻译专家。

# Task
将用户提供的文本翻译为简体中文。

# Hard Constraints
- 只输出严格 JSON：{"result": "翻译结果"}
- 严禁输出解释、代码块或多余文本。
- 所有占位符和格式符必须逐字保留，不得改动顺序和字符：
  - printf：%s %d %.2f
  - 花括号：{0} {1} {name}
  - 转义：\\n \\t \\\\
  - 样式码：§0-§f、§k§l§m§n§o§r
- 如果文本很短，也必须只翻译自然语言部分，保留占位符不变。'''


def translate(msg: str, sys_prompt: str = DEFAULT_TRANSLATE_PROMPT) -> str:
    prompts = [sys_prompt]
    if sys_prompt != STRICT_PLACEHOLDER_PROMPT:
        prompts.append(STRICT_PLACEHOLDER_PROMPT)

    last_err: Exception | None = None
    for prompt in prompts:
        for _ in range(2):
            try:
                zh = clear_dict(call_llm(msg, prompt))["result"]
                if not isinstance(zh, str) or not zh.strip():
                    raise ValueError("翻译结果为空")
                if not _has_matching_placeholders(msg, zh):
                    raise ValueError(f"占位符不匹配：src={_extract_placeholders(msg)} dst={_extract_placeholders(zh)}")
                return zh
            except Exception as e:
                last_err = e
                continue
    raise RuntimeError(f"翻译失败：{msg[:120]}") from last_err
