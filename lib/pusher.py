"""
PushPlus webhook (sends to multiple tokens).
"""

import requests
from . import config
from . import utils


def push_to_token(token: str, title: str, body: str, template: str = "txt") -> tuple:
    """
    Send a single PushPlus message.
    Returns (success: bool, response: str).
    """
    try:
        r = requests.post(
            config.PUSHPLUS_URL,
            json={
                "token": token,
                "title": title,
                "content": body,
                "template": template,
            },
            timeout=config.PUSH_TIMEOUT_SECONDS,
        )
        data = r.json()
        ok = (r.status_code == 200) and (data.get("code") == 200)
        return ok, str(data)
    except Exception as e:
        return False, str(e)


def push_to_all(tokens_list, title: str, body: str, state: dict = None) -> dict:
    """
    Push to all PushPlus tokens.
    If state is provided AND telegram is configured, also pushes to Telegram.
    Returns merged dict of {channel_name: (ok, response)}.
    """
    results = {}
    for tk in tokens_list:
        name = tk.get("name", "anon")
        token = tk.get("token")
        if not token:
            results[f"pp_{name}"] = (False, "no_token")
            continue
        ok, resp = push_to_token(token, title, body)
        results[f"pp_{name}"] = (ok, resp)

    # Telegram fallback (silent if not configured)
    if state is not None:
        try:
            from . import telegram as tg
            if tg.is_configured(state):
                tg_results = tg.send_to_all(state, title, body)
                for name, val in tg_results.items():
                    results[f"tg_{name}"] = val
        except Exception as e:
            results["tg_error"] = (False, str(e))

    return results


def any_succeeded(results: dict) -> bool:
    return any(ok for ok, _ in results.values())


def succeeded_names(results: dict) -> list:
    return [name for name, (ok, _) in results.items() if ok]
