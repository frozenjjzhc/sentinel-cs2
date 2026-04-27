"""
backend_api.py — FastAPI 桥接服务

将 state.json 和分析数据通过 REST API 暴露给前端。

启动：
    python backend_api.py
    # 默认 http://localhost:8000
    # API 文档自动生成在 http://localhost:8000/docs

端点：
    GET /api/state              完整状态文件
    GET /api/items              所有品种当前快照
    GET /api/items/{id}         单品种详细数据
    GET /api/items/{id}/history 单品种 history（可指定 hours）
    GET /api/market             大盘指数
    GET /api/portfolio          总仓位风险面板
    GET /api/sectors            板块分析（主+副）
    GET /api/shadow/stats       影子信号回测统计
    GET /api/shadow/recent      最近影子仓位
    GET /api/reviews            历史复盘列表
    GET /api/reviews/latest     最新一份复盘
"""

import sys
import re
from datetime import datetime, timedelta
from typing import Optional, List

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import os

try:
    from contextlib import asynccontextmanager
    from fastapi import FastAPI, HTTPException, Body
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("缺少依赖。请运行：pip install fastapi uvicorn")
    sys.exit(1)

from lib import config
from lib import state as state_mod
from lib import portfolio as portfolio_mod
from lib import correlation as corr_mod
from lib import shadow as shadow_mod
from lib import utils
from lib import llm_provider as llm_mod
from lib import embedded_scheduler as scheduler_mod


# ==================== Lifespan：启动时拉起监控调度器 ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # API 启动 → 自动开监控（除非 state 里关掉）
    try:
        state = state_mod.load_state()
        sched_cfg = state.get("global", {}).get("scheduler", {})
        if sched_cfg.get("mode", "embedded") == "embedded":
            scheduler_mod.start()
            print("[scheduler] embedded scheduler started")
        else:
            print("[scheduler] external mode (Windows Task Scheduler), skipped")
    except Exception as e:
        print(f"[scheduler] failed to start: {e}")
    yield
    # API 关闭 → 停掉调度器
    try:
        await scheduler_mod.stop()
        print("[scheduler] stopped")
    except Exception:
        pass


app = FastAPI(
    title="Sentinel CS2 Monitor API",
    version="1.0.0",
    description="本地状态文件 → REST API 桥接层 + 前端 dashboard + 嵌入式调度器。",
    lifespan=lifespan,
)

# ==================== 前端静态文件 ====================
# 把 dashboard 直接挂到 / 上，访问 http://localhost:8000/ 即可
FRONTEND_DIR = os.path.join(config.PROJECT_DIR, "frontend")


@app.get("/")
def serve_dashboard():
    """根路径直接返回 dashboard 页面。"""
    html_path = os.path.join(FRONTEND_DIR, "preview.html")
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")
    raise HTTPException(404, f"frontend not found at {html_path}")


# 把整个 frontend 目录挂到 /static（用于 css / js / 图片等静态资源）
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# ==================== CORS ====================
# 严格本地：只允许从 localhost / 127.0.0.1 / file:// 协议加载的前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:5173",   # Vite dev
        "http://localhost:8000",
        "http://localhost:8080",
        "http://127.0.0.1",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8080",
        "null",                    # file:// 协议（直接双击 preview.html）
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


# ==================== Helpers ====================
def _load_state_or_404():
    try:
        return state_mod.load_state()
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"读取 state 失败: {e}")


def _item_summary(item: dict) -> dict:
    """从 item 抽取一份精简快照（首页卡片用）。"""
    history = item.get("history", [])
    last = history[-1] if history else {}
    pos = item.get("position", {})
    legacy = item.get("legacy_holding")
    return {
        "id": item["id"],
        "name": item.get("name"),
        "short_name": item.get("short_name"),
        "url": item.get("url"),
        "phase": item.get("phase"),
        "current_stage": item.get("current_stage"),
        "price": last.get("price"),
        "today_pct": last.get("today_pct"),
        "week_pct": last.get("week_pct"),
        "today_volume": last.get("today_volume"),
        "stock": last.get("stock"),
        "highest_observed": item.get("highest_observed"),
        "lowest_observed": item.get("lowest_observed"),
        "key_levels": item.get("key_levels"),
        "position": {
            "tiers_count": len(pos.get("tiers", [])),
            "avg_entry_price": pos.get("avg_entry_price"),
            "total_qty_pct": pos.get("total_qty_pct", 0),
            "total_pieces": pos.get("total_pieces", 0),
            "highest_since_first_entry": pos.get("highest_since_first_entry"),
            "tp_executed": pos.get("tp_executed", []),
            "pnl_pct": (
                (last.get("price") - pos["avg_entry_price"]) / pos["avg_entry_price"]
                if pos.get("avg_entry_price") and last.get("price") else None
            ),
        } if pos.get("tiers") else None,
        "legacy": {
            "quantity": legacy.get("quantity"),
            "avg_entry_price": legacy.get("avg_entry_price"),
            "pnl_pct": (
                (last.get("price") - legacy["avg_entry_price"]) / legacy["avg_entry_price"]
                if legacy.get("avg_entry_price") and last.get("price") else None
            ),
        } if legacy else None,
        "history_len": len(history),
        "last_update": last.get("t"),
        "last_signal_pushed": item.get("last_signal_pushed"),
        "last_signal_time": item.get("last_signal_time"),
        "rs_score_1h": item.get("rs_score_1h"),
    }


# ==================== Endpoints ====================

@app.get("/api/health")
def health():
    return {"ok": True, "ts": utils.now_iso()}


@app.get("/api/health/freshness")
def freshness():
    """
    监控心跳检测：判断 state.json 是不是仍在被监控脚本更新。
    返回 status:
      ok      - 距上次更新 < 15 min
      delayed - 15-60 min（可能在两次扫描的间隙）
      stalled - > 60 min（监控可能已停）
    """
    import os as _os
    state_path = getattr(config, "STATE_FILE", None)
    # 1) 文件 mtime
    file_mtime_iso = None
    file_age_sec = None
    if state_path and _os.path.exists(state_path):
        try:
            mtime = _os.path.getmtime(state_path)
            file_mtime_dt = datetime.fromtimestamp(mtime).astimezone()
            file_mtime_iso = file_mtime_dt.isoformat()
            file_age_sec = (datetime.now().astimezone() - file_mtime_dt).total_seconds()
        except Exception:
            pass

    # 2) 最新 history[-1].t（更精确，是真正"扫到价格的时间戳"）
    data_age_sec = None
    data_t_iso = None
    item_id = None
    try:
        state = state_mod.load_state()
        for it in state.get("items", []):
            history = it.get("history", [])
            if not history:
                continue
            last_t = history[-1].get("t")
            if not last_t:
                continue
            t = utils.parse_iso(last_t)
            age = (datetime.now().astimezone() - t).total_seconds()
            if data_age_sec is None or age < data_age_sec:
                data_age_sec = age
                data_t_iso = last_t
                item_id = it.get("id")
    except Exception:
        pass

    # 3) data_age 优先，回落到 file_age
    age_sec = data_age_sec if data_age_sec is not None else file_age_sec
    age_min = round(age_sec / 60, 1) if age_sec is not None else None

    if age_sec is None:
        status = "unknown"
    elif age_sec < 15 * 60:
        status = "ok"
    elif age_sec < 60 * 60:
        status = "delayed"
    else:
        status = "stalled"

    return {
        "status": status,
        "age_seconds": age_sec,
        "age_minutes": age_min,
        "latest_data_time": data_t_iso,
        "latest_data_item": item_id,
        "state_file_mtime": file_mtime_iso,
        "thresholds": {"ok_max_min": 15, "delayed_max_min": 60},
        "now": utils.now_iso(),
    }


@app.get("/api/state")
def get_full_state():
    """完整 state（数据量大，慎用）。"""
    return _load_state_or_404()


@app.get("/api/items")
def list_items():
    """所有品种的精简快照（首页卡片）。"""
    state = _load_state_or_404()
    return {
        "count": len(state.get("items", [])),
        "items": [_item_summary(it) for it in state.get("items", [])],
    }


@app.get("/api/items/{item_id}")
def get_item(item_id: str):
    """单品种详细数据。"""
    state = _load_state_or_404()
    for it in state.get("items", []):
        if it["id"] == item_id:
            summary = _item_summary(it)
            summary["thresholds"] = it.get("thresholds")
            summary["whale_floor_price"] = it.get("whale_floor_price")
            summary["whale_buy_in_price"] = it.get("whale_buy_in_price")
            summary["whale_active_until"] = it.get("whale_active_until")
            summary["recent_signals"] = it.get("signals_log", [])[-20:]
            summary["recent_recommendations"] = it.get("recommendations_log", [])[-10:]
            return summary
    raise HTTPException(404, f"item not found: {item_id}")


@app.get("/api/items/{item_id}/history")
def get_item_history(item_id: str, hours: Optional[int] = 24):
    """单品种 history 时间序列。默认最近 24h。"""
    state = _load_state_or_404()
    for it in state.get("items", []):
        if it["id"] == item_id:
            history = it.get("history", [])
            if hours:
                cutoff = datetime.now().astimezone() - timedelta(hours=hours)
                history = [
                    h for h in history
                    if h.get("t") and utils.parse_iso(h["t"]) >= cutoff
                ]
            return {
                "item_id": item_id,
                "hours": hours,
                "count": len(history),
                "history": history,
            }
    raise HTTPException(404, f"item not found: {item_id}")


@app.get("/api/market")
def get_market():
    """大盘指数 + 最近 24h 趋势。"""
    state = _load_state_or_404()
    items = state.get("items", [])
    if not items:
        return {"error": "no items"}
    anchor = items[0].get("history", [])
    if not anchor:
        return {"error": "no history yet"}

    cutoff = datetime.now().astimezone() - timedelta(hours=24)
    recent = [h for h in anchor if h.get("t") and utils.parse_iso(h["t"]) >= cutoff]

    return {
        "current_index": anchor[-1].get("market_index"),
        "current_change_pct": anchor[-1].get("market_pct"),
        "last_update": anchor[-1].get("t"),
        "history_24h": [
            {"t": h.get("t"), "market_index": h.get("market_index"), "market_pct": h.get("market_pct")}
            for h in recent
        ],
    }


@app.get("/api/portfolio")
def get_portfolio():
    """总仓位风险面板。"""
    state = _load_state_or_404()
    return portfolio_mod.compute_summary(state)


@app.get("/api/sectors")
def get_sectors():
    """板块分析（主+副+综合）。"""
    state = _load_state_or_404()
    return corr_mod.detect_full_analysis(state)


@app.get("/api/sectors/opportunities")
def get_sector_opportunities():
    """主板块跟涨机会。"""
    state = _load_state_or_404()
    full_analysis = corr_mod.detect_full_analysis(state)
    return {"opportunities": corr_mod.find_following_opportunities(state, full_analysis)}


@app.get("/api/shadow/stats")
def get_shadow_stats():
    """影子信号回测统计（每类信号 7 日胜率/平均收益）。"""
    return {
        "stats": shadow_mod.get_stats(),
        "pending": shadow_mod.get_pending_count(),
    }


@app.get("/api/shadow/recent")
def get_shadow_recent(limit: int = 10):
    """最近 N 条已评估的影子仓位。"""
    return {"shadows": shadow_mod.get_recent(limit=limit)}


@app.get("/api/reviews")
def get_reviews():
    """所有历史复盘（最近 90 天）。"""
    state = _load_state_or_404()
    return {"reviews": state.get("global", {}).get("daily_review_log", [])}


@app.get("/api/reviews/latest")
def get_latest_review():
    """最近一份复盘。"""
    state = _load_state_or_404()
    log = state.get("global", {}).get("daily_review_log", [])
    if not log:
        raise HTTPException(404, "no review yet")
    return log[-1]


@app.get("/api/fundamentals")
def get_fundamentals():
    """基本面 bias + 庄家信号 + V社更新。"""
    state = _load_state_or_404()
    return state.get("global", {}).get("fundamentals", {})


@app.get("/api/circuit_breaker")
def get_circuit_breaker():
    """熔断状态。"""
    state = _load_state_or_404()
    return state.get("global", {}).get("circuit_breaker", {"active": False})


# ==================== 写入端点 ====================
# 板块固定选项（用户指定）
SECTOR_OPTIONS = ["一代手套", "二代手套", "三代手套", "武库", "千百战", "收藏品"]


@app.get("/api/sectors/options")
def sector_options():
    """前端下拉用：固定板块列表。"""
    return {"sectors": SECTOR_OPTIONS}


# ---------- 仓位 ----------
class BuyRequest(BaseModel):
    price: float
    qty_pieces: float            # 真实买入把数（必填，可小数）
    qty_pct: Optional[float] = None  # 占计划满仓的比例 0-1（选填）
    note: Optional[str] = None


class SellRequest(BaseModel):
    price: float
    qty_pieces: float            # 真实卖出把数
    qty_pct: Optional[float] = None  # 占计划的比例（选填）


class LegacyRequest(BaseModel):
    quantity: Optional[float] = None       # 把数（None + action=remove → 清除）
    avg_entry_price: Optional[float] = None
    action: Optional[str] = "set"          # set | remove


def _find_item(state, item_id):
    for it in state.get("items", []):
        if it["id"] == item_id:
            return it
    return None


@app.post("/api/positions/{item_id}/buy")
def position_buy(item_id: str, body: BuyRequest):
    """新建/加仓：往 position.tiers 推一档。"""
    if body.qty_pieces <= 0:
        raise HTTPException(400, "qty_pieces 必须为正（真实买入把数）")
    if body.price <= 0:
        raise HTTPException(400, "price 必须为正")
    if body.qty_pct is not None and (body.qty_pct <= 0 or body.qty_pct > 1):
        raise HTTPException(400, "qty_pct 必须在 (0, 1] 区间，例如 0.3 = 30%")
    state = _load_state_or_404()
    item = _find_item(state, item_id)
    if not item:
        raise HTTPException(404, f"item not found: {item_id}")
    pos = item.setdefault("position", {
        "tiers": [], "avg_entry_price": None, "total_qty_pct": 0,
        "highest_since_first_entry": None, "tp_executed": [],
    })
    tiers = pos.setdefault("tiers", [])
    new_tier = {
        "tier_idx": len(tiers) + 1,
        "entry_price": body.price,
        "qty_pieces": body.qty_pieces,
        "qty_pct": body.qty_pct if body.qty_pct is not None else 0,
        "entry_time": utils.now_iso(),
        "note": body.note or "",
        "source": "manual_dashboard",
    }
    tiers.append(new_tier)
    state_mod.compute_position_summary(item)
    if pos.get("highest_since_first_entry") is None:
        pos["highest_since_first_entry"] = body.price
    item.setdefault("recommendations_log", []).append({
        "t": utils.now_iso(),
        "type": "manual_buy",
        "price": body.price,
        "qty_pieces": body.qty_pieces,
        "qty_pct": body.qty_pct,
        "tier_idx": new_tier["tier_idx"],
        "note": body.note or "",
    })
    state_mod.save_state(state)
    return {"ok": True, "tier": new_tier, "position": pos}


@app.post("/api/positions/{item_id}/sell")
def position_sell(item_id: str, body: SellRequest):
    """
    卖出：按真实把数 qty_pieces 等比例缩减各档（保持档结构）。
    qty_pct 字段（占计划比例）会等比例缩减。
    """
    if body.qty_pieces <= 0:
        raise HTTPException(400, "qty_pieces 必须为正")
    state = _load_state_or_404()
    item = _find_item(state, item_id)
    if not item:
        raise HTTPException(404, f"item not found: {item_id}")
    pos = item.get("position", {})
    tiers = pos.get("tiers", [])
    if not tiers:
        raise HTTPException(400, "无新仓可卖")

    def _pieces(t):
        v = t.get("qty_pieces")
        return v if v is not None else t.get("qty_pct", 0)

    total_pieces = sum(_pieces(t) for t in tiers)
    if body.qty_pieces > total_pieces + 1e-6:
        raise HTTPException(400, f"卖出 {body.qty_pieces} 把超过当前持仓 {total_pieces} 把")

    if body.qty_pieces >= total_pieces - 1e-6:
        pos["tiers"] = []
        pos["avg_entry_price"] = None
        pos["total_qty_pct"] = 0
        pos["total_pieces"] = 0
        pos["highest_since_first_entry"] = None
        pos["tp_executed"] = []
        cleared = True
    else:
        ratio = 1 - (body.qty_pieces / total_pieces)
        for t in tiers:
            if t.get("qty_pieces") is not None:
                t["qty_pieces"] *= ratio
            t["qty_pct"] = t.get("qty_pct", 0) * ratio
        state_mod.compute_position_summary(item)
        cleared = False

    item.setdefault("recommendations_log", []).append({
        "t": utils.now_iso(),
        "type": "manual_sell",
        "price": body.price,
        "qty_pieces": body.qty_pieces,
        "qty_pct": body.qty_pct,
        "cleared": cleared,
    })
    state_mod.save_state(state)
    return {"ok": True, "cleared": cleared, "position": pos}


@app.post("/api/positions/{item_id}/clear")
def position_clear(item_id: str):
    """清空新仓（不影响 legacy_holding）。"""
    state = _load_state_or_404()
    item = _find_item(state, item_id)
    if not item:
        raise HTTPException(404, f"item not found: {item_id}")
    item["position"] = {
        "tiers": [], "avg_entry_price": None, "total_qty_pct": 0,
        "highest_since_first_entry": None, "tp_executed": [],
    }
    item.setdefault("recommendations_log", []).append({
        "t": utils.now_iso(), "type": "manual_clear",
    })
    state_mod.save_state(state)
    return {"ok": True}


@app.post("/api/positions/{item_id}/legacy")
def position_legacy(item_id: str, body: LegacyRequest):
    """设置/移除 legacy_holding（套牢仓）。"""
    state = _load_state_or_404()
    item = _find_item(state, item_id)
    if not item:
        raise HTTPException(404, f"item not found: {item_id}")
    if body.action == "remove":
        item.pop("legacy_holding", None)
    else:
        if body.quantity is None or body.avg_entry_price is None:
            raise HTTPException(400, "quantity 和 avg_entry_price 都必填")
        item["legacy_holding"] = {
            "quantity": body.quantity,
            "avg_entry_price": body.avg_entry_price,
            "set_at": utils.now_iso(),
        }
    state_mod.save_state(state)
    return {"ok": True}


# ---------- PushPlus tokens ----------
class TokenRequest(BaseModel):
    name: str
    token: str


@app.post("/api/tokens")
def add_token(body: TokenRequest):
    """新增 PushPlus token。"""
    if not body.name.strip() or not body.token.strip():
        raise HTTPException(400, "name 和 token 都不能为空")
    state = _load_state_or_404()
    tokens = state.setdefault("global", {}).setdefault("pushplus_tokens", [])
    if any(t.get("token") == body.token for t in tokens):
        raise HTTPException(400, "该 token 已存在")
    if any(t.get("name") == body.name for t in tokens):
        raise HTTPException(400, f"名字 '{body.name}' 已被使用")
    tokens.append({"name": body.name, "token": body.token})
    state_mod.save_state(state)
    return {"ok": True, "count": len(tokens)}


@app.delete("/api/tokens/{name}")
def remove_token(name: str):
    """按 name 删除 PushPlus token。"""
    state = _load_state_or_404()
    tokens = state.get("global", {}).get("pushplus_tokens", [])
    new_tokens = [t for t in tokens if t.get("name") != name]
    if len(new_tokens) == len(tokens):
        raise HTTPException(404, f"token 名 '{name}' 不存在")
    state["global"]["pushplus_tokens"] = new_tokens
    state_mod.save_state(state)
    return {"ok": True, "count": len(new_tokens)}


# ---------- 监控品种增删 ----------
class AddItemRequest(BaseModel):
    url: str
    name: str
    short_name: Optional[str] = None
    sector: str  # must be in SECTOR_OPTIONS
    phase: Optional[str] = "unknown"
    strong_support: Optional[float] = None
    primary_support: Optional[float] = None
    resistance_1: Optional[float] = None
    resistance_2: Optional[float] = None
    resistance_3: Optional[float] = None


def _slugify(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text).strip().lower()
    s = re.sub(r"[-\s]+", "-", s)
    return s[:50] or "item"


@app.post("/api/items")
def add_item(body: AddItemRequest):
    """新增监控品种（写入 state.items + 加到对应板块）。"""
    if body.sector not in SECTOR_OPTIONS:
        raise HTTPException(400, f"sector 必须是: {SECTOR_OPTIONS}")
    if not body.url.startswith("https://www.steamdt.com/"):
        raise HTTPException(400, "URL 必须以 https://www.steamdt.com/ 开头")

    state = _load_state_or_404()

    # 生成 id
    base_id = _slugify(body.name)
    existing_ids = {it["id"] for it in state.get("items", [])}
    item_id = base_id
    if item_id in existing_ids:
        for i in range(2, 100):
            cand = f"{base_id}-{i}"
            if cand not in existing_ids:
                item_id = cand
                break

    new_item = {
        "id": item_id,
        "name": body.name,
        "short_name": body.short_name or body.name[:20],
        "url": body.url,
        "phase": body.phase or "unknown",
        "key_levels": {
            "strong_support": body.strong_support,
            "primary_support": body.primary_support,
            "resistance_1": body.resistance_1,
            "resistance_2": body.resistance_2,
            "resistance_3": body.resistance_3,
        },
        "thresholds": {
            "today_pct_for_d1": 1.5,
            "rapid_drop_pct_1h": 4,
            "rapid_rise_pct_1h": 5,
            "d1_distance_to_r1_min": 0.02,
            "min_volume_d1": 8,
        },
        "history": [],
        "highest_observed": None,
        "lowest_observed": None,
        "position": {
            "tiers": [], "avg_entry_price": None, "total_qty_pct": 0,
            "highest_since_first_entry": None, "tp_executed": [],
        },
        "signals_log": [],
        "recommendations_log": [],
        "last_signal_pushed": None,
        "last_signal_time": None,
        "added_via": "dashboard",
        "added_at": utils.now_iso(),
    }

    # 加进板块
    sectors = state.setdefault("global", {}).setdefault("sectors", {})
    primary = sectors.setdefault("primary", {})
    primary.setdefault(body.sector, []).append(item_id)

    state.setdefault("items", []).append(new_item)
    state_mod.save_state(state)
    return {"ok": True, "id": item_id, "count": len(state["items"])}


# ---------- LLM 配置与调用 ----------
class LLMConfigRequest(BaseModel):
    provider: str
    model: str
    api_key: Optional[str] = None       # None 或 "***" 表示不修改
    base_url: Optional[str] = None
    enabled_modules: Optional[dict] = None
    monthly_budget_cny: Optional[float] = None


@app.get("/api/llm/config")
def get_llm_config():
    """返回当前 LLM 配置（api_key 脱敏）。"""
    state = _load_state_or_404()
    cfg = state.get("global", {}).get("llm_config", {}) or {}
    out = {
        "provider":            cfg.get("provider", "anthropic"),
        "model":               cfg.get("model", ""),
        "base_url":            cfg.get("base_url", ""),
        "enabled_modules":     cfg.get("enabled_modules", {}),
        "monthly_budget_cny":  cfg.get("monthly_budget_cny"),
        "configured":          bool(cfg.get("api_key")),
    }
    if cfg.get("api_key"):
        k = cfg["api_key"]
        out["api_key_masked"] = (k[:6] + "..." + k[-4:]) if len(k) > 12 else "***"
    return out


@app.post("/api/llm/config")
def set_llm_config(body: LLMConfigRequest):
    """保存配置。api_key 为空或以 *** 开头时表示不修改原 key。"""
    state = _load_state_or_404()
    glb = state.setdefault("global", {})
    cfg = glb.setdefault("llm_config", {})
    cfg["provider"] = body.provider
    cfg["model"]    = body.model
    if body.api_key and not body.api_key.startswith("***"):
        cfg["api_key"] = body.api_key.strip()
    if body.base_url is not None:
        cfg["base_url"] = (body.base_url or "").strip()
    if body.enabled_modules is not None:
        cfg["enabled_modules"] = body.enabled_modules
    if body.monthly_budget_cny is not None:
        cfg["monthly_budget_cny"] = body.monthly_budget_cny
    cfg["updated_at"] = utils.now_iso()
    state_mod.save_state(state)
    return {"ok": True, "configured": bool(cfg.get("api_key"))}


@app.post("/api/llm/test")
def test_llm():
    """快速调用一次 LLM 验证连通。"""
    state = _load_state_or_404()
    cfg = state.get("global", {}).get("llm_config", {}) or {}
    if not cfg.get("api_key"):
        raise HTTPException(400, "尚未配置 api_key")
    return llm_mod.test_connection(cfg)


@app.post("/api/llm/classify_news")
def llm_classify_news_now():
    """手动触发一次新闻 LLM 分类（用于测试 / 立即刷新）。"""
    from lib import news_monitor as nm
    from lib import llm_analyst
    state = _load_state_or_404()
    if not llm_mod.is_module_enabled(state, "news_classification"):
        raise HTTPException(400, "新闻分类模块未启用，请先在设置勾选")
    if not llm_mod.from_state(state):
        raise HTTPException(400, "LLM 未配置或 api_key 无效")
    news_items = nm.fetch_news()
    if not news_items:
        err = nm.get_last_fetch_error() or "未知原因"
        raise HTTPException(
            500,
            f"拉取 Steam News 失败：{err}。建议：① 检查网络能否访问 https://api.steampowered.com "
            "② 用代理/VPN 后重试 ③ 该错误不影响其他功能（仓位/dashboard/AI 复盘 都正常）",
        )
    result = llm_analyst.classify_news_with_llm(state, news_items)
    state_mod.save_state(state)   # 保存 audit log
    if not result:
        raise HTTPException(500, "LLM 分类失败，详见 /api/llm/audit_log")
    return result


@app.get("/api/llm/audit_log")
def get_llm_audit_log(limit: int = 30):
    """最近 N 条 LLM 调用记录。"""
    state = _load_state_or_404()
    log = state.get("global", {}).get("llm_audit_log", [])
    return {"log": log[-limit:]}


# ---------- Phase 3：每日复盘评论 ----------
@app.post("/api/llm/daily_review")
def llm_daily_review_now():
    """手动触发一次复盘评论。"""
    from lib import llm_analyst
    state = _load_state_or_404()
    if not llm_mod.from_state(state):
        raise HTTPException(400, "LLM 未配置")
    result = llm_analyst.daily_review_commentary(state, force=True)
    state_mod.save_state(state)
    if not result:
        raise HTTPException(500, "复盘生成失败，详见 audit log")
    return result


@app.get("/api/llm/reviews")
def get_llm_reviews(limit: int = 10):
    """最近 N 份 AI 复盘。"""
    state = _load_state_or_404()
    log = state.get("global", {}).get("ai_review", [])
    return {"reviews": log[-limit:][::-1]}   # 最新在前


# ---------- Phase 4：参数调整提案 ----------
@app.post("/api/llm/propose_params")
def llm_propose_params_now():
    """手动触发一次参数提案。"""
    from lib import llm_analyst
    state = _load_state_or_404()
    if not llm_mod.from_state(state):
        raise HTTPException(400, "LLM 未配置")
    result = llm_analyst.propose_parameter_changes(state, force=True)
    state_mod.save_state(state)
    if not result:
        raise HTTPException(500, "提案生成失败或样本不足，详见 audit log")
    return result


@app.get("/api/llm/proposals")
def get_llm_proposals(status: Optional[str] = None):
    """所有提案，可按 status 过滤 (pending/applied/rejected)。"""
    state = _load_state_or_404()
    proposals = state.get("global", {}).get("parameter_proposals", [])
    if status:
        proposals = [p for p in proposals if p.get("status") == status]
    proposals = sorted(proposals, key=lambda p: p.get("created_at", ""), reverse=True)
    return {"proposals": proposals}


@app.post("/api/llm/proposals/{proposal_id}/apply")
def apply_llm_proposal(proposal_id: str):
    """应用一条 pending 提案（自动备份原值）。"""
    from lib import llm_analyst
    state = _load_state_or_404()
    res = llm_analyst.apply_proposal(state, proposal_id)
    if not res.get("ok"):
        raise HTTPException(400, res.get("error", "apply failed"))
    state_mod.save_state(state)
    return res


@app.post("/api/llm/proposals/{proposal_id}/reject")
def reject_llm_proposal(proposal_id: str):
    """拒绝一条提案。"""
    from lib import llm_analyst
    state = _load_state_or_404()
    res = llm_analyst.reject_proposal(state, proposal_id)
    if not res.get("ok"):
        raise HTTPException(400, res.get("error", "reject failed"))
    state_mod.save_state(state)
    return res


# ---------- 嵌入式调度器控制 ----------
@app.get("/api/scheduler/status")
def scheduler_status():
    """调度器状态（运行中？最近一次跑？下次几点？）"""
    state = _load_state_or_404()
    cfg = state.get("global", {}).get("scheduler", {"mode": "embedded"})
    return {
        "mode":   cfg.get("mode", "embedded"),
        "status": scheduler_mod.get_status(),
    }


@app.post("/api/scheduler/start")
def scheduler_start():
    """手动启动调度器（如果先前 stop 了）。"""
    started = scheduler_mod.start()
    return {"ok": True, "newly_started": started}


@app.post("/api/scheduler/stop")
async def scheduler_stop():
    """手动停止调度器（监控会停，API 还在）。"""
    stopped = await scheduler_mod.stop()
    return {"ok": True, "newly_stopped": stopped}


@app.post("/api/scheduler/run/{task_name}")
async def scheduler_run_now(task_name: str):
    """手动立即触发一次任务（不影响调度节奏）。"""
    res = await scheduler_mod.trigger_now(task_name)
    if not res.get("ok"):
        raise HTTPException(400, res.get("error", "trigger failed"))
    return res


class SchedulerModeRequest(BaseModel):
    mode: str   # "embedded" | "external"


@app.post("/api/scheduler/mode")
async def scheduler_set_mode(body: SchedulerModeRequest):
    """切换调度器模式：embedded（API 自带）/ external（Windows 任务计划器）"""
    if body.mode not in ("embedded", "external"):
        raise HTTPException(400, "mode 必须是 embedded 或 external")
    state = _load_state_or_404()
    state.setdefault("global", {}).setdefault("scheduler", {})["mode"] = body.mode
    state_mod.save_state(state)
    if body.mode == "embedded":
        scheduler_mod.start()
    else:
        await scheduler_mod.stop()
    return {"ok": True, "mode": body.mode}


@app.delete("/api/items/{item_id}")
def remove_item(item_id: str):
    """删除监控品种 + 从所有板块清掉。"""
    state = _load_state_or_404()
    items = state.get("items", [])
    new_items = [it for it in items if it["id"] != item_id]
    if len(new_items) == len(items):
        raise HTTPException(404, f"item not found: {item_id}")
    state["items"] = new_items
    sectors = state.get("global", {}).get("sectors", {})
    for tier_key in ("primary", "secondary"):
        groups = sectors.get(tier_key) or {}
        for k, ids in list(groups.items()):
            if isinstance(ids, list) and item_id in ids:
                ids.remove(item_id)
    state_mod.save_state(state)
    return {"ok": True, "count": len(new_items)}


# ==================== 启动 ====================
if __name__ == "__main__":
    print("=" * 60)
    print("  Sentinel API Server (LOCAL ONLY)")
    print("=" * 60)
    print("  URL:        http://localhost:8000")
    print("  API 文档:   http://localhost:8000/docs")
    print("  调度器:     嵌入式（API 启动后自动开跑监控）")
    print("    - monitor_fast:  每 10 分钟")
    print("    - monitor_slow:  每 60 分钟")
    print("    - daily_review:  每天 23:00")
    print("  停止:       Ctrl+C 或关闭此窗口")
    print("  仅本机可访问，外部无法连接")
    print("=" * 60)
    uvicorn.run(
        "backend_api:app",
        host="127.0.0.1",   # 仅本机环回，局域网/外网均无法访问
        port=8000,
        reload=False,
        log_level="info",
    )
