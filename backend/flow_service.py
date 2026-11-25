from __future__ import annotations

import asyncio
import base64
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import hashlib
import json
import random
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlsplit

import httpx

import crawler_service
import database

MEDIA_DIR = Path(__file__).resolve().parent / "media"
FLOW_PROFILES_DIR = MEDIA_DIR / "flow_profiles"
FLOW_REFS_DIR = MEDIA_DIR / "flow_refs"
OUTPUTS_DIR = MEDIA_DIR / "outputs"
FLOW_PROFILES_DIR.mkdir(parents=True, exist_ok=True)
FLOW_REFS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

FLOW_HOME_URL = "https://flow.google.com/"
FLOW_LOGIN_URL = "https://accounts.google.com/ServiceLogin?continue=https://flow.google.com/&followup=https://flow.google.com/"
AISANDBOX_BASE = "https://aisandbox-pa.googleapis.com/v1"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

_FLOW_ACCOUNT_LOCKS: Dict[int, asyncio.Lock] = {}


def _get_flow_account_lock(account_id: int) -> asyncio.Lock:
    lock = _FLOW_ACCOUNT_LOCKS.get(account_id)
    if lock is None:
        lock = asyncio.Lock()
        _FLOW_ACCOUNT_LOCKS[account_id] = lock
    return lock

FLOW_MODELS_META: List[Dict[str, Any]] = [
    # 1. OmniFlash & Gemini Omni (Latest 2026 Multimodal Video Engine on flow.google.com)
    {
        "id": "omni_1_2_flash_10s_portrait",
        "group": "OmniFlash & Gemini Omni (Mới nhất 2026)",
        "label": "Omni 1.2 Flash (≤ 10s) — Dọc 9:16 · Siêu tốc, hỗ trợ cả Acc Free",
        "gemini_model": "veo-3.0-fast-generate-preview",
        "flow_studio_model": "Omni 1.2 Flash",
        "ui_keywords": ["Omni 1.2 Flash", "Omni Flash", "Gemini Omni"],
        "duration_hint": "10s",
        "badge": "HOT · Free/All Tiers",
    },
    {
        "id": "omni_1_2_flash_15s_portrait",
        "group": "OmniFlash & Gemini Omni (Mới nhất 2026)",
        "label": "Omni 1.2 Flash (11–15s) — Dọc 9:16 · Video dài 15s (AI Plus/Pro/Ultra)",
        "gemini_model": "veo-3.0-generate-preview",
        "flow_studio_model": "Omni 1.2 Flash",
        "ui_keywords": ["Omni 1.2 Flash", "Omni Flash"],
        "duration_hint": "15s",
        "badge": "11–15s Extended",
    },
    {
        "id": "gemini_omni_multimodal_portrait",
        "group": "OmniFlash & Gemini Omni (Mới nhất 2026)",
        "label": "Gemini Omni Multimodal — Dọc 9:16 · Ingredients & Video-to-Video",
        "gemini_model": "veo-3.0-generate-preview",
        "flow_studio_model": "Omni 1.2 Flash",
        "ui_keywords": ["Omni 1.2 Flash", "Gemini Omni", "Omni"],
        "duration_hint": "10s",
        "badge": "Multimodal",
    },
    {
        "id": "omni_1_1_flash_portrait",
        "group": "OmniFlash & Gemini Omni (Mới nhất 2026)",
        "label": "Omni 1.1 Flash — Dọc 9:16 · Phiên bản ổn định trên Flow Studio",
        "gemini_model": "veo-3.0-fast-generate-preview",
        "flow_studio_model": "Omni 1.1 Flash",
        "ui_keywords": ["Omni 1.1 Flash", "Omni 1.2 Flash"],
        "duration_hint": "8s",
        "badge": "Omni 1.1",
    },
    # 2. Veo 3.1 Series (Latest Physics + Native Audio Engine)
    {
        "id": "veo_3_1_lite_portrait",
        "group": "Veo 3.1 Series (Vật lý chân thực & Âm thanh gốc)",
        "label": "Veo 3.1 - Lite — Dọc 9:16 · Bản mới nhẹ, nhanh & hỗ trợ Acc Free",
        "gemini_model": "veo-3.0-fast-generate-preview",
        "flow_studio_model": "Veo 3.1 - Lite",
        "ui_keywords": ["Veo 3.1 - Lite", "Veo 3.1 Lite", "Veo Lite"],
        "duration_hint": "8s",
        "badge": "NEW · Lite",
    },
    {
        "id": "veo_3_1_t2v_fast_portrait",
        "group": "Veo 3.1 Series (Vật lý chân thực & Âm thanh gốc)",
        "label": "Veo 3.1 - Fast — Dọc 9:16 · Âm thanh gốc, tối ưu tốc độ & Credits",
        "gemini_model": "veo-3.0-fast-generate-preview",
        "flow_studio_model": "Veo 3.1 - Fast",
        "ui_keywords": ["Veo 3.1 - Fast", "Veo 3.1 Fast", "Veo 3.1 - Lite"],
        "duration_hint": "8s",
        "badge": "Fast Audio",
    },
    {
        "id": "veo_3_1_t2v_fast_portrait_ultra",
        "group": "Veo 3.1 Series (Vật lý chân thực & Âm thanh gốc)",
        "label": "Veo 3.1 Fast Ultra — Dọc 9:16 · Độ nét cao 1080p (AI Pro/Ultra)",
        "gemini_model": "veo-3.0-generate-preview",
        "flow_studio_model": "Veo 3.1 - Fast",
        "ui_keywords": ["Veo 3.1 - Fast", "Veo 3.1 Ultra", "Veo 3.1 - Quality"],
        "duration_hint": "8s",
        "badge": "1080p Ultra",
    },
    {
        "id": "veo_3_1_t2v_portrait",
        "group": "Veo 3.1 Series (Vật lý chân thực & Âm thanh gốc)",
        "label": "Veo 3.1 - Quality / Pro — Dọc 9:16 · Điện ảnh 1080p/4K + Đối thoại gốc",
        "gemini_model": "veo-3.0-generate-preview",
        "flow_studio_model": "Veo 3.1 - Quality",
        "ui_keywords": ["Veo 3.1 - Quality", "Veo 3.1 Quality", "Veo 3.1 - Fast"],
        "duration_hint": "8s",
        "badge": "Cinema 4K",
    },
    # 3. Nano Banana + OmniFlash / Veo Hybrid (Product Keyframe Consistency)
    {
        "id": "nano_banana_pro_omni_flash",
        "group": "Nano Banana + Video (Giữ chuẩn sản phẩm & chữ bao bì)",
        "label": "Nano Banana Pro + Omni 1.2 Flash — Dọc 9:16 · Chuẩn SP & chữ rõ nét",
        "gemini_model": "veo-3.0-generate-preview",
        "flow_studio_model": "Omni 1.2 Flash",
        "ui_keywords": ["Omni 1.2 Flash", "Nano Banana Pro"],
        "duration_hint": "10s",
        "badge": "Product Lock",
    },
    {
        "id": "nano_banana_2_1_veo_3_1",
        "group": "Nano Banana + Video (Giữ chuẩn sản phẩm & chữ bao bì)",
        "label": "Nano Banana 2.1 + Veo 3.1 — Dọc 9:16 · Keyframe sắc nét + Vật lý Veo",
        "gemini_model": "veo-3.0-generate-preview",
        "flow_studio_model": "Veo 3.1 - Quality",
        "ui_keywords": ["Veo 3.1 - Quality", "Veo 3.1 - Lite", "Nano Banana 2.1"],
        "duration_hint": "8s",
        "badge": "Keyframe + Veo",
    },
    # 4. Veo 3.0 & Veo 2 Series (API & Legacy Compatibility)
    {
        "id": "veo_3_0_fast_portrait",
        "group": "Veo 3.0 & Veo 2 (Tương thích Gemini API / Legacy)",
        "label": "Veo 3.0 Fast — Dọc 9:16 (veo-3.0-fast-generate-001)",
        "gemini_model": "veo-3.0-fast-generate-001",
        "flow_studio_model": "Veo 3.1 - Lite",
        "ui_keywords": ["Veo 3.1 - Lite", "Veo 3", "Veo 3 Fast"],
        "duration_hint": "8s",
        "badge": "API Ready",
    },
    {
        "id": "veo_3_0_portrait",
        "group": "Veo 3.0 & Veo 2 (Tương thích Gemini API / Legacy)",
        "label": "Veo 3.0 Standard — Dọc 9:16 (veo-3.0-generate-001)",
        "gemini_model": "veo-3.0-generate-001",
        "flow_studio_model": "Veo 3.1 - Quality",
        "ui_keywords": ["Veo 3.1 - Quality", "Veo 3", "Veo 3 Quality"],
        "duration_hint": "8s",
        "badge": "API Ready",
    },
    {
        "id": "veo_2_1_fast_d_15_t2v",
        "group": "Veo 3.0 & Veo 2 (Tương thích Gemini API / Legacy)",
        "label": "Veo 2.1 Fast — Dọc 9:16 (veo-2.0-generate-001)",
        "gemini_model": "veo-2.0-generate-001",
        "flow_studio_model": "Veo 3.1 - Lite",
        "ui_keywords": ["Veo 3.1 - Lite", "Veo 2", "Veo 2 - Fast"],
        "duration_hint": "8s",
        "badge": "Stable",
    },
]

_dynamic_synced_models: List[Dict[str, Any]] = []


def get_all_flow_models() -> List[Dict[str, Any]]:
    seen = {m["id"] for m in FLOW_MODELS_META}
    extra = [m for m in _dynamic_synced_models if m.get("id") not in seen]
    return list(FLOW_MODELS_META) + extra


def sync_latest_flow_models() -> Dict[str, Any]:
    """Fetch any newly released Veo / Omni / Imagen video models live from flow.google.com & configured Gemini API keys."""
    discovered: List[Dict[str, Any]] = []
    known_ids = {m["id"] for m in FLOW_MODELS_META}
    known_gem = {m["gemini_model"] for m in FLOW_MODELS_META}

    # 1. Check any Gemini API keys stored in flow_accounts
    with database.get_conn() as conn:
        rows = conn.execute("SELECT bearer_token FROM flow_accounts WHERE bearer_token LIKE 'AIza%'").fetchall()
    for r in rows:
        key = str(r["bearer_token"] or "").strip()
        if not key:
            continue
        try:
            resp = httpx.get(f"{GEMINI_API_BASE}/models?key={key}", timeout=10.0)
            if resp.status_code == 200:
                for item in resp.json().get("models") or []:
                    raw_name = str(item.get("name") or "").replace("models/", "").strip()
                    disp = str(item.get("displayName") or raw_name).strip()
                    if any(k in raw_name.lower() for k in ("veo", "omni", "video")) and raw_name not in known_ids and raw_name not in known_gem:
                        known_ids.add(raw_name)
                        discovered.append(
                            {
                                "id": raw_name,
                                "group": "Model mới phát hiện từ Google API",
                                "label": f"{disp} ({raw_name}) — Dọc 9:16",
                                "gemini_model": raw_name,
                                "ui_keywords": [disp, raw_name],
                                "duration_hint": "8s",
                                "badge": "Live Synced",
                            }
                        )
        except Exception:
            pass

    # 2. Check live flow.google.com/about?hl=en for any new Omni / Veo version numbers
    try:
        proc = subprocess.run(
            ["curl", "-sL", "--max-time", "8", "-A", "Mozilla/5.0", "https://flow.google.com/about?hl=en"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        html = proc.stdout or ""
        for pat in (r"\bOmni\s+\d+(?:\.\d+)?\s*(?:Flash|Pro|Ultra)?\b", r"\bVeo\s+\d+(?:\.\d+)?\s*(?:Lite|Fast|Ultra|Pro)?\b"):
            for m in re.finditer(pat, html, re.I):
                name_found = re.sub(r"\s+", " ", m.group(0)).strip()
                slug = re.sub(r"[^a-z0-9]+", "_", name_found.lower()).strip("_") + "_portrait"
                already_covered = any(
                    name_found.lower() in str(existing.get("label") or "").lower()
                    for existing in (FLOW_MODELS_META + discovered)
                )
                if not already_covered and slug not in known_ids:
                    known_ids.add(slug)
                    discovered.append(
                        {
                            "id": slug,
                            "group": "Model mới cập nhật trên flow.google.com",
                            "label": f"{name_found} — Dọc 9:16 (Live từ flow.google.com)",
                            "gemini_model": "veo-3.0-generate-preview",
                            "ui_keywords": [name_found],
                            "duration_hint": "10s",
                            "badge": "Live Web",
                        }
                    )
    except Exception:
        pass

    if discovered:
        _dynamic_synced_models.clear()
        _dynamic_synced_models.extend(discovered)

    all_models = get_all_flow_models()
    return {
        "ok": True,
        "count": len(all_models),
        "new_discovered": len(discovered),
        "models": all_models,
    }

_flow_browser_threads: Dict[int, threading.Thread] = {}
_flow_lock = threading.Lock()


def _chrome_executable() -> Optional[str]:
    mac_chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if Path(mac_chrome).exists():
        return mac_chrome
    return None


def get_flow_pool_summary() -> Dict[str, Any]:
    accs = database.list_flow_accounts()
    active = [a for a in accs if a.get("status") == "active"]
    return {
        "total_accounts": len(accs),
        "active_accounts": len(active),
        "total_credits_remaining": sum(int(a.get("credits_remaining") or 0) for a in accs),
        "renders_used": sum(int(a.get("renders_used") or 0) for a in accs),
        "weekly_capacity": sum(int(a.get("weekly_limit") or 0) for a in accs),
    }


def _has_google_auth_cookies(cookies: List[Dict[str, Any]]) -> bool:
    names = {
        str(c.get("name") or "")
        for c in (cookies or [])
        if "google.com" in str(c.get("domain") or "") and c.get("value")
    }
    return bool(("SID" in names and "SAPISID" in names) or "__Secure-1PSID" in names or "__Secure-3PSID" in names)


def _extract_google_email_from_html(html_text: str) -> str:
    if not html_text:
        return ""
    ignore_domains = {"google.com", "gstatic.com", "googleapis.com", "example.com", "w3.org", "schema.org"}
    for m in re.finditer(r"[a-zA-Z0-9._%+-]{2,64}@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,10}", html_text):
        cand = m.group(0).lower()
        dom = cand.split("@", 1)[-1]
        if dom not in ignore_domains and not dom.endswith((".png", ".jpg", ".svg", ".js", ".css")):
            return cand
    return ""


def _is_flow_page_authenticated(url: str, html_text: str, cookies: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """Verify the browser is genuinely signed into Google on flow.google.com (not on ServiceLogin or logged-out /about)."""
    cur_u = (url or "").lower()
    if not cur_u or "accounts.google.com" in cur_u:
        return False, ""
    if not _has_google_auth_cookies(cookies):
        return False, ""
    email = _extract_google_email_from_html(html_text)
    has_login_cta = "accounts.google.com/servicelogin" in (html_text or "").lower()
    if has_login_cta and not email and "/project/" not in cur_u:
        return False, ""
    return True, email


def _parse_cookie_input_to_playwright(raw_input: str) -> List[Dict[str, Any]]:
    """Parse EditThisCookie JSON, Netscape cookies.txt, or 'SID=...; HSID=...' header string into Playwright cookies."""
    txt = (raw_input or "").strip()
    if not txt:
        return []

    # 1. JSON array or object
    if txt.startswith("[") or txt.startswith("{"):
        try:
            obj = json.loads(txt)
            arr = obj if isinstance(obj, list) else (obj.get("cookies") or [])
            out: List[Dict[str, Any]] = []
            for c in arr:
                if not isinstance(c, dict) or not c.get("name") or c.get("value") is None:
                    continue
                dom = str(c.get("domain") or ".google.com")
                if "google" not in dom:
                    continue
                same_site_raw = str(c.get("sameSite") or "").capitalize()
                item: Dict[str, Any] = {
                    "name": str(c["name"]),
                    "value": str(c["value"]),
                    "domain": dom,
                    "path": str(c.get("path") or "/"),
                    "secure": bool(c.get("secure", True)),
                    "httpOnly": bool(c.get("httpOnly", False)),
                }
                if same_site_raw in {"Strict", "Lax", "None"}:
                    item["sameSite"] = same_site_raw
                out.append(item)
            if out:
                return out
        except Exception:
            pass

    # 2. Netscape cookies.txt lines
    if "\t" in txt:
        out_ns: List[Dict[str, Any]] = []
        for ln in txt.splitlines():
            s = ln.strip()
            if not s or s.startswith("#"):
                continue
            parts = s.split("\t")
            if len(parts) >= 7 and "google" in parts[0]:
                out_ns.append(
                    {
                        "name": parts[5].strip(),
                        "value": parts[6].strip(),
                        "domain": parts[0].strip(),
                        "path": parts[2].strip() or "/",
                        "secure": parts[3].strip().upper() == "TRUE",
                    }
                )
        if out_ns:
            return out_ns

    # 3. Raw Cookie header string: SID=...; SAPISID=...; __Secure-1PSID=...
    if "=" in txt and (";" in txt or txt.startswith(("SID=", "__Secure-", "HSID=", "SAPISID="))):
        out_hdr: List[Dict[str, Any]] = []
        for pair in txt.split(";"):
            if "=" not in pair:
                continue
            k, v = pair.split("=", 1)
            k = k.strip()
            v = v.strip()
            if k and v:
                out_hdr.append(
                    {
                        "name": k,
                        "value": v,
                        "domain": ".google.com",
                        "path": "/",
                        "secure": True,
                    }
                )
        if out_hdr:
            return out_hdr

    return []


def _default_credits_for_tier(tier: str) -> int:
    t = (tier or "").strip().lower()
    if "ultra" in t:
        return 25000
    if "plus" in t:
        return 200
    if "free" in t:
        return 50
    return 1000


def bulk_import_flow_accounts(
    raw_text: str,
    weekly_limit: int = 50,
    tier: str = "Flow Pro",
) -> Dict[str, Any]:
    """Import one or multiple flow.google.com accounts from JSON cookies, Cookie headers, Bearer tokens, or Gemini Veo API keys."""
    txt = (raw_text or "").strip()
    if not txt:
        return {"ok": False, "imported": 0, "error": "Dữ liệu nhập đang trống."}
    est_credits = _default_credits_for_tier(tier)

    # Case A: Entire input is a single JSON Cookie Array or session JSON
    if txt.startswith("[") or txt.startswith("{"):
        try:
            parsed_json = json.loads(txt)
            if isinstance(parsed_json, dict) and (parsed_json.get("access_token") or parsed_json.get("token")):
                tok = str(parsed_json.get("access_token") or parsed_json.get("token")).strip()
                user_obj = parsed_json.get("user") if isinstance(parsed_json.get("user"), dict) else {}
                email = str(user_obj.get("email") or parsed_json.get("email") or "").strip()
                acc = database.create_flow_account(
                    {
                        "label": email or "Flow Session Token",
                        "email": email,
                        "tier": tier,
                        "auth_mode": "bearer_token",
                        "bearer_token": tok,
                        "project_url": str(parsed_json.get("project_url") or FLOW_HOME_URL),
                        "weekly_limit": weekly_limit,
                        "credits_remaining": est_credits,
                        "credits_total": est_credits,
                        "status": "active",
                        "notes": "Nhập từ Session JSON",
                    }
                )
                return {"ok": True, "imported": 1, "accounts": [acc]}

            cookies = _parse_cookie_input_to_playwright(txt)
            if cookies:
                acc = database.create_flow_account(
                    {
                        "label": f"Flow Cookie ({len(cookies)} cookies)",
                        "email": "",
                        "tier": tier,
                        "auth_mode": "cookie_json",
                        "cookies_json": json.dumps(cookies, ensure_ascii=False),
                        "project_url": FLOW_HOME_URL,
                        "weekly_limit": weekly_limit,
                        "credits_remaining": est_credits,
                        "credits_total": est_credits,
                        "status": "active",
                        "notes": "Nhập từ Cookie JSON (EditThisCookie / Cookie-Editor)",
                    }
                )
                return {"ok": True, "imported": 1, "accounts": [acc]}
        except Exception:
            pass

    # Case B: Netscape cookies.txt multi-line paste
    if "\t" in txt and "google.com" in txt:
        cookies = _parse_cookie_input_to_playwright(txt)
        if cookies:
            acc = database.create_flow_account(
                {
                    "label": f"Flow Cookies.txt ({len(cookies)} cookies)",
                    "tier": tier,
                    "auth_mode": "cookie_json",
                    "cookies_json": json.dumps(cookies, ensure_ascii=False),
                    "project_url": FLOW_HOME_URL,
                    "weekly_limit": weekly_limit,
                    "credits_remaining": est_credits,
                    "credits_total": est_credits,
                    "status": "active",
                    "notes": "Nhập từ định dạng Netscape cookies.txt",
                }
            )
            return {"ok": True, "imported": 1, "accounts": [acc]}

    # Case C: Pipe-separated bulk lines: Label_or_Email | Credential | ProjectURL_or_Proxy | Proxy
    created: List[Dict[str, Any]] = []
    lines = [ln.strip() for ln in txt.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    for idx, line in enumerate(lines, start=1):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 1:
            label = f"Flow_Acc_{idx:02d}"
            cred = parts[0]
            extra_1 = ""
            extra_2 = ""
        elif len(parts) == 2:
            label, cred = parts[0], parts[1]
            extra_1, extra_2 = "", ""
        elif len(parts) == 3:
            label, cred, extra_1 = parts[0], parts[1], parts[2]
            extra_2 = ""
        else:
            label, cred, extra_1, extra_2 = parts[0], parts[1], parts[2], parts[3]

        if not cred:
            continue

        project_url = FLOW_HOME_URL
        proxy = ""
        for ex in (extra_1, extra_2):
            if not ex:
                continue
            if "flow.google.com" in ex or "labs.google" in ex:
                project_url = ex
            elif re.match(r"^(?:https?|socks5)://", ex, re.I):
                proxy = ex
            elif re.match(r"^[0-9a-fA-F-]{16,}$", ex):
                project_url = f"https://flow.google.com/project/{ex}"

        email = label if "@" in label else ""
        if cred.startswith("AIza"):
            auth_mode = "gemini_api_key"
            bearer = cred
            cookies_str = ""
            notes = "Gemini / Veo Official API Key"
        elif cred.startswith("ya29."):
            auth_mode = "bearer_token"
            bearer = cred
            cookies_str = ""
            notes = "Google OAuth Bearer Token (aisandbox-pa)"
        else:
            parsed_c = _parse_cookie_input_to_playwright(cred)
            if not parsed_c:
                continue
            auth_mode = "cookie_json"
            bearer = ""
            cookies_str = json.dumps(parsed_c, ensure_ascii=False)
            notes = f"Imported {len(parsed_c)} Google cookies"

        acc = database.create_flow_account(
            {
                "label": label[:80],
                "email": email[:120],
                "tier": tier,
                "auth_mode": auth_mode,
                "cookies_json": cookies_str,
                "bearer_token": bearer,
                "project_url": project_url,
                "proxy": proxy,
                "credits_remaining": est_credits,
                "credits_total": est_credits,
                "weekly_limit": weekly_limit,
                "status": "active",
                "notes": notes,
            }
        )
        created.append(acc)

    if not created:
        return {
            "ok": False,
            "imported": 0,
            "error": "Không nhận diện được Cookie Google (SID/SAPISID), Bearer Token (ya29...) hoặc Gemini Veo Key (AIza...).",
        }
    return {"ok": True, "imported": len(created), "accounts": created}


def start_flow_browser_login(
    account_id: Optional[int] = None,
    label: str = "",
    proxy: str = "",
    tier: str = "Flow Pro",
) -> Dict[str, Any]:
    """Open visible Chrome on flow.google.com so the user signs in directly; auto-extracts cookies & closes Chrome once authenticated."""
    if not crawler_service.has_playwright():
        return {"ok": False, "error": "Playwright chưa được cài đặt trên máy."}

    raw_acc: Optional[Dict[str, Any]] = None
    if account_id:
        raw_acc = database.get_flow_account(account_id)

    if not raw_acc:
        pub = database.create_flow_account(
            {
                "label": (label or "Google Flow Chrome").strip()[:80],
                "tier": tier,
                "auth_mode": "browser_profile",
                "proxy": proxy.strip(),
                "status": "login_pending",
                "notes": "Đang mở Chrome chờ đăng nhập flow.google.com...",
            }
        )
        acc_id = int(pub["id"])
        profile_dir = str(FLOW_PROFILES_DIR / f"acc_{acc_id}")
        Path(profile_dir).mkdir(parents=True, exist_ok=True)
        database.update_flow_account(acc_id, profile_dir=profile_dir)
        raw_acc = database.get_flow_account(acc_id)
    else:
        acc_id = int(raw_acc["id"])
        profile_dir = str(raw_acc.get("profile_dir") or (FLOW_PROFILES_DIR / f"acc_{acc_id}"))
        Path(profile_dir).mkdir(parents=True, exist_ok=True)
        database.update_flow_account(
            acc_id,
            profile_dir=profile_dir,
            auth_mode="browser_profile",
            status="login_pending",
            notes="Đang mở Chrome chờ đăng nhập flow.google.com...",
        )

    with _flow_lock:
        existing_th = _flow_browser_threads.get(acc_id)
        if existing_th and existing_th.is_alive():
            return {
                "ok": True,
                "account_id": acc_id,
                "message": "Cửa sổ Chrome cho tài khoản này đang mở sẵn — vui lòng hoàn tất đăng nhập trên trình duyệt.",
                "account": database.update_flow_account(acc_id),
            }

        def _watcher() -> None:
            async def _run() -> None:
                from playwright.async_api import async_playwright

                chrome_exe = _chrome_executable()
                launch_kwargs: Dict[str, Any] = {
                    "headless": False,
                    "args": ["--disable-blink-features=AutomationControlled"],
                    "viewport": {"width": 1280, "height": 860},
                }
                if chrome_exe:
                    launch_kwargs["executable_path"] = chrome_exe
                eff_proxy = (proxy or str((raw_acc or {}).get("proxy") or "")).strip()
                if eff_proxy:
                    launch_kwargs["proxy"] = {"server": eff_proxy}

                async with async_playwright() as p:
                    ctx = None
                    try:
                        ctx = await p.chromium.launch_persistent_context(profile_dir, **launch_kwargs)
                        # Only seed cookies if profile has none yet (never overwrite live rotating Google profile cookies)
                        existing_cookies_raw = str((raw_acc or {}).get("cookies_json") or "")
                        live_c = await ctx.cookies()
                        if existing_cookies_raw and not _has_google_auth_cookies(live_c):
                            try:
                                c_list = json.loads(existing_cookies_raw)
                                if isinstance(c_list, list) and c_list:
                                    await ctx.add_cookies(c_list)
                            except Exception:
                                pass

                        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
                        start_url = FLOW_LOGIN_URL if not existing_cookies_raw else FLOW_HOME_URL
                        await page.goto(start_url, wait_until="domcontentloaded", timeout=30000)

                        deadline = time.monotonic() + 240.0
                        captured_ok = False
                        while time.monotonic() < deadline:
                            await asyncio.sleep(2.0)
                            if not ctx.pages:
                                break
                            active_pg = ctx.pages[-1]
                            cur_url = active_pg.url or ""
                            all_cookies = await ctx.cookies()
                            on_flow = "flow.google.com" in cur_url and "accounts.google.com" not in cur_url

                            if on_flow and _has_google_auth_cookies(all_cookies):
                                html_probe = ""
                                try:
                                    html_probe = await active_pg.content()
                                except Exception:
                                    pass
                                is_authed, email_probe = _is_flow_page_authenticated(cur_url, html_probe, all_cookies)
                                if not is_authed:
                                    continue

                                await asyncio.sleep(1.5)
                                all_cookies = await ctx.cookies()
                                google_cookies = [
                                    c for c in all_cookies if "google.com" in str(c.get("domain") or "")
                                ]
                                email = email_probe or _extract_google_email_from_html(html_probe)
                                cur_lbl = str((raw_acc or {}).get("label") or "")
                                new_lbl = (
                                    email
                                    if (email and cur_lbl.startswith(("Google Flow", "Flow Account", "Flow_Acc")))
                                    else (cur_lbl or email or f"Flow #{acc_id}")
                                )
                                proj_u = cur_url if "/project/" in cur_url else str((raw_acc or {}).get("project_url") or FLOW_HOME_URL)
                                database.update_flow_account(
                                    acc_id,
                                    label=new_lbl[:80],
                                    email=email or str((raw_acc or {}).get("email") or ""),
                                    cookies_json=json.dumps(google_cookies, ensure_ascii=False),
                                    project_url=proj_u,
                                    status="active",
                                    notes=f"Đã đăng nhập Chrome ({len(google_cookies)} cookies) · Tự đóng trình duyệt thành công",
                                )
                                captured_ok = True
                                break

                        if not captured_ok:
                            database.update_flow_account(
                                acc_id,
                                status="expired",
                                notes="Chưa hoàn tất đăng nhập Google Flow trên Chrome.",
                            )
                    except Exception as exc:
                        database.update_flow_account(
                            acc_id,
                            status="expired",
                            notes=f"Lỗi mở Chrome: {str(exc)[:180]}",
                        )
                    finally:
                        if ctx is not None:
                            try:
                                await ctx.close()
                            except BaseException:
                                pass

            try:
                asyncio.run(_run())
            except Exception:
                pass

        th = threading.Thread(target=_watcher, daemon=True)
        _flow_browser_threads[acc_id] = th
        th.start()

    return {
        "ok": True,
        "account_id": acc_id,
        "message": "Đã mở Google Chrome tới flow.google.com! Anh đăng nhập tài khoản Google xong hệ thống sẽ tự động lấy Cookie & đóng trình duyệt.",
        "account": database.update_flow_account(acc_id),
    }


def open_flow_browser_workspace(account_id: int) -> Dict[str, Any]:
    """Open the persistent Chrome window on flow.google.com for manual inspection/project setup and sync cookies on close."""
    raw_acc = database.get_flow_account(account_id)
    if not raw_acc:
        return {"ok": False, "error": f"Không tìm thấy tài khoản Flow #{account_id}."}
    if not crawler_service.has_playwright():
        return {"ok": False, "error": "Playwright chưa sẵn sàng."}

    profile_dir = str(raw_acc.get("profile_dir") or (FLOW_PROFILES_DIR / f"acc_{account_id}"))
    Path(profile_dir).mkdir(parents=True, exist_ok=True)
    database.update_flow_account(account_id, profile_dir=profile_dir)

    with _flow_lock:
        existing_th = _flow_browser_threads.get(account_id)
        if existing_th and existing_th.is_alive():
            return {"ok": True, "message": "Trình duyệt Chrome của tài khoản này đang mở sẵn."}

        def _workspace_runner() -> None:
            async def _run_ws() -> None:
                from playwright.async_api import async_playwright

                chrome_exe = _chrome_executable()
                launch_kwargs: Dict[str, Any] = {
                    "headless": False,
                    "args": ["--disable-blink-features=AutomationControlled"],
                    "viewport": {"width": 1360, "height": 880},
                }
                if chrome_exe:
                    launch_kwargs["executable_path"] = chrome_exe
                if raw_acc.get("proxy"):
                    launch_kwargs["proxy"] = {"server": str(raw_acc["proxy"])}

                async with async_playwright() as p:
                    ctx = None
                    try:
                        ctx = await p.chromium.launch_persistent_context(profile_dir, **launch_kwargs)
                        live_c = await ctx.cookies()
                        if raw_acc.get("cookies_json") and not _has_google_auth_cookies(live_c):
                            try:
                                c_arr = json.loads(raw_acc["cookies_json"])
                                if isinstance(c_arr, list) and c_arr:
                                    await ctx.add_cookies(c_arr)
                            except Exception:
                                pass
                        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
                        target_u = str(raw_acc.get("project_url") or FLOW_HOME_URL)
                        await page.goto(target_u, wait_until="domcontentloaded", timeout=30000)

                        # Keep open until user closes window (up to 15 mins) and periodically sync cookies/project URL
                        deadline = time.monotonic() + 900.0
                        last_proj = target_u
                        while time.monotonic() < deadline:
                            await asyncio.sleep(3.0)
                            if not ctx.pages:
                                break
                            try:
                                u = ctx.pages[-1].url or ""
                                if "flow.google.com" in u and "/project/" in u:
                                    last_proj = u
                                c_now = await ctx.cookies()
                                if _has_google_auth_cookies(c_now):
                                    g_c = [c for c in c_now if "google.com" in str(c.get("domain") or "")]
                                    database.update_flow_account(
                                        account_id,
                                        cookies_json=json.dumps(g_c, ensure_ascii=False),
                                        project_url=last_proj,
                                        status="active",
                                    )
                            except Exception:
                                break
                    finally:
                        if ctx is not None:
                            try:
                                await ctx.close()
                            except BaseException:
                                pass

            try:
                asyncio.run(_run_ws())
            except Exception:
                pass

        th = threading.Thread(target=_workspace_runner, daemon=True)
        _flow_browser_threads[account_id] = th
        th.start()

    return {
        "ok": True,
        "message": "Đã mở trình duyệt Google Flow của tài khoản! Mọi thay đổi Project / Cookie sẽ tự lưu lại.",
    }


def verify_flow_account(account_id: int) -> Dict[str, Any]:
    """Live-check whether a Google Flow account's cookies / Chrome profile / Bearer / Gemini API key is valid."""
    raw_acc = database.get_flow_account(account_id)
    if not raw_acc:
        return {"ok": False, "error": f"Không tìm thấy tài khoản #{account_id}."}

    mode = str(raw_acc.get("auth_mode") or "browser_profile")
    bearer = str(raw_acc.get("bearer_token") or "").strip()

    # 1. Official Gemini / Veo API Key
    if mode == "gemini_api_key" or bearer.startswith("AIza"):
        try:
            r = httpx.get(f"{GEMINI_API_BASE}/models?key={bearer}", timeout=12.0)
            if r.status_code == 200:
                models = [str(m.get("name") or "") for m in (r.json().get("models") or [])]
                veo_models = [m.replace("models/", "") for m in models if "veo" in m.lower()]
                note = f"Gemini Key hợp lệ · {len(veo_models)} model Veo ({', '.join(veo_models[:2]) or 'sẵn sàng'})"
                pub = database.update_flow_account(account_id, status="active", auth_mode="gemini_api_key", notes=note)
                return {"ok": True, "status": "active", "message": note, "account": pub}
            err_msg = f"API Key bị từ chối (HTTP {r.status_code})"
            pub = database.update_flow_account(account_id, status="expired", notes=err_msg)
            return {"ok": False, "status": "expired", "message": err_msg, "account": pub}
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:180]}

    # 2. Google OAuth Bearer Token
    if mode == "bearer_token" or bearer.startswith("ya29."):
        try:
            r = httpx.get(f"https://oauth2.googleapis.com/tokeninfo?access_token={bearer}", timeout=10.0)
            if r.status_code == 200:
                info = r.json()
                email = str(info.get("email") or raw_acc.get("email") or "")
                exp = int(info.get("expires_in") or 0)
                note = f"Bearer Token hợp lệ (còn {exp // 60} phút){f' · {email}' if email else ''}"
                pub = database.update_flow_account(account_id, email=email, status="active", notes=note)
                return {"ok": True, "status": "active", "message": note, "account": pub}
            note = "Bearer Token đã hết hạn — vui lòng lấy lại hoặc dùng chế độ Đăng nhập Chrome."
            pub = database.update_flow_account(account_id, status="expired", notes=note)
            return {"ok": False, "status": "expired", "message": note, "account": pub}
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:180]}

    # 3. Browser Profile / Google Cookies check on https://flow.google.com/
    if not crawler_service.has_playwright():
        return {"ok": False, "error": "Cần Playwright để kiểm tra phiên Cookie Google Flow."}

    async def _check_browser() -> Tuple[bool, str, str, List[Dict[str, Any]]]:
        from playwright.async_api import async_playwright

        chrome_exe = _chrome_executable()
        launch_kwargs: Dict[str, Any] = {
            "headless": True,
            "args": ["--disable-blink-features=AutomationControlled"],
        }
        if chrome_exe:
            launch_kwargs["executable_path"] = chrome_exe
        if raw_acc.get("proxy"):
            launch_kwargs["proxy"] = {"server": str(raw_acc["proxy"])}

        cookies_in: List[Dict[str, Any]] = []
        if raw_acc.get("cookies_json"):
            try:
                cookies_in = json.loads(raw_acc["cookies_json"])
            except Exception:
                cookies_in = []

        prof_dir = str(raw_acc.get("profile_dir") or "")
        async with async_playwright() as p:
            browser = None
            ctx = None
            try:
                used_persistent = False
                if prof_dir and Path(prof_dir).exists():
                    ctx = await p.chromium.launch_persistent_context(prof_dir, **launch_kwargs)
                    used_persistent = True
                else:
                    browser = await p.chromium.launch(**launch_kwargs)
                    ctx = await browser.new_context()
                if cookies_in and (not used_persistent or not _has_google_auth_cookies(await ctx.cookies())):
                    await ctx.add_cookies(cookies_in)
                page = ctx.pages[0] if ctx.pages else await ctx.new_page()
                await page.goto(FLOW_HOME_URL, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(2200)
                cur_u = page.url or ""
                c_out = await ctx.cookies()
                g_cookies = [c for c in c_out if "google.com" in str(c.get("domain") or "")]
                html = await page.content()
                is_authed, email = _is_flow_page_authenticated(cur_u, html, g_cookies)
                if not is_authed:
                    return False, "", "Phiên Google Flow chưa đăng nhập hoặc Cookie đã hết hạn.", g_cookies
                return True, email, f"Phiên flow.google.com hoạt động tốt ({len(g_cookies)} cookies){f' · {email}' if email else ''}", g_cookies
            finally:
                for closer in (ctx, browser):
                    if closer is not None:
                        try:
                            await closer.close()
                        except BaseException:
                            pass

    try:
        ok, email, msg, g_cookies = asyncio.run(_check_browser())
    except Exception as exc:
        return {"ok": False, "error": f"Không thể mở phiên kiểm tra (có thể Chrome của acc này đang mở): {str(exc)[:160]}"}

    upd_fields: Dict[str, Any] = {
        "status": "active" if ok else "expired",
        "notes": msg[:280],
    }
    if email:
        upd_fields["email"] = email
    if ok and g_cookies:
        upd_fields["cookies_json"] = json.dumps(g_cookies, ensure_ascii=False)
    pub = database.update_flow_account(account_id, **upd_fields)
    return {"ok": ok, "status": "active" if ok else "expired", "message": msg, "account": pub}


def acquire_flow_account(preferred_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Reserve either a user-selected Flow account or rotate to the healthiest active Flow account."""
    with database.get_conn() as conn:
        if preferred_id and preferred_id > 0:
            row = conn.execute("SELECT * FROM flow_accounts WHERE id = ?", (preferred_id,)).fetchone()
        else:
            row = conn.execute(
                """
                SELECT * FROM flow_accounts
                WHERE status = 'active'
                  AND renders_used < weekly_limit
                  AND credits_remaining > 0
                ORDER BY last_used_at ASC, renders_used ASC, id ASC
                LIMIT 1
                """
            ).fetchone()
        if not row:
            return None
        acc = dict(row)
        if acc.get("status") != "active":
            return None
        credit_cost = 20
        new_credits = max(0, int(acc.get("credits_remaining") or 1000) - credit_cost)
        new_renders = int(acc.get("renders_used") or 0) + 1
        next_status = "cooldown" if new_renders >= int(acc.get("weekly_limit") or 50) else "active"
        conn.execute(
            """
            UPDATE flow_accounts
            SET credits_remaining = ?, renders_used = ?, status = ?, last_used_at = ?
            WHERE id = ?
            """,
            (new_credits, new_renders, next_status, database.utc_now_iso(), acc["id"]),
        )
        acc["credits_spent_now"] = credit_cost
        return acc


def extract_reference_frame_for_video(video_id: int, ffmpeg_bin: Optional[str]) -> str:
    """Extract the cleanest unobstructed, text-free 9:16 720x1280 product Ingredient image (using Vision-selected shot, frame_pos, and clean_crop_box_pct)."""
    video = database.get_video(video_id)
    if not video or not ffmpeg_bin:
        return ""

    local_mp4 = str(video.get("local_path") or "").strip()
    if not local_mp4 or not Path(local_mp4).is_file():
        ensured = crawler_service.ensure_video_playable_mp4(video_id)
        if ensured.get("ok") and ensured.get("video"):
            local_mp4 = str(ensured["video"].get("local_path") or "")

    if not local_mp4 or not Path(local_mp4).is_file():
        return ""

    bd = video.get("rea_breakdown") if isinstance(video.get("rea_breakdown"), dict) else {}
    best_idx = int(bd.get("best_clean_shot_index") or 0)
    best_pos = str(bd.get("best_clean_frame_pos") or "first").strip().lower()
    if best_pos not in ("first", "last"):
        best_pos = "first"
    crop_pct = bd.get("clean_crop_box_pct") if isinstance(bd.get("clean_crop_box_pct"), list) else [0.0, 0.0, 100.0, 100.0]
    shots = bd.get("shots") or []

    seek_candidates: List[str] = []
    if best_idx > 0 and shots:
        crop_sig = "_".join(str(int(round(float(x)))) for x in crop_pct[:4]) if len(crop_pct) == 4 else "0_0_100_100"
        out_jpg = FLOW_REFS_DIR / f"video_{video_id}_s{best_idx}_{best_pos}_{crop_sig}_ref.jpg"
        if out_jpg.exists() and out_jpg.stat().st_size > 5000:
            return str(out_jpg)

        shots_dir = MEDIA_DIR / "rea_outputs" / f"video_{video_id}" / "shots"
        cand_frames = [
            shots_dir / f"shot_{best_idx:03d}_{best_pos}.jpg",
            shots_dir / f"shot_{best_idx:03d}_first.jpg",
            shots_dir / f"shot_{best_idx:03d}_last.jpg",
        ]
        rea_src_jpg = next((p for p in cand_frames if p.is_file() and p.stat().st_size > 4000), None)
        if rea_src_jpg is not None:
            try:
                from PIL import Image

                im = Image.open(rea_src_jpg).convert("RGB")
                if len(crop_pct) == 4 and [round(float(x)) for x in crop_pct] != [0, 0, 100, 100]:
                    w, h = im.size
                    x1 = int(round(w * max(0.0, min(90.0, float(crop_pct[0]))) / 100.0))
                    y1 = int(round(h * max(0.0, min(90.0, float(crop_pct[1]))) / 100.0))
                    x2 = int(round(w * max(10.0, min(100.0, float(crop_pct[2]))) / 100.0))
                    y2 = int(round(h * max(10.0, min(100.0, float(crop_pct[3]))) / 100.0))
                    if x2 - x1 >= int(w * 0.35) and y2 - y1 >= int(h * 0.35):
                        im = im.crop((x1, y1, x2, y2))
                tmp_crop = FLOW_REFS_DIR / f"_tmp_crop_{video_id}.jpg"
                im.save(tmp_crop, format="JPEG", quality=92)
                cmd_img = [
                    ffmpeg_bin,
                    "-y",
                    "-i",
                    str(tmp_crop),
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280",
                    "-q:v",
                    "2",
                    str(out_jpg),
                ]
                proc_img = subprocess.run(cmd_img, capture_output=True, text=True, timeout=15, env=crawler_service.build_tool_env())
                tmp_crop.unlink(missing_ok=True)
                if proc_img.returncode == 0 and out_jpg.exists() and out_jpg.stat().st_size > 4000:
                    return str(out_jpg)
            except Exception:
                pass

        matched_shot = next((s for s in shots if int(s.get("index") or 0) == best_idx), None)
        if matched_shot:
            t_pick = (
                round(max(0.1, float(matched_shot.get("end") or 1.0) - 0.12), 2)
                if best_pos == "last"
                else round(float(matched_shot.get("start") or 0) + 0.08, 2)
            )
            seek_candidates.append(str(max(0.1, t_pick)))
    else:
        out_jpg = FLOW_REFS_DIR / f"video_{video_id}_clean_ref.jpg"
        if out_jpg.exists() and out_jpg.stat().st_size > 5000:
            return str(out_jpg)

    for fallback_s in ("4.5", "2.5", "1.2", "0.3"):
        if fallback_s not in seek_candidates:
            seek_candidates.append(fallback_s)

    for seek_s in seek_candidates:
        cmd = [
            ffmpeg_bin,
            "-y",
            "-ss",
            seek_s,
            "-i",
            local_mp4,
            "-frames:v",
            "1",
            "-vf",
            "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280",
            "-q:v",
            "3",
            str(out_jpg),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=25, env=crawler_service.build_tool_env())
        if proc.returncode == 0 and out_jpg.exists() and out_jpg.stat().st_size > 4000:
            return str(out_jpg)
    return ""


def _apply_stroke_text_removelogo(
    ffmpeg_bin: Optional[str],
    base_jpg: Path,
    dest_jpg: Path,
    overlay_text_boxes_pct: List[List[float]],
    mask_tag: str = "",
) -> bool:
    """Detect stroked caption glyphs (+ same-row emojis) inside overlay boxes and clean via FFmpeg removelogo."""
    if not base_jpg.is_file():
        return False
    if not overlay_text_boxes_pct:
        dest_jpg.write_bytes(base_jpg.read_bytes())
        return True

    try:
        from PIL import Image, ImageChops, ImageFilter
    except ImportError:
        dest_jpg.write_bytes(base_jpg.read_bytes())
        return True

    tag_safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", mask_tag or dest_jpg.stem)
    mask_png = FLOW_REFS_DIR / f"_tmp_mask_{tag_safe}.png"
    try:
        with Image.open(base_jpg) as raw_im:
            im = raw_im.convert("RGB")
        w_im, h_im = im.size
        full_mask = Image.new("L", im.size, 0)

        for box in (overlay_text_boxes_pct or [])[:8]:
            if not isinstance(box, (list, tuple)) or len(box) != 4:
                continue
            try:
                bx1, by1, bx2, by2 = [float(v) for v in box]
            except (TypeError, ValueError):
                continue
            if not (0.0 <= bx1 < bx2 <= 100.0 and 0.0 <= by1 < by2 <= 100.0):
                continue
            if ((bx2 - bx1) * (by2 - by1) / 10000.0) >= 0.40:
                continue

            px1 = max(4, min(w_im - 4, int(round(bx1 * w_im / 100.0)) - 6))
            py1 = max(4, min(h_im - 4, int(round(by1 * h_im / 100.0)) - 6))
            px2 = max(4, min(w_im - 4, int(round(bx2 * w_im / 100.0)) + 6))
            py2 = max(4, min(h_im - 4, int(round(by2 * h_im / 100.0)) + 6))
            if px2 - px1 < 8 or py2 - py1 < 8:
                continue

            rgb_crop = im.crop((px1, py1, px2, py2))
            g = rgb_crop.convert("L")
            bright = g.point(lambda p: 255 if p >= 210 else 0)
            dark = g.point(lambda p: 255 if p <= 75 else 0)
            dark_near = dark.filter(ImageFilter.MaxFilter(7))
            bright_near = bright.filter(ImageFilter.MaxFilter(7))
            stroked = ImageChops.lighter(
                ImageChops.darker(bright, dark_near),
                ImageChops.darker(dark, bright_near),
            )

            r_ch, g_ch, b_ch = rgb_crop.split()
            max_rgb = ImageChops.lighter(ImageChops.lighter(r_ch, g_ch), b_ch)
            min_rgb = ImageChops.darker(ImageChops.darker(r_ch, g_ch), b_ch)
            sat_mask = ImageChops.subtract(max_rgb, min_rgb).point(lambda p: 255 if p >= 95 else 0)

            crop_w, crop_h = rgb_crop.size
            stroked_bytes = stroked.tobytes()
            sat_bytes = sat_mask.tobytes()
            emoji_buf = bytearray(len(sat_bytes))
            for y in range(crop_h):
                row_off = y * crop_w
                row_end = row_off + crop_w
                if stroked_bytes.count(b"\xff", row_off, row_end) >= 4:
                    emoji_buf[row_off:row_end] = sat_bytes[row_off:row_end]
            emoji_mask = Image.frombytes("L", (crop_w, crop_h), bytes(emoji_buf))

            mask_crop = ImageChops.lighter(stroked, emoji_mask).filter(ImageFilter.MaxFilter(11))
            cur_region = full_mask.crop((px1, py1, px2, py2))
            full_mask.paste(ImageChops.lighter(cur_region, mask_crop), (px1, py1))

        nonzero_px = sum(full_mask.histogram()[1:])
        if full_mask.getbbox() is None or nonzero_px < 80 or not ffmpeg_bin:
            dest_jpg.write_bytes(base_jpg.read_bytes())
            return True

        full_mask.save(mask_png, format="PNG")
        cmd = [
            ffmpeg_bin,
            "-y",
            "-i",
            str(base_jpg),
            "-vf",
            f"removelogo={mask_png}",
            "-q:v",
            "2",
            str(dest_jpg),
        ]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=20, env=crawler_service.build_tool_env()
        )
        if proc.returncode == 0 and dest_jpg.is_file() and dest_jpg.stat().st_size > 3000:
            return True

        dest_jpg.write_bytes(base_jpg.read_bytes())
        return dest_jpg.is_file() and dest_jpg.stat().st_size > 3000
    except Exception:
        dest_jpg.write_bytes(base_jpg.read_bytes())
        return dest_jpg.is_file()
    finally:
        mask_png.unlink(missing_ok=True)


def extract_clean_scene_boundary_frames(
    video_id: int,
    scene_unit: Dict[str, Any],
    overlay_text_boxes_pct: List[List[float]],
    ffmpeg_bin: Optional[str],
) -> Tuple[str, str, str, str]:
    """Extract clean 720x1280 Start & End boundary frames for a Scene Unit using stroke-aware text removelogo."""
    shot_idxs: List[int] = []
    for x in (scene_unit.get("shot_indices") or []):
        try:
            xi = int(x)
            if xi > 0:
                shot_idxs.append(xi)
        except (TypeError, ValueError):
            pass

    first_shot = shot_idxs[0] if shot_idxs else int(scene_unit.get("unit_index") or 1)
    last_shot = shot_idxs[-1] if shot_idxs else first_shot
    u_idx = int(scene_unit.get("unit_index") or first_shot)

    shots_dir = MEDIA_DIR / "rea_outputs" / f"video_{video_id}" / "shots"
    start_rea = shots_dir / f"shot_{first_shot:03d}_first.jpg"
    end_rea = shots_dir / f"shot_{last_shot:03d}_last.jpg"

    start_p = FLOW_REFS_DIR / f"v{video_id}_u{u_idx}_start_v2.jpg"
    end_p = FLOW_REFS_DIR / f"v{video_id}_u{u_idx}_end_v2.jpg"

    video = database.get_video(video_id) or {}
    local_mp4 = str(video.get("local_path") or "").strip()
    if (not local_mp4 or not Path(local_mp4).is_file()) and (not start_rea.is_file() or not end_rea.is_file()):
        ensured = crawler_service.ensure_video_playable_mp4(video_id)
        if ensured.get("ok") and ensured.get("video"):
            local_mp4 = str(ensured["video"].get("local_path") or "")

    st_val = float(scene_unit.get("start") or 0.0)
    en_val = float(scene_unit.get("end") or (st_val + float(scene_unit.get("target_duration") or 4.5)))
    st_seek = round(max(0.05, st_val + 0.08), 2)
    en_seek = round(max(0.2, en_val - 0.12), 2)

    base_vf = "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280"

    def _render_frame(dest_p: Path, rea_jpg: Path, seek_t: float, tag: str) -> str:
        has_rea = rea_jpg.is_file() and rea_jpg.stat().st_size > 2000
        has_mp4 = bool(local_mp4 and Path(local_mp4).is_file())
        tmp_base = FLOW_REFS_DIR / f"_tmp_base_{video_id}_{u_idx}_{tag}.jpg"
        try:
            if not ffmpeg_bin:
                if has_rea:
                    tmp_base.write_bytes(rea_jpg.read_bytes())
                else:
                    return ""
            else:
                src_args = ["-i", str(rea_jpg)] if has_rea else (["-ss", str(seek_t), "-i", local_mp4] if has_mp4 else [])
                if not src_args:
                    return ""
                cmd = [ffmpeg_bin, "-y", *src_args, "-frames:v", "1", "-vf", base_vf, "-q:v", "2", str(tmp_base)]
                proc = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=20, env=crawler_service.build_tool_env()
                )
                if proc.returncode != 0 or not tmp_base.is_file() or tmp_base.stat().st_size <= 3000:
                    return ""

            ok_clean = _apply_stroke_text_removelogo(
                ffmpeg_bin,
                tmp_base,
                dest_p,
                overlay_text_boxes_pct,
                mask_tag=f"{video_id}_{u_idx}_{tag}",
            )
            if ok_clean and dest_p.is_file() and dest_p.stat().st_size > 3000:
                return str(dest_p)
            return ""
        finally:
            tmp_base.unlink(missing_ok=True)

    start_path = _render_frame(start_p, start_rea, st_seek, "start")
    end_path = _render_frame(end_p, end_rea, en_seek, "end")
    start_url = f"/media/flow_refs/{start_p.name}" if start_path else ""
    end_url = f"/media/flow_refs/{end_p.name}" if end_path else ""
    return start_path, end_path, start_url, end_url


def build_flow_scene_plan_for_video(
    video_id: int,
    clone_mode: str = "flow_frames_start_end",
    custom_hint: str = "",
    ffmpeg_bin: Optional[str] = None,
    flow_model: str = "omni_1_2_flash_10s_portrait",
    override_scene_plan: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build a 100% AI-Generated First-Frame -> End-Frame Viral Remake plan grounded in rea-video shots (ZERO source frames uploaded to Google Flow)."""
    video = database.get_video(video_id)
    if not video:
        return {"ok": False, "error": f"Không tìm thấy video #{video_id}."}

    bd = video.get("rea_breakdown") if isinstance(video.get("rea_breakdown"), dict) else {}
    existing_units = bd.get("scene_units") if isinstance(bd.get("scene_units"), list) else []
    has_ai_frame_prompts = any(
        isinstance(u, dict) and str(u.get("ai_start_image_prompt_en") or "").strip()
        for u in existing_units
    )
    if not existing_units or not has_ai_frame_prompts:
        try:
            import muse_service

            if existing_units or (MEDIA_DIR / "rea_outputs" / f"video_{video_id}" / "breakdown.json").is_file():
                upgraded_vid = muse_service.upgrade_rea_scene_units_for_ai_remake(video_id)
                if upgraded_vid:
                    video = upgraded_vid
                    bd = video.get("rea_breakdown") if isinstance(video.get("rea_breakdown"), dict) else {}
            if not bd.get("scene_units"):
                rea_res = muse_service._run_rea_decompose_sync(video_id, force_vlm=False)
                if rea_res.get("ok") and rea_res.get("video"):
                    video = rea_res["video"]
                    bd = video.get("rea_breakdown") if isinstance(video.get("rea_breakdown"), dict) else {}
        except Exception:
            pass

    product_en = str(bd.get("product_en") or "").strip()
    char_style_en = str(bd.get("character_and_room_style_en") or "").strip()
    ai_anchor_prompt = str(bd.get("ai_product_anchor_prompt_en") or "").strip()
    if not ai_anchor_prompt:
        ai_anchor_prompt = (
            f"Vertical 9:16 studio-lit smartphone product photograph of {product_en or 'the sleek modern featured product'}, "
            "resting cleanly in full unobstructed view with crisp natural lighting and realistic material texture. "
            "Photorealistic, NO text overlays, NO subtitles, NO watermarks, NO brand logos."
        )
    raw_units = bd.get("scene_units") if isinstance(bd.get("scene_units"), list) else []

    def _default_ai_start_prompt(idx_s: int, base_motion: str) -> str:
        return (
            f"Vertical 9:16 smartphone photograph recreating the exact opening camera angle of Scene {idx_s}: "
            f"{char_style_en or 'fresh presenter hands and clean modern lighting'} with {product_en or 'the featured product'} "
            f"at the beginning of the action ({base_motion[:180]}). "
            "Photorealistic, clean frame with NO text overlays, NO subtitles, NO watermarks, NO brand logos."
        )

    def _default_ai_end_prompt(base_motion: str) -> str:
        return (
            "Vertical 9:16 smartphone photograph matching the exact same camera angle, background, lighting, and presenter "
            f"from the attached Start Frame image, showing the completed closing state of ({base_motion[:180]}). "
            "Photorealistic, clean frame with NO text overlays, NO subtitles, NO watermarks, NO brand logos."
        )

    # Respect user-customized scene prompts from the UI if valid and non-bait
    usable_override: List[Dict[str, Any]] = []
    if override_scene_plan:
        for idx_o, uo in enumerate(override_scene_plan, start=1):
            if not isinstance(uo, dict):
                continue
            fp_o = str(uo.get("flow_prompt_en") or uo.get("frames_prompt_en") or "").strip()
            if fp_o and not is_stale_or_bait_veo_prompt(fp_o, video):
                st_o = round(float(uo.get("start") or 0.0), 2)
                en_o = round(float(uo.get("end") or (st_o + 4.5)), 2)
                td_o = round(max(2.0, min(7.9, float(uo.get("target_duration") or (en_o - st_o) or 4.5))), 2)
                fr_o = str(uo.get("frames_prompt_en") or fp_o).strip()
                raw_match = raw_units[idx_o - 1] if idx_o - 1 < len(raw_units) and isinstance(raw_units[idx_o - 1], dict) else {}
                ai_s_o = str(uo.get("ai_start_image_prompt_en") or raw_match.get("ai_start_image_prompt_en") or "").strip() or _default_ai_start_prompt(idx_o, fr_o)
                ai_e_o = str(uo.get("ai_end_image_prompt_en") or raw_match.get("ai_end_image_prompt_en") or "").strip() or _default_ai_end_prompt(fr_o)
                reuse_prev_o = (
                    bool(uo.get("reuse_prev_end_as_start"))
                    if "reuse_prev_end_as_start" in uo
                    else bool(raw_match.get("reuse_prev_end_as_start"))
                ) if idx_o > 1 else False
                # Preserve ONLY previously AI-generated frame URLs (never source-video v{id}_u{k}_start screenshots!)
                prev_s_url = str(uo.get("start_frame_url") or "")
                prev_e_url = str(uo.get("end_frame_url") or "")
                usable_override.append(
                    {
                        "unit_index": idx_o,
                        "title_vi": str(uo.get("title_vi") or f"Cảnh {idx_o} ({st_o}s–{en_o}s)"),
                        "shot_indices": list(uo.get("shot_indices") or []),
                        "start": st_o,
                        "end": en_o,
                        "target_duration": td_o,
                        "same_scene_as_prev": bool(uo.get("same_scene_as_prev")) if idx_o > 1 else False,
                        "reuse_prev_end_as_start": reuse_prev_o,
                        "action_vi": str(uo.get("action_vi") or ""),
                        "ai_product_anchor_prompt_en": str(uo.get("ai_product_anchor_prompt_en") or ai_anchor_prompt),
                        "ai_start_image_prompt_en": ai_s_o,
                        "ai_end_image_prompt_en": ai_e_o,
                        "flow_prompt_en": fp_o,
                        "frames_prompt_en": fr_o,
                        "start_frame_url": prev_s_url if "_ai_" in prev_s_url else "",
                        "end_frame_url": prev_e_url if "_ai_" in prev_e_url else "",
                        "ref_url": "",
                    }
                )

    scene_units: List[Dict[str, Any]] = usable_override if usable_override else []
    if not scene_units:
        for idx_u, u in enumerate(raw_units, start=1):
            if not isinstance(u, dict) or not str(u.get("flow_prompt_en") or u.get("frames_prompt_en") or "").strip():
                continue
            st_u = round(float(u.get("start") or 0.0), 2)
            en_u = round(float(u.get("end") or (st_u + 4.5)), 2)
            td_u = round(max(2.0, min(7.9, float(u.get("target_duration") or (en_u - st_u) or 4.5))), 2)
            fp_u = str(u.get("flow_prompt_en") or u.get("frames_prompt_en") or "").strip()
            frames_fp_u = str(u.get("frames_prompt_en") or fp_u).strip()
            ai_s_u = str(u.get("ai_start_image_prompt_en") or "").strip() or _default_ai_start_prompt(idx_u, frames_fp_u)
            ai_e_u = str(u.get("ai_end_image_prompt_en") or "").strip() or _default_ai_end_prompt(frames_fp_u)
            scene_units.append(
                {
                    "unit_index": idx_u,
                    "title_vi": str(u.get("title_vi") or f"Cảnh {idx_u} ({st_u}s–{en_u}s)"),
                    "shot_indices": list(u.get("shot_indices") or []),
                    "start": st_u,
                    "end": en_u,
                    "target_duration": td_u,
                    "same_scene_as_prev": bool(u.get("same_scene_as_prev")) if idx_u > 1 else False,
                    "reuse_prev_end_as_start": bool(u.get("reuse_prev_end_as_start")) if idx_u > 1 else False,
                    "action_vi": str(u.get("action_vi") or ""),
                    "ai_product_anchor_prompt_en": ai_anchor_prompt,
                    "ai_start_image_prompt_en": ai_s_u,
                    "ai_end_image_prompt_en": ai_e_u,
                    "flow_prompt_en": fp_u,
                    "frames_prompt_en": frames_fp_u,
                    "start_frame_url": "",
                    "end_frame_url": "",
                    "ref_url": "",
                }
            )

    # Single-unit fallback if video had no shots
    if not scene_units:
        fallback_p = str(bd.get("veo_prompt_en") or "").strip() or (
            f"Vertical 9:16 smartphone video showcasing {product_en or 'the sleek featured product'} "
            "in a sunlit modern room with natural human hand interaction. Photorealistic, crisp foley sound, clean frame with NO text overlays, NO subtitles, NO watermarks, NO logos."
        )
        dur_v = round(max(4.0, min(7.8, float(bd.get("duration") or 6.5))), 2)
        scene_units = [
            {
                "unit_index": 1,
                "title_vi": f"Cảnh 1 (0.0s–{dur_v}s · Toàn cảnh sản phẩm)",
                "shot_indices": [1],
                "start": 0.0,
                "end": dur_v,
                "target_duration": dur_v,
                "same_scene_as_prev": False,
                "reuse_prev_end_as_start": False,
                "action_vi": "Tự dựng Ảnh Đầu → Cuối mới & trình diễn trực quan sản phẩm",
                "ai_product_anchor_prompt_en": ai_anchor_prompt,
                "ai_start_image_prompt_en": _default_ai_start_prompt(1, fallback_p),
                "ai_end_image_prompt_en": _default_ai_end_prompt(fallback_p),
                "flow_prompt_en": fallback_p,
                "frames_prompt_en": fallback_p,
                "start_frame_url": "",
                "end_frame_url": "",
                "ref_url": "",
            }
        ]

    raw_hint = custom_hint.strip()
    vid_caps = {
        str(video.get("title") or "").strip(),
        str(video.get("hook_text") or "").strip(),
        str(video.get("caption") or "").strip(),
    }
    effective_hint = "" if (not raw_hint or raw_hint in vid_caps) else raw_hint
    if effective_hint and not usable_override:
        for u in scene_units:
            u["flow_prompt_en"] = f"{u['flow_prompt_en']} Styling note: {effective_hint}."
            u["frames_prompt_en"] = f"{u['frames_prompt_en']} Styling note: {effective_hint}."
            u["ai_start_image_prompt_en"] = f"{u['ai_start_image_prompt_en']} Styling note: {effective_hint}."
            u["ai_end_image_prompt_en"] = f"{u['ai_end_image_prompt_en']} Styling note: {effective_hint}."

    for u in scene_units:
        # Strict Zero-Source-Frame-Upload Policy: never attach screenshots from the source video
        u["start_frame_path"] = ""
        u["end_frame_path"] = ""
        if not str(u.get("frames_prompt_en") or "").strip():
            u["frames_prompt_en"] = u["flow_prompt_en"]

    combined_veo_prompt = "\n\n".join(
        f"[{u['title_vi']} · {u['target_duration']}s]\n"
        f"• AI First Frame: {u['ai_start_image_prompt_en']}\n"
        f"• AI End Frame: {u['ai_end_image_prompt_en']}\n"
        f"• Motion Bridge: {u['frames_prompt_en']}"
        for u in scene_units
    )

    return {
        "ok": True,
        "video_id": video_id,
        "product_en": product_en,
        "ai_product_anchor_prompt_en": ai_anchor_prompt,
        "veo_prompt": combined_veo_prompt,
        "scene_units": scene_units,
        "reference_frame_url": "",
        "reference_frame_path": "",
    }


def generate_veo_prompt_for_video(
    video_id: int,
    clone_mode: str = "flow_omni_ingredients",
    custom_hint: str = "",
    ffmpeg_bin: Optional[str] = None,
    flow_model: str = "omni_1_2_flash_10s_portrait",
) -> Dict[str, Any]:
    """Generate both the per-scene Google Flow execution plan (`scene_units`) and summary `veo_prompt` from rea-video."""
    return build_flow_scene_plan_for_video(
        video_id=video_id,
        clone_mode=clone_mode,
        custom_hint=custom_hint,
        ffmpeg_bin=ffmpeg_bin,
        flow_model=flow_model,
    )


def is_stale_or_bait_veo_prompt(veo_prompt: str, video: Dict[str, Any]) -> bool:
    """Detect if a saved veo_prompt was generated from engagement-bait captions or mismatches the Vision-identified product."""
    vp = (veo_prompt or "").strip().lower()
    if not vp:
        return True
    if any(b in vp for b in ("for the link", "link in bio", "comment \"", "comment “", "🔗")):
        return True
    bd = video.get("rea_breakdown") if isinstance(video.get("rea_breakdown"), dict) else {}
    vision_prod = str(bd.get("product_en") or "").strip().lower()
    if vision_prod:
        stop_words = {
            "with", "from", "that", "this", "compact", "modern", "portable", "small", "mini",
            "shape", "rounded", "corners", "front", "back", "side", "item", "product", "object",
        }
        keywords = [w for w in re.findall(r"[a-z]{4,}", vision_prod) if w not in stop_words]
        if keywords and not any(kw in vp for kw in keywords[:6]):
            return True
    return False


def _is_valid_video_bytes(head: bytes) -> bool:
    if not head or len(head) < 12:
        return False
    # ISO BMFF MP4 / MOV ('ftyp' box) or Matroska / WebM EBML header
    return (b"ftyp" in head[:36]) or head.startswith(b"\x1a\x45\xdf\xa3")


def _find_video_url_recursive(obj: Any) -> str:
    if isinstance(obj, dict):
        for k in ("fifeUrl", "videoUrl", "downloadUri", "uri", "signedUri"):
            v = obj.get(k)
            if isinstance(v, str) and v.startswith("http") and ("image" not in k.lower()):
                return v
        for v in obj.values():
            found = _find_video_url_recursive(v)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_video_url_recursive(item)
            if found:
                return found
    return ""


def _download_binary_video(url: str, dest_mp4: Path, headers: Optional[Dict[str, str]] = None) -> bool:
    cmd = ["curl", "-sL", "--max-time", "90", "-o", str(dest_mp4)]
    for hk, hv in (headers or {}).items():
        cmd.extend(["-H", f"{hk}: {hv}"])
    cmd.append(url)
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=95)
    if proc.returncode == 0 and dest_mp4.exists() and dest_mp4.stat().st_size > 20_000:
        with dest_mp4.open("rb") as f_chk:
            head = f_chk.read(48)
        if _is_valid_video_bytes(head):
            return True
        dest_mp4.unlink(missing_ok=True)
    return False


def _generate_via_gemini_veo_api(
    api_key: str,
    prompt: str,
    flow_model: str,
    clone_mode: str,
    ref_frame_path: str,
    dest_mp4: Path,
    on_progress: Optional[Callable[[int], None]] = None,
) -> Tuple[bool, str]:
    model_map = {m["id"]: m["gemini_model"] for m in get_all_flow_models()}
    gem_model = model_map.get(flow_model) or (flow_model if flow_model.startswith("veo-") else "veo-3.0-generate-preview")

    instance: Dict[str, Any] = {"prompt": prompt}
    if (
        clone_mode in ("flow_veo_i2v", "flow_omni_ingredients", "flow_frames_start_end", "flow_agent_auto", "flow_agent")
        and ref_frame_path
        and Path(ref_frame_path).is_file()
    ):
        b64_img = base64.b64encode(Path(ref_frame_path).read_bytes()).decode("ascii")
        instance["image"] = {"bytesBase64Encoded": b64_img, "mimeType": "image/jpeg"}

    payload = {
        "instances": [instance],
        "parameters": {
            "aspectRatio": "9:16",
            "sampleCount": 1,
        },
    }

    r = httpx.post(
        f"{GEMINI_API_BASE}/models/{gem_model}:predictLongRunning?key={api_key}",
        json=payload,
        timeout=30.0,
    )
    if r.status_code >= 400:
        return False, f"Gemini Veo API từ chối yêu cầu (HTTP {r.status_code}): {r.text[:220]}"

    op_name = str(r.json().get("name") or "").strip()
    if not op_name:
        return False, f"Gemini Veo không trả về operation ID: {r.text[:200]}"

    deadline = time.monotonic() + 210.0
    step = 0
    while time.monotonic() < deadline:
        time.sleep(6.0)
        step += 1
        if on_progress:
            on_progress(min(82, 42 + step * 4))
        pr = httpx.get(f"{GEMINI_API_BASE}/{op_name}?key={api_key}", timeout=20.0)
        if pr.status_code >= 400:
            continue
        pdata = pr.json()
        if pdata.get("error"):
            return False, f"Lỗi render Veo: {json.dumps(pdata['error'], ensure_ascii=False)[:220]}"
        if pdata.get("done"):
            vid_uri = _find_video_url_recursive(pdata.get("response") or pdata)
            if not vid_uri:
                return False, "Veo báo hoàn tất nhưng không tìm thấy URI video trong phản hồi."
            dl_u = f"{vid_uri}{'&' if '?' in vid_uri else '?'}key={api_key}" if "generativelanguage" in vid_uri and "key=" not in vid_uri else vid_uri
            if _download_binary_video(dl_u, dest_mp4):
                return True, ""
            return False, "Không tải được file MP4 từ URI của Gemini Veo."
    return False, "Quá thời gian chờ (210s) khi render video trên Gemini Veo API."


def _generate_via_aisandbox_bearer(
    bearer_token: str,
    project_url: str,
    prompt: str,
    flow_model: str,
    clone_mode: str,
    ref_frame_path: str,
    dest_mp4: Path,
    on_progress: Optional[Callable[[int], None]] = None,
) -> Tuple[bool, str]:
    proj_m = re.search(r"/project/([0-9a-fA-F-]{8,})", project_url or "")
    project_id = proj_m.group(1) if proj_m else ""
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
        "Origin": "https://flow.google.com",
        "Referer": "https://flow.google.com/",
    }
    seed = random.randint(100000, 999999)
    session_id = f";{int(time.time() * 1000)}"
    client_ctx: Dict[str, Any] = {"sessionId": session_id, "tool": "PINHOLE"}
    if project_id:
        client_ctx["projectId"] = project_id

    endpoint = f"{AISANDBOX_BASE}/video:batchAsyncGenerateVideoText"
    req_item: Dict[str, Any] = {
        "aspectRatio": "VIDEO_ASPECT_RATIO_PORTRAIT",
        "seed": seed,
        "textInput": {"prompt": prompt},
        "videoModelKey": flow_model or "veo_3_1_t2v_fast_portrait",
    }

    if (
        clone_mode in ("flow_veo_i2v", "flow_omni_ingredients", "flow_frames_start_end", "flow_agent_auto", "flow_agent")
        and ref_frame_path
        and Path(ref_frame_path).is_file()
    ):
        b64_img = base64.b64encode(Path(ref_frame_path).read_bytes()).decode("ascii")
        up_resp = httpx.post(
            f"{AISANDBOX_BASE}:uploadUserImage",
            headers=headers,
            json={
                "imageInput": {
                    "rawImageBytes": b64_img,
                    "mimeType": "image/jpeg",
                    "isUserUploaded": True,
                },
                "clientContext": client_ctx,
            },
            timeout=25.0,
        )
        if up_resp.status_code == 200:
            media_id = (
                ((up_resp.json().get("mediaGenerationId") or {}).get("mediaGenerationId"))
                or up_resp.json().get("mediaId")
            )
            if media_id:
                endpoint = f"{AISANDBOX_BASE}/video:batchAsyncGenerateVideoStartImage"
                i2v_model = flow_model.replace("_t2v_", "_i2v_s_") if "_t2v_" in flow_model else "veo_3_1_i2v_s_fast_portrait"
                req_item["videoModelKey"] = i2v_model
                req_item["startImage"] = {"mediaId": media_id}

    r = httpx.post(endpoint, headers=headers, json={"clientContext": client_ctx, "requests": [req_item]}, timeout=30.0)
    if r.status_code >= 400:
        return False, f"aisandbox-pa từ chối yêu cầu (HTTP {r.status_code}): {r.text[:240]}"

    resp_json = r.json()
    ops = resp_json.get("operations") or resp_json.get("media") or []
    if not ops:
        direct_u = _find_video_url_recursive(resp_json)
        if direct_u and _download_binary_video(direct_u, dest_mp4, headers={"Authorization": f"Bearer {bearer_token}"}):
            return True, ""
        return False, f"Flow API không trả về tiến trình render: {r.text[:220]}"

    deadline = time.monotonic() + 210.0
    step = 0
    while time.monotonic() < deadline:
        time.sleep(5.5)
        step += 1
        if on_progress:
            on_progress(min(82, 42 + step * 4))
        chk = httpx.post(
            f"{AISANDBOX_BASE}/video:batchCheckAsyncVideoGenerationStatus",
            headers=headers,
            json={"operations": ops},
            timeout=20.0,
        )
        if chk.status_code >= 400:
            continue
        cdata = chk.json()
        dump_str = json.dumps(cdata)
        if "MEDIA_GENERATION_STATUS_FAILED" in dump_str:
            return False, f"Google Flow báo render thất bại: {dump_str[:240]}"
        if "MEDIA_GENERATION_STATUS_SUCCESSFUL" in dump_str or "fifeUrl" in dump_str:
            vid_u = _find_video_url_recursive(cdata)
            if vid_u and _download_binary_video(vid_u, dest_mp4):
                return True, ""
    return False, "Quá thời gian chờ (210s) khi đợi video từ Google Flow API."


def _probe_video_meta_ffmpeg(ffmpeg_bin: Optional[str], media_path: Path) -> Tuple[float, bool, int, int]:
    """Return (duration_s, has_audio, width, height) using `ffmpeg -i` stderr (no ffprobe binary required)."""
    if not ffmpeg_bin or not media_path.is_file():
        return 0.0, False, 0, 0
    try:
        proc = subprocess.run(
            [ffmpeg_bin, "-hide_banner", "-i", str(media_path)],
            capture_output=True,
            text=True,
            timeout=15,
            env=crawler_service.build_tool_env(),
            encoding="utf-8",
            errors="replace",
        )
        info = (proc.stderr or "") + "\n" + (proc.stdout or "")
        dur = 0.0
        m_d = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", info)
        if m_d:
            dur = int(m_d.group(1)) * 3600 + int(m_d.group(2)) * 60 + float(m_d.group(3))
        has_aud = bool(re.search(r"Stream\s+#\d+:\d+.*Audio:", info))
        width, height = 0, 0
        m_v = re.search(r"Stream\s+#\d+:\d+[^\n]*Video:([^\n]+)", info)
        if m_v:
            m_dim = re.search(r"(?:^|[\s,])(\d{2,5})x(\d{2,5})(?=[\s,\[\]]|$)", m_v.group(1))
            if m_dim:
                width = int(m_dim.group(1))
                height = int(m_dim.group(2))
        return round(dur, 3), has_aud, width, height
    except Exception:
        return 0.0, False, 0, 0


def _probe_media_info_ffmpeg(ffmpeg_bin: Optional[str], media_path: Path) -> Tuple[float, bool]:
    """Return (duration_seconds, has_audio_stream) using `ffmpeg -i` stderr (no ffprobe binary required)."""
    if not ffmpeg_bin or not media_path.is_file():
        return 8.0, True
    dur, has_aud, _, _ = _probe_video_meta_ffmpeg(ffmpeg_bin, media_path)
    return (max(0.5, dur) if dur > 0 else 8.0), has_aud


def _trim_and_normalize_scene_clip(
    ffmpeg_bin: Optional[str],
    raw_mp4: Path,
    out_mp4: Path,
    target_duration: float,
    use_time_scale: bool = False,
) -> bool:
    """Trim (or time-scale when use_time_scale=True) a Flow clip to exact scene duration at 720x1280 24fps H.264/AAC."""
    if not raw_mp4.is_file():
        return False
    if not ffmpeg_bin:
        out_mp4.write_bytes(raw_mp4.read_bytes())
        return True

    actual_dur, has_audio = _probe_media_info_ffmpeg(ffmpeg_bin, raw_mp4)
    td_raw = float(target_duration or actual_dur)
    vf = "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,fps=24,format=yuv420p"

    speed = 1.0
    if use_time_scale and actual_dur > td_raw + 0.25:
        speed = min(2.0, max(1.0, actual_dur / max(1.8, td_raw)))
        vf = f"setpts={round(1.0 / speed, 5)}*PTS,{vf}"
        clip_dur = round(max(1.0, td_raw), 2)
    else:
        clip_dur = round(min(actual_dur, max(1.8, td_raw)), 2)

    fade_st = round(max(0.08, clip_dur - 0.14), 2)

    if has_audio:
        af_prefix = f"atempo={round(speed, 4)}," if speed > 1.0001 else ""
        af = (
            f"{af_prefix}aresample=48000,aformat=sample_rates=48000:channel_layouts=stereo,"
            f"afade=t=in:st=0:d=0.08,afade=t=out:st={fade_st}:d=0.14"
        )
        cmd = [
            ffmpeg_bin,
            "-y",
            "-i",
            str(raw_mp4),
            "-t",
            str(clip_dur),
            "-vf",
            vf,
            "-af",
            af,
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "19",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(out_mp4),
        ]
    else:
        cmd = [
            ffmpeg_bin,
            "-y",
            "-i",
            str(raw_mp4),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-t",
            str(clip_dur),
            "-vf",
            vf,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "19",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-b:a",
            "128k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(out_mp4),
        ]

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
        env=crawler_service.build_tool_env(),
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode == 0 and out_mp4.is_file() and out_mp4.stat().st_size > 15_000:
        return True
    out_mp4.write_bytes(raw_mp4.read_bytes())
    return out_mp4.is_file()


def _extract_clean_continuity_frame(
    ffmpeg_bin: Optional[str],
    scene_mp4: Path,
    dest_jpg: Path,
    target_duration: float,
) -> str:
    """Extract the clean ending frame of a generated scene clip so the next continuous scene keeps identical desk/hands/lighting."""
    if not ffmpeg_bin or not scene_mp4.is_file():
        return ""
    actual_dur, _ = _probe_media_info_ffmpeg(ffmpeg_bin, scene_mp4)
    seek_t = round(max(0.3, min(actual_dur - 0.25, float(target_duration or actual_dur) - 0.18)), 2)
    cmd = [
        ffmpeg_bin,
        "-y",
        "-ss",
        str(seek_t),
        "-i",
        str(scene_mp4),
        "-frames:v",
        "1",
        "-vf",
        "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280",
        "-q:v",
        "2",
        str(dest_jpg),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15, env=crawler_service.build_tool_env())
    if proc.returncode == 0 and dest_jpg.is_file() and dest_jpg.stat().st_size > 4000:
        return str(dest_jpg)
    return ""


def _stitch_scene_clips_ffmpeg(
    ffmpeg_bin: Optional[str],
    scene_clips: List[Path],
    dest_mp4: Path,
) -> Tuple[bool, str]:
    """Concatenate normalized per-scene clips into a single seamless 9:16 MP4 with frame-accurate timestamps & smooth Foley audio."""
    valid_clips = [p for p in scene_clips if p.is_file() and p.stat().st_size > 15_000]
    if not valid_clips:
        return False, "Không có clip cảnh thành phần nào hợp lệ để ghép video."
    if len(valid_clips) == 1 or not ffmpeg_bin:
        dest_mp4.write_bytes(valid_clips[0].read_bytes())
        return True, ""

    concat_txt = OUTPUTS_DIR / f"_concat_{dest_mp4.stem}_{int(time.time() * 1000)}.txt"
    try:
        lines = []
        for cp in valid_clips:
            escaped = str(cp.resolve()).replace("'", "'\\''")
            lines.append(f"file '{escaped}'")
        concat_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

        cmd = [
            ffmpeg_bin,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_txt),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "19",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(dest_mp4),
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=95,
            env=crawler_service.build_tool_env(),
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode == 0 and dest_mp4.is_file() and dest_mp4.stat().st_size > 20_000:
            return True, ""
        return False, (proc.stderr or "FFmpeg concat failed")[-320:]
    finally:
        concat_txt.unlink(missing_ok=True)


@dataclass
class _FlowBrowserSession:
    """Shared Playwright browser session state, network hooks, and deduplicated video capture helpers."""

    ctx: Any
    page: Any
    acc_id: int
    pending_video_urls: List[str] = field(default_factory=list)
    consumed_video_urls: set = field(default_factory=set)
    downloaded_hashes: set = field(default_factory=set)
    api_error_messages: List[str] = field(default_factory=list)
    known_asb_tokens: set = field(default_factory=set)
    consumed_tile_srcs: set = field(default_factory=set)
    generation_submitted: bool = False
    error: str = ""

    def register_saved_file(self, out_file: Path) -> bool:
        """Verify non-empty valid video bytes and deduplicate via SHA-256 across the session."""
        if not out_file.is_file() or out_file.stat().st_size <= 20_000:
            out_file.unlink(missing_ok=True)
            return False
        data = out_file.read_bytes()
        if not _is_valid_video_bytes(data[:48]):
            out_file.unlink(missing_ok=True)
            return False
        digest = hashlib.sha256(data).hexdigest()
        if digest in self.downloaded_hashes:
            out_file.unlink(missing_ok=True)
            return False
        self.downloaded_hashes.add(digest)
        return True

    async def try_save_video_to(self, vid_url: str, out_file: Path) -> bool:
        if not vid_url or not vid_url.startswith("http") or vid_url in self.consumed_video_urls:
            return False
        try:
            resp_dl = await self.ctx.request.get(vid_url, timeout=60000)
            if resp_dl.ok:
                body_bytes = await resp_dl.body()
                if len(body_bytes) > 20_000 and _is_valid_video_bytes(body_bytes[:48]):
                    out_file.write_bytes(body_bytes)
                    self.consumed_video_urls.add(vid_url)
                    return self.register_saved_file(out_file)
        except Exception:
            pass
        if _download_binary_video(vid_url, out_file):
            self.consumed_video_urls.add(vid_url)
            return self.register_saved_file(out_file)
        return False

    async def snapshot_existing_media(self) -> None:
        html_pre = await self.page.content()
        for m_tok in re.findall(r"/asb/([A-Za-z0-9_-]{20,})", html_pre):
            self.known_asb_tokens.add(m_tok)
        cur_thumb_srcs = set(
            await self.page.eval_on_selector_all(
                "flow-video-tile img.thumbnail, flow-video-tile img",
                "els => els.map(i => i.currentSrc || i.src || '').filter(Boolean)",
            )
        )
        self.consumed_tile_srcs.update(cur_thumb_srcs)
        for s_u in cur_thumb_srcs:
            for m_tok in re.findall(r"/asb/([A-Za-z0-9_-]{20,})", s_u):
                self.known_asb_tokens.add(m_tok)
        pre_vid_srcs = set(
            await self.page.eval_on_selector_all(
                "video", "els => els.map(v => v.currentSrc || v.src || '').filter(Boolean)"
            )
        )
        self.consumed_video_urls.update(s for s in pre_vid_srcs if s.startswith("http"))

    async def check_errors(self) -> Optional[str]:
        if self.api_error_messages:
            return self.api_error_messages[-1]
        alert_loc = self.page.locator(
            "mat-snack-bar-container:visible, simple-snack-bar:visible, [role='alert']:visible"
        ).first
        if await alert_loc.count() > 0:
            try:
                alert_txt = (await alert_loc.inner_text(timeout=1500)).strip()
                low_a = alert_txt.lower()
                if any(
                    k in low_a
                    for k in ("không thể", "lỗi", "tín dụng", "credit", "violat", "unable", "failed", "quota", "limit")
                ):
                    return alert_txt[:220]
            except Exception:
                pass
        return None


async def _dismiss_overlays(pg: Any) -> None:
    for _ in range(4):
        bd = pg.locator(".cdk-overlay-backdrop-showing")
        open_pop = pg.locator(
            '.cdk-overlay-container button.asset-item:visible, '
            '.cdk-overlay-container [role="menu"]:visible, '
            '.cdk-overlay-container button.sidebar-upload-btn:visible'
        )
        if await bd.count() == 0 and await open_pop.count() == 0:
            break
        try:
            await pg.keyboard.press("Escape")
            await pg.wait_for_timeout(280)
            if await bd.count() > 0:
                await bd.first.click(force=True, timeout=1800)
                await pg.wait_for_timeout(240)
            elif await open_pop.count() > 0:
                await pg.mouse.click(8, 8)
                await pg.wait_for_timeout(260)
        except Exception:
            break


async def _close_preview_modals(pg: Any) -> None:
    await _dismiss_overlays(pg)
    for _ in range(2):
        close_p = pg.locator(
            'mat-dialog-container button[aria-label*="Đóng"]:visible, '
            'mat-dialog-container button[aria-label*="Close"]:visible, '
            'button[aria-label="Quay lại"]:visible, '
            'button[aria-label="Back"]:visible'
        ).first
        if await close_p.count() > 0:
            try:
                await close_p.click(timeout=2000)
                await pg.wait_for_timeout(350)
            except Exception:
                break
        else:
            break
    await pg.keyboard.press("Escape")
    await pg.wait_for_timeout(250)


async def _turn_agent_mode(pg: Any, want_on: bool) -> None:
    """Toggle Creative Agent ('Tác nhân Flow') ON or OFF using verified Nov 22 flow.google.com selectors."""
    if want_on:
        agent_cfg = pg.locator(
            'button[aria-label="Cài đặt tác nhân"]:visible, button.agent-action-button:visible'
        ).first
        if await agent_cfg.count() > 0:
            return
        sw = pg.locator(
            'button.switch[aria-label*="Tác nhân"]:visible, button.switch[aria-label*="Flow Agent"]:visible'
        ).first
        if await sw.count() > 0:
            try:
                cls = ((await sw.get_attribute("class")) or "").lower()
                if not re.search(r"(?:^|[\s_-])checked(?:$|[\s_-])", cls):
                    await sw.click(timeout=3000)
                    await pg.wait_for_timeout(600)
            except Exception:
                pass
        return

    close_drawer = pg.locator('button[aria-label="Đóng"]:visible, button[aria-label="Close"]:visible').first
    if await close_drawer.count() > 0:
        try:
            await close_drawer.click(timeout=3000)
            await pg.wait_for_timeout(500)
        except Exception:
            pass

    sw = pg.locator(
        'button.switch[aria-label*="Tác nhân"]:visible, button.switch[aria-label*="Flow Agent"]:visible'
    ).first
    if await sw.count() > 0:
        try:
            cls = ((await sw.get_attribute("class")) or "").lower()
            txt = ((await sw.inner_text()) or "").lower()
            has_checked = bool(re.search(r"(?:^|[\s_-])checked(?:$|[\s_-])", cls))
            if has_checked or ("spark_off" not in txt):
                await sw.click(timeout=3000)
                await pg.wait_for_timeout(550)
        except Exception:
            pass

    agent_chip = pg.locator(".agent-mode-chip-checked:visible").first
    if await agent_chip.count() > 0:
        try:
            await agent_chip.click(timeout=3000)
            await pg.wait_for_timeout(500)
        except Exception:
            pass


def _resolve_studio_model_keywords(flow_model: str) -> Tuple[str, List[str]]:
    model_meta = next((m for m in get_all_flow_models() if m["id"] == flow_model), None)
    studio_model_name = str(
        (model_meta or {}).get("flow_studio_model")
        or ("Omni 1.2 Flash" if "omni" in (flow_model or "").lower() else "Veo 3.1 - Lite")
    )
    ui_kw_list: List[str] = [studio_model_name] + list((model_meta or {}).get("ui_keywords") or [])
    return studio_model_name, ui_kw_list


async def _configure_flow_video_studio_settings(
    pg: Any,
    flow_model: str,
    sub_mode: str = "ingredients",
) -> None:
    """Configure Direct Studio settings: Video -> Frames/Ingredients -> 9:16 -> Model -> 720p -> x1 -> Escape."""
    _, ui_kw_list = _resolve_studio_model_keywords(flow_model)
    stb = pg.locator("button.settings-trigger-button:visible").first
    if await stb.count() == 0:
        return
    try:
        await stb.click(timeout=4000)
        await pg.wait_for_timeout(600)

        vid_toggle = pg.locator('.cdk-overlay-container button:has-text("Video")').first
        if await vid_toggle.count() > 0:
            await vid_toggle.click(timeout=3000)
            await pg.wait_for_timeout(450)

        sub_sels = (
            ('.cdk-overlay-container button:has-text("Khung hình")', '.cdk-overlay-container button:has-text("Frames")')
            if sub_mode == "frames"
            else (
                '.cdk-overlay-container button:has-text("Thành phần")',
                '.cdk-overlay-container button:has-text("Ingredients")',
            )
        )
        for s_sel in sub_sels:
            sloc = pg.locator(s_sel).first
            if await sloc.count() > 0:
                await sloc.click(timeout=2500)
                await pg.wait_for_timeout(300)
                break

        r916 = pg.locator('.cdk-overlay-container button:has-text("9:16")').first
        if await r916.count() > 0:
            await r916.click(timeout=2500)
            await pg.wait_for_timeout(300)

        mod_btn = pg.locator(
            '.cdk-overlay-container button[aria-label*="mô hình"], '
            '.cdk-overlay-container button[aria-label*="model"], '
            '.cdk-overlay-container button:has-text("arrow_drop_down")'
        ).first
        if await mod_btn.count() > 0:
            await mod_btn.click(timeout=3000)
            await pg.wait_for_timeout(450)
            picked_model = False
            for kw_ui in dict.fromkeys(ui_kw_list):
                if not kw_ui:
                    continue
                m_opt = pg.locator(f'[role="menuitem"]:has-text("{kw_ui}"):visible').first
                if await m_opt.count() > 0:
                    await m_opt.click(timeout=3000)
                    await pg.wait_for_timeout(400)
                    picked_model = True
                    break
            if not picked_model:
                await pg.keyboard.press("Escape")
                await pg.wait_for_timeout(250)

        for opt_txt in ("720p", "x1"):
            oloc = pg.locator(f'.cdk-overlay-container button:has-text("{opt_txt}")').first
            if await oloc.count() > 0:
                try:
                    await oloc.click(timeout=2000)
                    await pg.wait_for_timeout(200)
                except Exception:
                    pass
    except Exception:
        pass
    finally:
        await pg.keyboard.press("Escape")
        await pg.wait_for_timeout(250)
        await _dismiss_overlays(pg)


async def _pick_or_upload_flow_asset(
    pg: Any,
    trigger_loc: Any,
    img_path: str,
    require_inactive_click: bool = True,
) -> bool:
    """Open Flow asset picker from trigger_loc, upload img_path if absent, wait until ready, and confirm selection."""
    if not img_path or not Path(img_path).is_file() or await trigger_loc.count() == 0:
        return False
    fname = Path(img_path).name

    async def _query_ready_asset(target_name: str) -> Dict[str, Any]:
        return await pg.evaluate(
            """(fname) => {
                const items = Array.from(document.querySelectorAll('.cdk-overlay-container button.asset-item'));
                for (let i = 0; i < items.length; i++) {
                    const txt = (items[i].innerText || '').trim();
                    if (!txt.includes(fname)) continue;
                    if (txt.includes('Đang tải lên') || txt.toLowerCase().includes('uploading')) {
                        return { found: false, uploading: true, index: i, active: false };
                    }
                    return {
                        found: true,
                        uploading: false,
                        index: i,
                        active: items[i].classList.contains('asset-item-active'),
                    };
                }
                return { found: false, uploading: false, index: -1, active: false };
            }""",
            target_name,
        )

    try:
        await trigger_loc.click(timeout=3500)
        await pg.wait_for_timeout(700)
        st_asset = await _query_ready_asset(fname)

        if not st_asset.get("found"):
            if not st_asset.get("uploading"):
                up_btn = pg.locator(
                    '.cdk-overlay-container button.sidebar-upload-btn:visible, '
                    'button.sidebar-upload-btn:visible, '
                    '.cdk-overlay-container button:has-text("upload"):visible, '
                    '.cdk-overlay-container [role="menuitem"]:has-text("Tải"):visible, '
                    '.cdk-overlay-container [role="menuitem"]:has-text("Upload"):visible'
                ).first
                if await up_btn.count() > 0:
                    async with pg.expect_file_chooser(timeout=6000) as fc_info:
                        await up_btn.click(timeout=3500)
                    fc = await fc_info.value
                    await fc.set_files(img_path)
                    st_asset["uploading"] = True

            if st_asset.get("uploading"):
                for _ in range(30):
                    await pg.wait_for_timeout(650)
                    crop_save = pg.locator(
                        '.cdk-overlay-container button:has-text("Cắt và lưu"):visible, '
                        '.cdk-overlay-container button:has-text("Crop and save"):visible'
                    ).first
                    if await crop_save.count() > 0 and await crop_save.is_enabled():
                        await crop_save.click(timeout=3000)
                        await pg.wait_for_timeout(600)
                    st_asset = await _query_ready_asset(fname)
                    if st_asset.get("found"):
                        break

        if not st_asset.get("found"):
            return False

        if (not st_asset.get("active")) or (not require_inactive_click):
            asset_loc = pg.locator(".cdk-overlay-container button.asset-item").nth(int(st_asset["index"]))
            if await asset_loc.count() > 0:
                try:
                    await asset_loc.click(timeout=3000)
                    await pg.wait_for_timeout(450)
                except Exception:
                    pass

        confirm_add = pg.locator(
            '.cdk-overlay-container button.detail-add-to-prompt-btn:visible, '
            'button.detail-add-to-prompt-btn:visible, '
            'button:has-text("Thêm vào câu lệnh"):visible, '
            'button:has-text("Add to prompt"):visible, '
            'button:has-text("Cắt và lưu"):visible, '
            'button:has-text("Crop and save"):visible'
        ).first
        if await confirm_add.count() > 0 and await confirm_add.is_enabled():
            await confirm_add.click(timeout=4000)
            await pg.wait_for_timeout(850)
        return True
    except Exception:
        return False
    finally:
        await _dismiss_overlays(pg)


async def _attach_ingredients_on_flow_page(pg: Any, ingredient_paths: List[str]) -> int:
    """Clear previous composer chips and attach each Ingredient via add-menu-trigger."""
    await _dismiss_overlays(pg)
    chip_del = pg.locator(
        'flow-base-prompt-box button[aria-label*="Xoá"]:visible, '
        'flow-base-prompt-box button[aria-label*="Remove"]:visible, '
        'flow-base-prompt-box button:has-text("close"):visible, '
        'flow-creative-agent-prompt-box button[aria-label*="Xoá"]:visible, '
        'flow-creative-agent-prompt-box button[aria-label*="Remove"]:visible'
    )
    for _ in range(await chip_del.count()):
        try:
            await chip_del.first.click(timeout=1500)
            await pg.wait_for_timeout(220)
        except Exception:
            break

    attached_count = 0
    for ing_p in ingredient_paths:
        add_trig = pg.locator("button.add-menu-trigger:visible").first
        if await add_trig.count() == 0:
            break
        if await _pick_or_upload_flow_asset(pg, add_trig, ing_p, require_inactive_click=True):
            attached_count += 1
    return attached_count


async def _fill_flow_prompt_box(pg: Any, prompt_text: str) -> bool:
    """Clear and fill .ProseMirror or fallback textbox, verifying text actually landed in the editor."""
    await _dismiss_overlays(pg)
    clean_text = re.sub(r"\s*\n+\s*", " ", (prompt_text or "")).strip()
    for inp_sel in (
        ".ProseMirror:visible",
        '[contenteditable="true"][role="textbox"]:visible',
        "textarea:visible",
    ):
        iloc = pg.locator(inp_sel).first
        if await iloc.count() > 0:
            try:
                await iloc.click(timeout=4000)
                await pg.wait_for_timeout(120)
                await iloc.evaluate(
                    """(el) => {
                        el.focus();
                        if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') {
                            el.value = '';
                        } else {
                            document.execCommand('selectAll', false, null);
                            document.execCommand('delete', false, null);
                        }
                    }"""
                )
                await pg.wait_for_timeout(150)
                await pg.keyboard.insert_text(clean_text)
                await pg.wait_for_timeout(180)
                cur_val = ((await iloc.inner_text()) or "").strip()
                if len(cur_val) < min(8, len(clean_text)):
                    await iloc.fill(clean_text, timeout=4000)
                    await pg.wait_for_timeout(150)
                return True
            except Exception:
                pass
    return False


async def _submit_flow_generation(pg: Any, sess: _FlowBrowserSession) -> bool:
    await _dismiss_overlays(pg)
    await sess.snapshot_existing_media()
    sess.pending_video_urls.clear()
    sess.api_error_messages.clear()
    sess.generation_submitted = True

    clicked_gen = False
    gen_candidates = (
        "button.generate-icon-button:visible",
        'button[aria-label="Bắt đầu tạo"]:visible',
        'button[aria-label*="Generate"]:visible',
        'button[aria-label*="Create"]:visible',
        'button:has-text("arrow_forward"):visible',
    )
    for attempt_idx in range(10):
        for gen_sel in gen_candidates:
            gloc = pg.locator(gen_sel).first
            if await gloc.count() > 0 and await gloc.is_enabled():
                await gloc.click(timeout=4000)
                clicked_gen = True
                break
        if clicked_gen:
            break
        if attempt_idx == 4:
            # Wake ProseMirror input listener if button is still disabled
            pm = pg.locator(".ProseMirror:visible").first
            if await pm.count() > 0:
                try:
                    await pm.click(timeout=2000)
                    await pg.keyboard.press("End")
                    await pg.keyboard.type(" ")
                except Exception:
                    pass
        await pg.wait_for_timeout(450)

    if not clicked_gen:
        await pg.keyboard.press("Enter")
    return clicked_gen


async def _capture_new_video_from_page(
    pg: Any,
    sess: _FlowBrowserSession,
    out_mp4: Path,
    submit_ts: float,
) -> bool:
    """Attempt Paths A (network video URL), B (new <flow-video-tile>), and C (<video> src) to save 1 unseen clip."""
    # Path A: Direct flow-content.google/video/... or video/mp4 network capture
    while sess.pending_video_urls:
        cand_url = sess.pending_video_urls.pop(0)
        if await sess.try_save_video_to(cand_url, out_mp4):
            return True

    # Path B: Brand-new completed <flow-video-tile> (strictly video tiles, ignoring image tiles)
    if (time.monotonic() - submit_ts) >= 12.0:
        new_tile_info: Dict[str, Any] = await pg.evaluate(
            """(payload) => {
                const knownSrcs = new Set(payload.srcs);
                const knownToks = new Set(payload.toks);
                const tiles = Array.from(document.querySelectorAll('flow-video-tile'));
                for (let i = 0; i < tiles.length; i++) {
                    const tile = tiles[i];
                    const hasSpin = Boolean(tile.querySelector('mat-progress-spinner, mat-spinner, [role="progressbar"]'));
                    const tTxt = (tile.innerText || '');
                    if (hasSpin || /\\b(?:[0-9]|[1-9][0-9])%/.test(tTxt)) continue;
                    const img = tile.querySelector('img.thumbnail, img');
                    const src = img ? (img.currentSrc || img.src || '') : '';
                    if (!src || knownSrcs.has(src)) continue;
                    const m = src.match(/\\/asb\\/([A-Za-z0-9_-]{20,})/);
                    if (m && knownToks.has(m[1])) continue;
                    if (src.includes('/asb/') || src.includes('googleusercontent')) {
                        return { idx: i, src: src, tok: m ? m[1] : '' };
                    }
                }
                return { idx: -1, src: '', tok: '' };
            }""",
            {"srcs": list(sess.consumed_tile_srcs), "toks": list(sess.known_asb_tokens)},
        )

        t_idx = int(new_tile_info.get("idx", -1))
        t_src = str(new_tile_info.get("src") or "")
        t_tok = str(new_tile_info.get("tok") or "")
        if t_idx >= 0:
            tile_loc = pg.locator("flow-video-tile").nth(t_idx)
            try:
                await tile_loc.scroll_into_view_if_needed(timeout=3000)
                await tile_loc.dblclick(timeout=4000)
                await pg.wait_for_timeout(2800)
            except Exception:
                pass

            while sess.pending_video_urls:
                cand_url = sess.pending_video_urls.pop(0)
                saved_cand = await sess.try_save_video_to(cand_url, out_mp4)
                if cand_url in sess.consumed_video_urls:
                    if t_src:
                        sess.consumed_tile_srcs.add(t_src)
                    if t_tok:
                        sess.known_asb_tokens.add(t_tok)
                if saved_cand:
                    await _close_preview_modals(pg)
                    return True

            # Check preview modal <video> element opened by dblclick
            now_srcs = await pg.eval_on_selector_all(
                "video", "els => els.map(v => v.currentSrc || v.src || '').filter(Boolean)"
            )
            for ns in now_srcs:
                if ns.startswith("http") and ns not in sess.consumed_video_urls:
                    saved_ns = await sess.try_save_video_to(ns, out_mp4)
                    if ns in sess.consumed_video_urls:
                        if t_src:
                            sess.consumed_tile_srcs.add(t_src)
                        if t_tok:
                            sess.known_asb_tokens.add(t_tok)
                    if saved_ns:
                        await _close_preview_modals(pg)
                        return True

            await _close_preview_modals(pg)

            # Fallback: right-click tile -> 'Tải xuống' / 'Download'
            try:
                await _dismiss_overlays(pg)
                await tile_loc.click(button="right", timeout=4000)
                await pg.wait_for_timeout(600)
                dl_menu = pg.locator(
                    '[role="menuitem"]:has-text("Tải xuống"):visible, '
                    '[role="menuitem"]:has-text("Download"):visible'
                ).first
                if await dl_menu.count() > 0:
                    await dl_menu.hover(timeout=2500)
                    await dl_menu.click(timeout=2500)
                    await pg.wait_for_timeout(700)
                    res_item = pg.locator(
                        '[role="menuitem"]:has-text("720p"):visible, '
                        '[role="menuitem"]:has-text("1080p"):visible, '
                        '[role="menuitem"]:has-text("Gốc"):visible, '
                        '[role="menuitem"]:has-text("Original"):visible'
                    ).first
                    if await res_item.count() > 0:
                        async with pg.expect_download(timeout=30000) as dl_info:
                            await res_item.click(timeout=3000)
                        dl_obj = await dl_info.value
                        await dl_obj.save_as(str(out_mp4))
                        if t_src:
                            sess.consumed_tile_srcs.add(t_src)
                        if t_tok:
                            sess.known_asb_tokens.add(t_tok)
                        if sess.register_saved_file(out_mp4):
                            return True
            except Exception:
                await _dismiss_overlays(pg)

    # Path C: Any newly mounted <video> element src
    now_srcs = await pg.eval_on_selector_all(
        "video", "els => els.map(v => v.currentSrc || v.src || '').filter(Boolean)"
    )
    for ns in now_srcs:
        if ns.startswith("http") and ns not in sess.consumed_video_urls:
            if await sess.try_save_video_to(ns, out_mp4):
                return True
    return False


async def _wait_and_capture_single_scene_clip(
    sess: _FlowBrowserSession,
    raw_scene_mp4: Path,
    s_idx: int,
    total_scenes: int,
    base_pct: int,
    end_pct: int,
    submit_ts: float,
    on_progress: Optional[Callable[[int], None]] = None,
) -> Tuple[bool, str]:
    """Poll up to 195s for one scene's newly generated MP4 on flow.google.com."""
    raw_scene_mp4.unlink(missing_ok=True)
    deadline = time.monotonic() + 195.0
    tick = 0

    while time.monotonic() < deadline:
        await sess.page.wait_for_timeout(4000)
        tick += 1
        if on_progress:
            on_progress(min(end_pct - 1, base_pct + max(1, tick // 2)))

        err_msg = await sess.check_errors()
        if err_msg:
            return False, f"Lỗi ở Cảnh {s_idx}/{total_scenes}: {err_msg}"

        if await _capture_new_video_from_page(sess.page, sess, raw_scene_mp4, submit_ts):
            return True, ""

    return (
        False,
        f"Quá 195s chưa nhận được MP4 ở Cảnh {s_idx}/{total_scenes} trên flow.google.com. Hãy kiểm tra dự án & số dư AI Credits.",
    )


@asynccontextmanager
async def _open_flow_project_session(
    raw_acc: Dict[str, Any],
    on_progress: Optional[Callable[[int], None]] = None,
) -> AsyncIterator[_FlowBrowserSession]:
    """Launch Chrome profile, verify login & anti-bot gate, create a fresh Flow /project/..., and persist cookies on exit."""
    if not crawler_service.has_playwright():
        yield _FlowBrowserSession(
            ctx=None,
            page=None,
            acc_id=int(raw_acc.get("id") or 0),
            error="Cần cài đặt Playwright để điều khiển phiên trình duyệt Google Flow.",
        )
        return

    from playwright.async_api import async_playwright

    acc_id = int(raw_acc["id"])
    prof_dir = str(raw_acc.get("profile_dir") or (FLOW_PROFILES_DIR / f"acc_{acc_id}"))
    Path(prof_dir).mkdir(parents=True, exist_ok=True)

    cookies_in: List[Dict[str, Any]] = []
    if raw_acc.get("cookies_json"):
        try:
            cookies_in = json.loads(raw_acc["cookies_json"])
        except Exception:
            cookies_in = []

    chrome_exe = _chrome_executable()
    launch_kwargs: Dict[str, Any] = {
        "headless": True,
        "accept_downloads": True,
        "args": ["--disable-blink-features=AutomationControlled"],
        "viewport": {"width": 1440, "height": 920},
    }
    if chrome_exe:
        launch_kwargs["executable_path"] = chrome_exe
    if raw_acc.get("proxy"):
        launch_kwargs["proxy"] = {"server": str(raw_acc["proxy"])}

    async with async_playwright() as p:
        browser = None
        ctx = None
        sess = _FlowBrowserSession(ctx=None, page=None, acc_id=acc_id)
        try:
            used_persistent = False
            try:
                ctx = await p.chromium.launch_persistent_context(prof_dir, **launch_kwargs)
                used_persistent = True
            except Exception:
                ephem_kwargs = {k: v for k, v in launch_kwargs.items() if k not in ("viewport", "accept_downloads")}
                browser = await p.chromium.launch(**ephem_kwargs)
                ctx = await browser.new_context(viewport={"width": 1440, "height": 920}, accept_downloads=True)

            if cookies_in and (not used_persistent or not _has_google_auth_cookies(await ctx.cookies())):
                try:
                    await ctx.add_cookies(cookies_in)
                except Exception:
                    pass

            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            page.set_default_timeout(8000)
            sess.ctx = ctx
            sess.page = page

            async def _on_response(resp: Any) -> None:
                u = resp.url or ""
                ct = (resp.headers.get("content-type") or "").lower()
                if not sess.generation_submitted and "/asb/" in u:
                    for m_tok in re.findall(r"/asb/([A-Za-z0-9_-]{20,})", u):
                        sess.known_asb_tokens.add(m_tok)
                is_banner = any(
                    s in u for s in ("/about", "gstatic.com/glue", "aitestkitchen/website/flow/banners", "landing")
                )
                if (
                    sess.generation_submitted
                    and not is_banner
                    and ("video/mp4" in ct or "flow-content.google/video/" in u)
                    and u.startswith("http")
                    and u not in sess.consumed_video_urls
                    and u not in sess.pending_video_urls
                ):
                    sess.pending_video_urls.append(u)
                if "batchexecute" in u or "aisandbox-pa.googleapis.com" in u:
                    try:
                        if resp.status == 429 and sess.generation_submitted:
                            sess.api_error_messages.append(
                                "Tài khoản Google Flow bị giới hạn tốc độ hoặc hết AI Credits (HTTP 429)."
                            )
                        elif resp.status in (401, 403) and sess.generation_submitted:
                            sess.api_error_messages.append(
                                "Phiên đăng nhập Google Flow bị từ chối quyền truy cập (HTTP 401/403)."
                            )
                        else:
                            txt = await resp.text()
                            if not sess.generation_submitted and "/asb/" in txt:
                                for m_tok in re.findall(r"/asb/([A-Za-z0-9_-]{20,})", txt):
                                    sess.known_asb_tokens.add(m_tok)
                            if sess.generation_submitted and "flow-content.google/video/" in txt:
                                for m_v in re.finditer(r"https://flow-content\.google/video/[^\"\\\s<>]+", txt):
                                    cand_u = m_v.group(0).encode("utf-8").decode("unicode_escape")
                                    if cand_u not in sess.consumed_video_urls and cand_u not in sess.pending_video_urls:
                                        sess.pending_video_urls.append(cand_u)
                            elif sess.generation_submitted and (
                                "MEDIA_GENERATION_STATUS_FAILED" in txt
                                or "INSUFFICIENT_CREDITS" in txt
                                or "PUBLIC_ERROR_" in txt
                            ):
                                if "INSUFFICIENT_CREDITS" in txt:
                                    sess.api_error_messages.append("Tài khoản Google Flow đã hết AI Credits.")
                                elif "PUBLIC_ERROR_" in txt:
                                    sess.api_error_messages.append(
                                        "PUBLIC_ERROR_UNSAFE: Câu lệnh vướng bộ lọc an toàn của Google Flow."
                                    )
                                else:
                                    sess.api_error_messages.append(
                                        "Google Flow báo không thể tạo nội dung (hết AI Credits hoặc nội dung bị chặn)."
                                    )
                    except Exception:
                        pass

            page.on("response", _on_response)

            await page.goto(FLOW_HOME_URL, wait_until="domcontentloaded", timeout=28000)
            await page.wait_for_timeout(3800)

            cur_u = page.url or ""
            c_now = await ctx.cookies()
            html_init = await page.content()
            is_authed, detected_email = _is_flow_page_authenticated(cur_u, html_init, c_now)
            if not is_authed:
                database.update_flow_account(acc_id, status="expired", notes="Phiên đăng nhập đã hết hạn.")
                sess.error = (
                    f"Tài khoản '{raw_acc.get('label')}' chưa đăng nhập hoặc Cookie Google đã hết hạn. "
                    "Hãy bấm 'Login lại' trên thẻ tài khoản."
                )
                yield sess
                return

            body_low = (await page.inner_text("body")).lower()
            if "/sorry/" in cur_u or "verify you are human" in body_low or "unusual traffic" in body_low:
                sess.error = (
                    "Google Flow yêu cầu xác minh người dùng trực tiếp trên trình duyệt. "
                    "Vui lòng bấm 'Mở Flow Web' trên tài khoản để kiểm tra."
                )
                yield sess
                return

            if "/project/" not in (page.url or ""):
                for new_proj_sel in (
                    'button:has-text("Dự án mới"):visible',
                    'button:has-text("New project"):visible',
                    'button:has-text("Create with Flow"):visible',
                    'button:has-text("Tạo bằng Google Flow"):visible',
                    'button:has-text("Try it now"):visible',
                ):
                    loc = page.locator(new_proj_sel).first
                    if await loc.count() > 0:
                        try:
                            await loc.click(timeout=5000)
                            await page.wait_for_timeout(4200)
                            if "/project/" in (page.url or ""):
                                break
                        except Exception:
                            pass

                if "/project/" not in (page.url or ""):
                    fallback_proj = page.locator('a[href*="/project/"]:visible').first
                    if await fallback_proj.count() > 0:
                        try:
                            await fallback_proj.click(timeout=5000)
                            await page.wait_for_timeout(4000)
                        except Exception:
                            pass

            if "/project/" in (page.url or ""):
                upd_fields: Dict[str, Any] = {"project_url": page.url}
                if detected_email and not raw_acc.get("email"):
                    upd_fields["email"] = detected_email
                database.update_flow_account(acc_id, **upd_fields)

            if on_progress:
                on_progress(35)

            yield sess
        finally:
            if ctx is not None:
                try:
                    fresh_cookies = await ctx.cookies()
                    if fresh_cookies:
                        database.update_flow_account(
                            acc_id,
                            cookies_json=json.dumps(fresh_cookies, ensure_ascii=False),
                        )
                except BaseException:
                    pass
            for closer in (ctx, browser):
                if closer is not None:
                    try:
                        await closer.close()
                    except BaseException:
                        pass


async def _generate_via_flow_creative_agent(
    job_id: int,
    raw_acc: Dict[str, Any],
    scene_plan: List[Dict[str, Any]],
    fallback_prompt: str,
    flow_model: str,
    ref_frame_path: str,
    ffmpeg_bin: Optional[str],
    dest_mp4: Path,
    on_progress: Optional[Callable[[int], None]] = None,
    on_scene_plan_update: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
    on_engine_note: Optional[Callable[[str], None]] = None,
) -> Tuple[bool, str, str]:
    """Run Google Flow Creative Agent ('Tác nhân Flow') and strictly gate output to >= len(scene_plan) valid 9:16 clips."""
    async with _open_flow_project_session(raw_acc, on_progress=on_progress) as sess:
        if sess.error or sess.page is None:
            return False, sess.error or "Không mở được phiên Flow Creative Agent.", "flow_agent"

        page = sess.page
        if await page.locator("button.settings-trigger-button:visible").count() > 0:
            await _configure_flow_video_studio_settings(page, flow_model, sub_mode="ingredients")
        await _turn_agent_mode(page, want_on=True)

        # Configure Agent settings: 'Không bao giờ' / 'Never', Image 9:16 x1, Video 9:16 x1 + model
        studio_model_name, ui_kw_list = _resolve_studio_model_keywords(flow_model)
        agent_cfg_btn = page.locator(
            'button[aria-label="Cài đặt tác nhân"]:visible, button.agent-action-button:visible'
        ).first
        if await agent_cfg_btn.count() > 0:
            try:
                await agent_cfg_btn.click(timeout=3500)
                await page.wait_for_timeout(550)

                never_btn = page.locator(
                    'button.mat-button-toggle-button:has-text("Không bao giờ"):visible, '
                    'button.mat-button-toggle-button:has-text("Never"):visible'
                ).first
                if await never_btn.count() > 0:
                    await never_btn.click(timeout=2500)
                    await page.wait_for_timeout(350)

                img_row = page.locator("button.image-defaults-row:visible").first
                if await img_row.count() > 0:
                    await img_row.click(timeout=3000)
                    await page.wait_for_timeout(450)
                    for lbl in ("9:16", "x1"):
                        tbtn = page.locator(f'button.mat-button-toggle-button:has-text("{lbl}"):visible').first
                        if await tbtn.count() > 0:
                            await tbtn.click(timeout=2000)
                            await page.wait_for_timeout(200)
                    b1 = page.locator('button[aria-label="Quay lại"]:visible, button[aria-label="Back"]:visible').first
                    if await b1.count() > 0:
                        await b1.click(timeout=2500)
                        await page.wait_for_timeout(450)

                vid_row = page.locator("button.video-defaults-row:visible").first
                if await vid_row.count() > 0:
                    await vid_row.click(timeout=3000)
                    await page.wait_for_timeout(450)
                    for lbl in ("9:16", "x1"):
                        tbtn = page.locator(f'button.mat-button-toggle-button:has-text("{lbl}"):visible').first
                        if await tbtn.count() > 0:
                            await tbtn.click(timeout=2000)
                            await page.wait_for_timeout(200)

                    dd_btn = page.locator(
                        'button[aria-label*="mô hình"]:visible, '
                        'button[aria-label*="model"]:visible, '
                        '.cdk-overlay-container button:has-text("arrow_drop_down"):visible, '
                        'button:has-text("arrow_drop_down"):visible'
                    ).first
                    if await dd_btn.count() > 0:
                        try:
                            dd_txt = (await dd_btn.inner_text(timeout=1500)).lower()
                            if studio_model_name.lower() not in dd_txt:
                                await dd_btn.click(timeout=2500)
                                await page.wait_for_timeout(400)
                                picked = False
                                for kw_ui in dict.fromkeys(ui_kw_list):
                                    if not kw_ui:
                                        continue
                                    m_opt = page.locator(
                                        f'[role="menuitem"]:has-text("{kw_ui}"):visible, '
                                        f'[role="option"]:has-text("{kw_ui}"):visible, '
                                        f'mat-option:has-text("{kw_ui}"):visible'
                                    ).first
                                    if await m_opt.count() > 0:
                                        await m_opt.click(timeout=2500)
                                        await page.wait_for_timeout(350)
                                        picked = True
                                        break
                                if not picked and await page.locator('[role="menu"]:visible, [role="listbox"]:visible').count() > 0:
                                    await page.keyboard.press("Escape")
                                    await page.wait_for_timeout(250)
                        except Exception:
                            pass

                    b2 = page.locator('button[aria-label="Quay lại"]:visible, button[aria-label="Back"]:visible').first
                    if await b2.count() > 0:
                        await b2.click(timeout=2500)
                        await page.wait_for_timeout(450)

                b_root = page.locator('button[aria-label="Quay lại"]:visible, button[aria-label="Back"]:visible').first
                if await b_root.count() > 0:
                    await b_root.click(timeout=2500)
                    await page.wait_for_timeout(450)
            except Exception:
                pass
            finally:
                await _dismiss_overlays(page)

        # Strict Zero-Source-Frame-Upload Rule: NEVER upload source video screenshots to Flow Creative Agent!
        target_n = max(1, len(scene_plan))
        prefix = (
            f"Create a fresh 100% original viral remake (NO text overlays, NO subtitles, NO logos). "
            f"Generate {target_n} separate 9:16 portrait video clips keeping the same product & presenter across clips: "
        )
        avail = max(80, 620 - len(prefix))
        sep_total = 3 * max(0, target_n - 1)
        per_clip_max = min(145, max(45, (avail - sep_total) // target_n))
        scene_specs: List[str] = []
        for idx_s, sc in enumerate(scene_plan, start=1):
            sdur = round(float(sc.get("target_duration") or 4.5), 1)
            s_act = re.sub(r"\s+", " ", str(sc.get("frames_prompt_en") or sc.get("flow_prompt_en") or sc.get("action_vi") or fallback_prompt)).strip()
            head = f"Clip {idx_s} ({sdur}s): "
            body_limit = max(20, min(140, per_clip_max - len(head)))
            scene_specs.append(f"{head}{s_act[:body_limit]}"[:145])

        director_prompt = (prefix + " | ".join(scene_specs))[:620]

        if not await _fill_flow_prompt_box(page, director_prompt):
            return False, f"Không tìm thấy ô nhập Prompt của Flow Creative Agent ({page.url}).", "flow_agent"

        await page.wait_for_timeout(850)
        submit_ts = time.monotonic()
        await _submit_flow_generation(page, sess)

        captured_raw_clips: List[Path] = []
        deadline = time.monotonic() + 180.0
        last_active_ts = time.monotonic()
        last_approve_ts = 0.0
        acc_disp = str(raw_acc.get("email") or raw_acc.get("label") or f"Acc #{raw_acc['id']}")

        approval_sels = (
            'button:has-text("Tạo tất cả"):visible',
            'button:has-text("Tiếp tục"):visible',
            'button:has-text("Chấp nhận"):visible',
            'button:has-text("Proceed"):visible',
        )

        while time.monotonic() < deadline and len(captured_raw_clips) < target_n:
            await page.wait_for_timeout(4000)

            err_msg = await sess.check_errors()
            if err_msg:
                return False, f"Creative Agent báo lỗi: {err_msg}", "flow_agent"

            if (time.monotonic() - last_approve_ts) >= 2.5:
                for app_sel in approval_sels:
                    aloc = page.locator(app_sel).first
                    if await aloc.count() > 0 and await aloc.is_enabled():
                        try:
                            await aloc.click(timeout=2500)
                            last_approve_ts = time.monotonic()
                            last_active_ts = time.monotonic()
                            await page.wait_for_timeout(700)
                            break
                        except Exception:
                            pass

            while len(captured_raw_clips) < target_n:
                clip_idx = len(captured_raw_clips) + 1
                raw_clip_p = OUTPUTS_DIR / f"flow_agent_{job_id}_{clip_idx}_raw.mp4"
                raw_clip_p.unlink(missing_ok=True)
                if not await _capture_new_video_from_page(page, sess, raw_clip_p, submit_ts):
                    break
                captured_raw_clips.append(raw_clip_p)
                last_active_ts = time.monotonic()
                if on_progress:
                    on_progress(min(84, 36 + int((len(captured_raw_clips) / target_n) * 46)))
                if on_engine_note:
                    on_engine_note(f"🤖 Flow Agent ({len(captured_raw_clips)}/{target_n} clip) · {acc_disp}")

            if len(captured_raw_clips) >= target_n:
                break

            is_generating = await page.evaluate(
                """() => {
                    const spin = document.querySelector('mat-progress-spinner, mat-spinner, [role="progressbar"], .loading-spinner');
                    if (spin && spin.offsetParent !== null) return true;
                    const nodes = document.querySelectorAll('flow-video-tile, [class*="progress"], [class*="generating"], [class*="status"]');
                    for (const el of nodes) {
                        const t = (el.innerText || '');
                        if (/\\b(?:[0-9]|[1-9][0-9])%/.test(t) || /\\b(generating|creating|đang tạo)\\b/i.test(t)) return true;
                    }
                    return false;
                }"""
            )
            if is_generating:
                last_active_ts = time.monotonic()
            elif len(captured_raw_clips) >= 1 and (time.monotonic() - last_active_ts) >= 40.0:
                break

        sess.generation_submitted = False
        await _close_preview_modals(page)

        if not captured_raw_clips:
            return False, "Flow Creative Agent không trả về video clip MP4 nào trong 180s.", "flow_agent"

        valid_clips: List[Path] = []
        last_reject = ""
        for cp in captured_raw_clips:
            dur, _, w, h = await asyncio.to_thread(_probe_video_meta_ffmpeg, ffmpeg_bin, cp)
            if dur < 2.5:
                last_reject = f"clip quá ngắn ({dur:.1f}s < 2.5s)"
                continue
            if not (h > w):
                last_reject = f"khung hình {w}x{h} không phải dọc 9:16"
                continue
            valid_clips.append(cp)

        if len(valid_clips) < target_n:
            return (
                False,
                f"Flow Agent chỉ tạo {len(valid_clips)}/{target_n} clip đạt chuẩn 9:16 ({last_reject or 'thiếu clip'}).",
                "flow_agent",
            )

        trimmed_files: List[Path] = []
        for idx_c, sc in enumerate(scene_plan):
            tdur = float(sc.get("target_duration") or 5.0)
            trimmed_mp4 = OUTPUTS_DIR / f"flow_scene_{job_id}_{idx_c + 1}.mp4"
            await asyncio.to_thread(_trim_and_normalize_scene_clip, ffmpeg_bin, valid_clips[idx_c], trimmed_mp4, tdur, False)
            trimmed_files.append(trimmed_mp4)
            sc["status"] = "done"
            sc["engine_used"] = "flow_agent"
            sc["clip_url"] = f"/media/outputs/{trimmed_mp4.name}?v={int(time.time())}"
            if on_scene_plan_update:
                on_scene_plan_update(scene_plan)

        if on_progress:
            on_progress(86)
        ok_stitch, err_stitch = await asyncio.to_thread(
            _stitch_scene_clips_ffmpeg, ffmpeg_bin, trimmed_files, dest_mp4
        )
        return ok_stitch, err_stitch, "flow_agent"


async def _configure_flow_image_studio_settings(pg: Any) -> None:
    """Configure Direct Studio settings for AI Keyframe generation: Hình ảnh (Nano Banana 2.1) -> 9:16 -> x1."""
    stb = pg.locator("button.settings-trigger-button:visible").first
    if await stb.count() == 0:
        return
    try:
        await stb.click(timeout=4000)
        await pg.wait_for_timeout(500)
        for sel_img in (
            '.cdk-overlay-container button:has-text("Hình ảnh")',
            '.cdk-overlay-container button:has-text("Image")',
        ):
            iloc = pg.locator(sel_img).first
            if await iloc.count() > 0:
                await iloc.click(timeout=3000)
                await pg.wait_for_timeout(400)
                break
        for opt_lbl in ("9:16", "x1"):
            oloc = pg.locator(f'.cdk-overlay-container button:has-text("{opt_lbl}")').first
            if await oloc.count() > 0:
                try:
                    await oloc.click(timeout=2500)
                    await pg.wait_for_timeout(250)
                except Exception:
                    pass
    except Exception:
        pass
    finally:
        await pg.keyboard.press("Escape")
        await pg.wait_for_timeout(250)
        await _dismiss_overlays(pg)


async def _clear_flow_composer_chips_and_text(pg: Any) -> None:
    """Clear text and remove any attached Ingredient / Start-End Frame chips inside flow-base-prompt-box."""
    await _dismiss_overlays(pg)
    clear_btn = pg.locator("flow-base-prompt-box button.clear-button:visible").first
    if await clear_btn.count() > 0:
        try:
            await clear_btn.click(timeout=2500)
            await pg.wait_for_timeout(250)
        except Exception:
            pass
    for _ in range(6):
        chip_btn = pg.locator("flow-base-prompt-box button.chip-container:visible").first
        if await chip_btn.count() == 0:
            break
        try:
            await chip_btn.click(timeout=2000)
            await pg.wait_for_timeout(220)
        except Exception:
            break


def _compute_visual_vec_8x8(raw_bytes: bytes) -> List[int]:
    """Compute a 192-int 8x8 RGB perceptual vector to match in-project Flow assets 100% accurately across URL/title rotations."""
    if not raw_bytes or len(raw_bytes) < 256:
        return []
    try:
        import io
        from PIL import Image

        with Image.open(io.BytesIO(raw_bytes)) as im:
            small = im.convert("RGB").resize((8, 8))
            return list(small.tobytes())
    except Exception:
        return []


async def _select_in_project_flow_asset(
    pg: Any,
    trigger_loc: Any,
    asset_ref: Dict[str, Any],
) -> bool:
    """Select an AI-generated asset already inside the current Flow project's Asset Library (ZERO external uploads)."""
    if not asset_ref or await trigger_loc.count() == 0:
        return False
    await _dismiss_overlays(pg)
    pre_chips = await pg.locator("flow-base-prompt-box img.chip-image").count()
    try:
        await trigger_loc.click(timeout=3500)
        await pg.wait_for_timeout(680)
        probe_res: Dict[str, Any] = await pg.evaluate(
            """(ref) => {
                const items = Array.from(document.querySelectorAll('.cdk-overlay-container button.asset-item'));
                if (!items.length) return { matched: -1, srcs: [] };
                const srcs = items.map(b => {
                    const im = b.querySelector('img');
                    return im ? (im.currentSrc || im.src || '') : '';
                });
                const wantUuid = (ref.image_uuid || '').trim();
                const wantAsb = (ref.asb_token || '').trim();
                const wantTileAsb = (ref.tile_asb_token || '').trim();
                const wantTitle = (ref.title_line || '').trim();
                for (let i = 0; i < srcs.length; i++) {
                    if (wantUuid && srcs[i].includes(wantUuid)) return { matched: i, srcs };
                    if (wantAsb && srcs[i].includes(wantAsb)) return { matched: i, srcs };
                    if (wantTileAsb && srcs[i].includes(wantTileAsb)) return { matched: i, srcs };
                }
                if (wantTitle && wantTitle.toLowerCase() !== 'hình ảnh' && wantTitle.toLowerCase() !== 'image') {
                    for (let i = 0; i < items.length; i++) {
                        const firstLn = ((items[i].innerText || '').split('\\n')[0] || '').trim();
                        if (firstLn && firstLn === wantTitle) return { matched: i, srcs };
                    }
                }
                return { matched: -2, srcs };
            }""",
            asset_ref,
        )
        matched_idx = int(probe_res.get("matched", -1))
        cand_srcs: List[str] = list(probe_res.get("srcs") or [])
        if matched_idx == -1 or not cand_srcs:
            return False

        # Exact 8x8 RGB visual fingerprint match whenever URL rotated (/image/<UUID> -> /asb/<TOK>) or title wasn't ready yet!
        want_vec = asset_ref.get("visual_vec")
        if matched_idx == -2 and isinstance(want_vec, list) and len(want_vec) == 192:
            best_i = 0
            best_dist = 1e9
            for idx_c, c_src in enumerate(cand_srcs):
                if not c_src.startswith("http"):
                    continue
                try:
                    r_th = await pg.context.request.get(c_src, timeout=8000)
                    if r_th.ok:
                        c_vec = _compute_visual_vec_8x8(await r_th.body())
                        if len(c_vec) == 192:
                            dist = sum(abs(a - b) for a, b in zip(want_vec, c_vec)) / 192.0
                            if dist < best_dist:
                                best_dist = dist
                                best_i = idx_c
                except Exception:
                    pass
            matched_idx = best_i
        elif matched_idx < 0:
            matched_idx = 0

        item_loc = pg.locator(".cdk-overlay-container button.asset-item").nth(matched_idx)
        if await item_loc.count() == 0:
            return False
        was_active = "asset-item-active" in ((await item_loc.get_attribute("class")) or "")
        await item_loc.click(timeout=3000)
        await pg.wait_for_timeout(480)

        now_chips = await pg.locator("flow-base-prompt-box img.chip-image").count()
        if now_chips <= pre_chips:
            confirm_btn = pg.locator(
                '.cdk-overlay-container button.detail-add-to-prompt-btn:visible, '
                'button.detail-add-to-prompt-btn:visible, '
                '.cdk-overlay-container button:has-text("Thêm vào câu lệnh"):visible, '
                '.cdk-overlay-container button:has-text("Add to prompt"):visible'
            ).first
            if await confirm_btn.count() > 0 and await confirm_btn.is_enabled():
                try:
                    await confirm_btn.click(timeout=3000)
                    await pg.wait_for_timeout(520)
                except Exception:
                    pass

            now_chips = await pg.locator("flow-base-prompt-box img.chip-image").count()
            if (
                now_chips <= pre_chips
                and not was_active
                and await pg.locator(".cdk-overlay-container button.asset-item:visible").count() > matched_idx
            ):
                try:
                    await pg.locator(".cdk-overlay-container button.asset-item").nth(matched_idx).click(timeout=3000)
                    await pg.wait_for_timeout(520)
                except Exception:
                    pass

        return (await pg.locator("flow-base-prompt-box img.chip-image").count()) > pre_chips
    except Exception:
        return False
    finally:
        await _dismiss_overlays(pg)


def _sanitize_image_prompt_for_retry(raw_prompt: str, level: int = 1) -> str:
    """Rewrite prompt if Nano Banana returns PUBLIC_ERROR_UNSAFE_GENERATION: strip all human/person/gender nouns and focus on POV hands/product action."""
    cleaned = re.sub(
        r"\b(female|male|woman|women|man|men|girl|girls|boy|boys|lady|guy|child|children|kid|kids|teen|face|faces|head|smiling|portrait|person|people|runner|runners|jogger|joggers|cyclist|cyclists|athlete|athletes|presenter|creator|model|celebrity|she|her|hers|he|his|him)\b",
        "athletic gear",
        raw_prompt,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    if level >= 2:
        return (
            "Vertical 9:16 commercial product-in-action photograph from a dynamic close-to-medium low angle "
            f"(strictly zero people or faces in frame, focusing on the glowing product and environment): {cleaned[:260]}. "
            "Photorealistic lighting, NO text overlays, NO watermarks, NO logos."
        )
    return (
        "Vertical 9:16 dynamic POV product-in-action smartphone photograph (cropped close to hands or footwear/mount only, "
        f"zero human faces visible): {cleaned[:280]}. Crisp natural lighting, photorealistic, NO text overlays, NO watermarks, NO brand logos."
    )


async def _generate_single_nano_banana_image(
    pg: Any,
    sess: _FlowBrowserSession,
    prompt_en: str,
    ingredient_assets: List[Dict[str, Any]],
    save_jpg_path: Path,
    ffmpeg_bin: Optional[str] = None,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Generate 1 9:16 AI keyframe natively inside Google Flow via Nano Banana 2.1, catching PUBLIC_ERROR_UNSAFE_GENERATION in ~2.5s and auto-retrying cleanly."""
    for attempt in range(3):
        eff_prompt = prompt_en if attempt == 0 else _sanitize_image_prompt_for_retry(prompt_en, level=attempt)
        eff_ings = ingredient_assets[:2] if attempt < 2 else []
        await _close_preview_modals(pg)
        await _clear_flow_composer_chips_and_text(pg)

        for ing_ref in eff_ings:
            add_trig = pg.locator("button.add-menu-trigger:visible").first
            if await add_trig.count() == 0:
                break
            await _select_in_project_flow_asset(pg, add_trig, ing_ref)
            await pg.wait_for_timeout(250)

        pre_state: Dict[str, List[str]] = await pg.evaluate(
            """() => {
                const srcs = [];
                const toks = [];
                for (const im of document.querySelectorAll('flow-image-tile img')) {
                    const s = im.currentSrc || im.src || '';
                    if (!s) continue;
                    srcs.push(s);
                    const m = s.match(/\\/asb\\/([A-Za-z0-9_-]{20,})/);
                    if (m) toks.push(m[1]);
                }
                return { srcs, toks };
            }"""
        )

        if not await _fill_flow_prompt_box(pg, eff_prompt):
            return False, f"Không tìm thấy ô nhập Prompt tạo ảnh Nano Banana ({pg.url}).", {}

        await pg.wait_for_timeout(450)
        submitted_ok = await _submit_flow_generation(pg, sess)
        if not submitted_ok:
            sess.generation_submitted = False
            if attempt == 0:
                await _configure_flow_image_studio_settings(pg)
                continue
            return False, "Nút tạo ảnh Nano Banana không kích hoạt được trên Google Flow.", {}

        new_tile_src = ""
        new_tile_tok = ""
        last_err = ""
        deadline = time.monotonic() + 105.0
        while time.monotonic() < deadline:
            await pg.wait_for_timeout(2500)
            err_chk = await sess.check_errors()
            if err_chk:
                last_err = err_chk
                break
            found_tile: Dict[str, str] = await pg.evaluate(
                """(pre) => {
                    const vp = document.querySelector('cdk-virtual-scroll-viewport');
                    if (vp && vp.scrollTop > 0) vp.scrollTop = 0;
                    const knownSrcs = new Set(pre.srcs || []);
                    const knownToks = new Set(pre.toks || []);
                    const tiles = Array.from(document.querySelectorAll('flow-image-tile'));
                    for (const t of tiles) {
                        const spin = Boolean(t.querySelector('mat-progress-spinner, mat-spinner, [role="progressbar"]'));
                        const tTxt = (t.innerText || '');
                        if (spin || /\\b(?:[0-9]|[1-9][0-9])%/.test(tTxt)) continue;
                        const im = t.querySelector('img');
                        const src = im ? (im.currentSrc || im.src || '') : '';
                        if (!src || knownSrcs.has(src)) continue;
                        const m = src.match(/\\/asb\\/([A-Za-z0-9_-]{20,})/);
                        if (m && knownToks.has(m[1])) continue;
                        if (src.includes('/asb/') || src.includes('flow-content.google/image/') || src.includes('googleusercontent')) {
                            return { src, tok: m ? m[1] : '' };
                        }
                    }
                    return { src: '', tok: '' };
                }""",
                pre_state,
            )
            if found_tile.get("src"):
                new_tile_src = str(found_tile["src"])
                new_tile_tok = str(found_tile.get("tok") or "")
                break

        sess.generation_submitted = False
        sess.api_error_messages.clear()

        if not new_tile_src:
            if attempt < 2:
                await _configure_flow_image_studio_settings(pg)
                continue
            return False, last_err or "Quá thời gian chờ tạo ảnh AI First/End Frame bằng Nano Banana trên Google Flow.", {}

        # Download AI-generated image locally so Frontend UI shows the exact AI Start/End frames!
        save_jpg_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            resp_img = await sess.ctx.request.get(new_tile_src, timeout=30000)
            if resp_img.ok:
                img_bytes = await resp_img.body()
                if len(img_bytes) > 4000:
                    tmp_raw = save_jpg_path.parent / f"_raw_{save_jpg_path.name}"
                    tmp_raw.write_bytes(img_bytes)
                    if ffmpeg_bin:
                        proc_n = await asyncio.to_thread(
                            subprocess.run,
                            [
                                ffmpeg_bin,
                                "-y",
                                "-i",
                                str(tmp_raw),
                                "-frames:v",
                                "1",
                                "-vf",
                                "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280",
                                "-q:v",
                                "2",
                                str(save_jpg_path),
                            ],
                            capture_output=True,
                            text=True,
                            timeout=15,
                            env=crawler_service.build_tool_env(),
                        )
                        if proc_n.returncode != 0 or not save_jpg_path.is_file():
                            save_jpg_path.write_bytes(img_bytes)
                        tmp_raw.unlink(missing_ok=True)
                    else:
                        save_jpg_path.write_bytes(img_bytes)
                        tmp_raw.unlink(missing_ok=True)
        except Exception:
            pass

        # Newest generated asset in Flow's Asset Picker is ALWAYS at index 0 (`items[0]`) + store 8x8 RGB visual fingerprint!
        vis_vec = _compute_visual_vec_8x8(save_jpg_path.read_bytes()) if save_jpg_path.is_file() else []
        asset_meta: Dict[str, Any] = {
            "asset_idx": 0,
            "title_line": "",
            "image_uuid": "",
            "asb_token": new_tile_tok,
            "tile_asb_token": new_tile_tok,
            "visual_vec": vis_vec,
        }
        add_trig_probe = pg.locator("button.add-menu-trigger:visible").first
        if await add_trig_probe.count() > 0:
            try:
                await add_trig_probe.click(timeout=3000)
                await pg.wait_for_timeout(620)
                probed: Dict[str, Any] = await pg.evaluate(
                    """() => {
                        const items = Array.from(document.querySelectorAll('.cdk-overlay-container button.asset-item'));
                        if (!items.length) return { src: '', title: '' };
                        const im = items[0].querySelector('img');
                        const src = im ? (im.currentSrc || im.src || '') : '';
                        const title = ((items[0].innerText || '').split('\\n')[0] || '').trim();
                        return { src, title };
                    }"""
                )
                p_src = str(probed.get("src") or "")
                p_title = str(probed.get("title") or "")
                if p_title:
                    asset_meta["title_line"] = p_title
                m_uuid = re.search(r"image/([0-9a-fA-F-]{16,})", p_src)
                if m_uuid:
                    asset_meta["image_uuid"] = m_uuid.group(1)
                m_asb = re.search(r"/asb/([A-Za-z0-9_-]{20,})", p_src)
                if m_asb:
                    asset_meta["asb_token"] = m_asb.group(1)
            except Exception:
                pass
            finally:
                await _dismiss_overlays(pg)

        return True, "", asset_meta

    return False, "Không thể tạo ảnh AI First/End Frame trên Google Flow.", {}


def _generate_ai_image_via_gateway(prompt_en: str, dest_jpg: Path) -> str:
    """Generate a synthetic 9:16 AI keyframe via `gemini-3.1-flash-image` for API-key accounts (ZERO source frames uploaded)."""
    settings = database.get_settings()
    base_u = (settings.get("rea_vlm_base_url") or "").strip().rstrip("/")
    api_k = (settings.get("rea_vlm_api_key") or "").strip()
    if not base_u or not api_k:
        return ""
    try:
        resp = httpx.post(
            f"{base_u}/chat/completions",
            headers={"Authorization": f"Bearer {api_k}", "Content-Type": "application/json"},
            json={
                "model": "gemini-3.1-flash-image",
                "messages": [{"role": "user", "content": f"Generate a vertical 9:16 portrait image: {prompt_en}"}],
            },
            timeout=55.0,
        )
        if resp.status_code != 200:
            return ""
        content = str((((resp.json().get("choices") or [{}])[0]).get("message") or {}).get("content") or "")
        m_b64 = re.search(r"data:image/[a-zA-Z0-9.+-]+;base64,([A-Za-z0-9+/=\s]+)", content)
        if not m_b64:
            return ""
        raw_bytes = base64.b64decode(re.sub(r"\s+", "", m_b64.group(1)))
        if len(raw_bytes) <= 4000:
            return ""
        dest_jpg.parent.mkdir(parents=True, exist_ok=True)
        dest_jpg.write_bytes(raw_bytes)
        return str(dest_jpg)
    except Exception:
        return ""


async def _generate_ai_remake_frames_start_end_via_flow(
    job_id: int,
    raw_acc: Dict[str, Any],
    scene_plan: List[Dict[str, Any]],
    flow_model: str,
    ffmpeg_bin: Optional[str],
    dest_mp4: Path,
    on_progress: Optional[Callable[[int], None]] = None,
    on_scene_plan_update: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
    on_engine_note: Optional[Callable[[str], None]] = None,
) -> Tuple[bool, str, str]:
    """2-Phase Viral Remake inside ONE Google Flow project:
    Phase 1: Generate 100% brand-new 9:16 AI First Frame & AI End Frame images with Nano Banana 2.1 (chained via Product Anchor & Start-Frame ingredients; ZERO source video screenshots uploaded -> ZERO policy violations!).
    Phase 2: Bridge each scene's AI First Frame (Bắt đầu) -> AI End Frame (Kết thúc) via Omni 1.2 Flash / Veo 3.1, time-scale smoothly to exact rea-video beat durations, and stitch into dest_mp4.
    """
    async with _open_flow_project_session(raw_acc, on_progress=on_progress) as sess:
        if sess.error or sess.page is None:
            return False, sess.error or "Không mở được phiên AI Remake First–End Frame trên Google Flow.", "flow_ai_frames_remake"

        page = sess.page
        acc_disp = str(raw_acc.get("email") or raw_acc.get("label") or f"Acc #{raw_acc['id']}")
        total_scenes = max(1, len(scene_plan))

        await _turn_agent_mode(page, want_on=False)

        # =====================================================================
        # PHASE 1: Generate 100% AI First Frame & AI End Frame via Nano Banana 2.1
        # =====================================================================
        await _configure_flow_image_studio_settings(page)

        anchor_asset: Optional[Dict[str, Any]] = None
        anchor_prompt = str((scene_plan[0] if scene_plan else {}).get("ai_product_anchor_prompt_en") or "").strip()
        if total_scenes >= 2 and anchor_prompt:
            if on_engine_note:
                on_engine_note(f"🎨 Nano Banana tạo Ảnh Gốc SP Remake · {acc_disp}")
            if on_progress:
                on_progress(35)
            anchor_jpg = FLOW_REFS_DIR / f"job_{job_id}_ai_anchor.jpg"
            ok_anc, _err_anc, anc_meta = await _generate_single_nano_banana_image(
                pg=page,
                sess=sess,
                prompt_en=anchor_prompt,
                ingredient_assets=[],
                save_jpg_path=anchor_jpg,
                ffmpeg_bin=ffmpeg_bin,
            )
            if ok_anc and anc_meta:
                anchor_asset = anc_meta

        scene_frame_assets: Dict[int, Dict[str, Dict[str, Any]]] = {}
        prev_end_asset: Optional[Dict[str, Any]] = None
        prev_end_jpg: Optional[Path] = None

        for s_idx, scene_item in enumerate(scene_plan, start=1):
            img_pct_start = 36 + int(((s_idx - 1) / total_scenes) * 22)
            img_pct_end = 36 + int((s_idx / total_scenes) * 22)
            if on_progress:
                on_progress(img_pct_start)
            if on_engine_note:
                on_engine_note(f"🎨 AI tạo Ảnh Đầu→Cuối ({s_idx}/{total_scenes}) · {acc_disp}")

            scene_item["status"] = "generating"
            if on_scene_plan_update:
                on_scene_plan_update(scene_plan)

            start_jpg = FLOW_REFS_DIR / f"job_{job_id}_u{s_idx}_ai_start.jpg"
            end_jpg = FLOW_REFS_DIR / f"job_{job_id}_u{s_idx}_ai_end.jpg"

            # 1A. AI First Frame (Bắt đầu): reuse previous End Frame when continuous cut at identical camera angle
            if s_idx > 1 and scene_item.get("reuse_prev_end_as_start") and prev_end_asset is not None:
                u_start_asset = dict(prev_end_asset)
                if prev_end_jpg and prev_end_jpg.is_file():
                    start_jpg.write_bytes(prev_end_jpg.read_bytes())
            else:
                start_ings: List[Dict[str, Any]] = [anchor_asset] if anchor_asset is not None else []
                ai_start_prompt = str(
                    scene_item.get("ai_start_image_prompt_en")
                    or scene_item.get("frames_prompt_en")
                    or scene_item.get("flow_prompt_en")
                    or ""
                ).strip()
                ok_st, err_st, u_start_asset = await _generate_single_nano_banana_image(
                    pg=page,
                    sess=sess,
                    prompt_en=ai_start_prompt,
                    ingredient_assets=start_ings,
                    save_jpg_path=start_jpg,
                    ffmpeg_bin=ffmpeg_bin,
                )
                if not ok_st or not u_start_asset:
                    scene_item["status"] = "failed"
                    if on_scene_plan_update:
                        on_scene_plan_update(scene_plan)
                    return False, f"Lỗi tạo Ảnh Đầu AI ở Cảnh {s_idx}/{total_scenes}: {err_st}", "flow_ai_frames_remake"

            if start_jpg.is_file():
                scene_item["start_frame_path"] = str(start_jpg)
                scene_item["start_frame_url"] = f"/media/flow_refs/{start_jpg.name}?v={int(time.time())}"
                if on_scene_plan_update:
                    on_scene_plan_update(scene_plan)

            # 1B. AI End Frame (Kết thúc): condition on u_start_asset (1 clean chip) so room, hands, lighting & product stay 100% locked!
            end_ings: List[Dict[str, Any]] = [u_start_asset]
            ai_end_prompt = str(
                scene_item.get("ai_end_image_prompt_en")
                or scene_item.get("frames_prompt_en")
                or scene_item.get("flow_prompt_en")
                or ""
            ).strip()
            ok_en, err_en, u_end_asset = await _generate_single_nano_banana_image(
                pg=page,
                sess=sess,
                prompt_en=ai_end_prompt,
                ingredient_assets=end_ings,
                save_jpg_path=end_jpg,
                ffmpeg_bin=ffmpeg_bin,
            )
            if not ok_en or not u_end_asset:
                scene_item["status"] = "failed"
                if on_scene_plan_update:
                    on_scene_plan_update(scene_plan)
                return False, f"Lỗi tạo Ảnh Cuối AI ở Cảnh {s_idx}/{total_scenes}: {err_en}", "flow_ai_frames_remake"

            if end_jpg.is_file():
                scene_item["end_frame_path"] = str(end_jpg)
                scene_item["end_frame_url"] = f"/media/flow_refs/{end_jpg.name}?v={int(time.time())}"
            if anchor_asset is None:
                anchor_asset = u_end_asset
            prev_end_asset = u_end_asset
            prev_end_jpg = end_jpg if end_jpg.is_file() else None
            scene_frame_assets[s_idx] = {"start": u_start_asset, "end": u_end_asset}

            if on_scene_plan_update:
                on_scene_plan_update(scene_plan)
            if on_progress:
                on_progress(img_pct_end)

        # =====================================================================
        # PHASE 2: Render Video Clips via 'Khung hình: Bắt đầu → Kết thúc'
        # =====================================================================
        await _configure_flow_video_studio_settings(page, flow_model, sub_mode="frames")
        trimmed_scene_files: List[Path] = []

        for s_idx, scene_item in enumerate(scene_plan, start=1):
            vid_base_pct = 58 + int(((s_idx - 1) / total_scenes) * 27)
            vid_end_pct = 58 + int((s_idx / total_scenes) * 27)
            if on_progress:
                on_progress(vid_base_pct)
            if on_engine_note:
                on_engine_note(f"🎬 Render Video Đầu→Cuối ({s_idx}/{total_scenes}) · {acc_disp}")

            scene_item["status"] = "generating"
            if on_scene_plan_update:
                on_scene_plan_update(scene_plan)

            await _close_preview_modals(page)
            await _clear_flow_composer_chips_and_text(page)

            pair_refs = scene_frame_assets.get(s_idx) or {}
            for slot_idx, ref_key in ((0, "start"), (1, "end")):
                target_ref = pair_refs.get(ref_key) or {}
                mounted = False
                for _attempt in range(2):
                    slot_loc = page.locator("flow-base-prompt-box .frame-trigger").nth(slot_idx)
                    await _select_in_project_flow_asset(page, slot_loc, target_ref)
                    await page.wait_for_timeout(450)
                    if await page.locator("flow-base-prompt-box .frame-trigger").nth(slot_idx).locator("img.chip-image").count() > 0:
                        mounted = True
                        break
                if not mounted:
                    scene_item["status"] = "failed"
                    if on_scene_plan_update:
                        on_scene_plan_update(scene_plan)
                    slot_lbl = "Bắt đầu" if slot_idx == 0 else "Kết thúc"
                    return (
                        False,
                        f"Không gắn được Ảnh AI {slot_lbl} ở Cảnh {s_idx}/{total_scenes} trên Google Flow.",
                        "flow_ai_frames_remake",
                    )

            scene_prompt = str(scene_item.get("frames_prompt_en") or scene_item.get("flow_prompt_en") or "").strip()
            if not await _fill_flow_prompt_box(page, scene_prompt):
                scene_item["status"] = "failed"
                if on_scene_plan_update:
                    on_scene_plan_update(scene_plan)
                return (
                    False,
                    f"Không tìm thấy ô nhập Prompt Video ở Cảnh {s_idx}/{total_scenes} trên Google Flow ({page.url}).",
                    "flow_ai_frames_remake",
                )

            raw_scene_mp4 = OUTPUTS_DIR / f"flow_scene_{job_id}_{s_idx}_raw.mp4"
            saved_ok = False
            err_wait = ""
            for vid_attempt in range(2):
                if vid_attempt > 0:
                    safe_vid_prompt = (
                        "Smooth continuous smartphone camera tracking bridging the opening frame seamlessly to the closing frame "
                        "with natural movement and crisp ambient foley sound. Vertical 9:16 smartphone footage, photorealistic, NO text overlays."
                    )
                    await _fill_flow_prompt_box(page, safe_vid_prompt)
                    await page.wait_for_timeout(500)
                else:
                    await page.wait_for_timeout(750)
                submit_ts = time.monotonic()
                await _submit_flow_generation(page, sess)

                saved_ok, err_wait = await _wait_and_capture_single_scene_clip(
                    sess=sess,
                    raw_scene_mp4=raw_scene_mp4,
                    s_idx=s_idx,
                    total_scenes=total_scenes,
                    base_pct=vid_base_pct,
                    end_pct=vid_end_pct,
                    submit_ts=submit_ts,
                    on_progress=on_progress,
                )
                sess.generation_submitted = False
                sess.api_error_messages.clear()
                await _close_preview_modals(page)
                if saved_ok and raw_scene_mp4.is_file():
                    break
                if "PUBLIC_ERROR" not in err_wait and "bị chặn" not in err_wait:
                    break

            if not saved_ok or not raw_scene_mp4.is_file():
                scene_item["status"] = "failed"
                if on_scene_plan_update:
                    on_scene_plan_update(scene_plan)
                return False, err_wait, "flow_ai_frames_remake"

            tdur = float(scene_item.get("target_duration") or 5.0)
            trimmed_mp4 = OUTPUTS_DIR / f"flow_scene_{job_id}_{s_idx}.mp4"
            await asyncio.to_thread(
                _trim_and_normalize_scene_clip, ffmpeg_bin, raw_scene_mp4, trimmed_mp4, tdur, True
            )
            trimmed_scene_files.append(trimmed_mp4)

            scene_item["status"] = "done"
            scene_item["engine_used"] = "flow_ai_frames_remake"
            scene_item["clip_url"] = f"/media/outputs/{trimmed_mp4.name}?v={int(time.time())}"
            if on_scene_plan_update:
                on_scene_plan_update(scene_plan)
            if on_progress:
                on_progress(vid_end_pct)

        if on_progress:
            on_progress(86)
        if on_engine_note:
            on_engine_note(f"🎨 AI Remake Đầu→Cuối ({total_scenes}/{total_scenes} cảnh) · {acc_disp}")
        ok_stitch, err_stitch = await asyncio.to_thread(
            _stitch_scene_clips_ffmpeg, ffmpeg_bin, trimmed_scene_files, dest_mp4
        )
        return ok_stitch, err_stitch, "flow_ai_frames_remake"


async def _generate_multi_scene_via_flow_browser_session(
    job_id: int,
    raw_acc: Dict[str, Any],
    scene_plan: List[Dict[str, Any]],
    flow_model: str,
    clone_mode: str,
    ref_frame_path: str,
    ffmpeg_bin: Optional[str],
    dest_mp4: Path,
    on_progress: Optional[Callable[[int], None]] = None,
    on_scene_plan_update: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
) -> Tuple[bool, str]:
    """Execute Ingredients / Text-to-Video Scene Units inside ONE fresh Google Flow project using ONLY AI-generated Ingredient assets (ZERO source frames uploaded)."""
    async with _open_flow_project_session(raw_acc, on_progress=on_progress) as sess:
        if sess.error or sess.page is None:
            return False, sess.error or "Không mở được phiên Google Flow."

        page = sess.page
        await _turn_agent_mode(page, want_on=False)

        ai_anchor_ref: Optional[Dict[str, Any]] = None
        if clone_mode in ("flow_omni_ingredients", "flow_veo_i2v") and scene_plan:
            await _configure_flow_image_studio_settings(page)
            anc_prompt = str(
                scene_plan[0].get("ai_product_anchor_prompt_en")
                or scene_plan[0].get("ai_start_image_prompt_en")
                or ""
            ).strip()
            if anc_prompt:
                anc_jpg = FLOW_REFS_DIR / f"job_{job_id}_ai_ing_anchor.jpg"
                ok_a, _err_a, anc_meta = await _generate_single_nano_banana_image(
                    pg=page,
                    sess=sess,
                    prompt_en=anc_prompt,
                    ingredient_assets=[],
                    save_jpg_path=anc_jpg,
                    ffmpeg_bin=ffmpeg_bin,
                )
                if ok_a and anc_meta:
                    ai_anchor_ref = anc_meta
                    if anc_jpg.is_file():
                        anc_url = f"/media/flow_refs/{anc_jpg.name}?v={int(time.time())}"
                        for sc_u in scene_plan:
                            sc_u["ref_url"] = anc_url
                            sc_u["start_frame_url"] = anc_url
                        if on_scene_plan_update:
                            on_scene_plan_update(scene_plan)

        await _configure_flow_video_studio_settings(
            page, flow_model, sub_mode="frames" if clone_mode == "flow_veo_i2v" else "ingredients"
        )

        total_scenes = max(1, len(scene_plan))
        trimmed_scene_files: List[Path] = []

        for s_idx, scene_item in enumerate(scene_plan, start=1):
            base_pct = 42 + int(((s_idx - 1) / total_scenes) * 42)
            end_pct = 42 + int((s_idx / total_scenes) * 42)
            if on_progress:
                on_progress(base_pct)

            scene_item["status"] = "generating"
            if on_scene_plan_update:
                on_scene_plan_update(scene_plan)

            await _close_preview_modals(page)
            await _clear_flow_composer_chips_and_text(page)

            if ai_anchor_ref is not None and clone_mode in ("flow_omni_ingredients", "flow_veo_i2v"):
                if clone_mode == "flow_veo_i2v":
                    slot0 = page.locator("flow-base-prompt-box .frame-trigger").nth(0)
                    await _select_in_project_flow_asset(page, slot0, ai_anchor_ref)
                else:
                    add_trig = page.locator("button.add-menu-trigger:visible").first
                    await _select_in_project_flow_asset(page, add_trig, ai_anchor_ref)

            scene_prompt = str(scene_item.get("flow_prompt_en") or scene_item.get("frames_prompt_en") or "").strip()
            if not await _fill_flow_prompt_box(page, scene_prompt):
                scene_item["status"] = "failed"
                if on_scene_plan_update:
                    on_scene_plan_update(scene_plan)
                return (
                    False,
                    f"Không tìm thấy ô nhập Prompt ở Cảnh {s_idx}/{total_scenes} trên Google Flow ({page.url}).",
                )

            await page.wait_for_timeout(850)
            submit_ts = time.monotonic()
            await _submit_flow_generation(page, sess)

            raw_scene_mp4 = OUTPUTS_DIR / f"flow_scene_{job_id}_{s_idx}_raw.mp4"
            saved_ok, err_wait = await _wait_and_capture_single_scene_clip(
                sess=sess,
                raw_scene_mp4=raw_scene_mp4,
                s_idx=s_idx,
                total_scenes=total_scenes,
                base_pct=base_pct,
                end_pct=end_pct,
                submit_ts=submit_ts,
                on_progress=on_progress,
            )
            sess.generation_submitted = False
            await _close_preview_modals(page)

            if not saved_ok or not raw_scene_mp4.is_file():
                scene_item["status"] = "failed"
                if on_scene_plan_update:
                    on_scene_plan_update(scene_plan)
                return False, err_wait

            tdur = float(scene_item.get("target_duration") or 5.0)
            trimmed_mp4 = OUTPUTS_DIR / f"flow_scene_{job_id}_{s_idx}.mp4"
            await asyncio.to_thread(_trim_and_normalize_scene_clip, ffmpeg_bin, raw_scene_mp4, trimmed_mp4, tdur, True)
            trimmed_scene_files.append(trimmed_mp4)

            scene_item["status"] = "done"
            scene_item["engine_used"] = clone_mode
            scene_item["clip_url"] = f"/media/outputs/{trimmed_mp4.name}?v={int(time.time())}"
            if on_scene_plan_update:
                on_scene_plan_update(scene_plan)
            if on_progress:
                on_progress(end_pct)

        if on_progress:
            on_progress(86)
        ok_stitch, err_stitch = await asyncio.to_thread(
            _stitch_scene_clips_ffmpeg, ffmpeg_bin, trimmed_scene_files, dest_mp4
        )
        return ok_stitch, err_stitch


async def _generate_via_flow_browser_session(
    raw_acc: Dict[str, Any],
    prompt: str,
    flow_model: str,
    clone_mode: str,
    ref_frame_path: str,
    dest_mp4: Path,
    on_progress: Optional[Callable[[int], None]] = None,
) -> Tuple[bool, str]:
    single_plan = [
        {
            "unit_index": 1,
            "title_vi": "Cảnh 1",
            "shot_indices": [1],
            "start": 0.0,
            "end": 8.0,
            "target_duration": 8.0,
            "same_scene_as_prev": False,
            "reuse_prev_end_as_start": False,
            "action_vi": "",
            "ai_start_image_prompt_en": prompt,
            "ai_end_image_prompt_en": prompt,
            "flow_prompt_en": prompt,
            "frames_prompt_en": prompt,
            "status": "pending",
        }
    ]
    return await _generate_multi_scene_via_flow_browser_session(
        job_id=0,
        raw_acc=raw_acc,
        scene_plan=single_plan,
        flow_model=flow_model,
        clone_mode=clone_mode,
        ref_frame_path="",
        ffmpeg_bin=None,
        dest_mp4=dest_mp4,
        on_progress=on_progress,
        on_scene_plan_update=None,
    )


async def generate_multi_scene_video_via_flow(
    job_id: int,
    raw_acc: Dict[str, Any],
    scene_plan: List[Dict[str, Any]],
    fallback_prompt: str,
    flow_model: str,
    clone_mode: str,
    ref_frame_path: str,
    ffmpeg_bin: Optional[str],
    dest_mp4: Path,
    on_progress: Optional[Callable[[int], None]] = None,
    on_scene_plan_update: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
    on_engine_note: Optional[Callable[[str], None]] = None,
) -> Tuple[bool, str]:
    """Generate all rea-video Scene Units via Google Flow using 100% AI-generated First/End Remake Frames (ZERO source video screenshots ever uploaded!)."""
    effective_plan = list(scene_plan) if scene_plan else [
        {
            "unit_index": 1,
            "title_vi": "Cảnh 1",
            "shot_indices": [1],
            "start": 0.0,
            "end": 8.0,
            "target_duration": 8.0,
            "same_scene_as_prev": False,
            "reuse_prev_end_as_start": False,
            "action_vi": "",
            "ai_start_image_prompt_en": fallback_prompt,
            "ai_end_image_prompt_en": fallback_prompt,
            "flow_prompt_en": fallback_prompt,
            "frames_prompt_en": fallback_prompt,
            "status": "pending",
        }
    ]
    mode = str(raw_acc.get("auth_mode") or "browser_profile")
    bearer = str(raw_acc.get("bearer_token") or "").strip()
    project_url = str(raw_acc.get("project_url") or FLOW_HOME_URL)

    # Non-browser API-key / Bearer accounts: synthesize clean AI start frames via gemini-3.1-flash-image (never upload source frames!)
    if mode in ("gemini_api_key", "bearer_token") or bearer.startswith("AIza") or bearer.startswith("ya29."):
        trimmed_files: List[Path] = []
        total_s = max(1, len(effective_plan))
        prev_cont = ""
        for s_idx, s_item in enumerate(effective_plan, start=1):
            s_item["status"] = "generating"
            if on_scene_plan_update:
                on_scene_plan_update(effective_plan)
            raw_s = OUTPUTS_DIR / f"flow_scene_{job_id}_{s_idx}_raw.mp4"
            ai_ref_path = ""
            if s_idx > 1 and s_item.get("reuse_prev_end_as_start") and prev_cont:
                ai_ref_path = prev_cont
            elif clone_mode != "flow_veo_t2v":
                ai_st_jpg = FLOW_REFS_DIR / f"job_{job_id}_u{s_idx}_ai_start.jpg"
                ai_st_p = str(s_item.get("ai_start_image_prompt_en") or s_item.get("frames_prompt_en") or fallback_prompt)
                ai_ref_path = await asyncio.to_thread(_generate_ai_image_via_gateway, ai_st_p, ai_st_jpg)
                if ai_ref_path:
                    s_item["start_frame_url"] = f"/media/flow_refs/{ai_st_jpg.name}?v={int(time.time())}"
                    if on_scene_plan_update:
                        on_scene_plan_update(effective_plan)

            s_prompt = str(s_item.get("frames_prompt_en") or s_item.get("flow_prompt_en") or fallback_prompt)
            if mode == "gemini_api_key" or bearer.startswith("AIza"):
                ok_s, err_s = await asyncio.to_thread(
                    _generate_via_gemini_veo_api, bearer, s_prompt, flow_model, clone_mode, ai_ref_path, raw_s, None
                )
            else:
                ok_s, err_s = await asyncio.to_thread(
                    _generate_via_aisandbox_bearer, bearer, project_url, s_prompt, flow_model, clone_mode, ai_ref_path, raw_s, None
                )
            if not ok_s or not raw_s.is_file():
                s_item["status"] = "failed"
                if on_scene_plan_update:
                    on_scene_plan_update(effective_plan)
                return False, f"Lỗi ở Cảnh {s_idx}/{total_s}: {err_s}"
            tdur = float(s_item.get("target_duration") or 6.0)
            cont_jpg = FLOW_REFS_DIR / f"job_{job_id}_u{s_idx}_ai_end.jpg"
            prev_cont = await asyncio.to_thread(_extract_clean_continuity_frame, ffmpeg_bin, raw_s, cont_jpg, tdur)
            if prev_cont:
                s_item["end_frame_url"] = f"/media/flow_refs/{cont_jpg.name}?v={int(time.time())}"
            trim_s = OUTPUTS_DIR / f"flow_scene_{job_id}_{s_idx}.mp4"
            await asyncio.to_thread(_trim_and_normalize_scene_clip, ffmpeg_bin, raw_s, trim_s, tdur, True)
            trimmed_files.append(trim_s)
            s_item["status"] = "done"
            s_item["engine_used"] = "flow_ai_frames_remake"
            s_item["clip_url"] = f"/media/outputs/{trim_s.name}?v={int(time.time())}"
            if on_scene_plan_update:
                on_scene_plan_update(effective_plan)
            if on_progress:
                on_progress(36 + int((s_idx / total_s) * 48))

        return await asyncio.to_thread(_stitch_scene_clips_ffmpeg, ffmpeg_bin, trimmed_files, dest_mp4)

    acc_disp = str(raw_acc.get("email") or raw_acc.get("label") or f"Acc #{raw_acc['id']}")
    acc_lock = _get_flow_account_lock(int(raw_acc["id"]))
    async with acc_lock:
        # Primary smooth remake modes: Agent self-generates Nano Banana AI First Frame & AI End Frame -> bridges via First-to-End Video Studio!
        if clone_mode in ("flow_frames_start_end", "flow_agent_auto", "flow_ai_frames_remake"):
            ok_fr, err_fr, _ = await _generate_ai_remake_frames_start_end_via_flow(
                job_id=job_id,
                raw_acc=raw_acc,
                scene_plan=effective_plan,
                flow_model=flow_model,
                ffmpeg_bin=ffmpeg_bin,
                dest_mp4=dest_mp4,
                on_progress=on_progress,
                on_scene_plan_update=on_scene_plan_update,
                on_engine_note=on_engine_note,
            )
            return ok_fr, err_fr

        if clone_mode == "flow_agent":
            ok_ag, _err_ag, _ = await _generate_via_flow_creative_agent(
                job_id=job_id,
                raw_acc=raw_acc,
                scene_plan=effective_plan,
                fallback_prompt=fallback_prompt,
                flow_model=flow_model,
                ref_frame_path="",
                ffmpeg_bin=ffmpeg_bin,
                dest_mp4=dest_mp4,
                on_progress=on_progress,
                on_scene_plan_update=on_scene_plan_update,
                on_engine_note=on_engine_note,
            )
            if ok_ag:
                return True, ""

            if on_engine_note:
                on_engine_note(f"🎨 AI Remake Đầu→Cuối (Dự phòng từ Agent) · {acc_disp}")
            for s_item in effective_plan:
                s_item["status"] = "pending"
                s_item["clip_url"] = ""
                s_item.pop("engine_used", None)
            if on_scene_plan_update:
                on_scene_plan_update(effective_plan)

            ok_fr, err_fr, _ = await _generate_ai_remake_frames_start_end_via_flow(
                job_id=job_id,
                raw_acc=raw_acc,
                scene_plan=effective_plan,
                flow_model=flow_model,
                ffmpeg_bin=ffmpeg_bin,
                dest_mp4=dest_mp4,
                on_progress=on_progress,
                on_scene_plan_update=on_scene_plan_update,
                on_engine_note=on_engine_note,
            )
            return ok_fr, err_fr

        return await _generate_multi_scene_via_flow_browser_session(
            job_id=job_id,
            raw_acc=raw_acc,
            scene_plan=effective_plan,
            flow_model=flow_model,
            clone_mode=clone_mode,
            ref_frame_path="",
            ffmpeg_bin=ffmpeg_bin,
            dest_mp4=dest_mp4,
            on_progress=on_progress,
            on_scene_plan_update=on_scene_plan_update,
        )


async def generate_video_via_flow(
    raw_acc: Dict[str, Any],
    prompt: str,
    flow_model: str,
    clone_mode: str,
    ref_frame_path: str,
    dest_mp4: Path,
    on_progress: Optional[Callable[[int], None]] = None,
) -> Tuple[bool, str]:
    """Single-clip wrapper around `generate_multi_scene_video_via_flow`."""
    return await generate_multi_scene_video_via_flow(
        job_id=0,
        raw_acc=raw_acc,
        scene_plan=[],
        fallback_prompt=prompt,
        flow_model=flow_model,
        clone_mode=clone_mode,
        ref_frame_path=ref_frame_path,
        ffmpeg_bin=None,
        dest_mp4=dest_mp4,
        on_progress=on_progress,
        on_scene_plan_update=None,
    )
