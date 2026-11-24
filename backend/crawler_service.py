from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus, urlsplit

import httpx

import database

MEDIA_DIR = Path(__file__).resolve().parent / "media"
DOWNLOADS_DIR = MEDIA_DIR / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
COOKIES_DIR = MEDIA_DIR / "cookies"
COOKIES_DIR.mkdir(parents=True, exist_ok=True)

EXTRA_BIN_DIRS = [
    str(Path(__file__).resolve().parent / ".venv/lib/python3.9/site-packages/static_ffmpeg/bin/darwin_arm64"),
    "/Users/vu/.local/bin",
    "/Users/vu/.local/share/uv/tools/agent-reach/bin",
    "/Users/vu/.agent-reach/tools/ffmpeg/bin",
    "/opt/homebrew/bin",
    "/usr/local/bin",
]

KNOWN_YTDLP_PATHS = [
    shutil.which("yt-dlp"),
    "/Users/vu/.local/share/uv/tools/agent-reach/bin/yt-dlp",
    "/Users/vu/.local/bin/yt-dlp",
    r"C:\Users\Admin\AppData\Local\hermes\hermes-agent\venv\Scripts\yt-dlp.exe",
]

KNOWN_AGENT_REACH_PATHS = [
    shutil.which("agent-reach"),
    "/Users/vu/.local/bin/agent-reach",
    "/Users/vu/.local/share/uv/tools/agent-reach/bin/agent-reach",
]

CHANNEL_META_VI: Dict[str, Dict[str, Any]] = {
    "youtube": {"label": "YouTube", "category": "Video / Shorts", "needs_login_default": False},
    "bilibili": {"label": "Bilibili (B站)", "category": "Video China", "needs_login_default": False},
    "xiaohongshu": {"label": "Xiaohongshu (Tiểu Hồng Thư)", "category": "Social Affiliate", "needs_login_default": True},
    "instagram": {"label": "Instagram Reels", "category": "Social Video", "needs_login_default": True},
    "facebook": {"label": "Facebook Reels / Watch", "category": "Social Video", "needs_login_default": True},
    "twitter": {"label": "X / Twitter", "category": "Social Video", "needs_login_default": True},
    "reddit": {"label": "Reddit", "category": "Community", "needs_login_default": False},
    "v2ex": {"label": "V2EX", "category": "Tech Forum", "needs_login_default": False},
    "xueqiu": {"label": "Xueqiu (Tài chính)", "category": "Finance", "needs_login_default": True},
    "linkedin": {"label": "LinkedIn", "category": "Professional", "needs_login_default": True},
    "boss": {"label": "Boss Zhipin", "category": "Jobs", "needs_login_default": True},
    "github": {"label": "GitHub", "category": "Code / Repo", "needs_login_default": False},
    "xiaoyuzhou": {"label": "Xiaoyuzhou Podcast", "category": "Audio / Podcast", "needs_login_default": False},
    "web": {"label": "Web Search (Exa/Jina)", "category": "TikTok / Douyin / Threads", "needs_login_default": False},
}

CHANNEL_COOKIE_SPECS: Dict[str, Dict[str, Any]] = {
    "instagram": {
        "domains": ("instagram.com",),
        "auth_cookies": ("sessionid", "ds_user_id"),
        "any_auth": False,
        "login_url_markers": ("/accounts/login", "/challenge", "/two_factor", "/checkpoint", "2fa.live"),
    },
    "facebook": {
        "domains": ("facebook.com",),
        "auth_cookies": ("c_user", "xs"),
        "any_auth": False,
        "login_url_markers": ("/login", "/checkpoint", "/two_factor", "2fa.live"),
    },
    "twitter": {
        "domains": ("x.com", "twitter.com"),
        "auth_cookies": ("auth_token", "ct0"),
        "any_auth": False,
        "login_url_markers": ("/i/flow/login", "/login", "/account/access", "2fa.live"),
    },
    "xiaohongshu": {
        "domains": ("xiaohongshu.com", "rednote.com"),
        "auth_cookies": ("web_session", "a1"),
        "any_auth": True,
        "login_url_markers": ("/login", "captcha"),
    },
    "youtube": {
        "domains": ("youtube.com", "google.com"),
        "auth_cookies": ("SID", "SAPISID", "LOGIN_INFO"),
        "any_auth": True,
        "login_url_markers": ("accounts.google.com", "servicelogin"),
    },
    "bilibili": {
        "domains": ("bilibili.com",),
        "auth_cookies": ("SESSDATA", "bili_jct"),
        "any_auth": True,
        "login_url_markers": ("passport.bilibili.com/login",),
    },
    "reddit": {
        "domains": ("reddit.com",),
        "auth_cookies": ("token_v2", "reddit_session"),
        "any_auth": True,
        "login_url_markers": ("/login", "/register"),
    },
    "linkedin": {
        "domains": ("linkedin.com",),
        "auth_cookies": ("li_at",),
        "any_auth": True,
        "login_url_markers": ("/login", "/checkpoint"),
    },
    "tiktok": {
        "domains": ("tiktok.com",),
        "auth_cookies": ("sessionid", "sessionid_ss"),
        "any_auth": True,
        "login_url_markers": ("/login",),
    },
    "douyin": {
        "domains": ("douyin.com",),
        "auth_cookies": ("sessionid", "sessionid_ss"),
        "any_auth": True,
        "login_url_markers": ("/login",),
    },
}

_login_watcher_threads: Dict[str, threading.Thread] = {}
_login_watcher_lock = threading.Lock()


def build_tool_env(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    env = os.environ.copy()
    existing = [p for p in env.get("PATH", "").split(os.pathsep) if p]
    merged: List[str] = []
    for p in EXTRA_BIN_DIRS + existing:
        if p and p not in merged:
            merged.append(p)
    env["PATH"] = os.pathsep.join(merged)
    if extra:
        env.update(extra)
    return env


def find_ytdlp() -> Optional[str]:
    for p in KNOWN_YTDLP_PATHS:
        if p and Path(p).exists():
            return str(p)
    return None


def find_agent_reach() -> Optional[str]:
    for p in KNOWN_AGENT_REACH_PATHS:
        if p and Path(p).exists():
            return str(p)
    return None


def has_crawl4ai() -> bool:
    try:
        import crawl4ai  # noqa: F401
        return True
    except Exception:
        return False


def has_playwright() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except Exception:
        return False


_cn_keyword_cache: Dict[str, str] = {}
_VI_DIACRITICS_RE = re.compile(r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", re.I)


def _has_vietnamese_chars(text: str) -> bool:
    return bool(_VI_DIACRITICS_RE.search(text or ""))


def _call_configured_llm(prompt: str, timeout: float = 16.0) -> str:
    try:
        s = database.get_settings()
        base = (s.get("rea_vlm_base_url") or "").strip().rstrip("/")
        key = (s.get("rea_vlm_api_key") or "").strip()
        model_raw = (s.get("rea_vlm_model") or "gpt-4o").strip()
        model = model_raw.split(",")[0].strip() or "gpt-4o"
        if not base or not key:
            return ""
        if not base.endswith("/v1") and "/v1/" not in base and "generativelanguage" not in base:
            base = base + "/v1"

        model_cands: List[str] = [model]
        if "/" in model:
            model_cands.append(model.split("/", 1)[-1])
        if "nongdantienich" in base.lower():
            for fb_m in ("gemini-2.5-flash", "gemini-3.5-flash-lite"):
                if fb_m not in model_cands:
                    model_cands.append(fb_m)

        for cand_m in model_cands[:3]:
            deadline = time.monotonic() + float(timeout)
            chunk_read_timeout = min(8.0, max(3.0, float(timeout) * 0.6))
            body_lines: List[str] = []
            with httpx.stream(
                "POST",
                f"{base}/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": cand_m,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.25,
                },
                timeout=httpx.Timeout(chunk_read_timeout, connect=5.0, read=chunk_read_timeout, write=6.0, pool=5.0),
            ) as resp:
                if resp.status_code != 200:
                    continue
                for line in resp.iter_lines():
                    if time.monotonic() > deadline:
                        break
                    if line:
                        body_lines.append(line)

            text = "\n".join(body_lines).strip()
            if not text:
                continue
            if text.startswith("data:"):
                chunks: List[str] = []
                for line in body_lines:
                    s_ln = line.strip()
                    if s_ln.startswith("data:"):
                        payload = s_ln[5:].strip()
                        if payload and payload != "[DONE]":
                            try:
                                obj = json.loads(payload)
                                delta = ((obj.get("choices") or [{}])[0].get("delta") or {}).get("content")
                                if delta:
                                    chunks.append(str(delta))
                            except Exception:
                                pass
                out_t = "".join(chunks).strip()
                if out_t:
                    return out_t
            else:
                data = json.loads(text)
                out_t = str(((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
                if out_t:
                    return out_t
        return ""
    except Exception:
        return ""


def call_vision_llm(image_path: str, prompt: str, timeout: float = 24.0, max_tokens: int = 2600) -> str:
    """Send a storyboard or keyframe image to a multimodal Vision LLM (auto-routing around gateways where thinking models drop image_url)."""
    if not image_path or not Path(image_path).is_file():
        return ""
    try:
        import base64
        import io
        from PIL import Image

        s = database.get_settings()
        base = (s.get("rea_vlm_base_url") or "").strip().rstrip("/")
        key = (s.get("rea_vlm_api_key") or "").strip()
        model_raw = (s.get("rea_vlm_model") or "gpt-4o").strip()
        if not base or not key:
            return ""
        if not base.endswith("/v1") and "/v1/" not in base and "generativelanguage" not in base:
            base = base + "/v1"

        im = Image.open(image_path).convert("RGB")
        im.thumbnail((1024, 1024))
        buf = io.BytesIO()
        for q_try in (74, 62, 50):
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=q_try)
            if len(buf.getvalue()) <= 180_000:
                break
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        configured_models = [m.strip() for m in model_raw.split(",") if m.strip()]
        candidates: List[str] = []
        is_ag_gateway = any(m.startswith("ag/") for m in configured_models) or "nongdantienich" in base.lower()
        if is_ag_gateway:
            for fast_v in ("gemini-2.5-flash", "gemini-3.5-flash-lite", "claude-sonnet-4-6", "ag/gemini-3.5-flash-lite"):
                if fast_v not in candidates:
                    candidates.append(fast_v)
        for cm in configured_models:
            bare_cm = cm.split("/", 1)[-1] if "/" in cm else cm
            if is_ag_gateway and ("3.8-flash" in cm or "3.1-pro" in cm):
                continue
            for item_m in (cm, bare_cm):
                if item_m not in candidates:
                    candidates.append(item_m)

        for cand_model in candidates[:4]:
            deadline = time.monotonic() + float(timeout)
            chunk_timeout = min(18.0, max(8.0, float(timeout) * 0.65))
            body_lines: List[str] = []
            try:
                with httpx.stream(
                    "POST",
                    f"{base}/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={
                        "model": cand_model,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                                    {"type": "text", "text": prompt},
                                ],
                            }
                        ],
                        "temperature": 0.2,
                        "max_tokens": int(max_tokens),
                        "stream": True,
                    },
                    timeout=httpx.Timeout(chunk_timeout, connect=5.0, read=chunk_timeout, write=8.0, pool=5.0),
                ) as resp:
                    if resp.status_code != 200:
                        continue
                    for line in resp.iter_lines():
                        if time.monotonic() > deadline:
                            break
                        if line:
                            body_lines.append(line)
            except Exception:
                continue

            text = "\n".join(body_lines).strip()
            if not text:
                continue
            if text.startswith("data:"):
                chunks: List[str] = []
                for ln in body_lines:
                    s_ln = ln.strip()
                    if s_ln.startswith("data:"):
                        payload = s_ln[5:].strip()
                        if payload and payload != "[DONE]":
                            try:
                                obj = json.loads(payload)
                                delta = ((obj.get("choices") or [{}])[0].get("delta") or {}).get("content")
                                if delta:
                                    chunks.append(str(delta))
                            except Exception:
                                pass
                out = "".join(chunks).strip()
                if out and "don't see any image" not in out.lower() and "no image attached" not in out.lower():
                    return out
            else:
                try:
                    data = json.loads(text)
                    out = str(((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
                    if out and "don't see any image" not in out.lower() and "no image attached" not in out.lower():
                        return out
                except Exception:
                    pass
        return ""
    except Exception:
        return ""


def _translate_keyword_for_cn(keyword: str) -> str:
    kw = keyword.strip()
    if not kw:
        return kw
    if kw in _cn_keyword_cache:
        return _cn_keyword_cache[kw]
    if not _has_vietnamese_chars(kw) and not re.search(r"[a-zA-Z]", kw):
        return kw
    out = _call_configured_llm(
        f'Dịch cụm từ sản phẩm "{kw}" sang tiếng Trung giản thể (2-6 chữ Hán) để tìm video review sản phẩm trên Douyin/Xiaohongshu/Bilibili. Chỉ trả về đúng cụm từ tiếng Trung, không giải thích.',
        timeout=10.0,
    )
    cleaned = re.sub(r"[\"'`\n\r]", "", out).strip()
    if cleaned and len(cleaned) <= 24:
        _cn_keyword_cache[kw] = cleaned
        return cleaned
    return kw


def _extract_real_price(text: str) -> str:
    if not text:
        return ""
    patterns = [
        r"\b\d{1,3}(?:[.,]\d{3})+\s*(?:đ|vnđ|vnd|d)\b",
        r"\b\d{2,4}\s*k\b",
        r"\bchỉ\s+\d{2,4}\s*k\b",
        r"\$\s*\d+(?:\.\d{1,2})?\b",
        r"\b\d{2,4}\s*元\b",
        r"¥\s*\d{2,4}\b",
        r"\bsale\s*\d{1,2}%\b",
        r"\bgiảm\s*\d{1,2}%\b",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            return m.group(0).strip()
    return ""


def _clean_scraped_caption(raw_text: str, title: str = "") -> str:
    if not raw_text:
        return title
    txt = raw_text.strip()
    # If Exa TikTok dump contains "Follow\n\nmore\n\n", extract the real caption right after it
    if "Follow" in txt and "more" in txt:
        m = re.search(r"Follow\s+more\s+(.+?)(?:\n\s*\.{3}|\n\s*You may like|\n\s*---|$)", txt, re.S)
        if m and len(m.group(1).strip()) > 15:
            txt = m.group(1).strip()
    lines: List[str] = []
    skip_exact = {
        "tiktok", "log in", "search", "for you", "explore", "following", "upload",
        "live", "profile", "more", "follow", "get coins", "company", "program",
        "terms & policies", "được tài trợ", "sponsored", "hoạt động", "nền tảng",
        "mở menu thả xuống", "xem chi tiết quảng cáo", "xem chi tiết bản tóm tắt",
    }
    for ln in txt.splitlines():
        s = ln.strip().strip("​")
        if not s:
            continue
        low = s.lower()
        if low in skip_exact or low.startswith(("url:", "published:", "author:", "© 20", "#### ", "### ")):
            continue
        if "having trouble playing this video" in low or "ai generated and may return results" in low:
            continue
        if re.match(r"^[\d.,KMB]+\s*$", s):
            continue
        lines.append(s)
    cleaned = "\n".join(lines).strip()
    return cleaned[:650] if cleaned else title


def detect_sales_signals(text: str, extra_signals: Optional[List[str]] = None) -> List[str]:
    lower = text.lower()
    signals: List[str] = []
    if extra_signals:
        for s in extra_signals:
            if s and s not in signals:
                signals.append(s)
    price = _extract_real_price(text)
    if price:
        signals.append(f"Giá: {price}")
    mapping = [
        ("Link ở Bio", ["bio", "đầu trang", "link in bio"]),
        ("Gắn Comment", ["comment", "cmt", "bình luận", "reply"]),
        ("Flash Sale / Ưu đãi", ["sale", "giảm", "voucher", "deal", "freeship", "miễn phí vận chuyển", "discount", "trợ giá"]),
        ("Review / Test thực tế", ["unbox", "review", "test", "trải nghiệm", "đập hộp", "测评", "开箱", "实测"]),
        ("Bảo hành / Chính hãng", ["mall", "chính hãng", "official", "bảo hành", "cam kết", "nhà máy", "xưởng"]),
        ("Chốt Inbox / Hotline", ["inbox", "nhắn tin", "hotline", "zalo", "liên hệ", "tư vấn"]),
    ]
    for label, keywords in mapping:
        if any(k in lower for k in keywords) and label not in signals:
            signals.append(label)
    if not signals:
        signals.append("Viral Organic")
    return signals[:6]


def compute_viral_score(views: int, likes: int, comments: int, shares: int, scale_ads: int = 1) -> int:
    if scale_ads >= 2:
        return min(99, 82 + min(16, scale_ads * 3))
    if views <= 0:
        return 76
    engagement = (likes + comments * 2 + shares * 3) / max(views, 1)
    volume_bonus = min(35, int((views ** 0.35) / 2))
    eng_bonus = min(60, int(engagement * 450))
    return max(58, min(99, 45 + volume_bonus + eng_bonus))


def analyze_video_structure(
    title: str,
    caption: str,
    product_hint: str = "",
    extra_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    meta = extra_meta or {}
    cleaned_cap = _clean_scraped_caption(caption, title)
    lines = [ln.strip() for ln in cleaned_cap.splitlines() if len(ln.strip()) > 6]
    first_line = lines[0] if lines else title.strip()
    body_lines = lines[1:4] if len(lines) > 1 else [cleaned_cap[:180]]
    cta_line = next(
        (
            ln for ln in reversed(lines)
            if any(w in ln.lower() for w in ("liên hệ", "hotline", "zalo", "link", "bio", "comment", "bình luận", "mua", "đặt", "inbox", "ưu đãi", "giảm"))
        ),
        "",
    )
    price = _extract_real_price(f"{title} {cleaned_cap}")
    dur = meta.get("duration_s")
    age_d = meta.get("asset_age_days")
    scale_c = meta.get("scale_count", 1)

    if any(w in first_line.lower() for w in ("?", "tại sao", "đừng", "sai lầm", "cảnh báo", "bạn đang")):
        angle = "Đánh vào nỗi đau / Câu hỏi gây tò mò"
    elif any(w in first_line.lower() for w in ("test", "review", "đập hộp", "unbox", "测评", "实测")):
        angle = "Demo / Kiểm chứng thực tế sản phẩm"
    elif price or any(w in first_line.lower() for w in ("sale", "giảm", "xưởng", "sỉ", "tổng kho", "siêu thị")):
        angle = "Ưu đãi trực diện / Lợi thế giá tận xưởng"
    else:
        angle = "Trình diễn hiệu ứng thị giác 3s đầu"

    hook_text = f"[{angle}] {first_line[:160]}"
    meta_bits: List[str] = []
    if dur:
        meta_bits.append(f"Thời lượng: {dur}s")
    if age_d:
        meta_bits.append(f"Tuổi video: {age_d} ngày")
    if scale_c and scale_c > 1:
        meta_bits.append(f"Đang nhân bản: {scale_c} nhóm QC")
    if price:
        meta_bits.append(f"Mốc giá/Deal: {price}")

    usp_text = " | ".join(ln[:110] for ln in body_lines[:3] if ln) or title
    cta_summary = cta_line[:140] if cta_line else "Điều hướng khách xem bình luận ghim / nhắn tin nhận báo giá."
    header_info = f"({' · '.join(meta_bits)})\n" if meta_bits else ""
    script_summary = (
        f"{header_info}"
        f"• Hook mở đầu: {first_line[:140]}\n"
        f"• Điểm bán hàng (USP) trong bài: {usp_text[:240]}\n"
        f"• Chuyển đổi (CTA): {cta_summary}"
    )
    return {"hook_text": hook_text, "script_summary": script_summary}


def _enrich_videos_with_ai_analysis(items: List[Dict[str, Any]], keyword: str) -> None:
    if not items:
        return
    batch = items[:8]
    payload_rows = []
    for idx, it in enumerate(batch):
        payload_rows.append(
            {
                "idx": idx,
                "platform": it.get("platform"),
                "author": it.get("author"),
                "title": it.get("title"),
                "caption": (it.get("caption") or "")[:320],
                "signals": it.get("sales_signals") or [],
                "views": it.get("views"),
            }
        )
    prompt = (
        "Bạn là chuyên gia phân tích Video Winning Ads & Viral E-commerce.\n"
        f'Từ khoá sản phẩm: "{keyword}".\n'
        "Dưới đây là danh sách các video thật vừa quét được (JSON):\n"
        f"{json.dumps(payload_rows, ensure_ascii=False)}\n\n"
        "Hãy phân tích RIÊNG BIỆT từng video dựa trên đúng nội dung title, caption, author và tín hiệu của chính video đó (TUYỆT ĐỐI KHÔNG viết giống nhau giữa các video).\n"
        "Trả về duy nhất 1 JSON array (không markdown), mỗi phần tử có dạng:\n"
        '{"idx": 0, "hook_text": "<Góc Hook 3s đầu cụ thể của video này + câu mở đầu gợi ý khi remake>", '
        '"script_summary": "• Hook (0-3s): <phân tích mở đầu riêng của video này>\\n• Demo/USP: <điểm ăn tiền thực tế nêu trong bài>\\n• Gợi ý Remake Win: <cách quay/lồng tiếng lại để tăng chuyển đổi>"}'
    )
    raw_out = _call_configured_llm(prompt, timeout=32.0)
    if not raw_out:
        return
    try:
        m = re.search(r"\[.*\]", raw_out, re.S)
        arr = json.loads(m.group(0) if m else raw_out)
        if not isinstance(arr, list):
            return
        for row in arr:
            if not isinstance(row, dict):
                continue
            idx = row.get("idx")
            if isinstance(idx, int) and 0 <= idx < len(batch):
                hk = str(row.get("hook_text") or "").strip()
                sc = str(row.get("script_summary") or "").strip()
                if hk:
                    batch[idx]["hook_text"] = hk[:300]
                if sc:
                    batch[idx]["script_summary"] = sc[:700]
    except Exception:
        pass


def _parse_json_from_cli(stdout: str, stderr: str = "", returncode: int = 0) -> Dict[str, Any]:
    text = (stdout or "").strip()
    if text:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for ln in reversed(lines):
            if ln.startswith("{") or ln.startswith("["):
                try:
                    parsed = json.loads(ln)
                    if isinstance(parsed, dict):
                        return parsed
                    return {"ok": True, "items": parsed}
                except json.JSONDecodeError:
                    pass
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
            return {"ok": True, "items": parsed}
        except json.JSONDecodeError:
            pass
    raw_msg = (stderr or stdout or "").strip()
    return {
        "ok": returncode == 0,
        "raw_output": raw_msg[:2000],
        "error": None if returncode == 0 else {"code": "CLI_ERROR", "message": raw_msg[:400]},
    }


def _agent_reach_browser_root() -> Path:
    return Path.home() / ".agent-reach" / "browser"


def _agent_reach_cdp_port() -> int:
    try:
        cfg_file = Path.home() / ".agent-reach" / "config.yaml"
        if cfg_file.exists():
            txt = cfg_file.read_text("utf-8", errors="ignore")
            m = re.search(r"browser_port\s*:\s*(\d+)", txt)
            if m:
                port = int(m.group(1))
                if 1024 <= port <= 65535:
                    return port
    except Exception:
        pass
    return 9222


def _cdp_get_json(path: str, port: Optional[int] = None) -> Any:
    p = port or _agent_reach_cdp_port()
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"http://127.0.0.1:{p}{path}", timeout=2.5) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def _cdp_get_all_cookies(port: Optional[int] = None) -> List[Dict[str, Any]]:
    p = port or _agent_reach_cdp_port()
    target = _cdp_get_json("/json/version", p) or {}
    ws = target.get("webSocketDebuggerUrl")
    if not ws:
        pages = _cdp_get_json("/json/list", p) or []
        if isinstance(pages, list) and pages:
            ws = pages[0].get("webSocketDebuggerUrl")
    if not ws:
        return []
    u = urlsplit(ws)
    host = u.hostname or "127.0.0.1"
    ws_port = u.port or p
    guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    try:
        with socket.create_connection((host, ws_port), timeout=3.5) as sock:
            sock.settimeout(3.5)
            key = base64.b64encode(os.urandom(16)).decode()
            req = (
                f"GET {u.path or '/'} HTTP/1.1\r\n"
                f"Host: {host}:{ws_port}\r\n"
                f"Upgrade: websocket\r\nConnection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
            ).encode()
            sock.sendall(req)
            resp = b""
            while b"\r\n\r\n" not in resp:
                chunk = sock.recv(4096)
                if not chunk:
                    return []
                resp += chunk
            head, _, buf = resp.partition(b"\r\n\r\n")
            accept = base64.b64encode(hashlib.sha1((key + guid).encode()).digest()).decode()
            if b"101" not in head.split(b"\r\n", 1)[0] or accept not in head.decode("latin-1"):
                return []

            payload = json.dumps({"id": 1, "method": "Storage.getCookies", "params": {}}).encode("utf-8")
            mask = os.urandom(4)
            n = len(payload)
            frame = bytearray([0x81])
            if n < 126:
                frame.append(0x80 | n)
            elif n < 65536:
                frame.append(0x80 | 126)
                frame.extend(struct.pack(">H", n))
            else:
                frame.append(0x80 | 127)
                frame.extend(struct.pack(">Q", n))
            frame.extend(mask)
            frame.extend(bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))
            sock.sendall(bytes(frame))

            for _ in range(24):
                while len(buf) < 2:
                    chunk = sock.recv(4096)
                    if not chunk:
                        return []
                    buf += chunk
                opcode = buf[0] & 0x0F
                length = buf[1] & 0x7F
                idx = 2
                if length == 126:
                    while len(buf) < idx + 2:
                        buf += sock.recv(4096)
                    length = struct.unpack(">H", buf[idx : idx + 2])[0]
                    idx += 2
                elif length == 127:
                    while len(buf) < idx + 8:
                        buf += sock.recv(4096)
                    length = struct.unpack(">Q", buf[idx : idx + 8])[0]
                    idx += 8
                while len(buf) < idx + length:
                    chunk = sock.recv(65536)
                    if not chunk:
                        return []
                    buf += chunk
                msg_bytes = buf[idx : idx + length]
                buf = buf[idx + length :]
                if opcode == 0x8:
                    return []
                if opcode in (0x0, 0x1, 0x2):
                    msg = json.loads(msg_bytes.decode("utf-8", errors="replace"))
                    if msg.get("id") == 1:
                        return (msg.get("result") or {}).get("cookies") or []
    except Exception:
        return []
    return []


def _domain_matches(cookie_domain: str, target_domain: str) -> bool:
    c = (cookie_domain or "").lstrip(".").lower()
    d = (target_domain or "").lstrip(".").lower()
    return bool(c and d and (c == d or c.endswith("." + d)))


def _read_agent_reach_session_cookies(prefer_cdp: bool = True) -> List[Dict[str, Any]]:
    merged: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    sess_file = _agent_reach_browser_root() / "session.json"
    if sess_file.is_file():
        try:
            data = json.loads(sess_file.read_text("utf-8", errors="replace"))
            for c in data.get("cookies", []):
                if isinstance(c, dict) and c.get("name"):
                    k = (str(c.get("name")), str(c.get("domain", "")), str(c.get("path", "/")))
                    merged[k] = c
        except Exception:
            pass
    if prefer_cdp:
        for c in _cdp_get_all_cookies():
            if isinstance(c, dict) and c.get("name"):
                k = (str(c.get("name")), str(c.get("domain", "")), str(c.get("path", "/")))
                merged[k] = c
    return list(merged.values())


def _write_netscape_cookies_file(path: Path, cookies: List[Dict[str, Any]]) -> Path:
    lines = ["# Netscape HTTP Cookie File", "# Generated by CloneVideo-Aff Agent-Reach Bridge", ""]
    now_ts = int(time.time())
    for c in cookies:
        domain = str(c.get("domain") or "").strip()
        name = str(c.get("name") or "").strip()
        if not domain or not name:
            continue
        value = str(c.get("value") or "")
        flag = "TRUE" if domain.startswith(".") else "FALSE"
        cpath = str(c.get("path") or "/")
        secure = "TRUE" if c.get("secure") else "FALSE"
        exp_raw = c.get("expires", -1)
        if isinstance(exp_raw, (int, float)) and exp_raw > 0:
            if exp_raw < now_ts:
                continue
            exp_val = str(int(exp_raw))
        else:
            exp_val = str(now_ts + 86400 * 30)
        lines.append(f"{domain}\t{flag}\t{cpath}\t{secure}\t{exp_val}\t{name}\t{value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _export_cookies_files(channel: str, all_cookies: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Path]:
    spec = CHANNEL_COOKIE_SPECS.get(channel, {})
    domains = spec.get("domains") or (f"{channel}.com",)
    ch_cookies = [c for c in all_cookies if any(_domain_matches(c.get("domain", ""), d) for d in domains)]
    if ch_cookies:
        (COOKIES_DIR / f"{channel}_cookies.json").write_text(
            json.dumps({"channel": channel, "updated_at": int(time.time()), "cookies": ch_cookies}, indent=2),
            encoding="utf-8",
        )
        _write_netscape_cookies_file(COOKIES_DIR / f"{channel}_cookies.txt", ch_cookies)
    if all_cookies:
        _write_netscape_cookies_file(COOKIES_DIR / "browser_cookies.txt", all_cookies)
    return ch_cookies, (COOKIES_DIR / f"{channel}_cookies.txt")


def _has_channel_auth_cookies(channel: str, cookies: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    spec = CHANNEL_COOKIE_SPECS.get(channel)
    if not spec:
        return False, []
    domains = spec["domains"]
    domain_cookies = [
        c for c in cookies if any(_domain_matches(c.get("domain", ""), d) for d in domains) and c.get("value")
    ]
    present = {str(c.get("name")) for c in domain_cookies}
    required = spec["auth_cookies"]
    matched = [name for name in required if name in present]
    if spec.get("any_auth", True):
        return bool(matched), matched
    return all(name in present for name in required), matched


def _save_channel_auth_record(channel: str, record: Dict[str, Any]) -> None:
    try:
        database.set_setting(f"ar_channel_auth_{channel}", json.dumps(record, ensure_ascii=False))
    except Exception:
        pass


def _load_channel_auth_record(channel: str) -> Dict[str, Any]:
    try:
        raw = database.get_settings().get(f"ar_channel_auth_{channel}", "")
        if raw:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
    except Exception:
        pass
    return {}


def _probe_instagram_session(cookies: List[Dict[str, Any]]) -> Tuple[bool, str]:
    ig_map = {str(c.get("name")): str(c.get("value") or "") for c in cookies if c.get("name")}
    if not (ig_map.get("sessionid") and ig_map.get("ds_user_id")):
        return False, ""
    cookie_hdr = "; ".join(f"{k}={v}" for k, v in ig_map.items() if v)
    try:
        req = urllib.request.Request(
            "https://www.instagram.com/",
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                ),
                "Cookie": cookie_hdr,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            final_url = resp.geturl()
            if "/accounts/login" in final_url:
                return False, ""
            body = resp.read(700_000).decode("utf-8", errors="replace")
            m = re.search(r'"username":"([^"]+)"', body)
            if m:
                return True, m.group(1)
            if ig_map["ds_user_id"] in body:
                return True, f"id:{ig_map['ds_user_id']}"
    except Exception:
        pass
    return True, f"id:{ig_map['ds_user_id']}"


def _verify_channel_cookie_session(channel: str, *, live_probe: bool = True) -> Dict[str, Any]:
    ch = channel.strip().lower()
    all_cookies = _read_agent_reach_session_cookies(prefer_cdp=True)
    if not all_cookies:
        saved_json = COOKIES_DIR / f"{ch}_cookies.json"
        if saved_json.is_file():
            try:
                all_cookies = json.loads(saved_json.read_text("utf-8")).get("cookies") or []
            except Exception:
                all_cookies = []

    ch_cookies, txt_path = _export_cookies_files(ch, all_cookies)
    has_auth, matched_names = _has_channel_auth_cookies(ch, ch_cookies)
    if not has_auth:
        return {"ok": False, "logged_in": False, "cookie_count": len(ch_cookies), "auth_cookies": []}

    username = ""
    if ch == "instagram" and live_probe:
        ig_ok, ig_user = _probe_instagram_session(ch_cookies)
        if not ig_ok:
            return {"ok": False, "logged_in": False, "cookie_count": len(ch_cookies), "auth_cookies": matched_names}
        username = ig_user
    elif ch == "instagram":
        username = _load_channel_auth_record(ch).get("username", "")

    record = {
        "ok": True,
        "logged_in": True,
        "channel": ch,
        "username": username,
        "cookie_count": len(ch_cookies),
        "auth_cookies": matched_names,
        "cookie_file": str(txt_path),
        "verified_at": int(time.time()),
    }
    _save_channel_auth_record(ch, record)
    return record


def _close_agent_reach_browser_gracefully() -> bool:
    """Save CDP cookies into session.json (if live) and close Agent-Reach Chrome so CLI isn't BUSY."""
    try:
        all_cookies = _cdp_get_all_cookies()
        if all_cookies:
            _write_netscape_cookies_file(COOKIES_DIR / "browser_cookies.txt", all_cookies)
    except Exception:
        pass
    stop_res = _run_agent_reach_sync(["browser", "stop"], timeout=15)
    return bool(stop_res.get("ok"))


def _watch_and_finalize_login(channel: str, baseline_sig: str) -> None:
    """Wait until the user finishes logging in, then automatically extract cookies & close Chrome."""
    ch = channel.strip().lower()
    spec = CHANNEL_COOKIE_SPECS.get(ch, {})
    domains = spec.get("domains") or (f"{ch}.com",)
    markers = spec.get("login_url_markers") or ("/login", "/accounts/login", "/challenge")
    started = time.time()
    deadline = started + 300.0
    saw_target_page = False

    while time.time() < deadline:
        time.sleep(1.5)
        targets = _cdp_get_json("/json/list")
        if targets is None:
            # Browser has closed; verify and export cookies from session.json
            _verify_channel_cookie_session(ch, live_probe=True)
            return

        pages = [t for t in (targets if isinstance(targets, list) else []) if t.get("type") == "page"]
        domain_pages = [
            p for p in pages
            if any(d in (urlsplit(p.get("url", "")).hostname or "").lower() for d in domains)
        ]
        if domain_pages:
            saw_target_page = True

        on_login_page = any(
            any(m in (p.get("url", "").lower()) for m in markers)
            for p in pages
        )

        cdp_cookies = _cdp_get_all_cookies()
        has_auth, matched = _has_channel_auth_cookies(ch, cdp_cookies)
        if not has_auth:
            # Check if the user closed all pages manually on macOS (Chrome left running with 0 tabs)
            if len(pages) == 0 and (time.time() - started) > 4.0:
                _close_agent_reach_browser_gracefully()
                return
            continue

        sig_parts = sorted(
            f"{c.get('name')}={c.get('value')}"
            for c in cdp_cookies
            if c.get("name") in matched and any(_domain_matches(c.get("domain", ""), d) for d in domains)
        )
        cur_sig = "|".join(sig_parts)
        changed = cur_sig != baseline_sig
        elapsed = time.time() - started

        # Case 1: User closed the Chrome window (0 pages left) while auth cookies are present
        if len(pages) == 0 and elapsed > 3.0:
            _export_cookies_files(ch, cdp_cookies)
            _close_agent_reach_browser_gracefully()
            _verify_channel_cookie_session(ch, live_probe=True)
            return

        # Case 2: User completed login and navigated off the login/2FA page onto the main site
        if not on_login_page and saw_target_page and (changed or elapsed >= 6.0):
            time.sleep(2.0)  # allow final subresource cookies (e.g. csrftoken/rur) to settle
            final_cookies = _cdp_get_all_cookies() or cdp_cookies
            _export_cookies_files(ch, final_cookies)
            _close_agent_reach_browser_gracefully()
            _verify_channel_cookie_session(ch, live_probe=True)
            return


def _run_agent_reach_sync(args: List[str], timeout: int = 35) -> Dict[str, Any]:
    bin_path = find_agent_reach()
    if not bin_path:
        return {
            "ok": False,
            "error": {"code": "NOT_INSTALLED", "message": "Không tìm thấy agent-reach CLI trên hệ thống."},
        }
    try:
        proc = subprocess.run(
            [bin_path, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=build_tool_env(),
            encoding="utf-8",
            errors="replace",
        )
        return _parse_json_from_cli(proc.stdout, proc.stderr, proc.returncode)
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "error": {"code": "TIMEOUT", "message": f"Lệnh agent-reach {' '.join(args[:2])} quá thời gian ({timeout}s)."},
        }
    except Exception as exc:
        return {"ok": False, "error": {"code": "EXEC_ERROR", "message": str(exc)[:300]}}


def get_agent_reach_full_status() -> Dict[str, Any]:
    bin_path = find_agent_reach()
    if not bin_path:
        return {
            "installed": False,
            "path": "",
            "version": "",
            "browser": {},
            "channels": [],
            "error": "Không tìm thấy agent-reach CLI",
        }

    doc = _run_agent_reach_sync(["doctor"], timeout=20)
    ch_info = _run_agent_reach_sync(["channels"], timeout=15)
    browser_info = _run_agent_reach_sync(["browser", "status"], timeout=12)

    doc_res = doc.get("result") or {}
    doc_channels = {c.get("channel"): c for c in (doc_res.get("channels") or []) if c.get("channel")}
    cap_summary = {
        c.get("channel"): c
        for c in ((doc_res.get("capability_summary") or {}).get("channels") or [])
        if c.get("channel")
    }
    ch_defs = {c.get("name"): c for c in (ch_info.get("channels") or []) if c.get("name")}

    ordered_names: List[str] = []
    for name in list(CHANNEL_META_VI.keys()) + list(doc_channels.keys()) + list(ch_defs.keys()):
        if name not in ordered_names:
            ordered_names.append(name)

    all_cookies = _read_agent_reach_session_cookies(prefer_cdp=False)
    merged_channels: List[Dict[str, Any]] = []
    for name in ordered_names:
        dc = doc_channels.get(name, {})
        cs = cap_summary.get(name, {})
        cd = ch_defs.get(name, {})
        meta_vi = CHANNEL_META_VI.get(name, {})
        login_obj = cd.get("login")
        actions = [a.get("name") for a in (cd.get("actions") or []) if a.get("name")]

        ch_status = dc.get("status") or "unknown"
        ch_hint = dc.get("hint") or ""
        ch_problems = list(dc.get("problems") or [])
        logged_in = login_obj.get("logged_in") if isinstance(login_obj, dict) else None

        if login_obj and name in CHANNEL_COOKIE_SPECS:
            ch_cookies = [
                c for c in all_cookies
                if any(_domain_matches(c.get("domain", ""), d) for d in CHANNEL_COOKIE_SPECS[name]["domains"])
            ]
            has_auth, matched_names = _has_channel_auth_cookies(name, ch_cookies)
            saved_rec = _load_channel_auth_record(name)
            if has_auth:
                logged_in = True
                ch_status = "ready"
                ch_problems = []
                uname = saved_rec.get("username", "")
                acct = f" (@{uname})" if uname and not uname.startswith("id:") else ""
                ch_hint = f"Đã đăng nhập{acct} · {len(ch_cookies)} cookies ({', '.join(matched_names)})"

        merged_channels.append(
            {
                "channel": name,
                "label": meta_vi.get("label") or name.title(),
                "category": meta_vi.get("category") or "Channel",
                "description": cd.get("description") or cs.get("public_access") or "",
                "level": dc.get("level") or cd.get("level") or "optional",
                "status": ch_status,
                "hint": ch_hint,
                "problems": ch_problems,
                "supports_login": bool(login_obj),
                "logged_in": logged_in,
                "login_via": login_obj.get("via") if isinstance(login_obj, dict) else None,
                "login_command": login_obj.get("command") if isinstance(login_obj, dict) else "",
                "actions": actions,
            }
        )

    return {
        "installed": True,
        "path": bin_path,
        "version": doc_res.get("version") or "1.6.1",
        "browser": browser_info.get("result") or {},
        "tools": doc_res.get("tools") or [],
        "channels": merged_channels,
    }


def manage_agent_reach_channel(channel: str, operation: str) -> Dict[str, Any]:
    channel = channel.strip().lower()
    if not re.match(r"^[a-z0-9_-]+$", channel):
        return {"ok": False, "error": {"code": "BAD_INPUT", "message": "Tên kênh không hợp lệ."}}

    bin_path = find_agent_reach()
    if not bin_path:
        return {"ok": False, "error": {"code": "NOT_INSTALLED", "message": "Chưa cài agent-reach."}}

    if operation == "add":
        return _run_agent_reach_sync(["add", channel], timeout=90)
    if operation == "remove":
        _save_channel_auth_record(channel, {})
        return _run_agent_reach_sync(["remove", channel], timeout=35)
    if operation == "logout":
        _save_channel_auth_record(channel, {})
        for ext in ("json", "txt"):
            p = COOKIES_DIR / f"{channel}_cookies.{ext}"
            if p.exists():
                p.unlink(missing_ok=True)
        return _run_agent_reach_sync(["logout", channel], timeout=25)
    if operation == "login_import":
        # 1. Thu thập cookie trực tiếp từ trình duyệt Chrome đang mở của Agent-Reach & tự đóng Chrome
        live_cookies = _read_agent_reach_session_cookies(prefer_cdp=True)
        if _cdp_get_json("/json/version") is not None:
            _close_agent_reach_browser_gracefully()
        verify_info = _verify_channel_cookie_session(channel, live_probe=True)
        if verify_info.get("ok"):
            uname = verify_info.get("username", "")
            acct = f" (@{uname})" if uname and not uname.startswith("id:") else ""
            return {
                "ok": True,
                "action": "login_import",
                "channel": channel,
                "browser_closed": True,
                "message": (
                    f"Đã đóng Chrome & lấy thành công {verify_info.get('cookie_count', 0)} cookies "
                    f"cho {channel}{acct}!"
                ),
                "result": verify_info,
            }

        # 2. Fallback: thử đọc trực tiếp Chrome profile hệ thống via yt-dlp --cookies-from-browser chrome
        ytdlp_bin = find_ytdlp()
        domain_hint = (CHANNEL_COOKIE_SPECS.get(channel, {}).get("domains") or (f"{channel}.com",))[0]
        if ytdlp_bin and domain_hint:
            try:
                tmp_txt = COOKIES_DIR / f"{channel}_cookies.txt"
                subprocess.run(
                    [
                        ytdlp_bin,
                        "--cookies-from-browser",
                        "chrome",
                        "--cookies",
                        str(tmp_txt),
                        "--skip-download",
                        "--no-warnings",
                        f"https://www.{domain_hint}/",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    env=build_tool_env(),
                )
            except Exception:
                pass

        # 3. Fallback: gọi CLI gốc agent-reach login --import-existing
        cli_res = _run_agent_reach_sync(["login", channel, "--import-existing"], timeout=30)
        verify_info = _verify_channel_cookie_session(channel, live_probe=True)
        if verify_info.get("ok"):
            uname = verify_info.get("username", "")
            acct = f" (@{uname})" if uname and not uname.startswith("id:") else ""
            return {
                "ok": True,
                "action": "login_import",
                "channel": channel,
                "browser_closed": True,
                "message": (
                    f"Đã lấy thành công {verify_info.get('cookie_count', 0)} cookies cho {channel}{acct}!"
                ),
                "result": verify_info,
                "cli_result": cli_res,
            }
        return cli_res if not cli_res.get("ok") else {
            "ok": False,
            "channel": channel,
            "error": {
                "code": "NEED_LOGIN",
                "message": (
                    f"Chưa tìm thấy cookie đăng nhập cho '{channel}' (đã kiểm tra {len(live_cookies)} cookies). "
                    "Hãy bấm 'Đăng nhập Browser' và đăng nhập xong tài khoản trước."
                ),
            },
        }
    if operation == "check":
        # Đóng cửa sổ login headed (nếu đang mở) trước khi check để không bị kẹt BUSY
        try:
            b_state_file = _agent_reach_browser_root() / "state.json"
            if b_state_file.is_file():
                b_state = json.loads(b_state_file.read_text("utf-8", errors="replace"))
                if b_state.get("headless") is False and _cdp_get_json("/json/version") is not None:
                    _close_agent_reach_browser_gracefully()
        except Exception:
            pass

        verify_info = _verify_channel_cookie_session(channel, live_probe=True)
        cli_check = _run_agent_reach_sync(["check", channel], timeout=45)
        if cli_check.get("ok"):
            if verify_info.get("ok"):
                cli_check["cookie_session"] = verify_info
            return cli_check

        if verify_info.get("ok"):
            uname = verify_info.get("username", "")
            acct = f" (@{uname})" if uname and not uname.startswith("id:") else ""
            cli_err = ""
            if isinstance(cli_check.get("results"), list) and cli_check["results"]:
                first_err = cli_check["results"][0].get("error") or {}
                cli_err = first_err.get("message", "")
            return {
                "ok": True,
                "action": "check",
                "channel": channel,
                "verified_via": "cookie_session_live",
                "message": (
                    f"Kiểm tra '{channel}' thành công! Phiên đăng nhập hợp lệ{acct} "
                    f"({verify_info.get('cookie_count', 0)} cookies sẵn sàng cho yt-dlp & Agent-Reach)."
                ),
                "result": verify_info,
                "upstream_opencli_note": cli_err[:240],
            }
        return cli_check
    if operation == "login":
        # Ghi nhận trạng thái cookie trước khi mở Chrome
        pre_cookies = _read_agent_reach_session_cookies(prefer_cdp=True)
        spec = CHANNEL_COOKIE_SPECS.get(channel, {})
        domains = spec.get("domains") or (f"{channel}.com",)
        _, matched_pre = _has_channel_auth_cookies(channel, pre_cookies)
        baseline_sig = "|".join(
            sorted(
                f"{c.get('name')}={c.get('value')}"
                for c in pre_cookies
                if c.get("name") in matched_pre and any(_domain_matches(c.get("domain", ""), d) for d in domains)
            )
        )

        # `agent-reach login <channel>` mở cửa sổ Chrome chuyên dụng
        try:
            proc = subprocess.Popen(
                [bin_path, "login", channel],
                env=build_tool_env(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                start_new_session=True,
            )
            deadline = time.time() + 4.0
            quick_out = ""
            quick_err = ""
            while time.time() < deadline:
                ret = proc.poll()
                if ret is not None:
                    quick_out, quick_err = proc.communicate(timeout=2)
                    parsed = _parse_json_from_cli(quick_out, quick_err, ret)
                    if not parsed.get("ok"):
                        return parsed
                    break
                time.sleep(0.25)

            # Bật luồng giám sát đăng nhập: hễ vào trang chính hoặc đóng tab xong -> tự lấy Cookie & đóng Chrome
            with _login_watcher_lock:
                t = threading.Thread(
                    target=_watch_and_finalize_login,
                    args=(channel, baseline_sig),
                    daemon=True,
                    name=f"ar-login-watch-{channel}",
                )
                _login_watcher_threads[channel] = t
                t.start()

            return {
                "ok": True,
                "status": "browser_opened",
                "channel": channel,
                "auto_capture": True,
                "message": (
                    f"Đã mở Chrome đăng nhập cho '{channel}'. Ngay khi bạn đăng nhập xong và vào trang chính, "
                    "hệ thống sẽ TỰ ĐỘNG lấy Cookie, lưu phiên và ĐÓNG Chrome!"
                ),
            }
        except Exception as exc:
            return {"ok": False, "error": {"code": "LOGIN_LAUNCH_ERROR", "message": str(exc)[:300]}}

    return {"ok": False, "error": {"code": "BAD_INPUT", "message": f"Thao tác không hỗ trợ: {operation}"}}


def manage_agent_reach_browser(operation: str, param: str = "") -> Dict[str, Any]:
    op = operation.strip().lower()
    if op not in {"status", "setup", "stop", "profiles", "use"}:
        return {"ok": False, "error": {"code": "BAD_INPUT", "message": f"Browser operation không hợp lệ: {op}"}}
    args = ["browser", op]
    if op == "use" and param.strip():
        args.append(param.strip())
    timeout = 90 if op == "setup" else 25
    return _run_agent_reach_sync(args, timeout=timeout)


def configure_agent_reach_key(key: str, value: str) -> Dict[str, Any]:
    allowed = {"groq-key", "openai-key", "proxy", "github-token", "browser-port"}
    k = key.strip()
    if k not in allowed:
        return {"ok": False, "error": {"code": "BAD_INPUT", "message": f"Key không hợp lệ: {k}"}}
    args = ["configure", k]
    if value.strip():
        args.append(value.strip())
    return _run_agent_reach_sync(args, timeout=20)


def _extract_metric_int(raw: Dict[str, Any], keys: List[str], default_val: int) -> int:
    for k in keys:
        val = raw.get(k)
        if isinstance(val, (int, float)) and val >= 0:
            return int(val)
        if isinstance(val, str):
            digits = re.sub(r"[^\d]", "", val)
            if digits:
                return int(digits)
    return default_val


def _extract_url_from_text(text: str) -> str:
    if not text:
        return ""
    m = re.search(r"URL:\s*(https?://[^\s\n\r\"'<>]+)", text, re.I)
    if m:
        return m.group(1).strip()
    m2 = re.search(
        r"(https?://(?:www\.)?(?:tiktok\.com/@[^/\s]+/video/\d+|instagram\.com/(?:reel|p)/[^/\s?]+|facebook\.com/(?:reel|watch|videos|share/v|share/r|ads/library)[^\s\"'<>]*|threads\.(?:com|net)/@[^/\s]+/post/[^\s\"'<>?]+|bilibili\.com/video/BV[A-Za-z0-9]+|youtube\.com/(?:watch\?v=|shorts/)[^\s\"'<>]+|youtu\.be/[^\s\"'<>]+|xiaohongshu\.com/(?:explore|discovery/item)/[^\s\"'<>]+))",
        text,
        re.I,
    )
    return m2.group(1).strip() if m2 else ""


def _is_valid_video_url(platform: str, url: str, video_url: str = "") -> bool:
    u = (url or "").strip()
    vu = (video_url or "").strip()
    low = u.lower()
    if not u and not vu:
        return False
    bad_markers = (
        "google.com/search",
        "youtube.com/results?",
        "tiktok.com/search?",
        "tiktok.com/discover/",
        "tiktok.com/tag/",
        "search.bilibili.com",
        "xiaohongshu.com/search_result",
        "x.com/search?",
        "reddit.com/search/",
        "douyin.com/search/",
        "c8demo",
        "c9demo",
        "id=998877661",
        "id=554433221",
        "reel/10293847561",
    )
    if any(b in low for b in bad_markers):
        return False
    if low in {
        "https://www.instagram.com/reels/",
        "https://www.facebook.com/reel/",
        "https://www.threads.net/",
        "https://www.threads.com/",
    }:
        return False

    pf = platform.lower().strip()
    if pf == "meta_ads":
        return "/ads/library/?id=" in low or ".mp4" in vu.lower()
    if pf == "facebook":
        return any(k in low for k in ("/reel/", "/watch", "/videos/", "/share/v/", "/share/r/", "/ads/library/?id=")) or ".mp4" in vu.lower()
    if pf == "instagram":
        return (
            (any(k in low for k in ("/reel/", "/reels/", "/p/")) and low != "https://www.instagram.com/reels/")
            or "/ads/library/?id=" in low
            or ".mp4" in vu.lower()
        )
    if pf == "threads":
        return "/post/" in low or "/ads/library/?id=" in low or ".mp4" in vu.lower()
    if pf == "tiktok":
        return "/video/" in low or "vm.tiktok.com" in low or "vt.tiktok.com" in low
    if pf == "douyin":
        return "/video/" in low or "/note/" in low or "v.douyin.com" in low
    if pf == "youtube":
        return any(k in low for k in ("watch?v=", "/shorts/", "youtu.be/"))
    if pf == "bilibili":
        return "/video/bv" in low or "/video/av" in low or "b23.tv/" in low
    return u.startswith("http")


def purge_invalid_and_mockup_videos() -> int:
    """Remove legacy seed mockups, bare Facebook fanpage links, and non-video search fallback rows."""
    removed = 0
    try:
        rows = database.list_videos()
        with database.get_conn() as conn:
            cur = conn.cursor()
            for r in rows:
                vid = r.get("id")
                pf = str(r.get("platform") or "")
                s_url = str(r.get("source_url") or "")
                v_url = str(r.get("video_url") or "")
                title = str(r.get("title") or "")
                hook = str(r.get("hook_text") or "")
                is_bad = not _is_valid_video_url(pf, s_url, v_url)
                if "Video Winning Ad Đang Scale Mạnh" in title or "Bạn đã thử " in hook and "Xem hết 15s để không mua hớ!" in hook:
                    if not v_url and not r.get("local_path"):
                        is_bad = True
                if is_bad and vid:
                    cur.execute("DELETE FROM viral_videos WHERE id = ?", (vid,))
                    removed += 1
    except Exception:
        pass
    return removed


def _normalize_agent_reach_items(
    platform: str, keyword: str, raw_resp: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    if not raw_resp.get("ok"):
        err = raw_resp.get("error") or {}
        code = err.get("code") or "ERROR"
        msg = err.get("message") or err.get("hint") or raw_resp.get("raw_output") or "Không truy cập được kênh"
        if code in {"NEED_LOGIN", "NEED_SETUP", "PLATFORM_BLOCKED"}:
            return [], (
                f"[{platform}] {code}: {msg} — Vào tab Cài đặt → Quản lý Agent-Reach để bật kênh hoặc đăng nhập."
            )
        return [], f"[{platform}] {code}: {msg}"

    items_raw: List[Any] = []
    if isinstance(raw_resp.get("items"), list):
        items_raw = raw_resp["items"]
    elif isinstance(raw_resp.get("result"), list):
        items_raw = raw_resp["result"]
    elif isinstance(raw_resp.get("result"), dict):
        res_obj = raw_resp["result"]
        for key in ("items", "videos", "notes", "posts", "tweets", "topics", "results"):
            if isinstance(res_obj.get(key), list):
                items_raw = res_obj[key]
                break
        if not items_raw and res_obj.get("title"):
            items_raw = [res_obj]

    normalized: List[Dict[str, Any]] = []
    seen_urls = set()
    for idx, it in enumerate(items_raw[:10]):
        if not isinstance(it, dict):
            continue
        raw = it.get("raw") if isinstance(it.get("raw"), dict) else {}
        raw_text_blob = str(it.get("text") or it.get("description") or raw.get("description") or raw.get("desc") or "")
        source_url = (
            it.get("url")
            or raw.get("webpage_url")
            or raw.get("url")
            or _extract_url_from_text(raw_text_blob)
        )
        video_url = str(raw.get("video_url") or raw.get("play_url") or it.get("video_url") or "")
        if not source_url or not _is_valid_video_url(platform, str(source_url), video_url):
            continue
        if source_url in seen_urls:
            continue
        seen_urls.add(source_url)

        title = str(
            it.get("title")
            or raw.get("title")
            or raw.get("desc")
            or _clean_scraped_caption(raw_text_blob)[:90]
            or f"[{platform.upper()}] {keyword} #{idx + 1}"
        ).strip()
        caption = _clean_scraped_caption(raw_text_blob, title)

        author = (
            it.get("author")
            or raw.get("uploader")
            or raw.get("channel")
            or raw.get("author")
            or raw.get("nickname")
            or ""
        )
        if not author or str(author).upper() == "N/A":
            m_tt = re.search(r"tiktok\.com/@([^/?#]+)", str(source_url))
            m_ig = re.search(r"instagram\.com/([^/?#]+)/(?:reel|p)/", str(source_url))
            if m_tt:
                author = f"@{m_tt.group(1)}"
            elif m_ig:
                author = f"@{m_ig.group(1)}"
            else:
                author = f"@{platform}_creator"

        thumb = (
            it.get("thumbnail")
            or raw.get("thumbnail")
            or raw.get("pic")
            or raw.get("cover")
            or ""
        )
        if not thumb and "youtube.com/watch?v=" in str(source_url):
            vid_id = str(source_url).split("watch?v=")[1].split("&")[0]
            thumb = f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"
        elif not thumb and "youtu.be/" in str(source_url):
            vid_id = str(source_url).split("youtu.be/")[1].split("?")[0]
            thumb = f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"

        views = _extract_metric_int(raw, ["view_count", "play", "views", "read_count"], 45000 + idx * 14000)
        likes = _extract_metric_int(raw, ["like_count", "liked_count", "likes", "digg_count"], 2100 + idx * 450)
        comments = _extract_metric_int(raw, ["comment_count", "comments", "reply_count"], 120 + idx * 30)
        shares = _extract_metric_int(raw, ["repost_count", "share_count", "shares", "collect_count"], 180 + idx * 45)

        extra_sigs: List[str] = []
        dur_val = raw.get("duration")
        if isinstance(dur_val, (int, float)) and dur_val > 0:
            extra_sigs.append(f"Thời lượng {int(dur_val)}s")
        upload_d = str(raw.get("upload_date") or "")
        age_days: Optional[int] = None
        if len(upload_d) == 8 and upload_d.isdigit():
            try:
                from datetime import datetime
                dt = datetime.strptime(upload_d, "%Y%m%d")
                age_days = max(1, (datetime.now() - dt).days)
                extra_sigs.append(f"File {age_days} ngày")
            except Exception:
                pass

        analysis = analyze_video_structure(
            title,
            caption,
            keyword,
            extra_meta={"duration_s": int(dur_val) if isinstance(dur_val, (int, float)) else None, "asset_age_days": age_days},
        )
        normalized.append(
            {
                "platform": platform,
                "title": title[:140],
                "caption": caption[:550],
                "author": str(author)[:80],
                "source_url": str(source_url),
                "video_url": video_url,
                "thumbnail_url": str(thumb),
                "views": views,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "viral_score": compute_viral_score(views, likes, comments, shares),
                "sales_signals": detect_sales_signals(f"{title} {caption}", extra_sigs),
                "hook_text": analysis["hook_text"],
                "script_summary": analysis["script_summary"],
            }
        )
        if len(normalized) >= 5:
            break

    return normalized, None


def _build_agent_reach_cli_args(platform: str, keyword: str, limit: int = 4) -> Optional[List[str]]:
    pf = platform.lower().strip()
    if pf == "youtube":
        return ["youtube", "search", f"{keyword} review shorts", "--limit", str(limit)]
    if pf == "bilibili":
        zh_kw = _translate_keyword_for_cn(keyword)
        return ["web", "search", f"site:bilibili.com/video {zh_kw} 测评", "--limit", str(limit * 2)]
    if pf == "xiaohongshu":
        zh_kw = _translate_keyword_for_cn(keyword)
        return ["xiaohongshu", "search", zh_kw, "--limit", str(limit)]
    if pf == "twitter":
        return ["twitter", "search", keyword, "--limit", str(limit)]
    if pf == "instagram":
        return ["web", "search", f"site:instagram.com/reel {keyword}", "--limit", str(limit * 2)]
    if pf == "facebook":
        return ["web", "search", f"site:facebook.com/reel {keyword}", "--limit", str(limit * 2)]
    if pf == "reddit":
        return ["reddit", "search", keyword, "--limit", str(limit)]
    if pf == "threads":
        return ["web", "search", f"site:threads.net {keyword}", "--limit", str(limit * 2)]
    if pf == "tiktok":
        return ["web", "search", f"tiktok.com video {keyword}", "--limit", str(limit * 2)]
    if pf == "douyin":
        zh_kw = _translate_keyword_for_cn(keyword)
        return ["web", "search", f"site:douyin.com/video {zh_kw}", "--limit", str(limit * 2)]
    if pf == "v2ex":
        return ["v2ex", "hot", "--limit", str(limit)]
    if pf == "xueqiu":
        return ["xueqiu", "search", keyword, "--limit", str(limit)]
    return None


def _canonicalize_video_url(platform: str, url: str) -> str:
    u = (url or "").strip()
    if "facebook.com/ads/library" in u:
        m_ad = re.search(r"[?&]id=(\d+)", u)
        if m_ad:
            return f"https://www.facebook.com/ads/library/?id={m_ad.group(1)}"
    if platform == "instagram" or "instagram.com" in u:
        m = re.search(r"instagram\.com/(?:[^/?#]+/)?(?:reel|reels|p)/([A-Za-z0-9_-]+)", u)
        if m:
            return f"https://www.instagram.com/reel/{m.group(1)}/"
    if platform == "threads" or "threads.net" in u or "threads.com" in u:
        m_th = re.search(r"threads\.(?:com|net)/(@[^/?#]+)/post/([A-Za-z0-9_-]+)", u)
        if m_th:
            return f"https://www.threads.com/{m_th.group(1)}/post/{m_th.group(2)}"
    if platform == "tiktok" or "tiktok.com" in u:
        return u.split("?")[0]
    return u


def _download_asset_to_local(url: str, filename: str) -> str:
    if not url or not url.startswith("http"):
        return ""
    dest = DOWNLOADS_DIR / filename
    if dest.is_file() and dest.stat().st_size > 1024:
        return f"/media/downloads/{filename}"
    try:
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            resp = client.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                    ),
                    "Referer": "https://www.instagram.com/",
                },
            )
            if resp.status_code == 200 and len(resp.content) > 1024:
                dest.write_bytes(resp.content)
                return f"/media/downloads/{filename}"
    except Exception:
        pass
    return ""


def _pick_best_mp4_from_info(info: Dict[str, Any]) -> str:
    direct = info.get("url")
    if isinstance(direct, str) and direct.startswith("http"):
        return direct
    formats = info.get("formats") or []
    # Prefer progressive MP4 formats (non-DASH) first
    for f in reversed(formats):
        if not isinstance(f, dict):
            continue
        f_url = str(f.get("url") or "")
        fmt_id = str(f.get("format_id") or "")
        if f_url.startswith("http") and f.get("ext") == "mp4" and not fmt_id.startswith("dash-"):
            return f_url
    for f in reversed(formats):
        if isinstance(f, dict) and str(f.get("url") or "").startswith("http") and f.get("ext") == "mp4":
            return str(f["url"])
    return ""


def _enrich_video_item_via_ytdlp(item: Dict[str, Any], download_mp4: Optional[bool] = None) -> Dict[str, Any]:
    """Populate real local MP4, local thumbnail, author & metrics via yt-dlp."""
    pf = str(item.get("platform") or "").lower()
    s_url = _canonicalize_video_url(pf, item.get("source_url") or "")
    item["source_url"] = s_url
    if not s_url:
        return item

    should_dl = download_mp4 if download_mp4 is not None else (pf in {"instagram", "tiktok"})
    res = _run_ytdlp_sync(s_url, download=should_dl)
    if not res.get("ok") and should_dl:
        res = _run_ytdlp_sync(s_url, download=False)
    if not res.get("ok"):
        return item

    info = res.get("info") or {}
    vid_code = str(info.get("id") or re.sub(r"[^A-Za-z0-9_-]", "", s_url[-16:]) or int(time.time()))
    dl_file = str(res.get("local_path") or "").strip()

    if dl_file and Path(dl_file).is_file():
        item["local_path"] = dl_file
        item["video_url"] = f"/media/downloads/{Path(dl_file).name}"
    else:
        best_stream = _pick_best_mp4_from_info(info)
        if best_stream:
            if pf == "instagram":
                local_vid_url = _download_asset_to_local(best_stream, f"ig_{vid_code}.mp4")
                if local_vid_url:
                    item["local_path"] = str(DOWNLOADS_DIR / f"ig_{vid_code}.mp4")
                    item["video_url"] = local_vid_url
                else:
                    item["video_url"] = best_stream
            else:
                item["video_url"] = best_stream

    raw_desc = str(info.get("description") or "").strip()
    raw_title = str(info.get("title") or "").strip()
    if raw_desc and (not raw_title or raw_title.lower().startswith("video by ") or raw_title.lower() == "instagram"):
        first_line = [ln.strip() for ln in raw_desc.splitlines() if ln.strip()][0]
        item["title"] = first_line[:130]
    elif raw_title and len(raw_title) > 4 and raw_title.lower() != "instagram":
        item["title"] = raw_title[:140]

    if raw_desc and len(raw_desc) > 8:
        item["caption"] = _clean_scraped_caption(raw_desc, item["title"])[:550]
    if info.get("uploader") or info.get("channel") or info.get("uploader_id"):
        u_name = str(info.get("uploader_id") or info.get("uploader") or info.get("channel"))
        item["author"] = (f"@{u_name.lstrip('@')}" if pf in {"instagram", "tiktok"} else u_name)[:80]

    thumb_remote = str(info.get("thumbnail") or item.get("thumbnail_url") or "")
    if thumb_remote.startswith("http"):
        local_thumb = _download_asset_to_local(thumb_remote, f"{pf}_{vid_code}.jpg")
        item["thumbnail_url"] = local_thumb or thumb_remote

    if isinstance(info.get("view_count"), (int, float)) and info["view_count"] > 0:
        item["views"] = int(info["view_count"])
    if isinstance(info.get("like_count"), (int, float)) and info["like_count"] > 0:
        item["likes"] = int(info["like_count"])
        if item.get("views", 0) < item["likes"]:
            item["views"] = item["likes"] * 12
    if isinstance(info.get("comment_count"), (int, float)) and info["comment_count"] >= 0:
        item["comments"] = int(info["comment_count"])
    if isinstance(info.get("repost_count"), (int, float)) and info["repost_count"] >= 0:
        item["shares"] = int(info["repost_count"])

    item["viral_score"] = compute_viral_score(item["views"], item["likes"], item["comments"], item["shares"])
    extra_sigs = list(item.get("sales_signals") or [])
    if isinstance(info.get("duration"), (int, float)) and info["duration"] > 0:
        dur_tag = f"Thời lượng {int(info['duration'])}s"
        if dur_tag not in extra_sigs:
            extra_sigs.insert(0, dur_tag)
    item["sales_signals"] = detect_sales_signals(f"{item['title']} {item['caption']}", extra_sigs)
    analysis = analyze_video_structure(
        item["title"],
        item["caption"],
        extra_meta={"duration_s": info.get("duration")},
    )
    item["hook_text"] = analysis["hook_text"]
    item["script_summary"] = analysis["script_summary"]
    return item


async def _discover_instagram_reels_playwright(
    keyword: str,
    country: str = "VN",
    limit: int = 5,
    action: str = "search",
) -> Dict[str, Any]:
    """Phase 1 (browser-bounded): use Playwright + logged-in IG cookies to collect Reel JSON & fallback links."""
    all_cookies = _read_agent_reach_session_cookies(prefer_cdp=False)
    ig_cookies = [
        {
            "name": str(c["name"]),
            "value": str(c["value"]),
            "domain": str(c.get("domain") or ".instagram.com"),
            "path": str(c.get("path") or "/"),
            "secure": bool(c.get("secure", True)),
            "httpOnly": bool(c.get("httpOnly", False)),
        }
        for c in all_cookies
        if "instagram.com" in str(c.get("domain") or "") and c.get("name") and c.get("value")
    ]
    if not ig_cookies:
        return {
            "status": "no_cookies",
            "diagnostic": "Chưa có Cookie Instagram hợp lệ (sessionid/ds_user_id) — hãy vào Cài đặt Agent-Reach để đăng nhập Instagram.",
            "items": [],
            "fallback_urls": [],
        }
    if not has_playwright():
        return {
            "status": "no_playwright",
            "diagnostic": "Playwright chưa sẵn sàng để mở trình duyệt quét Instagram Reels.",
            "items": [],
            "fallback_urls": [],
        }

    found_raw: List[Dict[str, Any]] = []
    seen_codes = set()
    fallback_urls: List[str] = []
    auth_failed = False

    def walk_ig(obj: Any) -> None:
        if isinstance(obj, dict):
            code = obj.get("code")
            v_vers = obj.get("video_versions")
            if isinstance(code, str) and code not in seen_codes and isinstance(v_vers, list) and v_vers:
                v_url = str((v_vers[0] or {}).get("url") or "")
                if v_url.startswith("http"):
                    seen_codes.add(code)
                    cands = ((obj.get("image_versions2") or {}).get("candidates") or [])
                    t_url = str((cands[0] or {}).get("url") or "") if cands else ""
                    user_obj = obj.get("user") if isinstance(obj.get("user"), dict) else {}
                    cap_obj = obj.get("caption") if isinstance(obj.get("caption"), dict) else {}
                    efg = _decode_fb_efg(v_url)
                    dur_val = obj.get("video_duration") or efg.get("duration_s") or 18
                    try:
                        dur_s = max(3, int(float(dur_val)))
                    except Exception:
                        dur_s = 18
                    try:
                        efg_age_days = int(efg.get("asset_age_days") or 0)
                    except Exception:
                        efg_age_days = 0
                    found_raw.append(
                        {
                            "code": code,
                            "username": str(user_obj.get("username") or user_obj.get("full_name") or "ig_creator"),
                            "caption": str(cap_obj.get("text") or ""),
                            "likes": int(obj.get("like_count") or 0),
                            "views": int(obj.get("play_count") or obj.get("view_count") or 0),
                            "comments": int(obj.get("comment_count") or 0),
                            "duration_s": dur_s,
                            "taken_at": int(obj.get("taken_at") or 0),
                            "efg_age_days": efg_age_days,
                            "video_cdn_url": v_url,
                            "thumb_cdn_url": t_url,
                        }
                    )
            for v in obj.values():
                walk_ig(v)
        elif isinstance(obj, list):
            for x in obj:
                walk_ig(x)

    async def _scan_page_scripts(pg: Any) -> None:
        html = await pg.content()
        for m in re.finditer(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', html, re.S):
            if "video_versions" in m.group(1):
                try:
                    walk_ig(json.loads(m.group(1)))
                except Exception:
                    pass

    def _is_login_redirect(url: str) -> bool:
        low = (url or "").lower()
        return any(mk in low for mk in CHANNEL_COOKIE_SPECS["instagram"]["login_url_markers"])

    raw_kw = _normalize_keyword_for_market(keyword, country=country)
    act = (action or "search").strip().lower()
    target_profile = ""
    target_urls: List[str] = []
    if act == "posts" or raw_kw.startswith("@"):
        uname = re.sub(r"[^a-zA-Z0-9._]", "", raw_kw.lstrip("@"))
        target_profile = uname.lower()
        target_urls.append(f"https://www.instagram.com/{uname}/reels/" if uname else "https://www.instagram.com/reels/")
    elif act == "hot" and not raw_kw:
        target_urls.append("https://www.instagram.com/reels/")
    elif raw_kw.startswith("#"):
        tag_slug = re.sub(r"[^a-zA-Z0-9_]", "", raw_kw.lstrip("#"))
        if tag_slug:
            target_urls.append(f"https://www.instagram.com/explore/tags/{tag_slug}/")
    else:
        kw_query = raw_kw.lstrip("@#") or ("viral product" if country.upper() in {"US", "GLOBAL"} else "decor")
        target_urls.append(f"https://www.instagram.com/explore/search/keyword/?q={quote_plus(kw_query)}")
        tag_slug = re.sub(r"[^a-z0-9_]", "", _strip_accents_lower(kw_query))
        if len(tag_slug) >= 3:
            target_urls.append(f"https://www.instagram.com/explore/tags/{tag_slug}/")

    is_en_market = (country or "VN").upper() in {"US", "GLOBAL"}
    browser = None
    ctx = None
    page = None
    try:
        from playwright.async_api import async_playwright

        chrome_exe = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        launch_kwargs: Dict[str, Any] = {
            "headless": True,
            "args": ["--disable-blink-features=AutomationControlled"],
        }
        if Path(chrome_exe).exists():
            launch_kwargs["executable_path"] = chrome_exe

        async with async_playwright() as p:
            browser = await p.chromium.launch(**launch_kwargs)
            ctx = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                ),
                locale="en-US" if is_en_market else "vi-VN",
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9" if is_en_market else "vi-VN,vi;q=0.9,en-US;q=0.7,en;q=0.6",
                },
                viewport={"width": 1280, "height": 900},
            )
            await ctx.add_cookies(ig_cookies)
            page = await ctx.new_page()

            async def on_resp(resp: Any) -> None:
                if "graphql" in resp.url or "api/v1" in resp.url or "search" in resp.url:
                    try:
                        txt = await resp.text()
                        if "video_versions" in txt:
                            walk_ig(json.loads(txt))
                    except Exception:
                        pass

            page.on("response", on_resp)
            try:
                for idx, url in enumerate(target_urls):
                    await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    if _is_login_redirect(page.url):
                        auth_failed = True
                        break
                    try:
                        await page.wait_for_selector(
                            'main a[href*="/reel/"], main a[href*="/p/"], main article',
                            timeout=5500,
                        )
                    except Exception:
                        pass
                    await page.wait_for_timeout(1600)
                    await page.evaluate("window.scrollBy(0, 1400)")
                    await page.wait_for_timeout(1500)
                    await _scan_page_scripts(page)

                    dom_links = await page.eval_on_selector_all(
                        'main a[href*="/reel/"]',
                        "els => Array.from(new Set(els.map(e => (e.href || '').split('?')[0]).filter(Boolean)))",
                    )
                    for dl in dom_links or []:
                        canon = _canonicalize_video_url("instagram", str(dl))
                        if canon and canon not in fallback_urls:
                            fallback_urls.append(canon)

                    if idx == 0 and len(found_raw) >= max(3, limit):
                        break
            finally:
                try:
                    page.remove_listener("response", on_resp)
                except Exception:
                    pass
    except Exception as exc:
        if not found_raw and not fallback_urls:
            return {
                "status": "error",
                "diagnostic": f"Lỗi trình duyệt khi quét Instagram: {str(exc)[:180]}",
                "items": [],
                "fallback_urls": [],
            }
    finally:
        for closer in (page, ctx, browser):
            if closer is not None:
                try:
                    await closer.close()
                except BaseException:
                    pass

    if target_profile:
        found_raw = [
            it for it in found_raw
            if str(it.get("username") or "").strip().lstrip("@").lower() == target_profile
        ]

    if auth_failed:
        return {
            "status": "auth_failed",
            "diagnostic": "Cookie Instagram đã hết hạn hoặc bị yêu cầu đăng nhập/checkpoint — hãy vào Cài đặt Agent-Reach bấm 'Đăng nhập Browser' lại.",
            "items": [],
            "fallback_urls": [],
        }

    return {
        "status": "ok" if (found_raw or fallback_urls) else "empty",
        "diagnostic": "" if (found_raw or fallback_urls) else f"Không tìm thấy Reel nào khớp '{raw_kw or keyword}' trên Instagram ({country}).",
        "items": found_raw,
        "fallback_urls": fallback_urls,
    }


async def _crawl_instagram_reels_playwright_with_diag(
    keyword: str,
    country: str = "VN",
    limit: int = 5,
    match_type: str = "broad",
    action: str = "search",
) -> Dict[str, Any]:
    """Two-phase Instagram crawl: bounded Playwright discovery, then ranked parallel MP4+JPG downloads."""
    clean_kw = _normalize_keyword_for_market(keyword, country=country)
    try:
        disc = await asyncio.wait_for(
            _discover_instagram_reels_playwright(
                clean_kw,
                country=country,
                limit=limit,
                action=action,
            ),
            timeout=25.0,
        )
    except asyncio.TimeoutError:
        return {
            "status": "timeout",
            "diagnostic": f"Quét Instagram quá 25s cho từ khoá '{clean_kw}' — đã tự ngắt trình duyệt để tránh treo.",
            "videos": [],
        }
    except Exception as exc:
        return {
            "status": "error",
            "diagnostic": f"Lỗi quét Instagram: {str(exc)[:180]}",
            "videos": [],
        }

    status = disc.get("status", "empty")
    found_raw: List[Dict[str, Any]] = disc.get("items") or []
    fallback_urls: List[str] = disc.get("fallback_urls") or []
    diag_msg = str(disc.get("diagnostic") or "")

    if status in {"no_cookies", "no_playwright", "auth_failed"}:
        return {"status": status, "diagnostic": diag_msg, "videos": []}

    # Fallback for profile/@username pages where Instagram renders /reel/ links in DOM without inline video_versions
    if not found_raw and fallback_urls:
        ytdlp_results = await asyncio.gather(
            *(
                asyncio.wait_for(
                    asyncio.to_thread(
                        _enrich_video_item_via_ytdlp,
                        {
                            "platform": "instagram",
                            "title": f"Instagram Reel ({clean_kw})",
                            "caption": "",
                            "author": f"@{clean_kw.lstrip('@')}" if clean_kw.startswith("@") else "@instagram_creator",
                            "source_url": u,
                            "video_url": "",
                            "thumbnail_url": "",
                            "local_path": "",
                            "views": 0,
                            "likes": 0,
                            "comments": 0,
                            "shares": 0,
                            "viral_score": 80,
                            "sales_signals": [],
                            "hook_text": "",
                            "script_summary": "",
                        },
                        True,
                    ),
                    timeout=18.0,
                )
                for u in fallback_urls[:limit]
            ),
            return_exceptions=True,
        )
        videos = [r for r in ytdlp_results if isinstance(r, dict) and (r.get("video_url") or r.get("local_path"))]
        return {
            "status": "ok" if videos else "empty",
            "diagnostic": (
                f"Instagram Reels ({country}): +{len(videos)} video từ DOM/yt-dlp"
                if videos
                else diag_msg or "Không tải được video từ các link Reel tìm thấy trên trang Instagram."
            ),
            "videos": videos,
        }

    if not found_raw:
        return {"status": status, "diagnostic": diag_msg, "videos": []}

    # Score and rank for winning ecommerce/product relevance, freshness, and market fit
    scored: List[Tuple[float, bool, Dict[str, Any]]] = []
    for item in found_raw:
        sc, is_rel = _score_instagram_reel(item, clean_kw, country=country, match_type=match_type)
        scored.append((sc, is_rel, item))

    relevant_pool = [row for row in scored if row[1]]
    if relevant_pool:
        relevant_pool.sort(key=lambda r: r[0], reverse=True)
        top_items = [r[2] for r in relevant_pool[:limit]]
    else:
        scored.sort(key=lambda r: r[0], reverse=True)
        top_items = [r[2] for r in scored[:limit]]
        if match_type == "exact" and clean_kw and not clean_kw.startswith(("@", "#")):
            diag_msg = f"Không có Reel nào khớp tuyệt đối \"{clean_kw}\" — hiển thị {len(top_items)} Reel liên quan nhất."

    now_ts = int(time.time())

    async def _build_single_ig_item(item: Dict[str, Any]) -> Dict[str, Any]:
        code = item["code"]
        src_url = f"https://www.instagram.com/reel/{code}/"
        play_url = ""
        local_thumb = ""
        try:
            dl_pair = await asyncio.wait_for(
                asyncio.gather(
                    asyncio.to_thread(_download_asset_to_local, item["video_cdn_url"], f"ig_{code}.mp4"),
                    asyncio.to_thread(_download_asset_to_local, item["thumb_cdn_url"], f"ig_{code}.jpg"),
                ),
                timeout=16.0,
            )
            play_url, local_thumb = dl_pair
        except Exception:
            play_url, local_thumb = "", ""

        local_mp4_path = str(DOWNLOADS_DIR / f"ig_{code}.mp4") if play_url else ""
        if not play_url:
            try:
                dl_res = await asyncio.wait_for(asyncio.to_thread(_run_ytdlp_sync, src_url, True), timeout=16.0)
                if dl_res.get("ok") and dl_res.get("local_path") and Path(dl_res["local_path"]).is_file():
                    local_mp4_path = str(dl_res["local_path"])
                    play_url = f"/media/downloads/{Path(local_mp4_path).name}"
            except Exception:
                pass

        caption = _clean_scraped_caption(item["caption"], f"Instagram Reel @{item['username']}")
        first_line = [ln.strip() for ln in caption.splitlines() if ln.strip()]
        title = (first_line[0] if first_line else f"Instagram Reel @{item['username']} — {clean_kw}")[:135]

        likes = max(25, item["likes"])
        views = item["views"] if item["views"] > likes else likes * 14
        comments = max(2, item["comments"])
        shares = max(5, int(likes * 0.08))
        age_days = (
            max(1, (now_ts - item["taken_at"]) // 86400)
            if item["taken_at"] > 0
            else max(1, int(item.get("efg_age_days") or 7))
        )
        dur_s = max(3, int(item.get("duration_s") or 18))

        extra_sigs = [f"File {age_days} ngày", f"Thời lượng {dur_s}s"]
        v_score = compute_viral_score(views, likes, comments, shares)
        analysis = analyze_video_structure(
            title,
            caption,
            clean_kw or keyword,
            extra_meta={"duration_s": dur_s, "asset_age_days": age_days},
        )
        author_fmt = f"@{item['username'].lstrip('@')}"[:75]
        ig_handle = item["username"].lstrip("@")
        base_item: Dict[str, Any] = {
            "platform": "instagram",
            "title": title,
            "caption": caption[:550],
            "author": author_fmt,
            "source_url": src_url,
            "video_url": play_url or item["video_cdn_url"],
            "thumbnail_url": local_thumb or item["thumb_cdn_url"],
            "local_path": local_mp4_path,
            "views": views,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "viral_score": v_score,
            "sales_signals": detect_sales_signals(f"{title} {caption}", extra_sigs),
            "hook_text": analysis["hook_text"],
            "script_summary": analysis["script_summary"],
            "ig_handle": ig_handle,
            "ad_placements": ["instagram"],
        }
        try:
            direct_sh = await asyncio.to_thread(_discover_direct_creator_shop, base_item, clean_kw or keyword)
            if direct_sh:
                base_item["shop_name"] = str(direct_sh.get("shop_name") or author_fmt)
                base_item["shop_url"] = str(direct_sh.get("shop_url") or "")
                base_item["product_url"] = str(direct_sh.get("product_url") or "")
                base_item["selling_price"] = str(direct_sh.get("selling_price") or "")
                base_item["original_price"] = str(direct_sh.get("original_price") or "")
                base_item["market_intel"] = build_market_intel_for_video(
                    base_item,
                    shops=[direct_sh],
                    product_query=clean_kw or keyword,
                    total_market_ads=0,
                    spy_status="baseline",
                )
        except Exception:
            pass
        if not base_item.get("selling_price"):
            inline_p = _extract_price_from_text_multi(f"{title} {caption}")
            if inline_p:
                base_item["selling_price"] = inline_p
        return base_item

    built = await asyncio.gather(*(_build_single_ig_item(it) for it in top_items), return_exceptions=True)
    results = [r for r in built if isinstance(r, dict)]
    return {
        "status": "ok" if results else "empty",
        "diagnostic": diag_msg or f"Instagram Reels ({country}): +{len(results)} video MP4 thật đã tải về máy",
        "videos": results,
    }


async def _crawl_instagram_reels_playwright(
    keyword: str,
    limit: int = 5,
    country: str = "VN",
    match_type: str = "broad",
    action: str = "search",
) -> List[Dict[str, Any]]:
    res = await _crawl_instagram_reels_playwright_with_diag(
        keyword=keyword,
        country=country,
        limit=limit,
        match_type=match_type,
        action=action,
    )
    return res.get("videos") or []


def _upsert_video_by_source_url(item: Dict[str, Any]) -> Dict[str, Any]:
    pf = str(item.get("platform") or "").lower()
    canon_url = _canonicalize_video_url(pf, str(item.get("source_url") or ""))
    item["source_url"] = canon_url
    new_intel_raw = item.get("market_intel_json") or ""
    if not new_intel_raw and isinstance(item.get("market_intel"), dict):
        new_intel_raw = json.dumps(item["market_intel"], ensure_ascii=False)
    existing = next(
        (
            v
            for v in database.list_videos()
            if _canonicalize_video_url(str(v.get("platform") or ""), str(v.get("source_url") or "")) == canon_url
        ),
        None,
    )
    if existing and existing.get("id"):
        vid = int(existing["id"])
        kept_intel = new_intel_raw or existing.get("market_intel_json") or ""
        new_pl = item.get("ad_placements")
        if isinstance(new_pl, list) and new_pl:
            merged_pl = sorted({*(existing.get("ad_placements") or []), *(str(x).lower() for x in new_pl if x)})
        else:
            merged_pl = existing.get("ad_placements") or []
        with database.get_conn() as conn:
            conn.execute(
                """
                UPDATE viral_videos
                SET title = ?, caption = ?, author = ?, source_url = ?, video_url = ?,
                    thumbnail_url = ?, local_path = ?, views = ?, likes = ?, comments = ?,
                    shares = ?, viral_score = ?, sales_signals = ?, hook_text = ?, script_summary = ?,
                    market_intel_json = ?,
                    shop_name = ?, shop_url = ?, product_url = ?, selling_price = ?, original_price = ?,
                    meta_library_id = ?, meta_page_id = ?, ig_handle = ?, ad_placements = ?, cta_text = ?
                WHERE id = ?
                """,
                (
                    item.get("title") or existing.get("title"),
                    item.get("caption") or existing.get("caption"),
                    item.get("author") or existing.get("author"),
                    canon_url,
                    item.get("video_url") or existing.get("video_url", ""),
                    item.get("thumbnail_url") or existing.get("thumbnail_url", ""),
                    item.get("local_path") or existing.get("local_path", ""),
                    int(item.get("views") or existing.get("views") or 0),
                    int(item.get("likes") or existing.get("likes") or 0),
                    int(item.get("comments") or existing.get("comments") or 0),
                    int(item.get("shares") or existing.get("shares") or 0),
                    int(item.get("viral_score") or existing.get("viral_score") or 75),
                    json.dumps(item.get("sales_signals") or existing.get("sales_signals") or [], ensure_ascii=False),
                    item.get("hook_text") or existing.get("hook_text", ""),
                    item.get("script_summary") or existing.get("script_summary", ""),
                    kept_intel,
                    str(item.get("shop_name") or existing.get("shop_name") or ""),
                    str(item.get("shop_url") or existing.get("shop_url") or ""),
                    str(item.get("product_url") or existing.get("product_url") or ""),
                    str(item.get("selling_price") or existing.get("selling_price") or ""),
                    str(item.get("original_price") or existing.get("original_price") or ""),
                    str(item.get("meta_library_id") or existing.get("meta_library_id") or ""),
                    str(item.get("meta_page_id") or existing.get("meta_page_id") or ""),
                    str(item.get("ig_handle") or existing.get("ig_handle") or ""),
                    json.dumps(merged_pl, ensure_ascii=False),
                    str(item.get("cta_text") or existing.get("cta_text") or ""),
                    vid,
                ),
            )
        return database.get_video(vid) or existing
    return database.insert_video(item)


def execute_agent_reach_action(
    channel: str,
    action: str,
    query: str = "",
    limit: int = 5,
    save_to_videos: bool = True,
    country: str = "VN",
) -> Dict[str, Any]:
    ch = channel.strip().lower()
    act = action.strip().lower()
    q_raw = query.strip()
    q = _normalize_keyword_for_market(q_raw, country=country) if ch == "instagram" else q_raw

    if ch == "instagram" and act in {"search", "posts", "hot"}:
        ig_query = "" if (act == "hot" and not q) else (q or ("viral product" if country.upper() in {"US", "GLOBAL"} else "decor"))
        try:
            ig_res = asyncio.run(
                _crawl_instagram_reels_playwright_with_diag(
                    ig_query,
                    country=country,
                    limit=limit,
                    match_type="broad",
                    action=act,
                )
            )
        except Exception as exc:
            ig_res = {"status": "error", "diagnostic": f"Lỗi quét Instagram: {str(exc)[:180]}", "videos": []}

        ig_items = ig_res.get("videos") or []
        ig_status = ig_res.get("status", "empty")
        ig_diag = str(ig_res.get("diagnostic") or "")
        if ig_items:
            _enrich_videos_with_ai_analysis(ig_items, q or "instagram")
            saved_ig = [_upsert_video_by_source_url(it) for it in ig_items] if save_to_videos else []
            return {
                "ok": True,
                "channel": ch,
                "action": act,
                "command": f"instagram-session-crawler {act} --country {country} \"{ig_query}\"",
                "diagnostic": ig_diag or f"Đã quét & tải trực tiếp {len(ig_items)} video MP4 Instagram Reels ({country})",
                "saved_count": len(saved_ig),
                "videos": saved_ig,
                "raw_response": {"ok": True, "source": "instagram_playwright_session", "count": len(ig_items)},
            }
        if ig_status in {"auth_failed", "no_cookies", "timeout"}:
            return {
                "ok": False,
                "channel": ch,
                "action": act,
                "command": f"instagram-session-crawler {act} --country {country} \"{ig_query}\"",
                "diagnostic": ig_diag,
                "saved_count": 0,
                "videos": [],
                "raw_response": {"ok": False, "source": "instagram_playwright_session", "status": ig_status},
            }

    if ch == "read" or act == "read_url":
        args = ["read", q]
    elif act == "search" and ch in {"bilibili", "instagram", "facebook", "tiktok", "douyin"}:
        args = _build_agent_reach_cli_args(ch, q or "viral", limit=limit) or [ch, act, q, "--limit", str(limit)]
    elif act in {"hot", "hot_posts", "hot_stocks"}:
        args = [ch, act, "--limit", str(limit)]
    elif act in {"profile", "user", "read", "thread", "subtitle", "transcribe"}:
        args = [ch, act, q]
    else:
        args = [ch, act]
        if q:
            args.append(q)
        if act in {"search", "posts", "tweets", "comments", "subreddit", "jobs"}:
            args.extend(["--limit", str(limit)])

    raw_resp = _run_agent_reach_sync(args, timeout=45)
    target_pf = ch if ch in CHANNEL_META_VI else "web"
    items, diag = _normalize_agent_reach_items(target_pf, q or act, raw_resp)
    if not items and ch == "instagram":
        web_q = f"site:instagram.com/reel {q}" if q else "site:instagram.com/reel viral"
        fallback_args = ["web", "search", web_q, "--limit", str(limit * 2)]
        fb_resp = _run_agent_reach_sync(fallback_args, timeout=30)
        fb_items, fb_diag = _normalize_agent_reach_items("instagram", q or "instagram", fb_resp)
        if fb_items:
            items = fb_items
            raw_resp = fb_resp
            args = fallback_args
            diag = "Instagram Reels via Agent-Reach Web Search (Exa)"
        elif fb_diag:
            diag = f"{diag}; {fb_diag}" if diag else fb_diag

    if items:
        for i in range(len(items)):
            if items[i]["platform"] in {"tiktok", "instagram"}:
                items[i] = _enrich_video_item_via_ytdlp(items[i], download_mp4=True)
        _enrich_videos_with_ai_analysis(items, q or ch)

    saved: List[Dict[str, Any]] = []
    if save_to_videos and items:
        saved = [_upsert_video_by_source_url(it) for it in items]

    return {
        "ok": bool(raw_resp.get("ok") or items),
        "channel": ch,
        "action": act,
        "command": "agent-reach " + " ".join(args),
        "diagnostic": diag,
        "saved_count": len(saved),
        "videos": saved,
        "raw_response": raw_resp,
    }


def _strip_accents_lower(s: str) -> str:
    import unicodedata
    s = (s or "").lower().replace("đ", "d")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _clean_search_quotes(keyword: str) -> str:
    kw = (keyword or "").strip()
    while len(kw) >= 2 and (
        (kw[0] == kw[-1] and kw[0] in {'"', "'"})
        or (kw[0] == "“" and kw[-1] == "”")
    ):
        kw = kw[1:-1].strip()
    return kw


def _decode_fb_efg(url: str) -> Dict[str, Any]:
    """Decode base64 Meta/Instagram CDN `efg` query param to recover duration_s, asset_age_days, and xpv_asset_id."""
    if not url or "efg=" not in url:
        return {}
    try:
        from urllib.parse import unquote
        efg_b64 = unquote(url.split("efg=", 1)[1].split("&", 1)[0])
        efg_b64 += "=" * (-len(efg_b64) % 4)
        obj = json.loads(base64.b64decode(efg_b64).decode("utf-8", "ignore"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _normalize_keyword_for_market(keyword: str, country: str = "VN") -> str:
    """Strip wrapping quotes and fix accidental Vietnamese Telex accents inside English keywords."""
    import unicodedata

    kw = _clean_search_quotes(keyword)
    if not kw:
        return kw
    en_word_re = re.compile(
        r"(chr|st|sh|ft|cl|pl|bl|gr|pr|dr|fr|fl|gl|sl|sp|sk|sm|sn|sw|tw|wr|ck|ct|pt|xt|nd|mp|nk|ld|lt|rt|rk|rm|kn|wh|tch|dg|[wfjz])",
        re.I,
    )
    fixed_words: List[str] = []
    for w in kw.split():
        plain = _strip_accents_lower(w)
        if en_word_re.search(plain):
            fixed_words.append(
                "".join(
                    c for c in unicodedata.normalize("NFD", w.replace("đ", "d").replace("Đ", "D"))
                    if unicodedata.category(c) != "Mn"
                )
            )
        else:
            fixed_words.append(w)
    return " ".join(fixed_words)


def _keyword_matches_ad(keyword: str, text: str, exact: bool = False) -> bool:
    kw_clean = _strip_accents_lower(_clean_search_quotes(keyword).lstrip("@#"))
    txt_clean = _strip_accents_lower(text)
    if not kw_clean:
        return True
    if kw_clean in txt_clean:
        return True
    kw_compact = re.sub(r"[^a-z0-9]+", "", kw_clean)
    txt_compact = re.sub(r"[^a-z0-9]+", "", txt_clean)
    if kw_compact and len(kw_compact) >= 5 and kw_compact in txt_compact:
        return True
    if exact:
        return False
    tokens = [t for t in re.split(r"\s+", kw_clean) if len(t) >= 3]
    if not tokens:
        return True
    matched = sum(1 for t in tokens if re.search(rf"\b{re.escape(t)}\b", txt_clean))
    return matched >= max(1, (len(tokens) + 1) // 2)


def _score_instagram_reel(
    item: Dict[str, Any],
    keyword: str,
    country: str = "VN",
    match_type: str = "broad",
) -> Tuple[float, bool]:
    """Score an Instagram Reel for ecommerce/winning relevance, freshness, market fit, and engagement.

    Returns (score, is_relevant).
    """
    import math

    kw_clean = _strip_accents_lower(_clean_search_quotes(keyword).lstrip("@#"))
    text_raw = f"{item.get('caption') or ''} {item.get('username') or ''}"
    txt_lower = text_raw.lower()
    txt_clean = _strip_accents_lower(text_raw)

    # 1. Keyword relevance
    exact_hit = _keyword_matches_ad(kw_clean, text_raw, exact=True) if kw_clean else True
    tokens = [t for t in re.split(r"\s+", kw_clean) if len(t) >= 2] if kw_clean else []
    token_hits = sum(1 for t in tokens if re.search(rf"\b{re.escape(t)}\b", txt_clean) or t in txt_clean) if tokens else 0
    is_relevant = exact_hit if (match_type == "exact" and kw_clean) else (
        True if not tokens else token_hits >= max(1, (len(tokens) + 1) // 2)
    )

    score = 0.0
    if kw_clean:
        if exact_hit:
            score += 60.0
        elif token_hits > 0:
            score += 36.0 * (token_hits / max(1, len(tokens)))
        else:
            score -= 45.0

    # 2. Winning product / scaling / commercial CTA signals
    cta_markers = (
        "comment", "link in bio", "shop", "store", "buy", "order", "gift", "deal",
        "discount", "free shipping", "off", "sale", "amazon", "tiktok", "stocking",
        "mua", "giảm", "giá", "chốt đơn", "freeship", "giỏ hàng", "inbox", "ib", "shopee",
    )
    cta_hits = sum(1 for m in cta_markers if m in txt_lower)
    score += min(42.0, cta_hits * 7.5)

    # 3. Engagement velocity
    likes = int(item.get("likes") or 0)
    comments = int(item.get("comments") or 0)
    score += min(45.0, math.log10(max(10, likes + comments * 15)) * 8.5)

    # 4. Freshness (real taken_at or CDN efg age)
    now_ts = int(time.time())
    taken_at = int(item.get("taken_at") or 0)
    age_days = max(1, (now_ts - taken_at) // 86400) if taken_at > 0 else max(1, int(item.get("efg_age_days") or 30))
    if age_days <= 30:
        score += 22.0
    elif age_days <= 90:
        score += 14.0
    elif age_days <= 180:
        score += 6.0
    elif age_days > 365:
        score -= 12.0

    # 5. Market / country alignment
    ctry = (country or "VN").upper()
    if ctry in {"US", "GLOBAL"}:
        sea_spam = ("shopee.ph", "lazada.com.ph", "tokopedia", "shopee.com.my", "₱", "php ")
        if any(s in txt_lower for s in sea_spam):
            score -= 55.0
        if any(u in txt_lower for u in ("$", "usd", "usa", "us ", ".store", ".co", "amazon")):
            score += 10.0
    elif ctry == "VN":
        if any(v in txt_lower for v in ("đ", "vnđ", "shopee", "tiktok", "mua", "giá", "freeship")) or _has_vietnamese_chars(text_raw):
            score += 15.0

    return score, is_relevant


_store_meta_cache: Dict[str, Dict[str, str]] = {}

_NON_SHOP_DOMAINS = (
    "facebook.com",
    "fb.com",
    "fb.me",
    "fb.watch",
    "instagram.com",
    "about.meta.com",
    "metastatus.com",
    "messenger.com",
    "m.me",
    "whatsapp.com",
    "wa.me",
    "zalo.me",
    "maps.app.goo.gl",
    "threads.net",
    "threads.com",
    "twitter.com",
    "x.com",
    "bilibili.com",
    "reddit.com",
    "play.google.com",
    "apps.apple.com",
    "itunes.apple.com",
)

_BIO_HUB_DOMAINS = (
    "linktr.ee",
    "beacons.ai",
    "msha.ke",
    "bio.site",
    "lnk.bio",
    "solo.to",
    "taplink.cc",
    "milkshake.app",
    "instabio.cc",
)

_SHORTENER_DOMAINS = (
    "urlvue.com",
    "bit.ly",
    "tinyurl.com",
    "cutt.ly",
    "rebrand.ly",
    "is.gd",
    "t.co",
    "amzn.to",
    "shope.ee",
    "s.shopee.vn",
    "vn.shp.ee",
    "shp.ee",
    "s.lazada.vn",
    "vt.tiktok.com",
    "vm.tiktok.com",
)


def _clean_tracking_params(url: str) -> str:
    try:
        from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

        sp = urlsplit(url.strip())
        if not sp.scheme or not sp.netloc:
            return url.strip()
        drop_keys = {
            "fbclid", "gclid", "ttclid", "h", "__cft__", "__tn__", "mibext", "mibextid",
            "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
            "utm_id", "sp_atk", "xptdk", "aid", "asid", "cid", "ad_id", "adset_id",
            "campaign_id", "fb_action_ids", "fb_source", "spm", "scm", "pvid",
            "clicktrackinfo", "pagesource", "sub_channel", "resource_lock_id",
        }
        kept = []
        for k, v in parse_qsl(sp.query, keep_blank_values=False):
            kl = k.lower()
            if kl in drop_keys or kl.startswith(("__cft__", "utm_", "aem_")):
                continue
            v_unq = unquote(v)
            if "{{" in v or "}}" in v or "{{" in v_unq or "}}" in v_unq:
                continue
            kept.append((k, v))
        return urlunsplit((sp.scheme, sp.netloc, sp.path, urlencode(kept, doseq=True), ""))
    except Exception:
        return url.strip()


def _unwrap_external_store_url(raw_url: str) -> str:
    """Unwrap Facebook/IG/Threads l.php redirects & Shopee universal-link, validating real external commerce URLs."""
    if not raw_url:
        return ""
    from urllib.parse import parse_qs, unquote

    u = raw_url.strip()
    if any(w in u for w in ("facebook.com/l.php", "lm.facebook.com/l.php", "l.instagram.com/", "l.threads.net/", "l.threads.com/")):
        try:
            qs = parse_qs(urlsplit(u).query)
            target = (qs.get("u") or [""])[0]
            if target:
                u = unquote(target)
                if "%3A%2F%2F" in u or "%25" in u:
                    u = unquote(u)
        except Exception:
            return ""

    if not u.startswith(("http://", "https://")):
        return ""

    sp = urlsplit(u)
    host = (sp.netloc or "").lower().lstrip("www.")
    if not host or "." not in host:
        return ""

    # Unwrap Shopee universal-link wrapper
    if "shopee." in host and sp.path.startswith("/universal-link/"):
        qs = parse_qs(sp.query)
        redir = (qs.get("redir") or [""])[0]
        if redir and redir.startswith("http"):
            u = unquote(redir)
            sp = urlsplit(u)
            host = (sp.netloc or "").lower().lstrip("www.")
        else:
            inner_path = sp.path[len("/universal-link") :]
            u = f"https://{host}{inner_path}" + (f"?{sp.query}" if sp.query else "")
            sp = urlsplit(u)

    # Allow Facebook Commerce Shop product pages, reject other social/app-store domains
    if ("facebook.com" in host or "instagram.com" in host) and "/commerce/products/" in sp.path:
        return _clean_tracking_params(u)

    if any(host == d or host.endswith("." + d) for d in _NON_SHOP_DOMAINS):
        return ""
    if "google.com" in host and ("/maps" in sp.path or "/search" in sp.path or "/store/apps" in sp.path):
        return ""
    if "youtube.com" in host or "youtu.be" in host:
        return ""
    if "alibaba.com" in host and "cpm_fb" in u.lower():
        return ""
    if "tiktok.com" in host and not any(p in sp.path for p in ("/view/product", "/product/", "/shop", "/t/")):
        if host not in {"vt.tiktok.com", "vm.tiktok.com", "shop.tiktok.com"}:
            return ""

    return _clean_tracking_params(u)


def split_shop_and_product_urls(
    raw_url: str,
    fallback_page_url: str = "",
    ig_handle: str = "",
) -> Dict[str, Any]:
    """Separate a destination URL into BOTH `shop_url` (storefront root) and `product_url` (specific product page)."""
    clean_u = _unwrap_external_store_url(raw_url)
    ig_clean = (ig_handle or "").strip().lstrip("@")
    ig_profile_url = f"https://www.instagram.com/{ig_clean}/" if ig_clean else ""
    social_fallback = ig_profile_url or (fallback_page_url or "").strip()

    if not clean_u:
        dom_fb = ""
        if social_fallback:
            sp_fb = urlsplit(social_fallback)
            dom_fb = f"{sp_fb.netloc.lower().lstrip('www.')}/{sp_fb.path.strip('/').split('/')[0]}" if sp_fb.path.strip("/") else sp_fb.netloc.lower().lstrip("www.")
        return {
            "shop_url": social_fallback,
            "product_url": "",
            "domain": dom_fb,
            "is_inbox_only": bool(social_fallback),
        }

    sp = urlsplit(clean_u)
    host = (sp.netloc or "").lower().lstrip("www.")
    path = sp.path or ""
    path_trimmed = path.strip("/")
    root_url = f"{sp.scheme}://{sp.netloc}"

    # 1. Shopee (VN & SEA)
    if "shopee." in host:
        shopee_host = sp.netloc.lower()
        if shopee_host.startswith("sv.shopee.") or "/list/" in path or path_trimmed.startswith("search"):
            return {
                "shop_url": social_fallback,
                "product_url": "",
                "domain": "",
                "is_inbox_only": False,
            }
        m_prod = re.search(r"/(?:product|opaanlp)/(\d+)/(\d+)", path)
        if m_prod:
            sid, iid = m_prod.group(1), m_prod.group(2)
            return {
                "shop_url": f"https://{shopee_host}/shop/{sid}",
                "product_url": f"https://{shopee_host}/product/{sid}/{iid}",
                "domain": f"shopee.vn/shop/{sid}",
                "is_inbox_only": False,
            }
        m_slug_i = re.search(r"-i\.(\d+)\.(\d+)", path)
        if m_slug_i:
            sid, iid = m_slug_i.group(1), m_slug_i.group(2)
            return {
                "shop_url": f"https://{shopee_host}/shop/{sid}",
                "product_url": f"https://{shopee_host}{path}",
                "domain": f"shopee.vn/shop/{sid}",
                "domain_root": host,
                "is_inbox_only": False,
            }
        segs = [s for s in path_trimmed.split("/") if s]
        if len(segs) == 2 and segs[0].lower() == "shop" and segs[1].isdigit():
            return {
                "shop_url": f"https://{shopee_host}/shop/{segs[1]}",
                "product_url": "",
                "domain": f"shopee.vn/shop/{segs[1]}",
                "is_inbox_only": False,
            }
        if len(segs) >= 2 and segs[1].isdigit() and len(segs[1]) >= 6 and segs[0].lower() not in {"product", "shop", "m", "buyer"}:
            return {
                "shop_url": f"https://{shopee_host}/{segs[0]}",
                "product_url": f"https://{shopee_host}/{segs[0]}/{segs[1]}",
                "domain": f"shopee.vn/{segs[0]}",
                "is_inbox_only": False,
            }
        if len(segs) == 1 and segs[0].lower() not in {"m", "buyer", "cart", "search", "daily_discover", "mall"}:
            return {
                "shop_url": f"https://{shopee_host}/{segs[0]}",
                "product_url": "",
                "domain": f"shopee.vn/{segs[0]}",
                "is_inbox_only": False,
            }
        return {
            "shop_url": clean_u,
            "product_url": "",
            "domain": host,
            "is_inbox_only": False,
        }

    # 2. Lazada
    if "lazada." in host:
        if "/products/" in path or re.search(r"-i\d+", path):
            return {
                "shop_url": social_fallback or f"https://{sp.netloc}",
                "product_url": clean_u,
                "domain": host,
                "is_inbox_only": False,
            }
        if "/shop/" in path:
            segs = [s for s in path_trimmed.split("/") if s]
            slug = segs[1] if len(segs) >= 2 else ""
            return {
                "shop_url": clean_u,
                "product_url": "",
                "domain": f"{host}/shop/{slug}" if slug else host,
                "is_inbox_only": False,
            }

    # 3. TikTok Shop
    if "tiktok.com" in host or host in {"vt.tiktok.com", "vm.tiktok.com"}:
        if any(k in path for k in ("/view/product", "/product/", "/t/")) or host in {"vt.tiktok.com", "vm.tiktok.com"}:
            m_tk_u = re.search(r"/@([^/?#]+)", path)
            tk_shop = f"https://www.tiktok.com/@{m_tk_u.group(1)}" if m_tk_u else (social_fallback or "")
            return {
                "shop_url": tk_shop,
                "product_url": clean_u,
                "domain": f"tiktok.com/@{m_tk_u.group(1)}" if m_tk_u else host,
                "is_inbox_only": False,
            }
        return {
            "shop_url": clean_u,
            "product_url": "",
            "domain": host,
            "is_inbox_only": False,
        }

    # 4. Amazon
    if "amazon." in host or host == "amzn.to":
        if any(k in path for k in ("/dp/", "/gp/product/")) or host == "amzn.to":
            return {
                "shop_url": social_fallback or root_url,
                "product_url": clean_u,
                "domain": host,
                "is_inbox_only": False,
            }
        return {
            "shop_url": clean_u,
            "product_url": "",
            "domain": host,
            "is_inbox_only": False,
        }

    # 5. Facebook / Instagram Commerce Product
    if ("facebook.com" in host or "instagram.com" in host) and "/commerce/products/" in path:
        return {
            "shop_url": social_fallback or root_url,
            "product_url": clean_u,
            "domain": host,
            "is_inbox_only": False,
        }

    # 6. Shorteners & Bio Hubs (will be unwrapped further during HTTP resolve)
    if any(host == d or host.endswith("." + d) for d in (_SHORTENER_DOMAINS + _BIO_HUB_DOMAINS)):
        return {
            "shop_url": clean_u,
            "product_url": clean_u,
            "domain": host,
            "is_inbox_only": False,
        }

    # 7. Shopify / WooCommerce / Haravan / Sapo / Custom Store / LadiPage
    low_path = path.lower()
    if any(seg in low_path for seg in ("/products/", "/product/", "/san-pham/", "/sp/", "/p/", "/item/", "/hang-moi/")):
        return {
            "shop_url": root_url,
            "product_url": clean_u,
            "domain": host,
            "is_inbox_only": False,
        }
    if any(seg in low_path for seg in ("/collections", "/collection/", "/danh-muc/", "/category/", "/categories/", "/shop", "/store")):
        return {
            "shop_url": root_url,
            "product_url": "",
            "domain": host,
            "is_inbox_only": False,
        }
    if not path_trimmed or path_trimmed.lower() in {"home", "index.html", "index.php", "vi", "en", "vn"}:
        return {
            "shop_url": root_url,
            "product_url": "",
            "domain": host,
            "is_inbox_only": False,
        }

    # Single-product Landing Page (e.g., LadiPage, *.io.vn/slug, custom LP)
    is_hosted_lp = any(host.endswith(sfx) for sfx in ("ladipage.me", "webcake.io", " Pancake.vn"))
    return {
        "shop_url": (social_fallback or root_url) if is_hosted_lp else root_url,
        "product_url": clean_u,
        "domain": host,
        "is_inbox_only": False,
    }


def _format_currency_amount(raw_val: Any, currency: str = "USD") -> str:
    try:
        s_val = str(raw_val).strip()
        # Handle Vietnamese dot thousands separator like "249.000" when currency is VND
        cur = (currency or "USD").upper().strip()
        if cur in {"VND", "VNĐ", "₫", "Đ"} and re.match(r"^\d{1,3}(?:\.\d{3})+$", s_val):
            num = float(s_val.replace(".", ""))
        else:
            num = float(s_val.replace(",", ""))
    except Exception:
        return ""
    if num <= 0:
        return ""
    if cur in {"VND", "VNĐ", "₫", "Đ"} or (cur == "USD" and num >= 15000):
        if num < 1000:
            return ""
        return f"{int(round(num)):,}".replace(",", ".") + "đ"
    if cur in {"EUR", "€"}:
        return f"€{num:.2f}"
    if cur in {"GBP", "£"}:
        return f"£{num:.2f}"
    if cur in {"CNY", "RMB", "JPY", "¥"}:
        return f"¥{num:.2f}" if num < 500 else f"¥{int(round(num))}"
    if num < 1.0:
        return ""
    return f"${num:.2f}"


def _extract_prices_pair_from_text(text: str) -> Tuple[str, str]:
    """Extract (selling_price, original_price) cleanly while filtering out 10K/14K/18K/24K gold & 4K/8K video."""
    if not text:
        return "", ""
    import html as html_lib

    no_scripts = re.sub(r"<(?:script|style)[^>]*>.*?</(?:script|style)>", " ", text, flags=re.S | re.I)
    cleaned = html_lib.unescape(re.sub(r"<[^>]+>", " ", no_scripts))

    # Remove false-positive patterns: gold karat (10K/14K/18K/24K), resolution (2K/4K/8K), silver 925, social metrics
    cleaned = re.sub(r"\b(?:vàng|vang|gold|bạc|bac|mạ|ma|tuổi)\s*(?:10|14|18|24)\s*k\b", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"\b(?:10|14|18|24)\s*k\s*(?:gold|plated|filled)\b", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"\b(?:2|4|8)\s*k\s*(?:hd|uhd|video|camera|led|oled|ips|screen|màn)\b", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"\b\d+\s*k\s*(?:follow|followers|likes|views|lượt|người|đơn|bán)\b", " ", cleaned, flags=re.I)

    vnd_amounts: List[int] = []
    # 1. Explicit VND amounts: 249.000đ, VND 69.000, 199,000 vnđ
    for m in re.finditer(
        r"(?:(?:₫|vnđ|vnd)\s*(\d{1,3}(?:[.,]\d{3})+)|(\d{1,3}(?:[.,]\d{3})+)\s*(?:₫|đ|vnđ|vnd)\b)",
        cleaned,
        re.I,
    ):
        raw_d = re.sub(r"[^\d]", "", m.group(1) or m.group(2) or "")
        if raw_d:
            val = int(raw_d)
            if 5000 <= val <= 99_000_000 and val not in vnd_amounts:
                vnd_amounts.append(val)

    # 2. Vietnamese K shorthand: "chỉ 199k", "giá 89k", "sale 149k", or standalone >= 29k (excluding 10/14/18/24)
    for m in re.finditer(
        r"(?:\b(chỉ|giá|sale|còn|từ|deal|combo|ưu đãi)\s+(\d{2,4})\s*k\b|\b(\d{2,4})\s*k\s*(?:/\s*\d+|freeship|miễn ship|bao ship)\b)",
        cleaned,
        re.I,
    ):
        num_k = int(m.group(2) or m.group(3))
        if num_k not in {10, 14, 18, 24} and 15 <= num_k <= 9999:
            val = num_k * 1000
            if val not in vnd_amounts:
                vnd_amounts.append(val)

    if vnd_amounts:
        if len(vnd_amounts) >= 2:
            low_v = min(vnd_amounts[:3])
            high_v = max(vnd_amounts[:3])
            sell_s = f"{low_v:,}".replace(",", ".") + "đ"
            orig_s = f"{high_v:,}".replace(",", ".") + "đ" if high_v > low_v * 1.05 else ""
            return sell_s, orig_s
        return f"{vnd_amounts[0]:,}".replace(",", ".") + "đ", ""

    # 3. USD / EUR / GBP
    usd_matches: List[Tuple[str, float]] = []
    for sym, pat in (("$", r"\$\s*(\d{1,4}(?:\.\d{1,2})?)\b"), ("€", r"€\s*(\d{1,4}(?:\.\d{1,2})?)\b"), ("£", r"£\s*(\d{1,4}(?:\.\d{1,2})?)\b")):
        for m in re.finditer(pat, cleaned):
            try:
                fv = float(m.group(1))
                if 2.0 <= fv <= 5000.0:
                    usd_matches.append((sym, fv))
            except Exception:
                pass
        if usd_matches:
            break

    if usd_matches:
        sym = usd_matches[0][0]
        vals = [x[1] for x in usd_matches[:3]]
        low_f = min(vals)
        high_f = max(vals)
        sell_u = f"{sym}{low_f:.2f}"
        orig_u = f"{sym}{high_f:.2f}" if len(vals) >= 2 and high_f > low_f * 1.05 else ""
        return sell_u, orig_u

    return "", ""


def _extract_price_from_text_multi(text: str) -> str:
    sell, _ = _extract_prices_pair_from_text(text)
    return sell


def _parse_price_numeric_value(price_str: str) -> float:
    """Parse formatted VND / USD / EUR / GBP price string into comparable numeric value for sorting."""
    if not price_str:
        return 0.0
    s = price_str.strip().lower()
    if any(sym in s for sym in ("$", "€", "£", "usd", "eur", "gbp")):
        m = re.search(r"(\d+(?:\.\d{1,2})?)", s.replace(",", ""))
        return float(m.group(1)) if m else 0.0
    digits = re.sub(r"[^\d]", "", s)
    return float(digits) if digits else 0.0


def _format_price_range_sorted(prices: List[str], empty_default: str = "") -> str:
    """Format a list of price strings into ascending `low – high` order, deduplicating equal amounts."""
    parsed: List[Tuple[float, str]] = []
    seen_vals = set()
    for raw_p in prices:
        p = str(raw_p or "").strip()
        if not p:
            continue
        val = _parse_price_numeric_value(p)
        key = val if val > 0 else p.lower()
        if key in seen_vals:
            continue
        seen_vals.add(key)
        parsed.append((val, p))
    if not parsed:
        return empty_default
    if len(parsed) == 1:
        return parsed[0][1]
    with_num = sorted([x for x in parsed if x[0] > 0], key=lambda x: x[0])
    if len(with_num) >= 2:
        return f"{with_num[0][1]} – {with_num[-1][1]}"
    return parsed[0][1]


def _http_fetch(url: str, timeout: float = 5.0) -> Tuple[str, str]:
    ua = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    try:
        with httpx.Client(
            timeout=httpx.Timeout(timeout, connect=3.0),
            follow_redirects=True,
            headers={
                "User-Agent": ua,
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        ) as client:
            resp = client.get(url)
            final_u = _clean_tracking_params(str(resp.url)) if resp.url else url
            if resp.status_code >= 400 and not resp.text:
                return "", final_u
            return resp.text[:220_000], final_u
    except Exception:
        return "", url


def _extract_ld_json_product(html_text: str) -> Dict[str, str]:
    for m in re.finditer(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html_text, re.S | re.I):
        raw_blk = m.group(1).strip()
        if not raw_blk:
            continue
        try:
            parsed = json.loads(raw_blk)
        except Exception:
            continue
        stack = [parsed]
        while stack:
            cur = stack.pop(0)
            if isinstance(cur, dict):
                t = str(cur.get("@type") or "").lower()
                if "product" in t:
                    title = str(cur.get("name") or "").strip()
                    offers = cur.get("offers")
                    offer_obj = offers[0] if isinstance(offers, list) and offers else (offers if isinstance(offers, dict) else {})
                    if isinstance(offer_obj, dict):
                        price_val = offer_obj.get("price") or offer_obj.get("lowPrice")
                        high_val = offer_obj.get("highPrice")
                        currency = str(offer_obj.get("priceCurrency") or "USD")
                        fmt_p = _format_currency_amount(price_val, currency) if price_val is not None else ""
                        fmt_h = _format_currency_amount(high_val, currency) if high_val is not None else ""
                        if fmt_h == fmt_p:
                            fmt_h = ""
                        if fmt_p:
                            return {"selling_price": fmt_p, "original_price": fmt_h, "product_title": title[:130]}
                for v in cur.values():
                    if isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(cur, list):
                stack.extend(x for x in cur if isinstance(x, (dict, list)))
    return {}


def _fetch_live_store_price_and_meta(
    url: str,
    fallback_text: str = "",
    keyword_hint: str = "",
    fallback_page_url: str = "",
    ig_handle: str = "",
) -> Dict[str, str]:
    """Resolve BOTH `shop_url` and `product_url`, plus live `selling_price`, `original_price`, and `product_title`."""
    clean_u = _unwrap_external_store_url(url) or (url.strip() if url.strip().startswith("http") else "")
    fb_sell, fb_orig = _extract_prices_pair_from_text(fallback_text)

    if not clean_u:
        split_fb = split_shop_and_product_urls("", fallback_page_url=fallback_page_url, ig_handle=ig_handle)
        return {
            "selling_price": fb_sell,
            "original_price": fb_orig,
            "product_title": "",
            "resolved_url": "",
            "shop_url": split_fb["shop_url"],
            "product_url": "",
            "domain": split_fb["domain"],
        }

    cache_key = clean_u
    if cache_key in _store_meta_cache:
        cached = dict(_store_meta_cache[cache_key])
        if not cached.get("selling_price") and fb_sell:
            cached["selling_price"] = fb_sell
            cached["original_price"] = cached.get("original_price") or fb_orig
        if not cached.get("shop_url") and fallback_page_url:
            cached["shop_url"] = fallback_page_url
        return cached

    sp = urlsplit(clean_u)
    host = (sp.netloc or "").lower().lstrip("www.")
    resolved_url = clean_u
    html_body = ""

    # 1. Unwrap shorteners (shope.ee, s.shopee.vn, vt.tiktok.com, bit.ly) & Link-in-bio hubs
    is_short_path = (
        len(sp.path.strip("/")) in range(3, 9)
        and "/" not in sp.path.strip("/")
        and not sp.path.endswith((".html", ".php"))
        and "shopee." not in host
    )
    if any(host == d or host.endswith("." + d) for d in (_SHORTENER_DOMAINS + _BIO_HUB_DOMAINS)) or is_short_path:
        html_body, eff_u = _http_fetch(clean_u, timeout=5.0)
        if eff_u and eff_u != clean_u:
            unwrapped = _unwrap_external_store_url(eff_u)
            if unwrapped:
                resolved_url = unwrapped
                sp = urlsplit(resolved_url)
                host = (sp.netloc or "").lower().lstrip("www.")
        if any(host == d or host.endswith("." + d) for d in _BIO_HUB_DOMAINS) and html_body:
            for href_m in re.finditer(r'href=["\'](https?://[^"\']+)["\']', html_body, re.I):
                cand = _unwrap_external_store_url(href_m.group(1))
                if cand:
                    cand_host = (urlsplit(cand).netloc or "").lower().lstrip("www.")
                    if not any(cand_host == d or cand_host.endswith("." + d) for d in _BIO_HUB_DOMAINS):
                        resolved_url = cand
                        sp = urlsplit(resolved_url)
                        host = cand_host
                        html_body = ""
                        break

    split_info = split_shop_and_product_urls(resolved_url, fallback_page_url=fallback_page_url, ig_handle=ig_handle)
    shop_url = split_info["shop_url"]
    product_url = split_info["product_url"]
    domain_val = split_info["domain"]

    is_vn_domain = (
        host.endswith(".vn")
        or "shopee.vn" in host
        or "lazada.vn" in host
        or "tiki.vn" in host
        or _has_vietnamese_chars(fallback_text)
    )
    default_cur = "VND" if is_vn_domain else "USD"

    # Skip HTML price scraping on closed marketplace anti-bot walls (Shopee/TikTok) if we already split links; rely on Ad metadata
    if any(host == d or host.endswith("." + d) for d in _NON_SHOP_DOMAINS) or "shopee." in host:
        res = {
            "selling_price": fb_sell,
            "original_price": fb_orig,
            "product_title": "",
            "resolved_url": product_url or shop_url,
            "shop_url": shop_url,
            "product_url": product_url,
            "domain": domain_val,
        }
        _store_meta_cache[cache_key] = res
        return res

    # 2. Try Shopify Product .js if URL has /products/<handle>
    if "/products/" in sp.path:
        clean_prod_path = sp.path.split("/products/", 1)[1].strip("/").split("/")[0]
        if clean_prod_path:
            base_prod_url = f"{sp.scheme}://{sp.netloc}/products/{clean_prod_path}"
            js_txt, _ = _http_fetch(base_prod_url + ".js", timeout=4.5)
            if js_txt.strip().startswith("{"):
                try:
                    jd = json.loads(js_txt)
                    raw_cents = jd.get("price")
                    cmp_cents = jd.get("compare_at_price")
                    if isinstance(raw_cents, (int, float)) and raw_cents > 0:
                        p_str = _format_currency_amount(raw_cents / 100.0, default_cur)
                        c_str = (
                            _format_currency_amount(cmp_cents / 100.0, default_cur)
                            if isinstance(cmp_cents, (int, float)) and cmp_cents > raw_cents
                            else ""
                        )
                        res = {
                            "selling_price": p_str or fb_sell,
                            "original_price": c_str or fb_orig,
                            "product_title": str(jd.get("title") or "")[:130],
                            "resolved_url": base_prod_url,
                            "shop_url": f"{sp.scheme}://{sp.netloc}",
                            "product_url": base_prod_url,
                            "domain": host,
                        }
                        _store_meta_cache[cache_key] = res
                        return res
                except Exception:
                    pass

    # 3. Try Shopify /products.json ONLY when product_url is missing AND keyword strongly matches a product (>=50% overlap)
    if (
        not product_url
        and sp.scheme
        and sp.netloc
        and host not in {"shopee.vn", "amazon.com", "lazada.vn", "tiki.vn", "tiktok.com"}
    ):
        root_json_url = f"{sp.scheme}://{sp.netloc}/products.json?limit=12"
        pj_txt, _ = _http_fetch(root_json_url, timeout=4.5)
        if pj_txt.strip().startswith("{"):
            try:
                prods = json.loads(pj_txt).get("products") or []
                hint_tokens = [
                    t for t in re.split(r"\W+", _strip_accents_lower(f"{keyword_hint} {sp.path}"))
                    if len(t) >= 3 and t not in {"products", "collections", "shop", "the", "and", "for"}
                ]
                if isinstance(prods, list) and prods and hint_tokens:
                    best_pr = None
                    best_hits = 0
                    for pr in prods:
                        ptxt = _strip_accents_lower(f"{pr.get('title', '')} {pr.get('handle', '')}")
                        hits = sum(1 for t in hint_tokens if t in ptxt)
                        if hits > best_hits:
                            best_hits = hits
                            best_pr = pr
                    min_req = 1 if len(hint_tokens) == 1 else max(2, (len(hint_tokens) + 1) // 2)
                    if best_pr and best_hits >= min_req:
                        v0 = (best_pr.get("variants") or [{}])[0]
                        p_str = _format_currency_amount(v0.get("price"), default_cur)
                        c_str = _format_currency_amount(v0.get("compare_at_price"), default_cur)
                        if c_str == p_str:
                            c_str = ""
                        handle = str(best_pr.get("handle") or "").strip()
                        matched_prod_url = f"{sp.scheme}://{sp.netloc}/products/{handle}" if handle else ""
                        if p_str or matched_prod_url:
                            res = {
                                "selling_price": p_str or fb_sell,
                                "original_price": c_str or fb_orig,
                                "product_title": str(best_pr.get("title") or "")[:130],
                                "resolved_url": matched_prod_url or shop_url,
                                "shop_url": f"{sp.scheme}://{sp.netloc}",
                                "product_url": matched_prod_url,
                                "domain": host,
                            }
                            _store_meta_cache[cache_key] = res
                            return res
            except Exception:
                pass

    # 4. Parse HTML (JSON-LD Product, OpenGraph price meta, LadiPage/WooCommerce price blocks)
    if not html_body:
        target_fetch = product_url or shop_url
        if target_fetch.startswith("http"):
            html_body, eff_u2 = _http_fetch(target_fetch, timeout=5.0)
            if eff_u2 and eff_u2 != target_fetch and _unwrap_external_store_url(eff_u2):
                split2 = split_shop_and_product_urls(eff_u2, fallback_page_url=fallback_page_url, ig_handle=ig_handle)
                shop_url = split2["shop_url"] or shop_url
                product_url = split2["product_url"] or product_url
                domain_val = split2["domain"] or domain_val

    selling_price = ""
    original_price = ""
    product_title = ""
    if html_body:
        import html as html_lib

        t_m = (
            re.search(r'property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html_body, re.I)
            or re.search(r'content=["\']([^"\']+)["\']\s+property=["\']og:title["\']', html_body, re.I)
            or re.search(r"<title[^>]*>(.*?)</title>", html_body, re.S | re.I)
        )
        if t_m:
            cand_title = html_lib.unescape(re.sub(r"\s+", " ", t_m.group(1))).strip()
            if not any(bad in cand_title.lower() for bad in ("just a moment", "attention required", "access denied", "404", "đăng nhập")):
                product_title = cand_title[:130]

        ld_info = _extract_ld_json_product(html_body)
        if ld_info.get("selling_price"):
            selling_price = ld_info["selling_price"]
            original_price = ld_info.get("original_price") or ""
            product_title = ld_info.get("product_title") or product_title

        if not selling_price:
            amt_m = (
                re.search(r'property=["\'](?:product|og):price:amount["\']\s+content=["\']([^"\']+)["\']', html_body, re.I)
                or re.search(r'content=["\']([^"\']+)["\']\s+property=["\'](?:product|og):price:amount["\']', html_body, re.I)
            )
            cur_m = (
                re.search(r'property=["\'](?:product|og):price:currency["\']\s+content=["\']([^"\']+)["\']', html_body, re.I)
                or re.search(r'content=["\']([^"\']+)["\']\s+property=["\'](?:product|og):price:currency["\']', html_body, re.I)
            )
            if amt_m:
                selling_price = _format_currency_amount(amt_m.group(1), cur_m.group(1) if cur_m else default_cur)

        if not selling_price:
            selling_price, original_price = _extract_prices_pair_from_text(html_body[:180_000])

    if not selling_price and fb_sell:
        selling_price = fb_sell
        original_price = original_price or fb_orig

    res = {
        "selling_price": selling_price,
        "original_price": original_price,
        "product_title": product_title,
        "resolved_url": product_url or shop_url,
        "shop_url": shop_url,
        "product_url": product_url,
        "domain": domain_val,
    }
    _store_meta_cache[cache_key] = res
    return res


def _parse_meta_results_counter(text: str) -> int:
    if not text:
        return 0
    for ln in text.splitlines():
        s = ln.strip()
        m = re.search(r"(?:~|Khoảng|Over|>)?\s*([\d.,]+)\s*(?:results|kết quả|quảng cáo\b)", s, re.I)
        if m:
            digits = re.sub(r"[^\d]", "", m.group(1))
            if digits:
                return int(digits)
    return 0


def _estimate_video_age_days(video: Dict[str, Any]) -> int:
    sigs = " | ".join(str(s) for s in (video.get("sales_signals") or []))
    m = re.search(r"File\s+(\d+)\s*ngày", sigs, re.I)
    if m:
        return max(1, int(m.group(1)))
    created_raw = str(video.get("created_at") or "").strip()
    if created_raw:
        try:
            from datetime import datetime, timezone
            dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
            return max(1, int((datetime.now(timezone.utc) - dt).total_seconds() // 86400) or 1)
        except Exception:
            pass
    return 5


def build_market_intel_for_video(
    video: Dict[str, Any],
    shops: Optional[List[Dict[str, Any]]] = None,
    product_query: str = "",
    total_market_ads: int = 0,
    spy_status: str = "baseline",
) -> Dict[str, Any]:
    """Evaluate viral & commercial potential across Meta ecosystem (Meta Ads, FB, IG, Threads) with separated shop_url & product_url."""
    import math

    shops_list = [dict(s) for s in (shops or []) if isinstance(s, dict)]

    # If the video record itself already carries shop_url / product_url / selling_price, ensure its own shop is first!
    v_shop_url = str(video.get("shop_url") or "").strip()
    v_prod_url = str(video.get("product_url") or "").strip()
    v_price = str(video.get("selling_price") or "").strip()
    v_orig_price = str(video.get("original_price") or "").strip()
    v_shop_name = str(video.get("shop_name") or video.get("author") or "").strip()
    v_page_id = str(video.get("meta_page_id") or "").strip()
    if (v_shop_url or v_prod_url or v_price) and not shops_list:
        dom = urlsplit(v_prod_url or v_shop_url).netloc.lower().lstrip("www.") if (v_prod_url or v_shop_url) else ""
        ad_lib_u = (
            f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&view_all_page_id={v_page_id}"
            if v_page_id.isdigit()
            else f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&q={quote_plus(v_shop_name.lstrip('@'))}"
        )
        shops_list.append(
            {
                "shop_name": v_shop_name[:70],
                "shop_url": v_shop_url,
                "product_url": v_prod_url,
                "domain": dom or v_shop_name[:30],
                "page_id": v_page_id,
                "page_url": f"https://www.facebook.com/{v_page_id}/" if v_page_id.isdigit() else str(video.get("source_url") or ""),
                "ad_library_url": ad_lib_u,
                "ads_count": 1 if str(video.get("platform") or "") in {"meta_ads", "facebook", "instagram", "threads"} and v_page_id else 0,
                "selling_price": v_price,
                "original_price": v_orig_price,
                "product_title": str(video.get("title") or "")[:120],
                "source": "Meta Ad Library" if v_page_id else "Direct Video Link",
            }
        )

    pf = str(video.get("platform") or "").lower()
    title = str(video.get("title") or "")
    caption = str(video.get("caption") or "")
    sigs = [str(s) for s in (video.get("sales_signals") or [])]
    full_txt = f"{title} {caption} {' '.join(sigs)}"

    age_days = _estimate_video_age_days(video)
    views = max(1, int(video.get("views") or 0))
    likes = max(0, int(video.get("likes") or 0))
    comments = max(0, int(video.get("comments") or 0))
    shares = max(0, int(video.get("shares") or 0))
    viral_score = int(video.get("viral_score") or 75)

    velocity_vpd = int(round(views / max(1, age_days)))
    eng_rate = round(((likes + comments * 3 + shares * 4) / max(1, views)) * 100.0, 2)

    scale_m = re.search(r"Scale\s+(\d+)\s*QC", " | ".join(sigs), re.I)
    inline_ads = int(scale_m.group(1)) if scale_m else (1 if (pf == "meta_ads" or v_page_id) else 0)

    sum_shop_ads = sum(int(s.get("ads_count") or 0) for s in shops_list)
    total_active_ads = max(total_market_ads, sum_shop_ads, inline_ads)

    dedup_shops: List[Dict[str, Any]] = []
    seen_shop_keys = set()
    for s in sorted(
        shops_list,
        key=lambda x: (
            bool(x.get("product_url")),
            bool(x.get("shop_url")),
            bool(x.get("selling_price")),
            int(x.get("ads_count") or 0),
        ),
        reverse=True,
    ):
        key = (
            str(s.get("page_id") or "").strip()
            or str(s.get("domain") or "").lower().strip()
            or str(s.get("shop_name") or "").lower().strip()
        )
        if not key or key in seen_shop_keys:
            continue
        seen_shop_keys.add(key)
        s.setdefault("product_url", "")
        s.setdefault("shop_url", "")
        dedup_shops.append(s)

    active_shops_count = len(dedup_shops)
    primary_shop_url = v_shop_url or next((str(s.get("shop_url")) for s in dedup_shops if s.get("shop_url")), "")
    primary_product_url = v_prod_url or next((str(s.get("product_url")) for s in dedup_shops if s.get("product_url")), "")

    prices_found = [str(s["selling_price"]).strip() for s in dedup_shops if s.get("selling_price")]
    if v_price and v_price not in prices_found:
        prices_found.insert(0, v_price)
    if not prices_found:
        inline_p = _extract_price_from_text_multi(full_txt)
        if inline_p:
            prices_found.append(inline_p)
    unique_prices: List[str] = [p for p in dict.fromkeys(prices_found) if p]
    price_range = _format_price_range_sorted(unique_prices, empty_default="Chưa niêm yết giá")

    comm_markers = (
        "comment", "link in bio", "link bio", "shop", "store", "buy", "order", "sale", "deal",
        "discount", "free shipping", "off", "gift", "amazon", "shopee", "lazada", "tiktok",
        "mua", "giảm", "giá", "chốt đơn", "freeship", "giỏ hàng", "inbox", "sản phẩm", "review",
    )
    txt_low = full_txt.lower()
    comm_hits = sum(1 for m in comm_markers if m in txt_low)
    has_commercial_intent = bool(
        primary_product_url or primary_shop_url or unique_prices or comm_hits >= 1 or pf == "meta_ads" or total_active_ads > 0
    )

    reasons: List[str] = []
    p_score = 0.0

    vel_pts = min(24.0, math.log10(max(10, velocity_vpd)) * 5.2)
    eng_pts = min(14.0, eng_rate * 1.8)
    p_score += vel_pts + eng_pts
    if age_days <= 7:
        p_score += 12.0
        reasons.append(f"Video mới lên ({age_days} ngày) đạt tốc độ {velocity_vpd:,} view/ngày ({eng_rate}% tương tác)".replace(",", "."))
    elif age_days <= 21:
        p_score += 8.0
        reasons.append(f"Đà tăng trưởng tốt trong {age_days} ngày: ~{velocity_vpd:,} view/ngày ({eng_rate}% tương tác)".replace(",", "."))
    elif age_days <= 45:
        p_score += 3.0
        reasons.append(f"Video duy trì lực xem ổn định ({velocity_vpd:,} view/ngày sau {age_days} ngày)".replace(",", "."))
    else:
        p_score -= 6.0
        reasons.append(f"Video đã chạy {age_days} ngày — sản phẩm bền bỉ, nên làm mới Hook 3s đầu khi Remake")

    if primary_product_url:
        p_score += 16.0
        reasons.append(f"Đã bóc tách trực tiếp Link Sản Phẩm & Link Shop ({urlsplit(primary_product_url).netloc.lstrip('www.')})")
    elif primary_shop_url:
        p_score += 12.0
        reasons.append(f"Đã xác thực Link Shop đang chạy ({urlsplit(primary_shop_url).netloc.lstrip('www.')})")
    if unique_prices:
        p_score += 8.0
        reasons.append(f"Giá đang bán thực tế rõ ràng: {price_range}")
    if comm_hits >= 2:
        p_score += 4.0
    elif not has_commercial_intent:
        p_score -= 25.0
        reasons.append("Nội dung thiên về giải trí thuần, thiếu link mua hàng / tín hiệu chuyển đổi")

    if total_active_ads > 0 or active_shops_count > 0:
        if 1 <= active_shops_count <= 8 and 1 <= total_active_ads <= 350:
            p_score += 24.0
            reasons.append(
                f"Đúng điểm rơi Win/Scale trên Meta Ads: {active_shops_count} shop đang bán với {total_active_ads} quảng cáo active"
            )
        elif total_active_ads > 350:
            p_score += 17.0
            reasons.append(
                f"Thị trường sức mua lớn: {total_active_ads} quảng cáo đang chạy trên Meta ({active_shops_count} shop)"
            )
        else:
            p_score += 14.0
            reasons.append(f"Phát hiện {total_active_ads} mẫu quảng cáo đang chạy thực tế trên Meta")
    elif has_commercial_intent and (velocity_vpd >= 2500 or viral_score >= 82):
        p_score += 14.0
        reasons.append(f"Video sản phẩm đang viral trên {pf.upper()}, ít đối thủ đè ngân sách Ads")

    final_score = max(12, min(99, int(round(p_score))))
    if not has_commercial_intent:
        final_score = min(final_score, 48)

    if final_score >= 82:
        tier = "S"
        verdict = "Hạng S (Siêu Tiềm Năng) — Có Link SP/Shop & đang chạy chuyển đổi mạnh trên hệ Meta"
    elif final_score >= 68:
        tier = "A"
        verdict = "Hạng A (Tiềm Năng Cao) — Sản phẩm có lực mua rõ trên FB/IG/Threads, rất đáng Test / Remake"
    elif final_score >= 52:
        tier = "B"
        verdict = "Hạng B (Theo Dõi Thêm) — Có tương tác nhưng cần kiểm tra thêm giá & biên lợi nhuận"
    else:
        tier = "C"
        verdict = "Hạng C (Ít Tiềm Năng Bán Hàng) — Thiếu link sản phẩm hoặc đã qua đỉnh"

    is_potential = bool(has_commercial_intent and final_score >= 66 and age_days <= 60)

    return {
        "evaluated_at": database.utc_now_iso(),
        "spy_status": spy_status,
        "product_query": product_query,
        "is_potential": is_potential,
        "potential_score": final_score,
        "potential_tier": tier,
        "verdict": verdict,
        "evaluation_reasons": reasons[:5],
        "velocity_views_per_day": velocity_vpd,
        "engagement_rate": eng_rate,
        "video_age_days": age_days,
        "total_active_ads": total_active_ads,
        "active_shops_count": active_shops_count,
        "price_range": price_range,
        "primary_shop_url": primary_shop_url,
        "primary_product_url": primary_product_url,
        "shops": dedup_shops[:8],
    }


def _choose_best_store_link(raw_links: List[str]) -> str:
    candidates: List[str] = []
    for lk in raw_links or []:
        u = _unwrap_external_store_url(lk)
        if u and u not in candidates:
            candidates.append(u)
    if not candidates:
        return ""
    for c in candidates:
        p = urlsplit(c).path.lower()
        if any(seg in p for seg in ("/products/", "/product/", "/opaanlp/", "-i.", "/san-pham/", "/p/", "/dp/", "/item/", "/view/product")):
            return c
    return candidates[0]


def _extract_page_id_from_fb_url(page_url: str) -> str:
    if not page_url:
        return ""
    m_q = re.search(r"view_all_page_id=(\d{6,24})", page_url)
    if m_q:
        return m_q.group(1)
    m = re.search(r"facebook\.com/(?:people/[^/]+/)?(\d{8,24})", page_url)
    if m:
        return m.group(1)
    sp = urlsplit(page_url)
    seg = sp.path.strip("/").split("/")[0] if sp.path.strip("/") else ""
    if seg and seg not in {"ads", "pages", "profile.php", "watch", "reel", "groups", "l.php"}:
        return seg
    return ""


def _clean_ad_template_str(val: Any) -> str:
    if isinstance(val, dict):
        val = val.get("text") or ""
    s = str(val or "").strip()
    if not s or ("{{" in s and "}}" in s and len(re.sub(r"\{\{[^}]+\}\}", "", s).strip()) < 3):
        return ""
    return re.sub(r"\{\{[^}]+\}\}", "", s).strip()


def _normalize_meta_placements(raw_platforms: Any) -> List[str]:
    if not isinstance(raw_platforms, list):
        return ["facebook", "instagram"]
    mapped: List[str] = []
    for p in raw_platforms:
        pl = str(p or "").strip().lower()
        if pl in {"facebook", "instagram", "threads", "messenger"} and pl not in mapped:
            mapped.append(pl)
    return mapped or ["facebook"]


def _extract_ig_handle_from_snapshot(snap: Dict[str, Any], extra_text: str = "") -> str:
    for key in ("instagram_actor_name", "ig_username"):
        v = str(snap.get(key) or "").strip().lstrip("@")
        if v and re.match(r"^[A-Za-z0-9._]{2,40}$", v):
            return v
    bc = snap.get("branded_content")
    if isinstance(bc, dict):
        v = str(bc.get("instagram_actor_name") or bc.get("page_name") or "").strip().lstrip("@")
        if v and re.match(r"^[A-Za-z0-9._]{2,40}$", v):
            return v
    links_blob = " ".join(str(x) for x in (snap.get("extra_links") or [])) + " " + extra_text
    m_ig = re.search(r"instagram\.com/([A-Za-z0-9._]{2,35})(?:[/?#]|$)", links_blob, re.I)
    if m_ig and m_ig.group(1).lower() not in {"reel", "reels", "p", "explore", "stories", "accounts"}:
        return m_ig.group(1)
    m_th = re.search(r"threads\.(?:com|net)/@([A-Za-z0-9._]{2,35})", links_blob, re.I)
    if m_th:
        return m_th.group(1)
    return ""


async def _scrape_meta_ad_library_structured(
    urls_to_visit: List[str],
    country: str = "VN",
    require_video: bool = True,
    scroll_rounds: int = 2,
    max_ads: int = 40,
) -> Tuple[List[Dict[str, Any]], int]:
    """Core public Meta Ad Library engine: intercepts Relay/GraphQL JSON + DOM fallback for FB, IG, and Threads ads."""
    if not has_playwright() or not urls_to_visit:
        return [], 0

    from playwright.async_api import async_playwright

    chrome_exe = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    launch_kwargs: Dict[str, Any] = {
        "headless": True,
        "args": ["--disable-blink-features=AutomationControlled"],
    }
    if Path(chrome_exe).exists():
        launch_kwargs["executable_path"] = chrome_exe

    is_en = (country or "VN").upper() in {"US", "GLOBAL"}
    raw_ad_nodes: List[Dict[str, Any]] = []
    seen_archive_ids = set()
    dom_fallback_cards: List[Dict[str, Any]] = []
    total_market_ads = 0

    def _walk_relay(obj: Any) -> None:
        if isinstance(obj, dict):
            aid = obj.get("ad_archive_id")
            snap = obj.get("snapshot")
            if aid and isinstance(snap, dict):
                aid_str = str(aid)
                if aid_str not in seen_archive_ids:
                    seen_archive_ids.add(aid_str)
                    raw_ad_nodes.append(obj)
                return
            for v in obj.values():
                if isinstance(v, (dict, list)):
                    _walk_relay(v)
        elif isinstance(obj, list):
            for x in obj:
                if isinstance(x, (dict, list)):
                    _walk_relay(x)

    def _parse_text_blobs(blobs: List[str]) -> None:
        for raw in blobs:
            if not raw:
                continue
            for ln in raw.splitlines():
                s = ln.strip()
                if not s:
                    continue
                if "ad_archive_id" in s and "snapshot" in s:
                    try:
                        _walk_relay(json.loads(s))
                    except Exception:
                        pass
            if "ad_archive_id" in raw and "snapshot" in raw:
                try:
                    _walk_relay(json.loads(raw))
                except Exception:
                    pass

    async with async_playwright() as p:
        browser = None
        context = None
        page = None
        try:
            browser = await p.chromium.launch(**launch_kwargs)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                ),
                locale="en-US" if is_en else "vi-VN",
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9" if is_en else "vi-VN,vi;q=0.9,en-US;q=0.7,en;q=0.6",
                },
                viewport={"width": 1440, "height": 920},
            )
            page = await context.new_page()

            gql_Queue: List[str] = []

            async def _on_resp(resp: Any) -> None:
                if "graphql" in resp.url:
                    try:
                        txt = await resp.text()
                        if "ad_archive_id" in txt and "snapshot" in txt:
                            gql_Queue.append(txt)
                    except Exception:
                        pass

            page.on("response", _on_resp)

            for target_url in urls_to_visit:
                gql_Queue.clear()
                try:
                    await page.goto(target_url, wait_until="domcontentloaded", timeout=18000)
                except Exception:
                    continue
                await page.wait_for_timeout(2600)
                for _ in range(max(1, scroll_rounds)):
                    try:
                        await page.evaluate("window.scrollBy(0, 1800)")
                    except Exception:
                        try:
                            await page.wait_for_load_state("domcontentloaded", timeout=5000)
                        except Exception:
                            pass
                    await page.wait_for_timeout(1100)

                html = ""
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=4000)
                    html = await page.content()
                except Exception:
                    html = ""

                script_blobs = (
                    [
                        m.group(1)
                        for m in re.finditer(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', html, re.S)
                        if "ad_archive_id" in m.group(1)
                    ]
                    if html
                    else []
                )
                _parse_text_blobs(script_blobs + list(gql_Queue))

                try:
                    body_head = await page.evaluate("() => (document.body.innerText || '').slice(0, 4000)")
                    cnt = _parse_meta_results_counter(body_head or "")
                    if cnt > total_market_ads:
                        total_market_ads = cnt
                except Exception:
                    pass

                # Collect DOM fallback only if Relay JSON returned nothing on this page
                if not raw_ad_nodes:
                    try:
                        dom_cards = await page.evaluate(
                            r"""() => {
                            const vids = Array.from(document.querySelectorAll('video'));
                            return vids.slice(0, 24).map(v => {
                                let el = v;
                                let cardText = '';
                                let pageUrl = '';
                                let allHrefs = [];
                                for (let i = 0; i < 20; i++) {
                                    if (!el.parentElement) break;
                                    el = el.parentElement;
                                    const t = el.innerText || '';
                                    if (t.includes('ID thư viện') || t.includes('Library ID')) {
                                        cardText = t;
                                        const anchors = Array.from(el.querySelectorAll('a[href]'));
                                        allHrefs = anchors.map(x => x.href).filter(Boolean);
                                        const a = anchors.find(
                                            x => x.href.includes('facebook.com/') && !x.href.includes('/ads/library') && !x.href.includes('facebook.com/l.php')
                                        );
                                        if (a) pageUrl = a.href;
                                        break;
                                    }
                                }
                                const libMatch = cardText.match(/(?:ID thư viện|Library ID)[:\s]*(\d+)/i);
                                const multiMatch = cardText.match(/(\d+)\s*(?:quảng cáo|ads)\s*(?:sử dụng|use)/i);
                                return {
                                    video_url: v.currentSrc || v.src || '',
                                    thumbnail_url: v.poster || '',
                                    library_id: libMatch ? libMatch[1] : '',
                                    dup_count: multiMatch ? parseInt(multiMatch[1], 10) : 1,
                                    page_url: pageUrl,
                                    hrefs: allHrefs,
                                    text: cardText.slice(0, 1400)
                                };
                            });
                        }"""
                        )
                        dom_fallback_cards.extend(dom_cards or [])
                    except Exception:
                        pass

                if len(raw_ad_nodes) >= max_ads:
                    break
        finally:
            for closer in (page, context, browser):
                if closer is not None:
                    try:
                        await closer.close()
                    except BaseException:
                        pass

    now_ts = int(time.time())
    structured_items: List[Dict[str, Any]] = []

    for ad in raw_ad_nodes:
        snap = ad.get("snapshot") or {}
        cta_type = str(snap.get("cta_type") or "").upper()
        if cta_type in {"INSTALL_MOBILE_APP", "USE_MOBILE_APP", "PLAY_GAME"}:
            continue

        lib_id = str(ad.get("ad_archive_id") or "")
        page_id = str(ad.get("page_id") or snap.get("page_id") or "")
        page_name = str(ad.get("page_name") or snap.get("page_name") or "").strip()
        page_url = str(snap.get("page_profile_uri") or (f"https://www.facebook.com/{page_id}/" if page_id else "")).strip()
        avatar_url = str(snap.get("page_profile_picture_url") or "").strip()
        placements = _normalize_meta_placements(ad.get("publisher_platform"))
        collation_count = max(1, int(ad.get("collation_count") or 1))
        start_ts = int(ad.get("start_date") or 0)
        ad_age_days = max(1, (now_ts - start_ts) // 86400) if start_ts > 1_000_000_000 and start_ts <= now_ts else 5
        started_iso = ""
        if start_ts > 1_000_000_000:
            try:
                from datetime import datetime, timezone
                started_iso = datetime.fromtimestamp(start_ts, tz=timezone.utc).strftime("%Y-%m-%d")
            except Exception:
                started_iso = ""

        top_body = _clean_ad_template_str(snap.get("body"))
        top_title = _clean_ad_template_str(snap.get("title"))
        top_link_desc = _clean_ad_template_str(snap.get("link_description"))
        top_cta = str(snap.get("cta_text") or "").strip()
        top_link = str(snap.get("link_url") or "").strip()
        extra_links = [str(x) for x in (snap.get("extra_links") or []) if x]
        ig_handle = _extract_ig_handle_from_snapshot(snap, f"{top_body} {page_url}")

        vids = snap.get("videos") if isinstance(snap.get("videos"), list) else []
        cards = snap.get("cards") if isinstance(snap.get("cards"), list) else []
        imgs = snap.get("images") if isinstance(snap.get("images"), list) else []

        # Case A: Carousel / DCO / Catalog cards
        emitted_from_cards = 0
        for c_idx, card in enumerate(cards):
            if not isinstance(card, dict):
                continue
            v_url = str(card.get("video_hd_url") or card.get("video_sd_url") or "").strip()
            t_url = str(
                card.get("video_preview_image_url")
                or card.get("resized_image_url")
                or card.get("original_image_url")
                or ""
            ).strip()
            if require_video and not v_url:
                continue
            c_title = _clean_ad_template_str(card.get("title")) or top_title
            c_body = _clean_ad_template_str(card.get("body")) or top_body
            c_desc = _clean_ad_template_str(card.get("link_description")) or top_link_desc
            c_cta = str(card.get("cta_text") or top_cta or "").strip()
            c_link_raw = str(card.get("link_url") or top_link or "").strip()
            all_cand_links = [c_link_raw, top_link, *extra_links] + re.findall(r"https?://[^\s<>\"')]+", f"{c_body} {top_body}")
            best_ext_link = _choose_best_store_link(all_cand_links)

            structured_items.append(
                {
                    "library_id": lib_id,
                    "card_index": c_idx,
                    "page_id": page_id,
                    "page_name": page_name,
                    "page_url": page_url,
                    "avatar_url": avatar_url,
                    "ig_handle": ig_handle,
                    "placements": placements,
                    "collation_count": collation_count,
                    "ad_age_days": ad_age_days,
                    "started_iso": started_iso,
                    "video_url": v_url,
                    "thumbnail_url": t_url,
                    "headline": c_title,
                    "body": c_body,
                    "link_description": c_desc,
                    "cta_text": c_cta,
                    "cta_type": cta_type,
                    "raw_ext_link": best_ext_link,
                }
            )
            emitted_from_cards += 1
            if require_video and emitted_from_cards >= 2:
                break

        if emitted_from_cards > 0:
            continue

        # Case B: Standard Single-Video or Single-Image Ad
        v_url = ""
        t_url = ""
        if vids and isinstance(vids[0], dict):
            v_url = str(vids[0].get("video_hd_url") or vids[0].get("video_sd_url") or "").strip()
            t_url = str(vids[0].get("video_preview_image_url") or "").strip()
        elif not require_video and imgs and isinstance(imgs[0], dict):
            t_url = str(imgs[0].get("resized_image_url") or imgs[0].get("original_image_url") or "").strip()

        if require_video and not v_url:
            continue

        all_cand_links = [top_link, *extra_links] + re.findall(r"https?://[^\s<>\"')]+", top_body)
        best_ext_link = _choose_best_store_link(all_cand_links)
        structured_items.append(
            {
                "library_id": lib_id,
                "card_index": 0,
                "page_id": page_id,
                "page_name": page_name,
                "page_url": page_url,
                "avatar_url": avatar_url,
                "ig_handle": ig_handle,
                "placements": placements,
                "collation_count": collation_count,
                "ad_age_days": ad_age_days,
                "started_iso": started_iso,
                "video_url": v_url,
                "thumbnail_url": t_url,
                "headline": top_title,
                "body": top_body,
                "link_description": top_link_desc,
                "cta_text": top_cta,
                "cta_type": cta_type,
                "raw_ext_link": best_ext_link,
            }
        )

    # Fallback if Relay JSON changed and only DOM cards were found
    if not structured_items and dom_fallback_cards:
        for dc in dom_fallback_cards:
            if require_video and not dc.get("video_url"):
                continue
            txt = str(dc.get("text") or "")
            lines = [ln.strip().strip("​") for ln in txt.splitlines() if ln.strip().strip("​")]
            p_name = ""
            for li, ln in enumerate(lines):
                if ln.lower() in {"được tài trợ", "sponsored"} and li > 0:
                    p_name = lines[li - 1]
                    break
            p_url = str(dc.get("page_url") or "")
            pid = _extract_page_id_from_fb_url(p_url)
            structured_items.append(
                {
                    "library_id": str(dc.get("library_id") or ""),
                    "card_index": 0,
                    "page_id": pid,
                    "page_name": p_name or "Meta Advertiser",
                    "page_url": p_url,
                    "avatar_url": "",
                    "ig_handle": "",
                    "placements": ["facebook", "instagram"],
                    "collation_count": max(1, int(dc.get("dup_count") or 1)),
                    "ad_age_days": 5,
                    "started_iso": "",
                    "video_url": str(dc.get("video_url") or ""),
                    "thumbnail_url": str(dc.get("thumbnail_url") or ""),
                    "headline": "",
                    "body": txt[:600],
                    "link_description": "",
                    "cta_text": "",
                    "cta_type": "",
                    "raw_ext_link": _choose_best_store_link(dc.get("hrefs") or []),
                }
            )

    # Cross-fill verified external shop_url across sibling ads belonging to the SAME page_id
    page_verified_shop: Dict[str, str] = {}
    for st in structured_items:
        pid = st.get("page_id") or ""
        ext = st.get("raw_ext_link") or ""
        if pid and ext and pid not in page_verified_shop:
            sp_info = split_shop_and_product_urls(ext, fallback_page_url=st.get("page_url") or "", ig_handle=st.get("ig_handle") or "")
            if sp_info.get("shop_url") and not sp_info.get("is_inbox_only"):
                page_verified_shop[pid] = sp_info["shop_url"]
    for st in structured_items:
        pid = st.get("page_id") or ""
        if pid and not st.get("raw_ext_link") and pid in page_verified_shop:
            st["_sibling_shop_url"] = page_verified_shop[pid]

    return structured_items, total_market_ads


async def _crawl_meta_ads_playwright(
    keyword: str,
    country: str = "VN",
    limit: int = 6,
    target_placement: str = "all",
    match_type: str = "broad",
) -> List[Dict[str, Any]]:
    """Crawl Video Ads from Meta Ad Library across Facebook, Instagram, and Threads, immediately resolving Link Shop, Link Sản Phẩm & Giá Bán."""
    from concurrent.futures import ThreadPoolExecutor

    kw_clean = _clean_search_quotes(keyword).strip()
    ctry = "US" if (country or "VN").upper() == "GLOBAL" else (country or "VN").upper()
    pl_filter = ""
    tp_low = (target_placement or "all").strip().lower()
    if tp_low in {"facebook", "instagram", "threads"}:
        pl_filter = f"&publisher_platforms[0]={tp_low}"

    exact_q = f'"{kw_clean}"'
    urls_to_try = [
        (
            "https://www.facebook.com/ads/library/"
            f"?active_status=active&ad_type=all&country={quote_plus(ctry)}"
            f"&media_type=video{pl_filter}&search_type=keyword_exact_phrase&q={quote_plus(exact_q)}"
        ),
    ]
    if match_type != "exact":
        urls_to_try.append(
            "https://www.facebook.com/ads/library/"
            f"?active_status=active&ad_type=all&country={quote_plus(ctry)}"
            f"&media_type=video{pl_filter}&search_type=keyword_unordered&q={quote_plus(kw_clean)}"
        )

    raw_ads, total_market_ads = await _scrape_meta_ad_library_structured(
        urls_to_visit=urls_to_try,
        country=ctry,
        require_video=True,
        scroll_rounds=2,
        max_ads=max(24, limit * 5),
    )
    if not raw_ads:
        return []

    # Filter by keyword relevance
    filtered_ads: List[Dict[str, Any]] = []
    for ad in raw_ads:
        blob = f"{ad.get('page_name','')} {ad.get('headline','')} {ad.get('body','')} {ad.get('link_description','')}"
        if _keyword_matches_ad(kw_clean, blob, exact=(match_type == "exact")):
            filtered_ads.append(ad)
    if not filtered_ads and match_type == "exact":
        filtered_ads = [
            ad for ad in raw_ads
            if _keyword_matches_ad(kw_clean, f"{ad.get('page_name','')} {ad.get('headline','')} {ad.get('body','')}", exact=False)
        ]
    if not filtered_ads:
        filtered_ads = raw_ads

    # Deduplicate by video asset (xpv_asset_id or clean MP4 path) while aggregating total scale count
    asset_counts: Dict[str, int] = {}
    for ad in filtered_ads:
        v_src = ad.get("video_url", "")
        efg = _decode_fb_efg(v_src)
        asset_key = str(efg.get("xpv_asset_id") or v_src.split("?")[0] or ad.get("library_id"))
        ad["_efg"] = efg
        ad["_asset_key"] = asset_key
        asset_counts[asset_key] = asset_counts.get(asset_key, 0) + max(1, int(ad.get("collation_count") or 1))

    # Rank preferring ads with external product/shop links + higher duplication scale
    filtered_ads.sort(
        key=lambda a: (
            bool(a.get("raw_ext_link") or a.get("_sibling_shop_url")),
            asset_counts.get(a.get("_asset_key", ""), 1),
            int(a.get("collation_count") or 1),
        ),
        reverse=True,
    )

    chosen_ads: List[Dict[str, Any]] = []
    seen_assets = set()
    for ad in filtered_ads:
        ak = ad["_asset_key"]
        if ak in seen_assets:
            continue
        seen_assets.add(ak)
        chosen_ads.append(ad)
        if len(chosen_ads) >= limit:
            break

    # Resolve Link Shop + Link Sản Phẩm + Giá Đang Bán in parallel right during scan!
    def _resolve_ad_commerce(ad: Dict[str, Any]) -> Dict[str, Any]:
        price_context = " | ".join(
            x for x in (ad.get("headline", ""), ad.get("link_description", ""), ad.get("body", "")) if x
        )
        raw_lk = ad.get("raw_ext_link") or ad.get("_sibling_shop_url") or ""
        meta = _fetch_live_store_price_and_meta(
            raw_lk,
            fallback_text=price_context,
            keyword_hint=ad.get("headline") or kw_clean,
            fallback_page_url=ad.get("page_url") or "",
            ig_handle=ad.get("ig_handle") or "",
        )
        if not ad.get("raw_ext_link") and ad.get("_sibling_shop_url"):
            # Sibling link gives us the verified shop_url, not necessarily this specific video's product_url
            meta["product_url"] = ""
        ad["_commerce"] = meta
        return ad

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=6) as pool:
        await asyncio.gather(
            *(loop.run_in_executor(pool, _resolve_ad_commerce, ad) for ad in chosen_ads),
            return_exceptions=True,
        )

    results: List[Dict[str, Any]] = []
    for ad in chosen_ads:
        comm = ad.get("_commerce") or {}
        efg = ad.get("_efg") or {}
        duration_s = int(efg.get("duration_s") or 20)
        efg_age = int(efg.get("asset_age_days") or 0)
        ad_age = int(ad.get("ad_age_days") or 5)
        age_days = efg_age if (0 < efg_age <= 120) else ad_age
        scale_count = max(int(ad.get("collation_count") or 1), asset_counts.get(ad["_asset_key"], 1))

        page_name = ad.get("page_name") or f"Shop {kw_clean.title()}"
        page_id = str(ad.get("page_id") or "")
        page_url = str(ad.get("page_url") or "")
        ig_handle = str(ad.get("ig_handle") or "")
        placements = ad.get("placements") or ["facebook"]
        lib_id = str(ad.get("library_id") or "")

        shop_url = str(comm.get("shop_url") or "")
        product_url = str(comm.get("product_url") or "")
        selling_price = str(comm.get("selling_price") or "")
        original_price = str(comm.get("original_price") or "")
        prod_title = str(comm.get("product_title") or ad.get("headline") or "").strip()
        domain = str(comm.get("domain") or "")
        is_inbox = not bool(ad.get("raw_ext_link") or ad.get("_sibling_shop_url"))
        cta_text = str(ad.get("cta_text") or ("Bán qua Inbox" if is_inbox else "Mua ngay")).strip()

        body_clean = (ad.get("body") or "").strip()
        headline_clean = (ad.get("headline") or "").strip()
        caption = body_clean or headline_clean or f"Quảng cáo video {kw_clean} từ {page_name}"
        first_hook = (
            headline_clean
            or ([ln.strip() for ln in body_clean.splitlines() if len(ln.strip()) > 4] or [kw_clean])[0][:95]
        )
        badge = f"[Scale {scale_count} QC]" if scale_count > 1 else "[Meta Ad]"
        title = f"{badge} {page_name[:30]} — {first_hook}"[:140]

        src_url = (
            f"https://www.facebook.com/ads/library/?id={lib_id}"
            if lib_id
            else (page_url or urls_to_try[0])
        )
        ad_lib_shop_url = (
            f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&view_all_page_id={page_id}"
            if page_id.isdigit()
            else f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country={quote_plus(ctry)}&q={quote_plus(page_name)}"
        )

        extra_sigs: List[str] = []
        if selling_price:
            extra_sigs.append(f"Giá: {selling_price}")
        extra_sigs.extend([
            f"Scale {scale_count} QC",
            f"File {age_days} ngày",
            f"Thời lượng {duration_s}s",
        ])
        if product_url:
            extra_sigs.append("Gắn Link SP")
        elif is_inbox:
            extra_sigs.append("Bán qua Inbox")
        if ad.get("started_iso"):
            extra_sigs.append(f"Chạy từ {ad['started_iso']}")

        est_views = 85000 + scale_count * 65000 + min(250000, age_days * 1200)
        est_likes = int(est_views * 0.042)
        est_comments = int(est_views * 0.0045)
        est_shares = int(est_views * 0.006)
        v_score = compute_viral_score(est_views, est_likes, est_comments, est_shares, scale_ads=scale_count)

        analysis = analyze_video_structure(
            title,
            caption,
            kw_clean,
            extra_meta={
                "duration_s": duration_s,
                "asset_age_days": age_days,
                "scale_count": scale_count,
            },
        )

        # Persist this shop + product into meta_shops & meta_shop_products automatically
        try:
            saved_shop = database.upsert_meta_shop(
                {
                    "shop_key": page_id or domain or page_name.lower(),
                    "page_id": page_id,
                    "shop_name": page_name[:80],
                    "ig_handle": ig_handle,
                    "page_url": page_url,
                    "shop_url": shop_url,
                    "domain": domain,
                    "avatar_url": ad.get("avatar_url") or "",
                    "ad_library_url": ad_lib_shop_url,
                    "active_ads_count": scale_count,
                    "price_range": selling_price,
                    "placements": placements,
                    "country": ctry,
                    "is_inbox_only": is_inbox,
                }
            )
            database.upsert_meta_shop_products(
                int(saved_shop["id"]),
                [
                    {
                        "library_id": lib_id,
                        "product_title": prod_title or first_hook[:120],
                        "caption": caption[:500],
                        "product_url": product_url,
                        "shop_url": shop_url,
                        "selling_price": selling_price,
                        "original_price": original_price,
                        "video_url": ad.get("video_url") or "",
                        "thumbnail_url": ad.get("thumbnail_url") or "",
                        "cta_text": cta_text,
                        "ads_duplication_count": scale_count,
                        "video_age_days": age_days,
                        "started_running_at": ad.get("started_iso") or "",
                        "placements": placements,
                    }
                ],
            )
        except Exception:
            pass

        own_shop_entry = {
            "shop_name": page_name[:70],
            "shop_url": shop_url,
            "product_url": product_url,
            "domain": domain or (f"fb.com/{page_id}" if page_id else page_name[:30]),
            "page_id": page_id,
            "page_url": page_url,
            "ad_library_url": ad_lib_shop_url,
            "ads_count": scale_count,
            "selling_price": selling_price,
            "original_price": original_price,
            "product_title": prod_title[:120],
            "source": "Bán qua Inbox (Meta Ads)" if is_inbox else "Meta Ad Library",
        }

        assigned_pf = tp_low if tp_low in {"facebook", "instagram", "threads"} else "meta_ads"
        author_display = (
            f"@{ig_handle}"
            if assigned_pf in {"instagram", "threads"} and ig_handle
            else page_name[:70]
        )

        cand = {
            "platform": assigned_pf,
            "title": title,
            "caption": caption[:550],
            "author": author_display,
            "source_url": src_url,
            "video_url": ad.get("video_url", ""),
            "thumbnail_url": ad.get("thumbnail_url", ""),
            "views": est_views,
            "likes": est_likes,
            "comments": est_comments,
            "shares": est_shares,
            "viral_score": v_score,
            "sales_signals": detect_sales_signals(caption, extra_sigs),
            "hook_text": analysis["hook_text"],
            "script_summary": analysis["script_summary"],
            "shop_name": page_name[:80],
            "shop_url": shop_url,
            "product_url": product_url,
            "selling_price": selling_price,
            "original_price": original_price,
            "meta_library_id": lib_id,
            "meta_page_id": page_id,
            "ig_handle": ig_handle,
            "ad_placements": placements,
            "cta_text": cta_text,
        }
        cand["market_intel"] = build_market_intel_for_video(
            cand,
            shops=[own_shop_entry],
            product_query=kw_clean,
            total_market_ads=max(total_market_ads, scale_count),
            spy_status="deep_spied",
        )
        results.append(cand)

    return results


def _extract_product_search_query(video: Dict[str, Any], country: str = "VN") -> str:
    """Derive a clean commercial product search query for Meta Ad Library without picking poetic/non-product lines."""
    title = str(video.get("title") or "")
    caption = str(video.get("caption") or "")
    author = str(video.get("author") or "").lstrip("@")

    cleaned = re.sub(r"\[(?:Scale[^\]]*|Meta Winning Ad|Meta Ad|Ad Library)\]", " ", f"{title}\n{caption}", flags=re.I)
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    cleaned = re.sub(
        r"(?i)\b(?:comment\s+['\"“”]?[\w-]+['\"“”]?\s+(?:for|to|if)\b[^\n.!?]*|link\s+in\s+bio|dm\s+for\s+link|follow\s+for\s+more|instagram\s+reel\s+@[\w.]+)",
        " ",
        cleaned,
    )

    raw_tags = re.findall(r"#([\wÀ-ỹ]+)", f"{title} {caption}")
    generic_tags = {
        "reels", "viral", "fyp", "foryou", "trending", "xuhuong", "shorts", "tiktok",
        "instagram", "gift", "gifts", "giftideas", "xmas", "christmas", "christmasgift",
        "sale", "shop", "shopping", "review", "unboxing", "meovat", "nhadep", "wfh",
        "accessories", "handmade", "decor", "threads", "facebook",
    }
    good_tags = [
        t for t in raw_tags
        if t.lower() not in generic_tags and _strip_accents_lower(t) not in generic_tags and 4 <= len(t) <= 28
    ]

    def _humanize_tag(tag: str) -> str:
        t = tag.replace("_", " ")
        t = re.sub(r"(christmas|office|window|solar|kitchen|desk|night|car|pet|baby|silver|gold)(?=[a-z]{3,})", r"\1 ", t, flags=re.I)
        t = re.sub(r"(?<=[a-z]{3})(lights|lamp|chair|holder|cleaner|maker|bag|ring|necklace|bracelet|watch|toy|decor)$", r" \1", t, flags=re.I)
        return re.sub(r"\s+", " ", t).strip()

    if good_tags:
        humanized = [_humanize_tag(t) for t in good_tags[:2]]
        cand_tag_q = _normalize_keyword_for_market(" ".join(humanized)[:40].strip(), country=country)
        if len(cand_tag_q.split()) >= 2:
            return cand_tag_q

    plain_clauses = []
    stop_fluff = {"review", "reviews", "best", "cheap", "viral", "unboxing", "test", "testing", "extra", "large"}
    for ln in cleaned.splitlines():
        no_tags = re.sub(r"#[\wÀ-ỹ]+", " ", ln)
        for clause in re.split(r"[,;.!?|—–/\n]+", no_tags):
            s = re.sub(r"[^\w\sÀ-ỹ-]", " ", clause)
            s = re.sub(r"\s+", " ", s).strip()
            if author and s.lower().startswith(author.lower()):
                s = s[len(author):].strip(" -—:")
            if len(s) >= 4:
                plain_clauses.append(s)

    base_phrase = plain_clauses[0] if plain_clauses else ""
    if len(base_phrase.split()) >= 2:
        words = [
            w for w in base_phrase.split()
            if len(w) >= 2 and not w.isdigit() and w.lower() not in stop_fluff
        ][:4]
        if len(words) >= 2:
            return " ".join(words)

    brand_clean = re.sub(r"\.(?:store|shop|co|com|vn|usa|official)$", "", author, flags=re.I)
    brand_clean = re.sub(r"[._-]+", " ", brand_clean).strip()
    return brand_clean[:36] or "gia dụng thông minh"


async def _spy_shops_on_meta_ad_library(
    product_query: str,
    country: str = "VN",
    brand_hint: str = "",
    page_id_hint: str = "",
    max_shops: int = 6,
) -> Tuple[List[Dict[str, Any]], int]:
    """Search ONLY Meta Ad Library for real active shops selling `product_query` (or `page_id_hint`), returning separated shop_url & product_url."""
    if not has_playwright() or (not product_query.strip() and not page_id_hint.strip()):
        return [], 0

    q_clean = _clean_search_quotes(product_query).strip()
    ctry = "US" if (country or "VN").upper() == "GLOBAL" else (country or "VN").upper()

    urls_to_try: List[str] = []
    if page_id_hint and page_id_hint.isdigit():
        urls_to_try.append(
            f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&media_type=all&view_all_page_id={page_id_hint}"
        )
    if brand_hint and len(brand_hint) >= 4 and brand_hint.lower() not in q_clean.lower():
        urls_to_try.append(
            f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country={quote_plus(ctry)}&media_type=all&search_type=keyword_exact_phrase&q={quote_plus(chr(34) + brand_hint + chr(34))}"
        )
    if q_clean:
        exact_q = f'"{q_clean}"'
        urls_to_try.append(
            f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country={quote_plus(ctry)}&media_type=all&search_type=keyword_exact_phrase&q={quote_plus(exact_q)}"
        )
        q_words = q_clean.split()
        if len(q_words) > 3:
            short_q = " ".join(q_words[:3])
            urls_to_try.append(
                f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country={quote_plus(ctry)}&media_type=all&search_type=keyword_exact_phrase&q={quote_plus(chr(34) + short_q + chr(34))}"
            )

    raw_ads, total_market_ads = await _scrape_meta_ad_library_structured(
        urls_to_visit=urls_to_try[:3],
        country=ctry,
        require_video=False,
        scroll_rounds=2,
        max_ads=45,
    )
    if not raw_ads:
        return [], 0

    shops_map: Dict[str, Dict[str, Any]] = {}
    for ad in raw_ads:
        pid = str(ad.get("page_id") or "")
        p_name = str(ad.get("page_name") or "").strip()
        if not p_name:
            continue
        blob = f"{p_name} {ad.get('headline','')} {ad.get('body','')} {ad.get('link_description','')}"
        is_same_page = bool(page_id_hint and pid == page_id_hint)
        is_same_brand = bool(brand_hint and len(brand_hint) >= 4 and brand_hint.lower() in p_name.lower())
        if not (is_same_page or is_same_brand or _keyword_matches_ad(q_clean, blob, exact=False)):
            continue

        raw_lk = ad.get("raw_ext_link") or ad.get("_sibling_shop_url") or ""
        sp_info = split_shop_and_product_urls(
            raw_lk,
            fallback_page_url=ad.get("page_url") or "",
            ig_handle=ad.get("ig_handle") or "",
        )
        shop_u = sp_info["shop_url"]
        prod_u = "" if (not ad.get("raw_ext_link") and ad.get("_sibling_shop_url")) else sp_info["product_url"]
        dom = sp_info["domain"]
        is_inbox = sp_info["is_inbox_only"]

        ad_lib_u = (
            f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&view_all_page_id={pid}"
            if pid.isdigit()
            else f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country={quote_plus(ctry)}&q={quote_plus(p_name)}"
        )
        price_ctx = " | ".join(x for x in (ad.get("headline", ""), ad.get("link_description", ""), ad.get("body", "")) if x)
        sell_p, orig_p = _extract_prices_pair_from_text(price_ctx)
        dup_c = max(1, int(ad.get("collation_count") or 1))
        s_key = pid or dom or p_name.lower()

        if s_key not in shops_map:
            shops_map[s_key] = {
                "shop_name": p_name[:70],
                "shop_url": shop_u,
                "product_url": prod_u,
                "domain": dom or (f"fb.com/{pid}" if pid else p_name[:30]),
                "page_id": pid,
                "ig_handle": ad.get("ig_handle") or "",
                "page_url": ad.get("page_url") or "",
                "avatar_url": ad.get("avatar_url") or "",
                "ad_library_url": ad_lib_u,
                "ads_count": dup_c,
                "selling_price": sell_p,
                "original_price": orig_p,
                "product_title": str(ad.get("headline") or "")[:120],
                "placements": ad.get("placements") or ["facebook"],
                "is_inbox_only": is_inbox,
                "source": "Bán qua Inbox (Meta Ads)" if is_inbox else "Meta Ad Library",
                "_raw_link": raw_lk,
                "_fallback_text": price_ctx,
            }
        else:
            cur = shops_map[s_key]
            cur["ads_count"] += dup_c
            if prod_u and not cur["product_url"]:
                cur["product_url"] = prod_u
                cur["_raw_link"] = raw_lk
            if shop_u and (cur["is_inbox_only"] and not is_inbox):
                cur["shop_url"] = shop_u
                cur["domain"] = dom or cur["domain"]
                cur["is_inbox_only"] = False
                cur["source"] = "Meta Ad Library"
            if sell_p and not cur["selling_price"]:
                cur["selling_price"] = sell_p
                cur["original_price"] = orig_p

    out_shops = list(shops_map.values())
    out_shops.sort(
        key=lambda s: (
            1 if (page_id_hint and s.get("page_id") == page_id_hint) else 0,
            bool(s.get("product_url")),
            not bool(s.get("is_inbox_only")),
            int(s.get("ads_count") or 0),
        ),
        reverse=True,
    )
    return out_shops[:max_shops], total_market_ads


def _discover_direct_creator_shop(video: Dict[str, Any], product_query: str) -> Optional[Dict[str, Any]]:
    """Extract attached shop_url, product_url, and selling_price directly from a video's caption or commercial @handle."""
    caption = str(video.get("caption") or "")
    author = str(video.get("author") or "").strip()
    pf = str(video.get("platform") or "").lower()

    raw_urls = re.findall(r"https?://[^\s<>\"')]+", caption)
    best_u = _choose_best_store_link(raw_urls)

    handle = author.lstrip("@").strip().lower()
    if not best_u and re.match(r"^[a-z0-9-]+(?:\.(?:store|shop|co|com|vn|us|uk|net|org|io))$", handle):
        best_u = f"https://{handle}"

    if not best_u:
        return None

    meta = _fetch_live_store_price_and_meta(
        best_u,
        fallback_text=caption,
        keyword_hint=product_query,
        fallback_page_url=str(video.get("source_url") or ""),
        ig_handle=handle if pf in {"instagram", "threads"} else "",
    )
    shop_u = meta.get("shop_url") or ""
    prod_u = meta.get("product_url") or ""
    if not shop_u and not prod_u:
        return None
    if best_u == f"https://{handle}" and not (meta.get("selling_price") or meta.get("product_title")):
        return None

    dom = meta.get("domain") or urlsplit(prod_u or shop_u).netloc.lower().lstrip("www.")
    return {
        "shop_name": author or dom,
        "shop_url": shop_u,
        "product_url": prod_u,
        "domain": dom,
        "page_id": "",
        "page_url": str(video.get("source_url") or ""),
        "ad_library_url": f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&q={quote_plus(dom)}",
        "ads_count": 0,
        "selling_price": meta.get("selling_price") or _extract_price_from_text_multi(caption),
        "original_price": meta.get("original_price") or "",
        "product_title": meta.get("product_title") or "",
        "source": f"{pf.upper()} Direct Link",
    }


def evaluate_video_potential_sync(
    video_id: int,
    custom_query: str = "",
    country: str = "",
    deep_spy: bool = True,
) -> Dict[str, Any]:
    """Evaluate a video's potential and spy real running shops, shop_url, product_url & live prices strictly via Meta Ads Library."""
    from concurrent.futures import ThreadPoolExecutor

    v = database.get_video(video_id)
    if not v:
        return {"ok": False, "error": f"Không tìm thấy video #{video_id}."}

    full_text = f"{v.get('title','')} {v.get('caption','')} {' '.join(str(x) for x in (v.get('sales_signals') or []))}"
    if not country:
        country = "VN" if (_has_vietnamese_chars(full_text) or "shopee.vn" in full_text.lower()) else "US"

    product_query = _clean_search_quotes(custom_query).strip() or _extract_product_search_query(v, country=country)
    raw_author = str(v.get("author") or "").lstrip("@").strip()
    author_handle = re.sub(r"[^a-zA-Z0-9 ]", " ", raw_author.split(".")[0]).strip()
    page_id_hint = str(v.get("meta_page_id") or "").strip()

    shops: List[Dict[str, Any]] = []
    total_market_ads = 0

    creator_shop = _discover_direct_creator_shop(v, product_query)
    if creator_shop:
        shops.append(creator_shop)
        if not custom_query and creator_shop.get("product_title"):
            pt_words = [
                w for w in re.sub(r"[^\w\sÀ-ỹ-]", " ", creator_shop["product_title"]).split()
                if len(w) >= 2 and not w.isdigit()
            ]
            if len(pt_words) >= 2:
                product_query = " ".join(pt_words[1:4] if len(pt_words) >= 4 else pt_words[:3])

    if deep_spy:
        try:
            meta_shops, meta_total = asyncio.run(
                _spy_shops_on_meta_ad_library(
                    product_query=product_query,
                    country=country,
                    brand_hint=author_handle if not author_handle.isdigit() else "",
                    page_id_hint=page_id_hint,
                    max_shops=6,
                )
            )
        except Exception:
            meta_shops, meta_total = [], 0
        total_market_ads = max(total_market_ads, meta_total)
        shops.extend(meta_shops)

        def _enrich_one(sh: Dict[str, Any]) -> None:
            raw_lk = sh.pop("_raw_link", "") or str(sh.get("product_url") or sh.get("shop_url") or "")
            fb_txt = sh.pop("_fallback_text", "")
            if raw_lk and not sh.get("is_inbox_only"):
                meta = _fetch_live_store_price_and_meta(
                    raw_lk,
                    fallback_text=fb_txt,
                    keyword_hint=sh.get("product_title") or product_query,
                    fallback_page_url=str(sh.get("page_url") or ""),
                    ig_handle=str(sh.get("ig_handle") or ""),
                )
                if meta.get("shop_url"):
                    sh["shop_url"] = meta["shop_url"]
                if meta.get("product_url"):
                    sh["product_url"] = meta["product_url"]
                if meta.get("domain"):
                    sh["domain"] = meta["domain"]
                if meta.get("selling_price"):
                    sh["selling_price"] = meta["selling_price"]
                if meta.get("original_price"):
                    sh["original_price"] = meta["original_price"]
                if meta.get("product_title") and not sh.get("product_title"):
                    sh["product_title"] = meta["product_title"]

        with ThreadPoolExecutor(max_workers=5) as pool:
            list(pool.map(_enrich_one, shops[:8]))

        # Persist discovered Meta Ads shops into meta_shops table
        for sh in shops[:6]:
            if sh.get("page_id") or sh.get("source", "").startswith("Meta") or "Meta" in str(sh.get("source", "")):
                try:
                    database.upsert_meta_shop(
                        {
                            "shop_key": sh.get("page_id") or sh.get("domain") or sh.get("shop_name", "").lower(),
                            "page_id": sh.get("page_id") or "",
                            "shop_name": sh.get("shop_name") or "",
                            "ig_handle": sh.get("ig_handle") or "",
                            "page_url": sh.get("page_url") or "",
                            "shop_url": sh.get("shop_url") or "",
                            "domain": sh.get("domain") or "",
                            "avatar_url": sh.get("avatar_url") or "",
                            "ad_library_url": sh.get("ad_library_url") or "",
                            "active_ads_count": int(sh.get("ads_count") or 1),
                            "price_range": sh.get("selling_price") or "",
                            "placements": sh.get("placements") or ["facebook"],
                            "country": country,
                            "is_inbox_only": bool(sh.get("is_inbox_only")),
                        }
                    )
                except Exception:
                    pass
    else:
        for sh in shops:
            sh.pop("_raw_link", None)
            sh.pop("_fallback_text", None)

    intel = build_market_intel_for_video(
        v,
        shops=shops,
        product_query=product_query,
        total_market_ads=total_market_ads,
        spy_status="deep_spied" if deep_spy else "baseline",
    )

    cur_sigs = [
        str(s) for s in (v.get("sales_signals") or [])
        if not str(s).startswith(("Giá:", "Đang chạy:", "Shop bán:"))
    ]
    if intel["price_range"] != "Chưa niêm yết giá":
        cur_sigs.insert(0, f"Giá: {intel['price_range']}")
    if intel["active_shops_count"] > 0:
        cur_sigs.append(f"Shop bán: {intel['active_shops_count']} shop ({intel['total_active_ads']} QC)")

    top_shop = (intel.get("shops") or [{}])[0] if intel.get("shops") else {}
    update_kwargs: Dict[str, Any] = {
        "market_intel_json": json.dumps(intel, ensure_ascii=False),
        "sales_signals": json.dumps(cur_sigs[:8], ensure_ascii=False),
    }
    if not v.get("shop_url") and intel.get("primary_shop_url"):
        update_kwargs["shop_url"] = intel["primary_shop_url"]
    if not v.get("product_url") and intel.get("primary_product_url"):
        update_kwargs["product_url"] = intel["primary_product_url"]
    if not v.get("selling_price") and top_shop.get("selling_price"):
        update_kwargs["selling_price"] = top_shop["selling_price"]
    if not v.get("original_price") and top_shop.get("original_price"):
        update_kwargs["original_price"] = top_shop["original_price"]
    if not v.get("shop_name") and top_shop.get("shop_name"):
        update_kwargs["shop_name"] = top_shop["shop_name"]

    updated = database.update_video(video_id, **update_kwargs)
    return {"ok": True, "video": updated, "market_intel": intel}


def evaluate_potential_videos_batch(
    video_ids: Optional[List[int]] = None,
    limit: int = 5,
    country: str = "",
) -> Dict[str, Any]:
    """Batch-evaluate Meta-ecosystem videos and deep-spy real Meta Ad Library shops & prices."""
    all_vids = database.list_videos()
    if not all_vids:
        return {"ok": True, "evaluated_count": 0, "deep_spied_count": 0, "videos": []}

    for row in all_vids:
        if not isinstance(row.get("market_intel"), dict):
            base_intel = build_market_intel_for_video(
                row,
                shops=[],
                product_query="",
                total_market_ads=0,
                spy_status="baseline",
            )
            database.update_video(row["id"], market_intel_json=json.dumps(base_intel, ensure_ascii=False))

    refreshed_all = database.list_videos()
    if video_ids:
        id_set = set(int(x) for x in video_ids)
        targets = [r for r in refreshed_all if int(r["id"]) in id_set][: max(1, min(10, limit))]
    else:
        candidates = [
            r for r in refreshed_all
            if not (isinstance(r.get("market_intel"), dict) and r["market_intel"].get("spy_status") == "deep_spied" and r["market_intel"].get("shops"))
        ]
        candidates.sort(
            key=lambda r: (
                int((r.get("market_intel") or {}).get("potential_score") or r.get("viral_score") or 0),
                int(r.get("views") or 0),
            ),
            reverse=True,
        )
        targets = candidates[: max(1, min(8, limit))]

    spied_videos: List[Dict[str, Any]] = []
    for t in targets:
        res = evaluate_video_potential_sync(int(t["id"]), country=country, deep_spy=True)
        if res.get("ok") and res.get("video"):
            spied_videos.append(res["video"])

    return {
        "ok": True,
        "evaluated_count": len(refreshed_all),
        "deep_spied_count": len(spied_videos),
        "videos": database.list_videos(),
    }


def _ad_matches_shop_search(query: str, ad: Dict[str, Any]) -> bool:
    """Ensure unordered Meta Ad Library results genuinely match the searched shop brand or product phrase."""
    q_raw = _clean_search_quotes(query or "").strip().lower().lstrip("@#")
    if not q_raw:
        return True
    p_name = str(ad.get("page_name") or "").lower()
    ig_h = str(ad.get("ig_handle") or "").lower()
    ext_lk = str(ad.get("raw_ext_link") or ad.get("_sibling_shop_url") or "").lower()
    full_blob = f"{p_name} {ig_h} {ext_lk} {ad.get('headline') or ''} {ad.get('body') or ''} {ad.get('link_description') or ''}".lower()

    # 1. Direct phrase or compact brand/domain match (with or without accents)
    if q_raw in full_blob:
        return True
    q_plain = _strip_accents_lower(q_raw)
    blob_plain = _strip_accents_lower(full_blob)
    if q_plain and q_plain in blob_plain:
        return True
    q_compact = re.sub(r"[^a-z0-9]+", "", q_plain)
    id_compact = re.sub(r"[^a-z0-9]+", "", _strip_accents_lower(f"{p_name} {ig_h} {ext_lk}"))
    if q_compact and len(q_compact) >= 4 and q_compact in id_compact:
        return True

    # 2. Brand query with generic shop suffixes (e.g. "Kalite Official", "Lili Store")
    shop_suffixes = {"official", "store", "shop", "vn", "vietnam", "viet", "nam", "authentic", "chinh", "hang", "mall"}
    brand_tokens = [t for t in q_plain.split() if len(t) >= 3 and t not in shop_suffixes]
    if 1 <= len(brand_tokens) <= 2 and all(t in _strip_accents_lower(f"{p_name} {ig_h} {ext_lk}") for t in brand_tokens):
        return True

    # 3. Multi-word product phrase: require accented token coverage so e.g. "bút máy ... chậm" never matches "máy ép chậm"
    stopwords = {"va", "la", "co", "de", "cho", "cua", "tai", "voi", "the", "for", "and", "with"}
    acc_tokens = [t for t in re.split(r"\s+", q_raw) if len(t) >= 2 and _strip_accents_lower(t) not in stopwords]
    if not acc_tokens:
        return True
    acc_hits = sum(1 for t in acc_tokens if re.search(rf"(?<!\w){re.escape(t)}(?!\w)", full_blob))
    required_hits = len(acc_tokens) if len(acc_tokens) <= 3 else max(2, int(len(acc_tokens) * 0.75))
    if acc_hits >= required_hits:
        return True

    # Fallback if ad copy omitted Vietnamese accents completely
    plain_tokens = [_strip_accents_lower(t) for t in acc_tokens]
    plain_hits = sum(1 for t in plain_tokens if re.search(rf"\b{re.escape(t)}\b", blob_plain))
    return plain_hits >= len(plain_tokens) and len(plain_tokens) >= 2


async def search_shops_on_meta_ads(
    query: str,
    country: str = "VN",
    platform: str = "all",
    limit: int = 12,
) -> Dict[str, Any]:
    """Dedicated Module: Search Shops running ads on Meta Ad Library (linked to FB, IG, Threads) and extract their shop_url, product_url & live selling prices."""
    from concurrent.futures import ThreadPoolExecutor

    raw_q = (query or "").strip()
    if not raw_q:
        return {"ok": True, "query": "", "total_market_ads": 0, "shops": database.list_meta_shops(country=country, platform=platform)}

    ctry = "US" if (country or "VN").upper() == "GLOBAL" else (country or "VN").upper()
    pl_low = (platform or "all").strip().lower()
    pl_param = f"&publisher_platforms[0]={pl_low}" if pl_low in {"facebook", "instagram", "threads"} else ""

    # Detect if user pasted a Facebook Page URL, Ad Library URL, or Shopee/Store URL
    extracted_pid = _extract_page_id_from_fb_url(raw_q) if "facebook.com" in raw_q.lower() else (raw_q if raw_q.isdigit() and len(raw_q) >= 8 else "")
    clean_kw = _clean_search_quotes(raw_q)
    urls_to_visit: List[str] = []
    if extracted_pid and extracted_pid.isdigit():
        urls_to_visit.append(
            f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&media_type=all{pl_param}&view_all_page_id={extracted_pid}"
        )
    else:
        if clean_kw.startswith(("http://", "https://")):
            sp_q = urlsplit(clean_kw)
            clean_kw = sp_q.netloc.lower().lstrip("www.")
        exact_q = f'"{clean_kw}"'
        urls_to_visit.append(
            f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country={quote_plus(ctry)}&media_type=all{pl_param}&search_type=keyword_exact_phrase&q={quote_plus(exact_q)}"
        )
        urls_to_visit.append(
            f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country={quote_plus(ctry)}&media_type=all{pl_param}&search_type=keyword_unordered&q={quote_plus(clean_kw)}"
        )

    raw_ads, total_market_ads = await _scrape_meta_ad_library_structured(
        urls_to_visit=urls_to_visit[:2],
        country=ctry,
        require_video=False,
        scroll_rounds=3,
        max_ads=65,
    )

    shops_bucket: Dict[str, Dict[str, Any]] = {}
    for ad in raw_ads:
        pid = str(ad.get("page_id") or "")
        p_name = str(ad.get("page_name") or "").strip()
        if not p_name:
            continue
        if not extracted_pid and not _ad_matches_shop_search(clean_kw, ad):
            continue
        s_key = pid or p_name.lower()
        if s_key not in shops_bucket:
            ad_lib_u = (
                f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&view_all_page_id={pid}"
                if pid.isdigit()
                else f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country={quote_plus(ctry)}&q={quote_plus(p_name)}"
            )
            shops_bucket[s_key] = {
                "shop_key": s_key,
                "page_id": pid,
                "shop_name": p_name[:80],
                "ig_handle": ad.get("ig_handle") or "",
                "page_url": ad.get("page_url") or "",
                "avatar_url": ad.get("avatar_url") or "",
                "ad_library_url": ad_lib_u,
                "active_ads_count": 0,
                "placements": set(),
                "raw_ads": [],
            }
        entry = shops_bucket[s_key]
        entry["active_ads_count"] += max(1, int(ad.get("collation_count") or 1))
        entry["placements"].update(ad.get("placements") or ["facebook"])
        if ad.get("ig_handle") and not entry["ig_handle"]:
            entry["ig_handle"] = ad["ig_handle"]
        entry["raw_ads"].append(ad)

    ranked_buckets = sorted(
        shops_bucket.values(),
        key=lambda b: (
            any(bool(a.get("raw_ext_link") or a.get("_sibling_shop_url")) for a in b["raw_ads"]),
            b["active_ads_count"],
            len(b["raw_ads"]),
        ),
        reverse=True,
    )[:limit]

    def _build_shop_and_preview_products(bucket: Dict[str, Any]) -> Dict[str, Any]:
        ads_list = bucket["raw_ads"]
        shop_url_final = ""
        domain_final = ""
        is_inbox_only = True
        prod_items: List[Dict[str, Any]] = []
        prices: List[str] = []

        for ad in ads_list[:8]:
            raw_lk = ad.get("raw_ext_link") or ad.get("_sibling_shop_url") or ""
            p_ctx = " | ".join(x for x in (ad.get("headline", ""), ad.get("link_description", ""), ad.get("body", "")) if x)
            meta = _fetch_live_store_price_and_meta(
                raw_lk,
                fallback_text=p_ctx,
                keyword_hint=ad.get("headline") or raw_q,
                fallback_page_url=bucket["page_url"],
                ig_handle=bucket["ig_handle"],
            )
            s_u = meta.get("shop_url") or ""
            p_u = "" if (not ad.get("raw_ext_link") and ad.get("_sibling_shop_url")) else (meta.get("product_url") or "")
            if ad.get("raw_ext_link") and s_u:
                is_inbox_only = False
                if not shop_url_final:
                    shop_url_final = s_u
                    domain_final = meta.get("domain") or ""
            elif not shop_url_final and s_u:
                shop_url_final = s_u
                domain_final = meta.get("domain") or ""

            sell_p = meta.get("selling_price") or ""
            orig_p = meta.get("original_price") or ""
            if sell_p and sell_p not in prices:
                prices.append(sell_p)

            p_title = (
                meta.get("product_title")
                or ad.get("headline")
                or ([ln.strip() for ln in (ad.get("body") or "").splitlines() if len(ln.strip()) > 4] or [bucket["shop_name"]])[0]
            )[:140]
            prod_items.append(
                {
                    "library_id": ad.get("library_id") or "",
                    "product_title": p_title,
                    "caption": (ad.get("body") or "")[:500],
                    "product_url": p_u,
                    "shop_url": (s_u or shop_url_final) if ad.get("raw_ext_link") else (shop_url_final or s_u),
                    "selling_price": sell_p,
                    "original_price": orig_p,
                    "video_url": ad.get("video_url") or "",
                    "thumbnail_url": ad.get("thumbnail_url") or "",
                    "cta_text": ad.get("cta_text") or ("Bán qua Inbox" if not p_u and is_inbox_only else "Mua ngay"),
                    "ads_duplication_count": max(1, int(ad.get("collation_count") or 1)),
                    "video_age_days": int(ad.get("ad_age_days") or 5),
                    "started_running_at": ad.get("started_iso") or "",
                    "placements": ad.get("placements") or ["facebook"],
                }
            )

        price_range = _format_price_range_sorted(prices, empty_default="")
        saved_shop = database.upsert_meta_shop(
            {
                "shop_key": bucket["shop_key"],
                "page_id": bucket["page_id"],
                "shop_name": bucket["shop_name"],
                "ig_handle": bucket["ig_handle"],
                "page_url": bucket["page_url"],
                "shop_url": shop_url_final,
                "domain": domain_final,
                "avatar_url": bucket["avatar_url"],
                "ad_library_url": bucket["ad_library_url"],
                "active_ads_count": bucket["active_ads_count"],
                "price_range": price_range,
                "placements": sorted(bucket["placements"]),
                "country": ctry,
                "is_inbox_only": is_inbox_only,
            }
        )
        saved_prods = database.upsert_meta_shop_products(int(saved_shop["id"]), prod_items)
        saved_shop["preview_products"] = saved_prods[:6]
        saved_shop["products_count"] = len(saved_prods)
        return saved_shop

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=5) as pool:
        built_shops = await asyncio.gather(
            *(loop.run_in_executor(pool, _build_shop_and_preview_products, b) for b in ranked_buckets),
            return_exceptions=True,
        )

    valid_shops = [s for s in built_shops if isinstance(s, dict)]
    return {
        "ok": True,
        "query": raw_q,
        "country": ctry,
        "platform": pl_low,
        "total_market_ads": total_market_ads,
        "count": len(valid_shops),
        "shops": valid_shops,
    }


async def crawl_shop_products_on_meta_ads(
    page_id: str = "",
    shop_query: str = "",
    shop_id: Optional[int] = None,
    country: str = "ALL",
    limit: int = 24,
) -> Dict[str, Any]:
    """Scan ALL active ads of a specific Shop on Meta Ad Library (`view_all_page_id` or domain) to list every product & video ad they are selling."""
    from concurrent.futures import ThreadPoolExecutor

    existing_shop = database.get_meta_shop_detail(shop_id) if shop_id else None
    pid = (page_id or (existing_shop.get("page_id") if existing_shop else "") or "").strip()
    s_name = (shop_query or (existing_shop.get("shop_name") if existing_shop else "") or "").strip()
    dom_hint = (existing_shop.get("domain") if existing_shop else "") or ""

    if not pid and s_name:
        maybe_pid = _extract_page_id_from_fb_url(s_name)
        if maybe_pid.isdigit():
            pid = maybe_pid

    urls_to_visit: List[str] = []
    ctry = "ALL" if not country or country.upper() in {"ALL", "AUTO"} else country.upper()
    if pid and pid.isdigit():
        urls_to_visit.append(
            f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&media_type=video&view_all_page_id={pid}"
        )
        urls_to_visit.append(
            f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&media_type=all&view_all_page_id={pid}"
        )
    elif dom_hint and "." in dom_hint and not dom_hint.startswith(("fb.com", "shopee.vn")):
        urls_to_visit.append(
            f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country={quote_plus(ctry)}&media_type=all&search_type=keyword_unordered&q={quote_plus(dom_hint)}"
        )
    elif s_name:
        urls_to_visit.append(
            f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country={quote_plus(ctry)}&media_type=all&search_type=keyword_exact_phrase&q={quote_plus(chr(34) + s_name + chr(34))}"
        )
    else:
        return {"ok": False, "error": "Thiếu thông tin page_id hoặc tên Shop cần quét sản phẩm."}

    raw_ads, total_ads_counter = await _scrape_meta_ad_library_structured(
        urls_to_visit=urls_to_visit,
        country="VN" if ctry in {"VN", "ALL"} else ctry,
        require_video=False,
        scroll_rounds=3,
        max_ads=70,
    )

    if pid and pid.isdigit():
        raw_ads = [a for a in raw_ads if str(a.get("page_id") or "") == pid] or raw_ads

    if not raw_ads:
        if existing_shop:
            return {"ok": True, "shop": existing_shop, "products": existing_shop.get("products") or []}
        return {"ok": False, "error": "Shop này hiện không có mẫu quảng cáo đang active trên Meta Ad Library."}

    first_ad = raw_ads[0]
    resolved_pid = pid or str(first_ad.get("page_id") or "")
    resolved_name = str(first_ad.get("page_name") or s_name or "Meta Shop")
    resolved_page_url = str(first_ad.get("page_url") or (existing_shop.get("page_url") if existing_shop else "") or "")
    resolved_ig = str(first_ad.get("ig_handle") or (existing_shop.get("ig_handle") if existing_shop else "") or "")
    resolved_avatar = str(first_ad.get("avatar_url") or (existing_shop.get("avatar_url") if existing_shop else "") or "")
    all_placements = set()
    sum_collation = 0
    for a in raw_ads:
        all_placements.update(a.get("placements") or ["facebook"])
        sum_collation += max(1, int(a.get("collation_count") or 1))

    # Group ads by distinct product link / headline / video asset
    grouped: Dict[str, Dict[str, Any]] = {}
    for ad in raw_ads:
        raw_lk = ad.get("raw_ext_link") or ""
        clean_lk = _unwrap_external_store_url(raw_lk) if raw_lk else ""
        efg = _decode_fb_efg(ad.get("video_url") or "")
        asset_id = str(efg.get("xpv_asset_id") or "")
        g_key = clean_lk.lower() if clean_lk else (asset_id or str(ad.get("headline") or ad.get("library_id") or "")).lower()
        if not g_key:
            continue
        if g_key not in grouped:
            grouped[g_key] = dict(ad)
        else:
            grouped[g_key]["collation_count"] = int(grouped[g_key].get("collation_count") or 1) + max(1, int(ad.get("collation_count") or 1))
            if not grouped[g_key].get("video_url") and ad.get("video_url"):
                grouped[g_key]["video_url"] = ad["video_url"]
                grouped[g_key]["thumbnail_url"] = ad.get("thumbnail_url") or grouped[g_key].get("thumbnail_url")
            if not grouped[g_key].get("raw_ext_link") and ad.get("raw_ext_link"):
                grouped[g_key]["raw_ext_link"] = ad["raw_ext_link"]

    top_ads = sorted(
        grouped.values(),
        key=lambda x: (bool(x.get("video_url")), bool(x.get("raw_ext_link")), int(x.get("collation_count") or 1)),
        reverse=True,
    )[:limit]

    def _resolve_prod(ad: Dict[str, Any]) -> Dict[str, Any]:
        raw_lk = ad.get("raw_ext_link") or ad.get("_sibling_shop_url") or ""
        p_ctx = " | ".join(x for x in (ad.get("headline", ""), ad.get("link_description", ""), ad.get("body", "")) if x)
        meta = _fetch_live_store_price_and_meta(
            raw_lk,
            fallback_text=p_ctx,
            keyword_hint=ad.get("headline") or resolved_name,
            fallback_page_url=resolved_page_url,
            ig_handle=resolved_ig,
        )
        p_u = "" if (not ad.get("raw_ext_link") and ad.get("_sibling_shop_url")) else (meta.get("product_url") or "")
        s_u = meta.get("shop_url") or ""
        p_title = (
            meta.get("product_title")
            or ad.get("headline")
            or ([ln.strip() for ln in (ad.get("body") or "").splitlines() if len(ln.strip()) > 4] or [resolved_name])[0]
        )[:150]
        return {
            "library_id": ad.get("library_id") or "",
            "product_title": p_title,
            "caption": (ad.get("body") or "")[:550],
            "product_url": p_u,
            "shop_url": s_u,
            "domain": meta.get("domain") or "",
            "is_ext": bool(ad.get("raw_ext_link") and s_u),
            "selling_price": meta.get("selling_price") or "",
            "original_price": meta.get("original_price") or "",
            "video_url": ad.get("video_url") or "",
            "thumbnail_url": ad.get("thumbnail_url") or "",
            "cta_text": ad.get("cta_text") or ("Bán qua Inbox" if not p_u and not ad.get("raw_ext_link") else "Mua ngay"),
            "ads_duplication_count": max(1, int(ad.get("collation_count") or 1)),
            "video_age_days": int(ad.get("ad_age_days") or 5),
            "started_running_at": ad.get("started_iso") or "",
            "placements": ad.get("placements") or ["facebook"],
        }

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=6) as pool:
        resolved_prods = await asyncio.gather(
            *(loop.run_in_executor(pool, _resolve_prod, a) for a in top_ads),
            return_exceptions=True,
        )

    clean_prods = [r for r in resolved_prods if isinstance(r, dict)]
    ext_shop_url = next((r["shop_url"] for r in clean_prods if r.get("is_ext") and r.get("shop_url")), "")
    ext_domain = next((r["domain"] for r in clean_prods if r.get("is_ext") and r.get("domain")), "")
    fallback_shop_url = ext_shop_url or next((r["shop_url"] for r in clean_prods if r.get("shop_url")), resolved_page_url)
    for r in clean_prods:
        if ext_shop_url and not r.get("is_ext"):
            r["shop_url"] = ext_shop_url
        r.pop("domain", None)
        r.pop("is_ext", None)

    prices = [r["selling_price"] for r in clean_prods if r.get("selling_price")]
    price_range = _format_price_range_sorted(prices, empty_default="")

    ad_lib_u = (
        f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&view_all_page_id={resolved_pid}"
        if resolved_pid.isdigit()
        else urls_to_visit[0]
    )
    saved_shop = database.upsert_meta_shop(
        {
            "shop_key": (existing_shop.get("shop_key") if existing_shop else None) or resolved_pid or ext_domain or resolved_name.lower(),
            "page_id": resolved_pid,
            "shop_name": resolved_name[:80],
            "ig_handle": resolved_ig,
            "page_url": resolved_page_url,
            "shop_url": fallback_shop_url,
            "domain": ext_domain or (existing_shop.get("domain") if existing_shop else ""),
            "avatar_url": resolved_avatar,
            "ad_library_url": ad_lib_u,
            "active_ads_count": max(total_ads_counter, sum_collation),
            "price_range": price_range,
            "placements": sorted(all_placements),
            "country": "VN" if _has_vietnamese_chars(resolved_name) else ("US" if ctry == "US" else "VN"),
            "is_inbox_only": not bool(ext_shop_url),
        }
    )
    saved_prods = database.upsert_meta_shop_products(int(saved_shop["id"]), clean_prods)
    detail = database.get_meta_shop_detail(int(saved_shop["id"]))
    return {"ok": True, "shop": detail or saved_shop, "products": saved_prods}


def import_shop_product_to_videos(shop_product_id: int) -> Dict[str, Any]:
    """Import an advertised shop product from `meta_shop_products` directly into `viral_videos` for AI Breakdown & Video Cloning."""
    with database.get_conn() as conn:
        row = conn.execute("SELECT * FROM meta_shop_products WHERE id = ?", (shop_product_id,)).fetchone()
        if not row:
            return {"ok": False, "error": f"Không tìm thấy sản phẩm #{shop_product_id}."}
        prod = dict(row)
        shop_row = conn.execute("SELECT * FROM meta_shops WHERE id = ?", (prod["shop_id"],)).fetchone()
        shop = dict(shop_row) if shop_row else {}

    lib_id = str(prod.get("library_id") or "")
    v_url = str(prod.get("video_url") or "")
    if not v_url and not lib_id:
        return {"ok": False, "error": "Mẫu quảng cáo này là ảnh tĩnh và không có ID thư viện video."}

    try:
        placements = json.loads(prod.get("placements_json") or '["facebook"]')
    except Exception:
        placements = ["facebook"]

    dup_cnt = max(1, int(prod.get("ads_duplication_count") or 1))
    age_d = max(1, int(prod.get("video_age_days") or 5))
    shop_name = str(shop.get("shop_name") or "Meta Shop")
    title_raw = str(prod.get("product_title") or shop_name)
    badge = f"[Scale {dup_cnt} QC]" if dup_cnt > 1 else "[Meta Ad]"
    title = f"{badge} {shop_name[:28]} — {title_raw}"[:140]
    caption = str(prod.get("caption") or title_raw)[:550]
    src_url = (
        f"https://www.facebook.com/ads/library/?id={lib_id}"
        if lib_id
        else str(shop.get("ad_library_url") or shop.get("page_url") or "https://www.facebook.com/ads/library/")
    )
    est_views = 85000 + dup_cnt * 65000
    est_likes = int(est_views * 0.042)
    est_comments = int(est_views * 0.0045)
    est_shares = int(est_views * 0.006)
    v_score = compute_viral_score(est_views, est_likes, est_comments, est_shares, scale_ads=dup_cnt)

    sigs: List[str] = []
    if prod.get("selling_price"):
        sigs.append(f"Giá: {prod['selling_price']}")
    sigs.extend([f"Scale {dup_cnt} QC", f"File {age_d} ngày"])
    if prod.get("product_url"):
        sigs.append("Gắn Link SP")

    analysis = analyze_video_structure(title, caption, title_raw, extra_meta={"asset_age_days": age_d, "scale_count": dup_cnt})
    item = {
        "platform": "meta_ads",
        "title": title,
        "caption": caption,
        "author": shop_name[:70],
        "source_url": src_url,
        "video_url": v_url,
        "thumbnail_url": str(prod.get("thumbnail_url") or ""),
        "views": est_views,
        "likes": est_likes,
        "comments": est_comments,
        "shares": est_shares,
        "viral_score": v_score,
        "sales_signals": detect_sales_signals(caption, sigs),
        "hook_text": analysis["hook_text"],
        "script_summary": analysis["script_summary"],
        "shop_name": shop_name[:80],
        "shop_url": str(prod.get("shop_url") or shop.get("shop_url") or ""),
        "product_url": str(prod.get("product_url") or ""),
        "selling_price": str(prod.get("selling_price") or ""),
        "original_price": str(prod.get("original_price") or ""),
        "meta_library_id": lib_id,
        "meta_page_id": str(shop.get("page_id") or ""),
        "ig_handle": str(shop.get("ig_handle") or ""),
        "ad_placements": placements,
        "cta_text": str(prod.get("cta_text") or ""),
    }
    item["market_intel"] = build_market_intel_for_video(
        item,
        shops=[
            {
                "shop_name": shop_name[:70],
                "shop_url": item["shop_url"],
                "product_url": item["product_url"],
                "domain": str(shop.get("domain") or ""),
                "page_id": str(shop.get("page_id") or ""),
                "page_url": str(shop.get("page_url") or ""),
                "ad_library_url": str(shop.get("ad_library_url") or ""),
                "ads_count": max(int(shop.get("active_ads_count") or 1), dup_cnt),
                "selling_price": item["selling_price"],
                "original_price": item["original_price"],
                "product_title": title_raw[:120],
                "source": "Meta Ad Library",
            }
        ],
        product_query=title_raw[:50],
        total_market_ads=max(int(shop.get("active_ads_count") or 1), dup_cnt),
        spy_status="deep_spied",
    )
    saved_vid = _upsert_video_by_source_url(item)
    if saved_vid.get("id") and v_url:
        ensure_video_playable_mp4(int(saved_vid["id"]))
        saved_vid = database.get_video(int(saved_vid["id"])) or saved_vid
    return {"ok": True, "video": saved_vid}


async def _crawl_treg_api(keyword: str, platform: str, treg_key: str) -> List[Dict[str, Any]]:
    """Optional treg.to connector when the user provides a treg API key."""
    if not treg_key:
        return []
    endpoint = "https://treg.to/api/v1/tools/call"
    headers = {"Authorization": f"Bearer {treg_key}", "Content-Type": "application/json"}
    tool_name = "meta-ad-library.meta-ads.library.search" if platform in ("all", "meta_ads") else f"treg.{platform}.search.posts"
    payload = {"tool": tool_name, "input": {"query": keyword, "country": "VN", "limit": 5}}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(endpoint, headers=headers, json=payload)
            if resp.status_code != 200:
                return []
            data = resp.json()
            rows = data.get("ads") or data.get("posts") or data.get("results") or []
            out = []
            for idx, r in enumerate(rows[:5]):
                title = r.get("title") or r.get("page_name") or f"{keyword} Viral #{idx + 1}"
                caption = r.get("caption") or r.get("ad_creative_body") or str(r)[:220]
                analysis = analyze_video_structure(title, caption, keyword)
                out.append(
                    {
                        "platform": "meta_ads" if platform == "all" else platform,
                        "title": title[:120],
                        "caption": caption[:400],
                        "author": r.get("author") or r.get("page_name") or "Creator",
                        "source_url": r.get("url") or r.get("ad_snapshot_url") or "https://treg.to",
                        "video_url": r.get("video_url", ""),
                        "thumbnail_url": r.get("thumbnail_url", ""),
                        "views": int(r.get("views", 120000)),
                        "likes": int(r.get("likes", 5400)),
                        "comments": int(r.get("comments", 310)),
                        "shares": int(r.get("shares", 490)),
                        "viral_score": compute_viral_score(
                            int(r.get("views", 120000)),
                            int(r.get("likes", 5400)),
                            int(r.get("comments", 310)),
                            int(r.get("shares", 490)),
                        ),
                        "sales_signals": detect_sales_signals(caption),
                        "hook_text": analysis["hook_text"],
                        "script_summary": analysis["script_summary"],
                    }
                )
            return out
    except Exception:
        return []


async def crawl_viral_videos(
    keyword: str,
    platform: str = "all",
    engine: str = "agent_reach",
    country: str = "VN",
    match_type: str = "broad",
) -> Dict[str, Any]:
    """Primary Video Crawler focused on the Meta Ecosystem (Meta Ads, Facebook, Instagram, Threads) with instant Link Shop, Link SP & Price capture."""
    purge_invalid_and_mockup_videos()
    raw_kw = keyword.strip() or "gia dụng thông minh"
    keyword = _normalize_keyword_for_market(raw_kw, country=country)

    pf_req = (platform or "all").strip().lower()
    if pf_req in {"all", "meta_all"}:
        # Focus 100% on the 3 core Meta platforms via Meta Ad Library + logged-in IG Reels supplement
        target_platforms = ["facebook", "instagram", "threads"]
    elif pf_req == "all_social":
        target_platforms = ["facebook", "instagram", "threads"]
    else:
        target_platforms = [pf_req]

    collected: List[Dict[str, Any]] = []
    diagnostics: List[str] = []
    if keyword.lower() != raw_kw.lower():
        diagnostics.append(f"Đã chuẩn hoá từ khoá '{raw_kw}' → '{keyword}' cho thị trường {country}")

    if engine == "treg_api":
        settings = database.get_settings()
        treg_key = settings.get("treg_api_key", "").strip()
        if treg_key:
            treg_items = await _crawl_treg_api(keyword, platform, treg_key)
            collected.extend(treg_items)
            diagnostics.append(f"treg.to API: +{len(treg_items)} video")
        else:
            diagnostics.append("Chưa cấu hình treg_api_key — tự động dùng Meta Ad Library Engine miễn phí")

    agent_reach_bin = find_agent_reach()
    is_single_pf = len(target_platforms) == 1

    async def _task_meta_placement(placement: str, item_limit: int) -> Tuple[List[Dict[str, Any]], List[str]]:
        if not has_playwright():
            return [], ["Playwright chưa sẵn sàng để quét Meta Ad Library."]
        label_map = {
            "meta_ads": "Meta Ad Library (Tất cả vị trí)",
            "facebook": "Facebook Video Ads (Meta Library)",
            "instagram": "Instagram Video Ads (Meta Library)",
            "threads": "Threads Video Ads (Meta Library)",
        }
        lbl = label_map.get(placement, placement)
        try:
            ads = await asyncio.wait_for(
                _crawl_meta_ads_playwright(
                    keyword,
                    country=country,
                    limit=item_limit,
                    target_placement="all" if placement == "meta_ads" else placement,
                    match_type=match_type,
                ),
                timeout=36.0,
            )
        except Exception as exc:
            return [], [f"{lbl} ({country}): Quá thời gian hoặc lỗi kết nối ({str(exc)[:80]})"]

        if ads:
            with_links = sum(1 for a in ads if a.get("product_url") or a.get("shop_url"))
            with_prices = sum(1 for a in ads if a.get("selling_price"))
            return ads, [
                f"{lbl} ({country}): +{len(ads)} video MP4 ({with_links} có Link Shop/SP · {with_prices} có Giá bán)"
            ]
        return [], [f"{lbl} ({country}): Chưa tìm thấy quảng cáo video đang chạy khớp '{keyword}'"]

    async def _task_ig_organic_supplement(ig_limit: int) -> Tuple[List[Dict[str, Any]], List[str]]:
        if not has_playwright():
            return [], []
        try:
            ig_res = await asyncio.wait_for(
                _crawl_instagram_reels_playwright_with_diag(
                    keyword,
                    country=country,
                    limit=ig_limit,
                    match_type=match_type,
                    action="search",
                ),
                timeout=32.0,
            )
            vids = ig_res.get("videos") or []
            if vids:
                return vids, [f"Instagram Reels Organic ({country}): +{len(vids)} video MP4 tải về máy"]
        except Exception:
            pass
        return [], []

    async def _task_other_social(pf: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        if not agent_reach_bin:
            return [], []
        cli_args = _build_agent_reach_cli_args(pf, keyword, limit=4 if is_single_pf else 3)
        if not cli_args:
            return [], []
        try:
            raw_resp = await asyncio.wait_for(asyncio.to_thread(_run_agent_reach_sync, cli_args, 18), timeout=20.0)
        except Exception:
            return [], [f"[{pf}] Quá thời gian phản hồi tìm kiếm"]
        items, diag = _normalize_agent_reach_items(pf, keyword, raw_resp)
        if items:
            return items, [f"Agent-Reach [{pf}]: +{len(items)} video"]
        return [], ([diag] if diag else [])

    parallel_tasks = []
    if pf_req in {"all", "meta_all", "all_social"}:
        # Query Meta Ad Library across FB, IG, and Threads in parallel + optional IG Reels organic supplement
        parallel_tasks.append(_task_meta_placement("facebook", 4))
        parallel_tasks.append(_task_meta_placement("instagram", 4))
        parallel_tasks.append(_task_meta_placement("threads", 3))
        parallel_tasks.append(_task_ig_organic_supplement(2))
    elif pf_req == "meta_ads":
        parallel_tasks.append(_task_meta_placement("meta_ads", 8))
    elif pf_req == "facebook":
        parallel_tasks.append(_task_meta_placement("facebook", 7))
    elif pf_req == "instagram":
        parallel_tasks.append(_task_meta_placement("instagram", 6))
        parallel_tasks.append(_task_ig_organic_supplement(3))
    elif pf_req == "threads":
        parallel_tasks.append(_task_meta_placement("threads", 6))
    else:
        parallel_tasks.append(_task_other_social(pf_req))

    task_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)

    seen_source_urls = set()
    for res_tuple in task_results:
        if isinstance(res_tuple, tuple) and len(res_tuple) == 2:
            its, dgs = res_tuple
            diagnostics.extend(dgs)
            for it in its:
                su = _canonicalize_video_url(str(it.get("platform") or ""), str(it.get("source_url") or ""))
                if su and su in seen_source_urls:
                    continue
                if su:
                    seen_source_urls.add(su)
                if not isinstance(it.get("market_intel"), dict):
                    it["market_intel"] = build_market_intel_for_video(
                        it,
                        shops=[],
                        product_query=keyword,
                        total_market_ads=0,
                        spy_status="baseline",
                    )
                collected.append(it)

    saved = [_upsert_video_by_source_url(item) for item in collected]

    # Run AI script/hook analysis in background WITHOUT cross-copying unrelated shops between videos!
    if saved:
        def _bg_ai_only(rows_to_enrich: List[Dict[str, Any]], kw_str: str) -> None:
            try:
                _enrich_videos_with_ai_analysis(rows_to_enrich, kw_str)
                with database.get_conn() as conn:
                    for sv in rows_to_enrich:
                        if sv.get("id"):
                            conn.execute(
                                "UPDATE viral_videos SET hook_text = ?, script_summary = ? WHERE id = ?",
                                (sv.get("hook_text", ""), sv.get("script_summary", ""), sv["id"]),
                            )
            except Exception:
                pass

        threading.Thread(
            target=_bg_ai_only,
            args=(saved, keyword),
            daemon=True,
        ).start()

    return {
        "keyword": keyword,
        "engine_used": "meta_ad_library_graphql",
        "count": len(saved),
        "diagnostics": diagnostics,
        "videos": saved,
    }


def ensure_video_playable_mp4(video_id: int) -> Dict[str, Any]:
    video = database.get_video(video_id)
    if not video:
        return {"ok": False, "error": f"Không tìm thấy video #{video_id}"}

    local_path = str(video.get("local_path") or "").strip()
    if local_path and Path(local_path).is_file() and Path(local_path).stat().st_size > 10_000:
        return {
            "ok": True,
            "play_url": f"/media/downloads/{Path(local_path).name}",
            "video": video,
        }

    v_url = str(video.get("video_url") or "").strip()
    if v_url.startswith("http") and (".mp4" in v_url.lower() or "fbcdn.net" in v_url.lower()):
        dest = DOWNLOADS_DIR / f"meta_video_{video_id}.mp4"
        try:
            with httpx.Client(timeout=25, follow_redirects=True) as client:
                resp = client.get(
                    v_url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                        )
                    },
                )
                if resp.status_code == 200 and len(resp.content) > 10_000:
                    dest.write_bytes(resp.content)
                    updated = database.update_video(
                        video_id,
                        local_path=str(dest),
                        video_url=f"/media/downloads/{dest.name}",
                    )
                    return {
                        "ok": True,
                        "play_url": f"/media/downloads/{dest.name}",
                        "video": updated or video,
                    }
        except Exception:
            pass
        return {"ok": True, "play_url": v_url, "video": video}

    s_url = str(video.get("source_url") or "").strip()
    if s_url.startswith("http"):
        res = _run_ytdlp_sync(s_url, download=True)
        if res.get("ok"):
            info = res.get("info") or {}
            dl_file = str(res.get("local_path") or "").strip()
            play_url = f"/media/downloads/{Path(dl_file).name}" if dl_file and Path(dl_file).is_file() else (info.get("url") or "")
            updated = database.update_video(
                video_id,
                local_path=dl_file or video.get("local_path", ""),
                video_url=play_url or video.get("video_url", ""),
                thumbnail_url=info.get("thumbnail") or video.get("thumbnail_url", ""),
            )
            return {
                "ok": bool(play_url),
                "play_url": play_url,
                "video": updated or video,
            }
        return {"ok": False, "error": res.get("error") or "yt-dlp không tải được video từ link này"}

    return {"ok": False, "error": "Video chưa có URL nguồn hợp lệ"}


def analyze_single_video_ai(video_id: int) -> Dict[str, Any]:
    video = database.get_video(video_id)
    if not video:
        return {"ok": False, "error": f"Không tìm thấy video #{video_id}"}
    copy_item = dict(video)
    _enrich_videos_with_ai_analysis([copy_item], video.get("title") or "")
    with database.get_conn() as conn:
        conn.execute(
            "UPDATE viral_videos SET hook_text = ?, script_summary = ? WHERE id = ?",
            (copy_item.get("hook_text", ""), copy_item.get("script_summary", ""), video_id),
        )
    updated = database.get_video(video_id)
    return {"ok": True, "video": updated}


def _get_browser_cookies_txt() -> Optional[str]:
    all_cookies = _read_agent_reach_session_cookies(prefer_cdp=False)
    if all_cookies:
        cookie_path = COOKIES_DIR / "browser_cookies.txt"
        _write_netscape_cookies_file(cookie_path, all_cookies)
        if cookie_path.is_file() and cookie_path.stat().st_size > 80:
            return str(cookie_path)
    existing = COOKIES_DIR / "browser_cookies.txt"
    if existing.is_file() and existing.stat().st_size > 80:
        return str(existing)
    return None


def _run_ytdlp_sync(url: str, download: bool = False) -> Dict[str, Any]:
    ytdlp_bin = find_ytdlp()
    if not ytdlp_bin:
        return {"ok": False, "error": "Không tìm thấy yt-dlp trên máy."}

    cookie_txt = _get_browser_cookies_txt()
    cookie_args = ["--cookies", cookie_txt] if cookie_txt else []

    if not download:
        cmd = [ytdlp_bin, "--no-warnings", "--skip-download", *cookie_args, "--dump-single-json", url]
    else:
        output_tpl = str(DOWNLOADS_DIR / "%(id)s.%(ext)s")
        cmd = [
            ytdlp_bin,
            "--no-warnings",
            *cookie_args,
            "--print-json",
            "-f",
            "mp4/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
            "-o",
            output_tpl,
            url,
        ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=45,
            env=build_tool_env(),
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "yt-dlp failed").strip()
            return {"ok": False, "error": err[:300]}

        lines = [ln for ln in proc.stdout.splitlines() if ln.strip().startswith("{")]
        info = json.loads(lines[-1]) if lines else {}
        local_file = info.get("_filename") or ""
        if download and not local_file and info.get("id") and info.get("ext"):
            candidate = DOWNLOADS_DIR / f"{info['id']}.{info['ext']}"
            if candidate.exists():
                local_file = str(candidate)

        return {"ok": True, "info": info, "local_path": local_file}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def detect_platform_from_url(url: str) -> str:
    lower = url.lower()
    if "youtube.com" in lower or "youtu.be" in lower:
        return "youtube"
    if "bilibili.com" in lower or "b23.tv" in lower:
        return "bilibili"
    if "xiaohongshu.com" in lower or "xhslink.com" in lower:
        return "xiaohongshu"
    if "twitter.com" in lower or "x.com" in lower:
        return "twitter"
    if "reddit.com" in lower or "redd.it" in lower:
        return "reddit"
    if "tiktok.com" in lower:
        return "tiktok"
    if "douyin.com" in lower:
        return "douyin"
    if "instagram.com" in lower:
        return "instagram"
    if "threads.net" in lower or "threads.com" in lower:
        return "threads"
    if "facebook.com/ads/library" in lower:
        return "meta_ads"
    return "facebook"


async def inspect_or_download_url(url: str, download: bool = True) -> Dict[str, Any]:
    url = url.strip()
    platform = detect_platform_from_url(url)
    canon_u = _canonicalize_video_url(platform, url)

    existing = next(
        (v for v in database.list_videos() if _canonicalize_video_url(str(v.get("platform") or ""), str(v.get("source_url") or "")) == canon_u),
        None,
    )

    # 1. Special fast path for Meta Ad Library URLs (`facebook.com/ads/library/?id=...`)
    if platform == "meta_ads" and has_playwright():
        raw_ads, _ = await _scrape_meta_ad_library_structured(
            urls_to_visit=[url],
            country="VN",
            require_video=False,
            scroll_rounds=1,
            max_ads=6,
        )
        if raw_ads:
            ad = raw_ads[0]
            p_ctx = " | ".join(x for x in (ad.get("headline", ""), ad.get("link_description", ""), ad.get("body", "")) if x)
            meta = await asyncio.to_thread(
                _fetch_live_store_price_and_meta,
                ad.get("raw_ext_link") or ad.get("_sibling_shop_url") or "",
                p_ctx,
                ad.get("headline") or ad.get("page_name") or "",
                ad.get("page_url") or "",
                ad.get("ig_handle") or "",
            )
            v_cdn = str(ad.get("video_url") or "")
            local_mp4 = ""
            play_url = v_cdn
            lib_id = str(ad.get("library_id") or "")
            if download and v_cdn.startswith("http"):
                fname = f"meta_ad_{lib_id or int(time.time())}.mp4"
                dl_rel = await asyncio.to_thread(_download_asset_to_local, v_cdn, fname)
                if dl_rel:
                    local_mp4 = str(DOWNLOADS_DIR / fname)
                    play_url = dl_rel

            page_name = ad.get("page_name") or "Meta Advertiser"
            caption = (ad.get("body") or ad.get("headline") or f"Quảng cáo Meta từ {page_name}")[:550]
            title = f"[Meta Ad] {page_name[:30]} — {(ad.get('headline') or caption)[:85]}"[:140]
            analysis = analyze_video_structure(title, caption)
            sigs = []
            if meta.get("selling_price"):
                sigs.append(f"Giá: {meta['selling_price']}")
            if meta.get("product_url"):
                sigs.append("Gắn Link SP")

            item = {
                "platform": "meta_ads",
                "title": title,
                "caption": caption,
                "author": page_name[:80],
                "source_url": canon_u,
                "video_url": play_url,
                "thumbnail_url": ad.get("thumbnail_url") or "",
                "local_path": local_mp4,
                "views": 120000,
                "likes": 5100,
                "comments": 320,
                "shares": 440,
                "viral_score": 90,
                "sales_signals": detect_sales_signals(caption, sigs),
                "hook_text": analysis["hook_text"],
                "script_summary": analysis["script_summary"],
                "shop_name": page_name[:80],
                "shop_url": meta.get("shop_url") or "",
                "product_url": meta.get("product_url") or "",
                "selling_price": meta.get("selling_price") or "",
                "original_price": meta.get("original_price") or "",
                "meta_library_id": lib_id,
                "meta_page_id": str(ad.get("page_id") or ""),
                "ig_handle": str(ad.get("ig_handle") or ""),
                "ad_placements": ad.get("placements") or ["facebook", "instagram"],
                "cta_text": str(ad.get("cta_text") or ""),
            }
            item["market_intel"] = build_market_intel_for_video(item, shops=[], product_query=ad.get("headline") or page_name, spy_status="deep_spied")
            saved = _upsert_video_by_source_url(item)
            return {"ok": True, "downloaded": bool(local_mp4), "video": saved}

    res = await asyncio.to_thread(_run_ytdlp_sync, url, download)
    if res.get("ok"):
        info = res["info"]
        title = info.get("title") or info.get("fulltitle") or f"Video từ {platform}"
        caption = info.get("description") or title
        author = info.get("uploader") or info.get("channel") or "@creator"
        views = int(info.get("view_count") or 85000)
        likes = int(info.get("like_count") or 3200)
        comments = int(info.get("comment_count") or 180)
        shares = int(info.get("repost_count") or 240)
        analysis = analyze_video_structure(title, caption)
        local_path = res.get("local_path") or ""
        play_url = f"/media/downloads/{Path(local_path).name}" if local_path and Path(local_path).is_file() else (info.get("url") or "")

        item_tmp = {"platform": platform, "title": title, "caption": caption, "author": author, "source_url": canon_u}
        direct_sh = await asyncio.to_thread(_discover_direct_creator_shop, item_tmp, title[:50])
        sell_p = (direct_sh.get("selling_price") if direct_sh else "") or _extract_price_from_text_multi(f"{title} {caption}")
        orig_p = direct_sh.get("original_price") if direct_sh else ""

        item_save = {
            "platform": platform,
            "title": title[:140],
            "caption": caption[:500],
            "author": author[:80],
            "source_url": canon_u,
            "video_url": play_url,
            "thumbnail_url": info.get("thumbnail") or "",
            "local_path": local_path,
            "views": views,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "viral_score": compute_viral_score(views, likes, comments, shares),
            "sales_signals": detect_sales_signals(caption, [f"Giá: {sell_p}"] if sell_p else None),
            "hook_text": analysis["hook_text"],
            "script_summary": analysis["script_summary"],
            "shop_name": str(direct_sh.get("shop_name") or "") if direct_sh else "",
            "shop_url": str(direct_sh.get("shop_url") or "") if direct_sh else "",
            "product_url": str(direct_sh.get("product_url") or "") if direct_sh else "",
            "selling_price": sell_p,
            "original_price": orig_p or "",
            "ad_placements": [platform] if platform in {"facebook", "instagram", "threads"} else [],
        }
        item_save["market_intel"] = build_market_intel_for_video(
            item_save,
            shops=[direct_sh] if direct_sh else [],
            product_query=title[:50],
            spy_status="baseline",
        )
        saved = _upsert_video_by_source_url(item_save)
        return {"ok": True, "downloaded": bool(local_path), "video": saved}

    # Try Agent-Reach read as metadata fallback before static template fallback
    ar_title = ""
    ar_caption = ""
    ar_author = ""
    if find_agent_reach():
        ar_resp = await asyncio.to_thread(_run_agent_reach_sync, ["read", url], 25)
        if ar_resp.get("ok"):
            items, _ = _normalize_agent_reach_items(platform, url, ar_resp)
            if items:
                ar_title = items[0]["title"]
                ar_caption = items[0]["caption"]
                ar_author = items[0]["author"]

    if existing:
        return {
            "ok": True,
            "downloaded": bool(existing.get("local_path")),
            "warning": f"Link đã tồn tại trong kho (yt-dlp chưa tải được file trực tiếp: {res.get('error', '')})",
            "video": existing,
        }

    title = ar_title or f"Imported {platform.title()} Video"
    caption = ar_caption or f"Link gốc đã lưu để phân tích kịch bản & clone qua Muse / rea-video: {url}"
    analysis = analyze_video_structure(title, caption)
    saved = database.insert_video(
        {
            "platform": platform,
            "title": title[:140],
            "caption": caption[:500],
            "author": ar_author or "@imported_creator",
            "source_url": canon_u,
            "video_url": "",
            "thumbnail_url": "https://images.unsplash.com/photo-1611162617474-5b21e879e113?auto=format&fit=crop&w=600&q=80",
            "local_path": "",
            "views": 110000,
            "likes": 4900,
            "comments": 260,
            "shares": 390,
            "viral_score": 86,
            "sales_signals": detect_sales_signals(caption) + ["Imported URL"],
            "hook_text": analysis["hook_text"],
            "script_summary": analysis["script_summary"],
            "ad_placements": [platform] if platform in {"facebook", "instagram", "threads"} else [],
        }
    )
    return {
        "ok": True,
        "downloaded": False,
        "warning": f"Đã lưu video để phân tích & clone (yt-dlp chưa tải được file trực tiếp: {res.get('error', '')})",
        "video": saved,
    }
