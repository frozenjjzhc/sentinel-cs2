"""
lib/llm_provider.py — 通用 LLM 客户端

支持的 provider:
  - anthropic   (https://api.anthropic.com/v1/messages)
  - openai      (https://api.openai.com/v1/chat/completions)
  - custom      (任意 OpenAI 兼容协议: DeepSeek / Qwen / Moonshot / 自托管)

用 requests 直接调 HTTP，不依赖 SDK，部署简单。

config 形状（存于 state.global.llm_config）:
{
  "provider": "anthropic" | "openai" | "custom",
  "model": "claude-sonnet-4-6" | "gpt-4o" | "deepseek-chat" | ...,
  "api_key": "sk-ant-...",
  "base_url": "https://api.anthropic.com",  // optional
  "enabled_modules": {
    "news_classification": true,
    "whale_parsing": false,
    "daily_review": false,
    "param_proposal": false
  },
  "monthly_budget_cny": 50.0
}
"""

import json
import time
from typing import Any, Optional

import requests


# ============================================================
# Errors
# ============================================================
class LLMError(Exception):
    pass


# ============================================================
# Provider
# ============================================================
class LLMProvider:
    DEFAULT_BASE = {
        "anthropic": "https://api.anthropic.com",
        "openai":    "https://api.openai.com/v1",
        "custom":    "https://api.openai.com/v1",   # 用户自填 base_url
    }

    def __init__(self, cfg: dict):
        self.provider = (cfg.get("provider") or "anthropic").lower()
        self.model    = cfg.get("model")
        self.api_key  = cfg.get("api_key")
        self.base_url = (cfg.get("base_url") or self.DEFAULT_BASE.get(self.provider, "")).rstrip("/")
        if not self.api_key:
            raise LLMError("missing api_key")
        if not self.model:
            raise LLMError("missing model")
        if not self.base_url:
            raise LLMError("missing base_url")

    # -------- 公开方法 --------
    def chat(self, system: str, user: str,
             json_schema: Optional[dict] = None,
             max_tokens: int = 2000,
             temperature: float = 0.3,
             timeout: int = 60) -> str:
        """返回助手输出文本（如果 json_schema 给了，请 caller 自行 parse）。"""
        if self.provider == "anthropic":
            return self._call_anthropic(system, user, json_schema, max_tokens, temperature, timeout)
        return self._call_openai(system, user, json_schema, max_tokens, temperature, timeout)

    def chat_json(self, system: str, user: str,
                  schema: dict, **kwargs) -> Any:
        """强制 JSON 输出，自动 parse。失败抛 LLMError。"""
        text = self.chat(system, user, json_schema=schema, **kwargs)
        return _parse_json_loose(text)

    # -------- 内部：Anthropic --------
    def _call_anthropic(self, system, user, json_schema, max_tokens, temperature, timeout):
        url = f"{self.base_url}/v1/messages"
        sys = system or ""
        if json_schema:
            sys += ("\n\n你必须严格按照下面的 JSON Schema 输出 JSON 对象，"
                    "不要输出任何 JSON 之外的文字（不要 markdown 代码块）：\n"
                    + json.dumps(json_schema, ensure_ascii=False))
        body = {
            "model":       self.model,
            "max_tokens":  max_tokens,
            "temperature": temperature,
            "messages":    [{"role": "user", "content": user}],
        }
        if sys:
            body["system"] = sys
        headers = {
            "x-api-key":         self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        }
        r = requests.post(url, headers=headers, json=body, timeout=timeout)
        if not r.ok:
            raise LLMError(f"Anthropic API {r.status_code}: {r.text[:300]}")
        data = r.json()
        try:
            return data["content"][0]["text"]
        except (KeyError, IndexError) as e:
            raise LLMError(f"Anthropic API 返回格式异常: {e} | {str(data)[:300]}")

    # -------- 内部：OpenAI 兼容 --------
    def _call_openai(self, system, user, json_schema, max_tokens, temperature, timeout):
        url = f"{self.base_url}/chat/completions"
        sys = system or ""
        if json_schema:
            sys += ("\n\n你必须严格输出 JSON 对象，不输出 JSON 之外的任何文字。"
                    "JSON 必须符合 schema:\n" + json.dumps(json_schema, ensure_ascii=False))
        messages = []
        if sys:
            messages.append({"role": "system", "content": sys})
        messages.append({"role": "user", "content": user})
        body = {
            "model":       self.model,
            "messages":    messages,
            "max_tokens":  max_tokens,
            "temperature": temperature,
        }
        if json_schema:
            body["response_format"] = {"type": "json_object"}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
        }
        r = requests.post(url, headers=headers, json=body, timeout=timeout)
        if not r.ok:
            raise LLMError(f"OpenAI-compat API {r.status_code}: {r.text[:300]}")
        data = r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise LLMError(f"OpenAI-compat API 返回格式异常: {e} | {str(data)[:300]}")


# ============================================================
# Helpers
# ============================================================
def _parse_json_loose(text: str):
    """容忍 markdown 代码块包裹的 JSON。"""
    s = (text or "").strip()
    if s.startswith("```"):
        # ```json ... ``` 或 ``` ... ```
        s = s.split("```", 2)[1]
        if s.startswith("json"):
            s = s[4:]
        s = s.strip().rstrip("`").strip()
    return json.loads(s)


def from_state(state: dict) -> Optional[LLMProvider]:
    """从 state.global.llm_config 创建 provider。未配置/缺 key 返回 None。"""
    cfg = (state or {}).get("global", {}).get("llm_config")
    if not cfg or not cfg.get("api_key"):
        return None
    try:
        return LLMProvider(cfg)
    except LLMError:
        return None


def is_module_enabled(state: dict, module_name: str) -> bool:
    cfg = (state or {}).get("global", {}).get("llm_config", {})
    return bool(cfg.get("enabled_modules", {}).get(module_name))


def test_connection(cfg: dict) -> dict:
    """快速连通测试。返回 {ok, latency_ms, response, error}."""
    try:
        provider = LLMProvider(cfg)
        t0 = time.time()
        text = provider.chat(
            system="You are a connection tester. Respond with exactly: OK",
            user="ping",
            max_tokens=10,
            temperature=0,
        )
        return {
            "ok": True,
            "latency_ms": int((time.time() - t0) * 1000),
            "response": (text or "").strip()[:100],
            "model": provider.model,
            "provider": provider.provider,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


def append_audit(state: dict, module: str, status: str, detail: str = "",
                 cost_estimate: Optional[float] = None):
    """写一条调用记录到 state.global.llm_audit_log（最多保留 200 条）。"""
    from . import utils
    log = state.setdefault("global", {}).setdefault("llm_audit_log", [])
    log.append({
        "t":      utils.now_iso(),
        "module": module,
        "status": status,
        "detail": detail[:300] if detail else "",
        "cost":   cost_estimate,
    })
    if len(log) > 200:
        state["global"]["llm_audit_log"] = log[-200:]
