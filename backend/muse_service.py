from __future__ import annotations

import asyncio
import base64
import concurrent.futures
import io
import json
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from PIL import Image, ImageDraw, ImageFont

import crawler_service
import database
import flow_service
import publisher_service

MEDIA_DIR = Path(__file__).resolve().parent / "media"
OUTPUTS_DIR = MEDIA_DIR / "outputs"
REA_OUTPUTS_DIR = MEDIA_DIR / "rea_outputs"
DOWNLOADS_DIR = MEDIA_DIR / "downloads"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
REA_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

KNOWN_FFMPEG_PATHS = [
    shutil.which("ffmpeg"),
    str(Path(__file__).resolve().parent / ".venv/lib/python3.9/site-packages/static_ffmpeg/bin/darwin_arm64/ffmpeg"),
    "/Users/vu/.agent-reach/tools/ffmpeg/bin/ffmpeg",
    "/opt/homebrew/bin/ffmpeg",
    "/usr/local/bin/ffmpeg",
    r"C:\Users\Admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe",
]

KNOWN_REA_VIDEO_PATHS = [
    shutil.which("rea-video"),
    "/Users/vu/.local/bin/rea-video",
    "/Users/vu/.gemini/antigravity/scratch/rea-video/.venv/bin/rea-video",
]

REA_SAMPLE_VIDEOS_DIR = Path("/Users/vu/.gemini/antigravity/scratch/rea-video/docs/cases/videos")
REA_SAMPLE_VIDEO_FILES = [
    "v11_tiktok_original.mp4",
    "unboxing.mp4",
    "dual_role.mp4",
    "v12_oiioii_juicer_remake.mp4",
]


def find_ffmpeg() -> Optional[str]:
    for p in KNOWN_FFMPEG_PATHS:
        if p and Path(p).exists():
            return str(p)
    return None


def find_rea_video() -> Optional[str]:
    for p in KNOWN_REA_VIDEO_PATHS:
        if p and Path(p).exists():
            return str(p)
    return None


def _load_vn_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\tahoma.ttf",
        ]
        if bold
        else [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\tahoma.ttf",
        ]
    )
    for fp in candidates:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size=size)
            except Exception:
                pass
    return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: Any, max_width: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    current = ""
    for w in words:
        trial = f"{current} {w}".strip()
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines[:3]


_MULTIMODAL_HINTS = (
    "gemini",
    "gpt-4o",
    "gpt-4.1",
    "gpt-5",
    "claude-3",
    "claude-sonnet",
    "claude-opus",
    "claude-haiku",
    "qwen-vl",
    "qwen2-vl",
    "qwen2.5-vl",
    "qwen3-vl",
    "doubao",
    "vision",
    "-vl",
    "pixtral",
    "llava",
    "omni",
)


def _extract_model_ids(payload: Any) -> List[str]:
    candidates: List[str] = []
    if isinstance(payload, dict):
        items = payload.get("data")
        if not isinstance(items, list):
            items = payload.get("models")
        if not isinstance(items, list):
            items = payload.get("results")
    elif isinstance(payload, list):
        items = payload
    else:
        items = []

    if not isinstance(items, list):
        return []

    for item in items:
        mid = ""
        if isinstance(item, str):
            mid = item
        elif isinstance(item, dict):
            mid = str(item.get("id") or item.get("model") or item.get("name") or "")
        mid = mid.strip()
        if mid.startswith("models/"):
            mid = mid[len("models/") :]
        if mid and mid not in candidates:
            candidates.append(mid)
    return candidates


async def fetch_vlm_models(base_url: str, api_key: str = "") -> Dict[str, Any]:
    """Fetch available models from an OpenAI-compatible, Gemini, or local Ollama endpoint."""
    raw_base = (base_url or "").strip().rstrip("/")
    if not raw_base:
        return {
            "ok": False,
            "base_url": "",
            "count": 0,
            "models": [],
            "recommended": [],
            "error": "Vui lòng nhập VLM Endpoint Base URL trước khi Fetch Model.",
        }

    if not re.match(r"^https?://", raw_base, flags=re.IGNORECASE):
        raw_base = f"https://{raw_base}"

    clean_base = re.sub(r"/(chat/completions|completions|models)$", "", raw_base).rstrip("/")
    key_clean = (api_key or "").strip()

    probe_targets: List[Tuple[str, str]] = [(f"{clean_base}/models", clean_base)]
    if not re.search(r"/(v1|v1beta|v1beta/openai|openai|api/paas/v4)$", clean_base):
        probe_targets.append((f"{clean_base}/v1/models", f"{clean_base}/v1"))
    if "generativelanguage.googleapis.com" in clean_base:
        gemini_openai = "https://generativelanguage.googleapis.com/v1beta/openai"
        probe_targets.append((f"{gemini_openai}/models", gemini_openai))
        if key_clean:
            probe_targets.append(
                (f"https://generativelanguage.googleapis.com/v1beta/models?key={key_clean}", gemini_openai)
            )
    if "localhost" in clean_base or "127.0.0.1" in clean_base:
        probe_targets.append((f"{clean_base}/api/tags", f"{clean_base}/v1"))

    seen_urls = set()
    unique_targets: List[Tuple[str, str]] = []
    for url, resolved in probe_targets:
        if url not in seen_urls:
            seen_urls.add(url)
            unique_targets.append((url, resolved))

    headers: Dict[str, str] = {"User-Agent": "rea-video/0.1.0", "Accept": "application/json"}
    if key_clean:
        headers["Authorization"] = f"Bearer {key_clean}"
        headers["x-api-key"] = key_clean

    last_error = "Không kết nối được tới endpoint."
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for url, resolved_base in unique_targets:
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code >= 400:
                    snippet = resp.text.strip().replace("\n", " ")[:180]
                    last_error = f"HTTP {resp.status_code} tại {url}: {snippet}"
                    continue
                payload = resp.json()
                raw_models = _extract_model_ids(payload)
                if not raw_models:
                    last_error = f"Endpoint {url} trả về JSON nhưng không tìm thấy danh sách model."
                    continue
                recommended = [m for m in raw_models if any(h in m.lower() for h in _MULTIMODAL_HINTS)]
                others = [m for m in raw_models if m not in recommended]
                ordered_models = recommended + others
                return {
                    "ok": True,
                    "base_url": resolved_base,
                    "count": len(ordered_models),
                    "models": ordered_models,
                    "recommended": recommended,
                }
            except Exception as exc:
                last_error = f"Lỗi kết nối {url}: {str(exc)[:180]}"

    return {
        "ok": False,
        "base_url": clean_base,
        "count": 0,
        "models": [],
        "recommended": [],
        "error": last_error,
    }


def _render_organic_hook_pill_png(output_png: Path, hook_text: str) -> None:
    """Render an ultra-clean creator hook pill (no product box, no price, no affiliate code)."""
    width, height = 720, 1280
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_title = _load_vn_font(34, bold=True)
    hook_lines = _wrap_text(draw, (hook_text or "").strip(), font_title, 580)[:2]
    if not hook_lines:
        img.save(output_png, "PNG")
        return

    line_h = 44
    box_h = max(84, 34 + len(hook_lines) * line_h)
    y1 = 115
    y2 = y1 + box_h
    draw.rounded_rectangle([(56, y1), (664, y2)], radius=24, fill=(15, 23, 42, 195))

    y_cursor = y1 + 20
    for ln in hook_lines:
        bbox = draw.textbbox((0, 0), ln, font=font_title)
        tw = bbox[2] - bbox[0]
        tx = max(72, (width - tw) // 2)
        draw.text((tx, y_cursor), ln, font=font_title, fill=(255, 255, 255, 255))
        y_cursor += line_h

    img.save(output_png, "PNG")


def bulk_import_tokens(raw_text: str, default_weekly_limit: int = 50) -> int:
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    items: List[Dict[str, Any]] = []
    for idx, line in enumerate(lines, start=1):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            label, token, proxy = parts[0], parts[1], parts[2]
        elif len(parts) == 2:
            label, token, proxy = parts[0], parts[1], ""
        else:
            label = f"Muse_Bulk_{idx:03d}"
            token = parts[0]
            proxy = ""
        if not token:
            continue
        items.append(
            {
                "label": label[:80],
                "account_identifier": label[:80],
                "auth_token": token,
                "proxy": proxy,
                "tokens_remaining": 1000000000,
                "tokens_total": 1000000000,
                "weekly_used": 0,
                "weekly_limit": default_weekly_limit,
                "status": "active",
                "notes": "Bulk imported vào kho token",
            }
        )
    if not items:
        return 0
    return database.insert_muse_tokens_bulk(items)


def acquire_next_token() -> Optional[Dict[str, Any]]:
    """Select the healthiest active Muse account with remaining weekly quota and reserve usage."""
    with database.get_conn() as conn:
        row = conn.execute(
            """
            SELECT * FROM muse_tokens
            WHERE status = 'active'
              AND weekly_used < weekly_limit
              AND tokens_remaining >= 50000
            ORDER BY last_used_at ASC, weekly_used ASC, id ASC
            LIMIT 1
            """
        ).fetchone()
        if not row:
            return None
        token = dict(row)
        tokens_cost = 450000
        new_remaining = max(0, int(token["tokens_remaining"]) - tokens_cost)
        new_weekly = int(token["weekly_used"]) + 1
        new_status = "cooldown" if new_weekly >= int(token["weekly_limit"]) else "active"
        conn.execute(
            """
            UPDATE muse_tokens
            SET tokens_remaining = ?, weekly_used = ?, status = ?, last_used_at = ?
            WHERE id = ?
            """,
            (new_remaining, new_weekly, new_status, database.utc_now_iso(), token["id"]),
        )
        token["tokens_spent_now"] = tokens_cost
        return token


def _ensure_video_mp4_sync(video: Dict[str, Any]) -> Tuple[Optional[str], str]:
    local_path = video.get("local_path") or ""
    if local_path and Path(local_path).exists():
        return local_path, "local_existing"

    source_url = (video.get("source_url") or "").strip()
    is_concrete_url = (
        source_url.startswith("http")
        and "Demo" not in source_url
        and "search_query=" not in source_url
        and "/ads/library/?" not in source_url
        and not source_url.rstrip("/").endswith(("/reels", "/reel", "threads.net"))
    )
    if is_concrete_url and crawler_service.find_ytdlp():
        dl = crawler_service._run_ytdlp_sync(source_url, download=True)
        if dl.get("ok") and dl.get("local_path") and Path(dl["local_path"]).exists():
            database.update_video(video["id"], local_path=dl["local_path"])
            return dl["local_path"], "ytdlp_downloaded"

    # Use bundled rea-video real MP4 sample or synthesize one with FFmpeg so shot analysis always runs cleanly
    sample_dest = DOWNLOADS_DIR / f"sample_video_{video['id']}.mp4"
    if not sample_dest.exists() and REA_SAMPLE_VIDEOS_DIR.exists():
        sample_name = REA_SAMPLE_VIDEO_FILES[int(video["id"]) % len(REA_SAMPLE_VIDEO_FILES)]
        sample_src = REA_SAMPLE_VIDEOS_DIR / sample_name
        if sample_src.exists():
            shutil.copy2(sample_src, sample_dest)
            database.update_video(video["id"], local_path=str(sample_dest))
            return str(sample_dest), f"rea_sample:{sample_name}"

    if sample_dest.exists():
        database.update_video(video["id"], local_path=str(sample_dest))
        return str(sample_dest), "sample_cached"

    ffmpeg_bin = find_ffmpeg()
    if ffmpeg_bin:
        cmd = [
            ffmpeg_bin,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x111827:s=720x1280:d=5:r=25",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(sample_dest),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=crawler_service.build_tool_env())
        if proc.returncode == 0 and sample_dest.exists():
            database.update_video(video["id"], local_path=str(sample_dest))
            return str(sample_dest), "ffmpeg_synthesized"

    return None, "no_mp4_source"


_VLM_VISION_CAPABILITY_CACHE: Dict[Tuple[str, str], Tuple[float, bool]] = {}


def _probe_vlm_vision_support(base_url: str, api_key: str, model: str) -> bool:
    """Fast 6s probe checking whether the configured OpenAI-compatible gateway actually responds to image_url vision payloads."""
    clean_base = (base_url or "").strip().rstrip("/")
    clean_model = (model or "").split(",")[0].strip()
    if not clean_base or not api_key or not clean_model:
        return False

    cache_key = (clean_base, clean_model)
    cached = _VLM_VISION_CAPABILITY_CACHE.get(cache_key)
    if cached and (time.monotonic() - cached[0]) < 900.0:
        return cached[1]

    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (120, 140, 160)).save(buf, format="JPEG", quality=60)
    tiny_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    ok = False
    try:
        resp = httpx.post(
            f"{clean_base}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "CloneVideoAff-ReaProbe/1.0",
            },
            json={
                "model": clean_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{tiny_b64}"}},
                            {"type": "text", "text": 'Reply JSON: {"ok":true}'},
                        ],
                    }
                ],
                "max_tokens": 32,
            },
            timeout=6.0,
        )
        ok = resp.status_code == 200 and len(resp.text.strip()) > 5
    except Exception:
        ok = False

    _VLM_VISION_CAPABILITY_CACHE[cache_key] = (time.monotonic(), ok)
    return ok


def _build_motion_storyboard_sheet(out_dir: Path, raw_shots: List[Dict[str, Any]]) -> Optional[Path]:
    """Build a 2-column chronological motion storyboard from each shot's 4-frame strip (shot_XXX.jpg) so Vision sees Start -> Mid -> End of every shot."""
    shots_dir = out_dir / "shots"
    if not shots_dir.is_dir() or not raw_shots:
        return None
    strips: List[Tuple[str, Image.Image]] = []
    for r in raw_shots[:14]:
        idx = int(r.get("index") or (len(strips) + 1))
        st = round(float(r.get("start") or 0), 2)
        en = round(float(r.get("end") or 0), 2)
        dur = round(max(0.1, en - st), 2)
        strip_p = shots_dir / f"shot_{idx:03d}.jpg"
        if not strip_p.is_file():
            strip_p = shots_dir / f"shot_{idx:03d}_first.jpg"
        if not strip_p.is_file():
            continue
        try:
            im = Image.open(strip_p).convert("RGB")
            strips.append((f"SHOT #{idx} ({st}s-{en}s, {dur}s) [Start -> 33% -> 66% -> End]", im))
        except Exception:
            continue

    if not strips:
        return None

    cols = 2 if len(strips) >= 4 else 1
    col_w = 720
    pad = 10
    hdr_h = 28
    rows = (len(strips) + cols - 1) // cols

    # Normalize each strip width to col_w
    resized_cells: List[Tuple[str, Image.Image]] = []
    max_strip_h = 260
    for label, im in strips:
        w, h = im.size
        target_h = max(140, min(340, int(round(h * (col_w / max(1, w))))))
        max_strip_h = max(max_strip_h, target_h)
        resized_cells.append((label, im.resize((col_w, target_h), Image.Resampling.LANCZOS)))

    cell_h = hdr_h + max_strip_h
    canvas_w = cols * col_w + (cols + 1) * pad
    canvas_h = rows * cell_h + (rows + 1) * pad
    canvas = Image.new("RGB", (canvas_w, canvas_h), (15, 23, 42))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 15)
    except Exception:
        font = ImageFont.load_default()

    for i, (label, strip_im) in enumerate(resized_cells):
        r_idx = i // cols
        c_idx = i % cols
        x0 = pad + c_idx * (col_w + pad)
        y0 = pad + r_idx * (cell_h + pad)
        draw.rectangle([x0, y0, x0 + col_w, y0 + hdr_h], fill=(30, 41, 59))
        draw.text((x0 + 8, y0 + 6), label, fill=(248, 250, 252), font=font)
        canvas.paste(strip_im, (x0, y0 + hdr_h))

    dest = out_dir / "motion_storyboard.jpg"
    try:
        canvas.save(dest, format="JPEG", quality=84)
        return dest
    except Exception:
        return None


def _build_fallback_scene_units(
    shots_parsed: List[Dict[str, Any]],
    product_en: str,
) -> List[Dict[str, Any]]:
    """Group contiguous rea-video shots into <=7.6s scene units with 100% AI-generated First Frame & End Frame prompts."""
    if not shots_parsed:
        return []
    subj = product_en or "the sleek modern featured product with clean unbranded finish"
    groups: List[List[Dict[str, Any]]] = []
    cur_group: List[Dict[str, Any]] = []
    cur_dur = 0.0
    for s in shots_parsed:
        sd = max(0.2, float(s.get("duration") or (float(s.get("end") or 0) - float(s.get("start") or 0)) or 2.0))
        if cur_group and (cur_dur + sd > 7.6 or len(cur_group) >= 4):
            groups.append(cur_group)
            cur_group = [s]
            cur_dur = sd
        else:
            cur_group.append(s)
            cur_dur += sd
    if cur_group:
        groups.append(cur_group)

    units: List[Dict[str, Any]] = []
    for u_idx, grp in enumerate(groups, start=1):
        st = round(float(grp[0].get("start") or 0.0), 2)
        en = round(float(grp[-1].get("end") or (st + 4.0)), 2)
        tdur = round(max(2.2, min(7.9, en - st)), 2)
        s_nums = [int(x.get("index") or 1) for x in grp]
        rel_beats: List[str] = []
        t_cursor = 0.0
        for x in grp:
            xd = round(max(0.3, float(x.get("duration") or 1.5)), 1)
            t_next = round(min(tdur, t_cursor + xd), 1)
            xp = re.sub(r"^Vertical 9:16 [^:]+:\s*", "", str(x.get("prompt") or "").strip())
            rel_beats.append(f"[{round(t_cursor, 1)}s-{t_next}s] {xp or 'Product action showcase'}")
            t_cursor = t_next

        first_desc = re.sub(r"^Vertical 9:16 [^:]+:\s*", "", str(grp[0].get("prompt") or "").strip()) or f"opening view of {subj}"
        last_desc = re.sub(r"^Vertical 9:16 [^:]+:\s*", "", str(grp[-1].get("prompt") or "").strip()) or f"completed action view of {subj}"
        shot_tag = f"Shot #{s_nums[0]}" if len(s_nums) == 1 else f"Shots #{s_nums[0]}–#{s_nums[-1]}"

        ai_start_p = (
            f"Vertical 9:16 smartphone photograph recreating the opening camera angle and framing: "
            f"fresh presenter hands and clean modern environment with {subj} at the start of the action ({first_desc[:180]}). "
            f"Crisp natural lighting, photorealistic, clean frame with NO text overlays, NO subtitles, NO watermarks, NO brand logos."
        )
        ai_end_p = (
            f"Vertical 9:16 smartphone photograph matching the exact same camera angle, lighting, presenter outfit/hands, and {subj} "
            f"from the start frame, now showing the completed end state of the action ({last_desc[:180]}). "
            f"Crisp natural lighting, photorealistic, clean frame with NO text overlays, NO subtitles, NO watermarks, NO brand logos."
        )
        flow_p = (
            f"Vertical 9:16 smartphone video ({tdur}s): Using the exact AI-remade {subj} from the attached reference ingredient image "
            f"(preserving 100% of its shape, color, and mechanism), a fresh presenter performs the exact action sequence: "
            f"{' '.join(rel_beats)}. Authentic movement, crisp natural foley audio, photorealistic, clean frame with NO text overlays, NO subtitles, NO watermarks, NO logos."
        )
        frames_p = (
            f"Smooth continuous physical motion bridging the AI start frame to the AI end frame ({tdur}s) of {subj}: "
            f"{' '.join(rel_beats)}. Natural movement and steady product interaction matching start and end states, "
            "Vertical 9:16 smartphone footage, photorealistic, natural foley sound, clean frame with NO text overlays, NO subtitles, NO watermarks."
        )
        units.append(
            {
                "unit_index": u_idx,
                "title_vi": f"Cảnh {u_idx} ({st}s–{en}s · {shot_tag})",
                "shot_indices": s_nums,
                "start": st,
                "end": en,
                "target_duration": tdur,
                "same_scene_as_prev": u_idx > 1,
                "reuse_prev_end_as_start": False,
                "action_vi": "; ".join(str(x.get("prompt") or "")[:90] for x in grp)[:240],
                "ai_start_image_prompt_en": ai_start_p,
                "ai_end_image_prompt_en": ai_end_p,
                "flow_prompt_en": flow_p,
                "frames_prompt_en": frames_p,
            }
        )
    return units


def _synthesize_rea_shot_prompts_with_llm(
    video: Dict[str, Any],
    summary: Dict[str, Any],
    raw_shots: List[Dict[str, Any]],
    storyboard_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Visually analyze 4-frame per-shot motion strips (Start -> 33% -> 66% -> End) via Multimodal Vision LLM to design a 100% AI-generated First-Frame -> End-Frame Viral Remake Plan (ZERO source frames uploaded)."""
    mi = video.get("market_intel") if isinstance(video.get("market_intel"), dict) else {}
    prod_name = str(mi.get("product_query") or video.get("title") or "").strip()[:120]
    caption = str(video.get("caption") or video.get("hook_text") or "").strip()[:260]

    shot_specs: List[str] = []
    for r in raw_shots[:14]:
        idx = int(r.get("index") or 0)
        st = round(float(r.get("start") or 0), 2)
        en = round(float(r.get("end") or 0), 2)
        dur = round(max(0.1, en - st), 2)
        lbl = str((r.get("base") or {}).get("label") or "live_action")
        tr = str(r.get("transition_in") or "cut")
        rep = r.get("replication") or {}
        framing = str((rep.get("capsule") or {}).get("framing") or "")[:90]
        shot_specs.append(f"Shot #{idx} ({st}s-{en}s, dur={dur}s, {lbl}, {tr}): {framing}")

    if not shot_specs:
        return {}

    total_dur = round(float(summary.get("duration") or raw_shots[-1].get("end") or 10.0), 2)
    prompt = (
        "Examine the chronological 4-frame motion storyboard image carefully! Each box 'SHOT #k (start-end) [Start -> 33% -> 66% -> End]' shows 4 sequential frames from start to end of that shot.\n"
        f"Total Video Duration: {total_dur}s across {len(shot_specs)} shots.\n"
        f"Metadata Caption (IGNORE engagement bait like 'Comment X for link' — trust ONLY what you physically see across the 4 frames of each shot!): {prod_name} | {caption}\n"
        "Measured Shots:\n"
        + "\n".join(shot_specs)
        + "\n\nWe are building a 100% AI-GENERATED VIRAL REMAKE on Google Flow (Nano Banana 2.1 AI First/End Keyframes -> Omni/Veo First-to-End Video).\n"
        "We NEVER upload frames from the original video (to prevent copyright/policy violations). Instead, Nano Banana 2.1 will generate brand-new 9:16 AI First Frame & AI End Frame images that recreate the EXACT camera angles, shot framing, lighting mood, product design, and viral physical actions with a FRESH AI presenter/outfit & clean environment!\n"
        "Return STRICT JSON ONLY (no markdown fences) with this exact schema:\n"
        "{\n"
        '  "product_en": "Precise physical specification of the real product(s) shown (exact color, shape, surface finish, LED light color/strip shape, buttons, slots, connectors, output/mounting mechanism — NO brand names/logos, NEVER invent parts not visible in the frames!)",\n'
        '  "character_and_room_style_en": "Consistent fresh AI presenter / outfit / hands & clean environment style used across the remake (distinct person/outfit from original creator for 0% identity overlap, while matching the exact time-of-day, setting type, and lighting mood!)",\n'
        '  "ai_product_anchor_prompt_en": "65-90 word English 9:16 Nano Banana AI Image prompt showing a crystal-clear, unobstructed close-up reference photo of the exact product_en in matching natural lighting on a clean surface/mount so downstream scene keyframes lock 100% onto its exact shape, color, and features. End with: Vertical 9:16 smartphone photography, photorealistic, NO text overlays, NO subtitles, NO watermarks, NO brand logos.",\n'
        '  "best_clean_shot_index": 6,\n'
        '  "best_clean_frame_pos": "first",\n'
        '  "clean_crop_box_pct": [0, 0, 100, 100],\n'
        '  "overlay_text_boxes_pct": [[8, 9, 92, 23]],\n'
        '  "verdict_vi": "Mô tả tiếng Việt chuẩn xác sản phẩm thật sự là gì và diễn biến hành động chi tiết từ đầu đến cuối video",\n'
        '  "veo_prompt_en": "Summary 95-130 word English 9:16 prompt covering the full remade story",\n'
        '  "shots": {\n'
        '    "1": "Exact English visual & motion description from Start frame to End frame of Shot #1 (who/hands, exact physical action, camera framing, NO caption text)",\n'
        '    "2": "..."\n'
        "  },\n"
        '  "scene_units": [\n'
        "    {\n"
        '      "unit_index": 1,\n'
        '      "title_vi": "Cảnh 1 (0.0s–4.3s · Shots #1–#2): Tóm tắt hành động cảnh 1 bằng tiếng Việt",\n'
        '      "shot_indices": [1, 2],\n'
        '      "start": 0.0,\n'
        '      "end": 4.33,\n'
        '      "target_duration": 4.33,\n'
        '      "same_scene_as_prev": false,\n'
        '      "reuse_prev_end_as_start": false,\n'
        '      "action_vi": "Mô tả chi tiết góc máy & hành động vật lý cần tái hiện ở cụm cảnh này",\n'
        '      "ai_start_image_prompt_en": "65-95 word English 9:16 AI First Frame (Bắt đầu) image generation prompt recreating the EXACT opening camera angle, shot distance (extreme close-up / medium / wide / POV), lighting mood, fresh AI presenter/hands (character_and_room_style_en), and exact physical state of product_en (matching the attached product reference image) at the START of shot_indices[0]. End with: Vertical 9:16 smartphone photography, photorealistic, clean frame with NO text overlays, NO subtitles, NO watermarks, NO brand logos.",\n'
        '      "ai_end_image_prompt_en": "65-95 word English 9:16 AI End Frame (Kết thúc) image generation prompt keeping the EXACT same camera angle, background, lighting, and AI presenter/hands from the attached Start Frame image while showing the exact completed physical state of product_en at the END of shot_indices[-1] (e.g. cloth lifted revealing product, LED switched on glowing neon pink/cyan, glossy photo printed & held up, cyclist/runner further down the path). End with: Vertical 9:16 smartphone photography, photorealistic, clean frame with NO text overlays, NO subtitles, NO watermarks, NO brand logos.",\n'
        '      "flow_prompt_en": "85-120 word English Ingredients-to-Video prompt for Google Flow (Portrait 9:16) locking onto the attached AI product reference image and performing the exact physical action beats [0.0s-X.Xs] ... [X.Xs-Y.Ys] with a fresh presenter. End with: Vertical 9:16 smartphone footage, photorealistic, natural foley sound, clean frame with NO text overlays, NO subtitles, NO watermarks, NO logos.",\n'
        '      "frames_prompt_en": "65-95 word English First-Frame-to-End-Frame video motion prompt describing the smooth continuous physical movement, hand/body motion, camera tracking, and product behavior bridging ai_start_image_prompt_en to ai_end_image_prompt_en. End with: Vertical 9:16 smartphone footage, photorealistic, natural foley sound, clean frame with NO text overlays, NO subtitles, NO watermarks."\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "CRITICAL RULES:\n"
        "1. Read each SHOT box strictly LEFT-TO-RIGHT `[Frame 1 Start -> Frame 2 (33%) -> Frame 3 (66%) -> Frame 4 End]` to capture the true physical action direction (e.g. lifting cover upward to reveal product, pressing button to turn LED strip on, docking phone & ejecting photo, riding/running at night with glowing safety lights).\n"
        "2. NEVER create a scene unit or End Frame from a pure black/solid text-only outro card (e.g., a final 0.5s black screen saying 'What do you bring?' or 'Link in bio')! Always end the final scene unit on real visual product/human action, folding any tiny trailing 0.3-0.8s black outro timestamp into the real action shot.\n"
        "3. Group ALL visual shots into 2–4 chronological `scene_units` (or 1 unit if total video <= 7.5s) where every unit has `target_duration` <= 7.9s. Group shots that share a similar camera setup into the same unit so Start Frame -> End Frame forms one natural continuous shot without jarring camera teleports inside a single clip! Cut to a new `scene_unit` whenever camera angle/location jumps dramatically (e.g. close-up hands installing clip -> wide shot running/riding outdoors).\n"
        "4. Set `reuse_prev_end_as_start: true` ONLY when `unit_index > 1` AND this unit starts at the EXACT same camera angle, distance, and pose where the previous unit's End Frame finished (so reusing previous End Frame makes a 100% seamless cut!). Set `reuse_prev_end_as_start: false` whenever camera angle or framing changes between units.\n"
        "5. Every `ai_start_image_prompt_en`, `ai_end_image_prompt_en`, and `frames_prompt_en` MUST pass Google Flow's strict safety classifier (`PUBLIC_ERROR_UNSAFE_GENERATION`): NEVER use gendered/person-portrait nouns like 'female', 'woman', 'girl', 'man', 'boy', 'face', 'portrait', or 'celebrity'! Instead, describe human interaction using authentic viral-ad POV hands-in-action, dynamic low-angle footwear/legs-in-stride, or over-the-shoulder framing where human faces are out of frame while keeping 100% of the original shot's camera angle, lighting, environment, and physical product action! Zero burned-in text, zero brand logos."
    )

    raw_txt = ""
    if storyboard_path and storyboard_path.is_file():
        ex_v = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            fut_v = ex_v.submit(crawler_service.call_vision_llm, str(storyboard_path), prompt, 48.0, 4200)
            raw_txt = (fut_v.result(timeout=51.0) or "").strip()
        except Exception:
            raw_txt = ""
        finally:
            ex_v.shutdown(wait=False)

    if not raw_txt:
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            fut = ex.submit(crawler_service._call_configured_llm, prompt, 18.0)
            raw_txt = (fut.result(timeout=19.5) or "").strip()
        except Exception:
            raw_txt = ""
        finally:
            ex.shutdown(wait=False)

    if not raw_txt:
        return {}

    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_txt.strip())
    m = re.search(r"\{[\s\S]*\}", cleaned)
    if not m:
        return {}
    try:
        parsed = json.loads(m.group(0))
        if not isinstance(parsed, dict):
            return {}
        shots_map_raw = parsed.get("shots") if isinstance(parsed.get("shots"), dict) else {}
        shots_map: Dict[int, str] = {}
        for k, v in shots_map_raw.items():
            try:
                shots_map[int(str(k).strip().lstrip("#"))] = str(v or "").strip()
            except ValueError:
                pass
        best_idx = 0
        try:
            best_idx = int(parsed.get("best_clean_shot_index") or 0)
        except (TypeError, ValueError):
            best_idx = 0
        best_pos = str(parsed.get("best_clean_frame_pos") or "first").strip().lower()
        if best_pos not in ("first", "last"):
            best_pos = "first"
        crop_raw = parsed.get("clean_crop_box_pct")
        crop_box = [0.0, 0.0, 100.0, 100.0]
        if isinstance(crop_raw, list) and len(crop_raw) == 4:
            try:
                c_vals = [max(0.0, min(100.0, float(x))) for x in crop_raw]
                if c_vals[2] - c_vals[0] >= 35.0 and c_vals[3] - c_vals[1] >= 35.0:
                    crop_box = c_vals
            except Exception:
                pass

        overlay_boxes_raw = parsed.get("overlay_text_boxes_pct")
        overlay_boxes: List[List[float]] = []
        if isinstance(overlay_boxes_raw, list):
            for box in overlay_boxes_raw[:8]:
                if isinstance(box, (list, tuple)) and len(box) == 4:
                    try:
                        b_vals = [round(max(0.0, min(100.0, float(v))), 2) for v in box]
                        if 0.0 <= b_vals[0] < b_vals[2] <= 100.0 and 0.0 <= b_vals[1] < b_vals[3] <= 100.0:
                            overlay_boxes.append(b_vals)
                    except (TypeError, ValueError):
                        pass

        prod_spec = str(parsed.get("product_en") or "").strip()
        char_style = str(parsed.get("character_and_room_style_en") or "").strip()
        anchor_prompt = str(parsed.get("ai_product_anchor_prompt_en") or "").strip()
        if not anchor_prompt and prod_spec:
            anchor_prompt = (
                f"Vertical 9:16 studio-lit smartphone product photograph of {prod_spec}, resting cleanly in full unobstructed view "
                f"with crisp natural lighting and realistic material texture. Photorealistic, NO text overlays, NO subtitles, NO watermarks, NO brand logos."
            )

        raw_units = parsed.get("scene_units") if isinstance(parsed.get("scene_units"), list) else []
        clean_units: List[Dict[str, Any]] = []
        for idx_u, u in enumerate(raw_units[:6], start=1):
            if not isinstance(u, dict):
                continue
            fp = str(u.get("flow_prompt_en") or u.get("frames_prompt_en") or "").strip()
            if not fp:
                continue
            frames_fp = str(u.get("frames_prompt_en") or "").strip() or fp
            st_u = round(float(u.get("start") or 0.0), 2)
            en_u = round(float(u.get("end") or (st_u + 4.5)), 2)
            td_u = round(max(2.0, min(7.9, float(u.get("target_duration") or (en_u - st_u) or 4.5))), 2)
            s_idxs: List[int] = []
            for sx in (u.get("shot_indices") or []):
                try:
                    s_idxs.append(int(sx))
                except (TypeError, ValueError):
                    pass
            ai_start_p = str(u.get("ai_start_image_prompt_en") or "").strip()
            ai_end_p = str(u.get("ai_end_image_prompt_en") or "").strip()
            if not ai_start_p:
                ai_start_p = (
                    f"Vertical 9:16 smartphone photograph recreating the opening camera angle of Scene {idx_u}: "
                    f"{char_style or 'fresh presenter hands in clean lighting'} with {prod_spec or 'the featured product'} at the start of: {frames_fp[:180]}. "
                    "Photorealistic, clean frame with NO text overlays, NO subtitles, NO watermarks, NO brand logos."
                )
            if not ai_end_p:
                ai_end_p = (
                    f"Vertical 9:16 smartphone photograph matching the exact same camera angle, lighting, and presenter from the Start Frame, "
                    f"showing the completed end state of: {frames_fp[:180]}. "
                    "Photorealistic, clean frame with NO text overlays, NO subtitles, NO watermarks, NO brand logos."
                )
            clean_units.append(
                {
                    "unit_index": idx_u,
                    "title_vi": str(u.get("title_vi") or f"Cảnh {idx_u} ({st_u}s–{en_u}s)").strip(),
                    "shot_indices": s_idxs,
                    "start": st_u,
                    "end": en_u,
                    "target_duration": td_u,
                    "same_scene_as_prev": bool(u.get("same_scene_as_prev")) if idx_u > 1 else False,
                    "reuse_prev_end_as_start": bool(u.get("reuse_prev_end_as_start")) if idx_u > 1 else False,
                    "action_vi": str(u.get("action_vi") or "").strip(),
                    "ai_start_image_prompt_en": ai_start_p,
                    "ai_end_image_prompt_en": ai_end_p,
                    "flow_prompt_en": fp,
                    "frames_prompt_en": frames_fp,
                }
            )

        return {
            "product_en": prod_spec,
            "character_and_room_style_en": char_style,
            "ai_product_anchor_prompt_en": anchor_prompt,
            "best_clean_shot_index": best_idx,
            "best_clean_frame_pos": best_pos,
            "clean_crop_box_pct": crop_box,
            "overlay_text_boxes_pct": overlay_boxes,
            "verdict_vi": str(parsed.get("verdict_vi") or "").strip(),
            "veo_prompt_en": str(parsed.get("veo_prompt_en") or "").strip(),
            "shots": shots_map,
            "scene_units": clean_units,
        }
    except Exception:
        return {}


def _apply_rea_vision_review(
    rea_bin: str,
    out_dir: Path,
    product_en: str,
    verdict_vi: str,
    shots_parsed: List[Dict[str, Any]],
    scene_units: List[Dict[str, Any]],
) -> None:
    """Populate review_answers.json and run `rea-video apply-review` so report.html, VIDEO.md, and video/remake.md contain full Vision prompts & props."""
    try:
        subprocess.run(
            [rea_bin, "review", "--force", str(out_dir)],
            capture_output=True,
            text=True,
            timeout=15,
            env=crawler_service.build_tool_env(),
            encoding="utf-8",
            errors="replace",
        )
        ans_path = out_dir / "review_answers.json"
        if not ans_path.is_file():
            return
        ans = json.loads(ans_path.read_text(encoding="utf-8"))
        shot_lookup = {int(s["index"]): s for s in shots_parsed}
        ans["by"] = "Vision AI"
        for s_entry in ans.get("shots") or []:
            sid = str(s_entry.get("id") or "")
            m_num = re.search(r"(\d+)", sid)
            if not m_num:
                continue
            s_idx = int(m_num.group(1))
            sp = shot_lookup.get(s_idx)
            if not sp:
                continue
            desc_en = str(sp.get("prompt") or "").strip()
            if not desc_en:
                continue
            s_entry["description"] = desc_en
            rep_obj = s_entry.setdefault("replication", {})
            rep_obj["video_prompt"] = desc_en
            rep_obj["video_prompt_en"] = desc_en
            rep_obj["image_prompt"] = (
                f"Clean vertical 9:16 frame featuring {product_en or 'the product'}: {desc_en} (no text overlays)"
            )
        story_obj = ans.setdefault("story", {})
        story_obj["summary"] = verdict_vi or product_en
        if shots_parsed:
            story_obj["hook"] = str(shots_parsed[0].get("prompt") or "")[:200]
            story_obj["highlights"] = [str(u.get("title_vi") or "") for u in scene_units[:4] if u.get("title_vi")]
        cast_obj = ans.setdefault("cast", {})
        if product_en:
            cast_obj["props"] = [
                {
                    "name": product_en[:160],
                    "note": "Exact physical product locked across all Google Flow scenes",
                    "shots": [int(s["index"]) for s in shots_parsed],
                }
            ]
        if scene_units:
            cast_obj["scenes"] = [
                {
                    "id": f"S{u['unit_index']}",
                    "where": u.get("title_vi") or f"Scene {u['unit_index']}",
                    "when": "Daylight / indoor warm light",
                    "look": u.get("action_vi") or "",
                    "shots": u.get("shot_indices") or [],
                }
                for u in scene_units
            ]
        ans_path.write_text(json.dumps(ans, ensure_ascii=False, indent=2), encoding="utf-8")
        subprocess.run(
            [rea_bin, "apply-review", str(out_dir), "--by", "Vision AI"],
            capture_output=True,
            text=True,
            timeout=25,
            env=crawler_service.build_tool_env(),
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        pass


def _run_rea_decompose_sync(video_id: int, force_vlm: Optional[bool] = None) -> Dict[str, Any]:
    rea_bin = find_rea_video()
    if not rea_bin:
        return {"ok": False, "error": "Không tìm thấy rea-video CLI trên máy."}

    video = database.get_video(video_id)
    if not video:
        return {"ok": False, "error": f"Không tìm thấy video #{video_id}."}

    mp4_path, source_note = _ensure_video_mp4_sync(video)
    if not mp4_path:
        return {"ok": False, "error": "Không thể tải hoặc tạo file MP4 để phân tích."}

    out_dir = REA_OUTPUTS_DIR / f"video_{video_id}"
    out_dir.mkdir(parents=True, exist_ok=True)

    settings = database.get_settings()
    vlm_base = (settings.get("rea_vlm_base_url") or "https://api.openai.com/v1").strip()
    vlm_key = (settings.get("rea_vlm_api_key") or "").strip()
    vlm_model = (settings.get("rea_vlm_model") or "gemini-2.5-pro,gpt-4o").strip()
    vlm_wanted = force_vlm if force_vlm is not None else (settings.get("rea_vlm_enabled") == "1")
    lang = (settings.get("rea_report_lang") or "en").strip()
    if lang not in ("zh", "en"):
        lang = "en"

    # Probe whether the configured gateway responds to image_url vision calls before spawning parallel VLM shot workers
    vision_supported = False
    vlm_fallback_reason = ""
    if vlm_wanted and vlm_key:
        vision_supported = _probe_vlm_vision_support(vlm_base, vlm_key, vlm_model)
        if not vision_supported:
            vlm_fallback_reason = "Đã chạy rea-video Forensics + Multimodal Vision 4-frame/shot phân tích đầy đủ hành động & Cụm Cảnh"

    base_cmd = [
        rea_bin,
        "decompose",
        mp4_path,
        "-o",
        str(out_dir),
        "--no-stems",
        "--no-asr",
        "--no-speakers",
        "--no-ocr",
        "--no-packaging",
        "--lang",
        lang,
    ]

    breakdown_path = out_dir / "breakdown.json"
    ran_ok = False

    if vision_supported:
        extra_env = {
            "REA_VLM_BASE_URL": vlm_base,
            "REA_VLM_API_KEY": vlm_key,
            "REA_VLM_MODEL": vlm_model,
            "REA_VLM_MEDIA": "frames",
            "REA_VLM_TIMEOUT": "16",
            "REA_VLM_REASONING_EFFORT": "low",
        }
        vlm_cmd = base_cmd + ["--vlm", "--no-whole", "--max-vlm-shots", "6"]
        try:
            proc_vlm = subprocess.run(
                vlm_cmd,
                capture_output=True,
                text=True,
                timeout=72,
                env=crawler_service.build_tool_env(extra_env),
                encoding="utf-8",
                errors="replace",
            )
            if proc_vlm.returncode == 0 and breakdown_path.exists():
                ran_ok = True
            else:
                vlm_fallback_reason = "VLM quá tải -> Đã chuyển sang rea-video Forensics + Vision 4-frame/shot"
        except subprocess.TimeoutExpired:
            vlm_fallback_reason = "VLM phản hồi quá 72s -> Đã chuyển sang rea-video Forensics + Vision 4-frame/shot"

    if not ran_ok:
        if breakdown_path.exists():
            try:
                breakdown_path.unlink()
            except OSError:
                pass
        try:
            proc = subprocess.run(
                base_cmd + ["--no-vlm"],
                capture_output=True,
                text=True,
                timeout=65,
                env=crawler_service.build_tool_env(),
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "error": "Video quá dài hoặc hỏng định dạng khiến rea-video phân tích quá 65 giây.",
            }

        if proc.returncode != 0 or not breakdown_path.exists():
            err = (proc.stderr or proc.stdout or "rea-video decompose failed").strip()
            return {"ok": False, "error": err[-400:]}

    bd = json.loads(breakdown_path.read_text(encoding="utf-8"))
    summary = bd.get("summary") or {}
    source_meta = bd.get("source") or {}
    raw_shots = bd.get("shots") or []

    # Build 4-frame-per-shot full motion sheet so Vision sees Start -> 33% -> 66% -> End of EVERY shot!
    motion_sheet = _build_motion_storyboard_sheet(out_dir, raw_shots)
    sb_file = motion_sheet or (out_dir / "storyboard.jpg")
    vision_enrichment: Dict[str, Any] = {}
    if raw_shots:
        vision_enrichment = _synthesize_rea_shot_prompts_with_llm(
            video, summary, raw_shots, storyboard_path=sb_file if sb_file and sb_file.exists() else None
        )

    verdict_vi = str(vision_enrichment.get("verdict_vi") or "").strip()
    product_en = str(vision_enrichment.get("product_en") or "").strip()
    character_and_room_style_en = str(vision_enrichment.get("character_and_room_style_en") or "").strip()
    ai_product_anchor_prompt_en = str(vision_enrichment.get("ai_product_anchor_prompt_en") or "").strip()
    veo_prompt_en = str(vision_enrichment.get("veo_prompt_en") or "").strip()
    best_clean_shot_index = int(vision_enrichment.get("best_clean_shot_index") or 0)
    best_clean_frame_pos = str(vision_enrichment.get("best_clean_frame_pos") or "first")
    clean_crop_box_pct = vision_enrichment.get("clean_crop_box_pct") or [0.0, 0.0, 100.0, 100.0]
    overlay_text_boxes_pct = vision_enrichment.get("overlay_text_boxes_pct") or []
    llm_shot_prompts: Dict[int, str] = vision_enrichment.get("shots") or {}
    scene_units: List[Dict[str, Any]] = vision_enrichment.get("scene_units") or []

    subj_hint = (
        product_en
        or str(video.get("title") or "featured product").split("#")[0].strip()[:90]
        or "featured product"
    )
    shots_parsed: List[Dict[str, Any]] = []
    bd_modified = False

    for r in raw_shots[:15]:
        idx = int(r.get("index") or (len(shots_parsed) + 1))
        base = r.get("base") or {}
        rep = r.get("replication") or {}
        assets = r.get("assets") or {}
        rel_thumb = assets.get("first_frame") or assets.get("sheet") or ""
        thumb_url = f"/media/rea_outputs/video_{video_id}/{rel_thumb}" if rel_thumb else ""
        route_items = rep.get("route") or []
        remake_route = f"{rep.get('rule', '')} · {' -> '.join(route_items[:2])}".strip(" ·")
        vlm_data = r.get("vlm") if isinstance(r.get("vlm"), dict) else {}

        measured_shoot = str((rep.get("shoot") or {}).get("summary") or "").strip()
        measured_framing = str((rep.get("capsule") or {}).get("framing") or "").strip()
        trans_in = str(r.get("transition_in") or "cut")
        measured_prompt = (
            f"Vertical 9:16 {base.get('label') or 'live_action'} shot ({round(float(r.get('duration') or 0), 1)}s, {trans_in}) "
            f"of {subj_hint}: {measured_framing or 'centered product framing'}; {measured_shoot or rep.get('note') or ''}"
        ).strip("; ")

        prompt_hint = (
            llm_shot_prompts.get(idx, "")
            or str(vlm_data.get("prompt") or "").strip()
            or measured_prompt
        )

        if prompt_hint:
            r["vlm"] = {**(vlm_data or {}), "prompt": prompt_hint, "description": prompt_hint}
            if isinstance(rep.get("capsule"), dict):
                rep["capsule"]["prompt_en"] = prompt_hint
                rep["capsule"]["prompt"] = prompt_hint
            bd_modified = True

        shots_parsed.append(
            {
                "index": idx,
                "start": round(float(r.get("start") or 0), 2),
                "end": round(float(r.get("end") or 0), 2),
                "duration": round(float(r.get("duration") or 0), 2),
                "label": base.get("label") or "unknown",
                "confidence": round(float(base.get("confidence") or 0), 2),
                "verdict": r.get("verdict") or "",
                "remake_route": remake_route,
                "prompt": str(prompt_hint)[:420],
                "thumb_url": thumb_url,
            }
        )

    if not scene_units and shots_parsed:
        scene_units = _build_fallback_scene_units(shots_parsed, product_en)

    if bd_modified:
        try:
            breakdown_path.write_text(json.dumps(bd, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    # Write Vision answers back into rea-video via `review` + `apply-review` so report.html & video/remake.md match 100%!
    if shots_parsed and (llm_shot_prompts or product_en):
        _apply_rea_vision_review(rea_bin, out_dir, product_en, verdict_vi, shots_parsed, scene_units)

    storyboard_url = (
        f"/media/rea_outputs/video_{video_id}/storyboard.jpg"
        if (out_dir / "storyboard.jpg").exists()
        else ""
    )
    report_url = (
        f"/media/rea_outputs/video_{video_id}/report.html"
        if (out_dir / "report.html").exists()
        else ""
    )
    video_md_excerpt = ""
    if (out_dir / "VIDEO.md").exists():
        video_md_excerpt = (out_dir / "VIDEO.md").read_text(encoding="utf-8")[:1800]

    remake_md_excerpt = ""
    if (out_dir / "video" / "remake.md").exists():
        remake_md_excerpt = (out_dir / "video" / "remake.md").read_text(encoding="utf-8")[:1800]

    label_vi_map = {
        "live_action": "Quay thật",
        "ai_video": "AI Video",
        "cg_3d": "Đồ hoạ 3D",
        "avatar": "Avatar AI",
        "screen_capture": "Quay màn hình",
        "still_motion": "Ảnh tĩnh chuyển động",
        "anim_2d": "Hoạt hình 2D",
    }
    mix_parts = [
        f"{label_vi_map.get(str(m.get('label')), str(m.get('label')))} {round(float(m.get('ratio') or 0) * 100)}%"
        for m in (summary.get("production_mix") or [])
        if float(m.get("ratio") or 0) >= 0.03
    ]
    raw_verdict_en = str(summary.get("verdict") or "")
    bpm_m = re.search(r"(\d+(?:\.\d+)?)BPM", raw_verdict_en)
    bpm_str = f" · Nhạc nền {bpm_m.group(1)} BPM" if bpm_m else ""
    beat_str = " (cắt cảnh khớp nhịp beat)" if "cuts land on the music beat" in raw_verdict_en else ""
    measured_verdict_vi = (
        f"Cấu trúc {int(summary.get('shots') or len(raw_shots))} shots ({round(float(summary.get('duration') or 0), 1)}s, trung bình {round(float(summary.get('avg_shot_s') or 0), 2)}s/shot): "
        f"{' + '.join(mix_parts) if mix_parts else raw_verdict_en[:120]}{bpm_str}{beat_str}"
    )

    final_verdict = verdict_vi or measured_verdict_vi
    final_vlm_note = (
        f"Vision 4-Frame/Shot đã lập {len(scene_units)} Cụm Cảnh Remake AI (Tự tạo Ảnh Đầu → Cuối mới, 0% lấy ảnh gốc)"
        if product_en and scene_units
        else (
            vlm_fallback_reason
            or ("Đã chạy rea-video Forensics + AI tạo Prompt chi tiết từng Shot" if llm_shot_prompts else str(summary.get("vlm") or "")[:180])
        )
    )

    breakdown_payload: Dict[str, Any] = {
        "source_note": source_note,
        "verdict": final_verdict,
        "product_en": product_en,
        "character_and_room_style_en": character_and_room_style_en,
        "ai_product_anchor_prompt_en": ai_product_anchor_prompt_en,
        "best_clean_shot_index": best_clean_shot_index,
        "best_clean_frame_pos": best_clean_frame_pos,
        "clean_crop_box_pct": clean_crop_box_pct,
        "overlay_text_boxes_pct": overlay_text_boxes_pct,
        "veo_prompt_en": veo_prompt_en,
        "scene_units": scene_units,
        "shots_count": int(summary.get("shots") or len(raw_shots)),
        "duration": float(summary.get("duration") or source_meta.get("duration") or 0),
        "confidence": float(summary.get("confidence") or 0),
        "avg_shot_s": float(summary.get("avg_shot_s") or 0),
        "vlm_note": final_vlm_note,
        "production_mix": summary.get("production_mix") or [],
        "storyboard_url": storyboard_url,
        "report_url": report_url,
        "shots": shots_parsed,
        "video_md_excerpt": video_md_excerpt,
        "remake_md_excerpt": remake_md_excerpt,
    }

    shot_lines = [
        f"Shot #{s['index']} ({s['start']}s-{s['end']}s · {s['label']}): {s['prompt'] or s['verdict'] or s['remake_route']}"
        for s in shots_parsed[:6]
    ]
    new_script_summary = (
        f"[rea-video Shot-by-Shot] {breakdown_payload['verdict']} "
        f"({breakdown_payload['shots_count']} shots → {len(scene_units)} cụm cảnh Flow, {breakdown_payload['duration']}s)\n"
        + "\n".join(shot_lines)
    )

    updated_video = database.update_video(
        video_id,
        rea_breakdown_json=json.dumps(breakdown_payload, ensure_ascii=False),
        rea_report_url=report_url,
        script_summary=new_script_summary,
    )
    return {
        "ok": True,
        "video": updated_video,
        "breakdown": breakdown_payload,
    }


def upgrade_rea_scene_units_for_ai_remake(video_id: int) -> Optional[Dict[str, Any]]:
    """Fast ~12s Vision upgrade when breakdown.json already exists on disk but lacks AI Start/End Remake prompts."""
    video = database.get_video(video_id)
    if not video:
        return None
    out_dir = REA_OUTPUTS_DIR / f"video_{video_id}"
    breakdown_path = out_dir / "breakdown.json"
    if not breakdown_path.is_file():
        res = _run_rea_decompose_sync(video_id, force_vlm=False)
        return res.get("video") if res.get("ok") else None
    try:
        raw_bd = json.loads(breakdown_path.read_text(encoding="utf-8"))
        summary = raw_bd.get("summary") or {}
        raw_shots = raw_bd.get("shots") or []
        if not raw_shots:
            return None
        sb_file = out_dir / "motion_storyboard.jpg"
        if not sb_file.is_file():
            sb_file = _build_motion_storyboard_sheet(out_dir, raw_shots) or (out_dir / "storyboard.jpg")
        enrichment = _synthesize_rea_shot_prompts_with_llm(
            video, summary, raw_shots, storyboard_path=sb_file if sb_file and sb_file.is_file() else None
        )
        if not enrichment or not enrichment.get("scene_units"):
            return None
        cur_bd = dict(video.get("rea_breakdown") or {})
        for k in (
            "product_en",
            "character_and_room_style_en",
            "ai_product_anchor_prompt_en",
            "verdict_vi",
            "veo_prompt_en",
            "scene_units",
        ):
            if enrichment.get(k):
                if k == "verdict_vi":
                    cur_bd["verdict"] = enrichment[k]
                else:
                    cur_bd[k] = enrichment[k]
        cur_bd["vlm_note"] = (
            f"Vision 4-Frame/Shot đã lập {len(enrichment['scene_units'])} Cụm Cảnh Remake AI "
            "(Tự tạo Ảnh Đầu → Cuối mới, 0% lấy ảnh gốc)"
        )
        return database.update_video(
            video_id,
            rea_breakdown_json=json.dumps(cur_bd, ensure_ascii=False),
        )
    except Exception:
        return None


async def decompose_video_with_rea(video_id: int, force_vlm: Optional[bool] = None) -> Dict[str, Any]:
    return await asyncio.to_thread(_run_rea_decompose_sync, video_id, force_vlm)


def _compose_organic_remake_video(
    ffmpeg_bin: str,
    source_local_path: str,
    output_mp4: Path,
    clone_mode: str = "rea_video_remake",
    anti_duplicate: bool = True,
    hook_overlay_png: Optional[Path] = None,
) -> Tuple[bool, str]:
    """Render a clean 9:16 720x1280 H.264/AAC organic viral remake without affiliate CTA banners."""
    has_source = bool(source_local_path and Path(source_local_path).exists())
    has_hook_overlay = bool(hook_overlay_png and hook_overlay_png.exists())

    vf_parts = [
        (
            "scale=744:1322:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,"
            "eq=contrast=1.03:saturation=1.05:brightness=0.005"
        )
        if anti_duplicate
        else "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1"
    ]
    if clone_mode == "muse_prompt_remap":
        vf_parts.append("unsharp=3:3:0.35")
    base_vf = ",".join(vf_parts)

    if has_source:
        if has_hook_overlay:
            filter_complex = f"[0:v]{base_vf}[bg];[bg][1:v]overlay=0:0:enable='between(t,0,3.2)':format=auto[vout]"
            cmd = [
                ffmpeg_bin,
                "-y",
                "-t",
                "120",
                "-i",
                source_local_path,
                "-i",
                str(hook_overlay_png),
                "-filter_complex",
                filter_complex,
                "-map",
                "[vout]",
                "-map",
                "0:a?",
                "-map_metadata",
                "-1",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(output_mp4),
            ]
        else:
            cmd = [
                ffmpeg_bin,
                "-y",
                "-t",
                "120",
                "-i",
                source_local_path,
                "-vf",
                base_vf,
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
                "-map_metadata",
                "-1",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(output_mp4),
            ]
    else:
        if has_hook_overlay:
            cmd = [
                ffmpeg_bin,
                "-y",
                "-f",
                "lavfi",
                "-i",
                "gradients=s=720x1280:r=25:d=6:c0=0f172a:c1=1e1b4b:c2=312e81:speed=0.4",
                "-i",
                str(hook_overlay_png),
                "-f",
                "lavfi",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-filter_complex",
                "[0:v][1:v]overlay=0:0:enable='between(t,0,3.2)':format=auto[vout]",
                "-map",
                "[vout]",
                "-map",
                "2:a",
                "-t",
                "6",
                "-map_metadata",
                "-1",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                "-movflags",
                "+faststart",
                str(output_mp4),
            ]
        else:
            cmd = [
                ffmpeg_bin,
                "-y",
                "-f",
                "lavfi",
                "-i",
                "gradients=s=720x1280:r=25:d=6:c0=0f172a:c1=1e1b4b:c2=312e81:speed=0.4",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-map",
                "0:v:0",
                "-map",
                "1:a",
                "-t",
                "6",
                "-map_metadata",
                "-1",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                "-movflags",
                "+faststart",
                str(output_mp4),
            ]

    env = crawler_service.build_tool_env()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        if has_hook_overlay:
            fallback_cmd = [
                ffmpeg_bin,
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=0x0f172a:s=720x1280:d=5:r=25",
                "-i",
                str(hook_overlay_png),
                "-f",
                "lavfi",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-filter_complex",
                "[0:v][1:v]overlay=0:0:enable='between(t,0,3.2)'[vout]",
                "-map",
                "[vout]",
                "-map",
                "2:a",
                "-t",
                "5",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(output_mp4),
            ]
        else:
            fallback_cmd = [
                ffmpeg_bin,
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=0x0f172a:s=720x1280:d=5:r=25",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-map",
                "0:v:0",
                "-map",
                "1:a",
                "-t",
                "5",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(output_mp4),
            ]
        proc2 = subprocess.run(
            fallback_cmd, capture_output=True, text=True, timeout=60, env=env, encoding="utf-8", errors="replace"
        )
        if proc2.returncode != 0:
            return False, (proc2.stderr or proc.stderr or "FFmpeg render failed")[-400:]
    return True, ""


async def run_clone_job(job_id: int) -> None:
    job = database.get_clone_job(job_id)
    if not job:
        return

    video = database.get_video(job["source_video_id"])
    product = database.get_product(job["product_id"]) if job.get("product_id") else None
    if not video:
        database.update_clone_job(job_id, status="failed", error_message="Không tìm thấy video gốc.")
        return

    reserved_flow_acc: Optional[Dict[str, Any]] = None
    try:
        is_flow_mode = str(job.get("clone_mode") or "").startswith("flow_")
        database.update_clone_job(job_id, status="analyzing", progress=15)

        if is_flow_mode:
            # Google Flow Multi-Scene Pipeline: follow rea-video Scene Units -> generate per-scene Ingredients clips -> stitch into 1 video
            flow_acc = flow_service.acquire_flow_account(job.get("flow_account_id"))
            if not flow_acc:
                database.update_clone_job(
                    job_id,
                    status="failed",
                    progress=20,
                    error_message="Chưa có tài khoản Google Flow (flow.google.com) nào đang Active hoặc còn hạn mức. Vui lòng bấm 'Đăng nhập Chrome' hoặc nhập Cookie/Key trong mục Clone Google Flow!",
                )
                return
            reserved_flow_acc = flow_acc

            mp4_path = video.get("local_path") or ""
            has_thumb = bool(video.get("thumbnail_url"))
            if (not mp4_path or not Path(mp4_path).exists()) and not has_thumb:
                try:
                    mp4_path, _ = await asyncio.wait_for(
                        asyncio.to_thread(_ensure_video_mp4_sync, video),
                        timeout=22.0,
                    )
                except Exception:
                    mp4_path = ""

            # Ensure rea-video 4-frame Vision breakdown + scene_units exist so Google Flow follows the exact rea-video plan
            bd_existing = video.get("rea_breakdown") if isinstance(video.get("rea_breakdown"), dict) else {}
            if not bd_existing.get("scene_units") and find_rea_video():
                database.update_clone_job(job_id, progress=20)
                rea_res = await decompose_video_with_rea(video["id"], force_vlm=False)
                if rea_res.get("ok") and rea_res.get("video"):
                    video = rea_res["video"]

            database.update_clone_job(job_id, progress=26)
            ffmpeg_bin_now = find_ffmpeg()
            chosen_flow_model = str(job.get("flow_model") or "omni_1_2_flash_10s_portrait")
            existing_scene_plan = job.get("scene_plan") if isinstance(job.get("scene_plan"), list) else []

            plan_bundle = await asyncio.to_thread(
                flow_service.build_flow_scene_plan_for_video,
                video["id"],
                job["clone_mode"],
                job.get("prompt_script") or "",
                ffmpeg_bin_now,
                chosen_flow_model,
                existing_scene_plan if existing_scene_plan else None,
            )
            ref_frame_path = str(plan_bundle.get("reference_frame_path") or "")
            ref_frame_url = str(plan_bundle.get("reference_frame_url") or "")
            scene_units = list(plan_bundle.get("scene_units") or [])
            veo_prompt = str(plan_bundle.get("veo_prompt") or job.get("veo_prompt") or video.get("title") or "")

            live_scene_plan: List[Dict[str, Any]] = []
            for idx_u, su in enumerate(scene_units, start=1):
                live_scene_plan.append(
                    {
                        **su,
                        "unit_index": idx_u,
                        "status": "pending",
                        "ref_url": su.get("ref_url") or ref_frame_url,
                        "clip_url": "",
                    }
                )

            clone_mode_val = str(job.get("clone_mode") or "flow_frames_start_end")
            acc_email_lbl = flow_acc.get("email") or flow_acc.get("label") or f"Acc #{flow_acc['id']}"
            if clone_mode_val in ("flow_frames_start_end", "flow_agent_auto", "flow_ai_frames_remake"):
                acc_display = f"🎨 AI Remake Đầu→Cuối · {len(live_scene_plan)} cảnh · {acc_email_lbl}"[:75]
            elif clone_mode_val == "flow_agent":
                acc_display = f"🤖 Flow Agent Remake · {len(live_scene_plan)} cảnh · {acc_email_lbl}"[:75]
            else:
                acc_display = (
                    f"🎨 Flow Remake ({len(live_scene_plan)} cảnh · {chosen_flow_model[:12]}) · {acc_email_lbl}"
                )[:75]
            database.update_clone_job(
                job_id,
                status="generating_muse",
                progress=32,
                flow_account_id=flow_acc["id"],
                muse_token_label=acc_display,
                tokens_spent=int(flow_acc.get("credits_spent_now") or 20) * max(1, len(live_scene_plan)),
                veo_prompt=veo_prompt,
                scene_plan=live_scene_plan,
            )

            def _on_engine_note(note: str) -> None:
                if note:
                    database.update_clone_job(job_id, muse_token_label=str(note)[:75])

            flow_raw_mp4 = OUTPUTS_DIR / f"flow_raw_{job_id}.mp4"
            ok_flow, err_flow = await flow_service.generate_multi_scene_video_via_flow(
                job_id=job_id,
                raw_acc=flow_acc,
                scene_plan=live_scene_plan,
                fallback_prompt=veo_prompt,
                flow_model=chosen_flow_model,
                clone_mode=clone_mode_val,
                ref_frame_path=ref_frame_path,
                ffmpeg_bin=ffmpeg_bin_now,
                dest_mp4=flow_raw_mp4,
                on_progress=lambda pct: database.update_clone_job(job_id, progress=int(pct)),
                on_scene_plan_update=lambda sp: database.update_clone_job(job_id, scene_plan=sp),
                on_engine_note=_on_engine_note,
            )
            if not ok_flow or not flow_raw_mp4.exists():
                database.update_flow_account(
                    int(flow_acc["id"]),
                    credits_remaining=int(flow_acc.get("credits_remaining") or 1000),
                    renders_used=max(0, int(flow_acc.get("renders_used") or 0)),
                )
                reserved_flow_acc = None
                database.update_clone_job(
                    job_id,
                    status="failed",
                    progress=45,
                    error_message=err_flow or "Google Flow không trả về video MP4.",
                )
                return

            reserved_flow_acc = None
            remake_source_mp4 = str(flow_raw_mp4)
        else:
            # Phase 1: Local shot-by-shot analysis (fast local mode without blocking VLM network calls)
            database.update_clone_job(job_id, status="analyzing", progress=20)
            if not video.get("rea_breakdown_json") and find_rea_video():
                rea_res = await decompose_video_with_rea(video["id"], force_vlm=False)
                if rea_res.get("ok") and rea_res.get("video"):
                    video = rea_res["video"]
            else:
                await asyncio.sleep(0.2)

            mp4_path = video.get("local_path") or ""
            if not mp4_path or not Path(mp4_path).exists():
                mp4_path, _ = await asyncio.to_thread(_ensure_video_mp4_sync, video)
                mp4_path = mp4_path or ""

            remake_source_mp4 = mp4_path

            # Phase 2: Acquire optional Muse Token or run Local rea-video Remake engine
            token = acquire_next_token()
            uses_muse_cloud = job["clone_mode"] in ("muse_prompt_remap", "muse_avatar_motion")
            if uses_muse_cloud and not token:
                database.update_clone_job(
                    job_id,
                    status="failed",
                    progress=25,
                    error_message="Kho Token Muse đã hết tài khoản Active hoặc chạm giới hạn tuần. Hãy chuyển chế độ rea-video Remake Local hoặc nạp thêm token!",
                )
                return

            database.update_clone_job(
                job_id,
                status="generating_muse",
                progress=55,
                muse_token_id=token["id"] if token else None,
                muse_token_label=token["label"] if token else "Local rea-video Engine",
                tokens_spent=token["tokens_spent_now"] if token else 0,
            )

            out_dir = REA_OUTPUTS_DIR / f"video_{video['id']}"
            rea_bin = find_rea_video()
            if job["clone_mode"] in ("rea_video_remake", "muse_prompt_remap") and rea_bin and out_dir.exists():
                def _try_remake() -> Optional[str]:
                    proc = subprocess.run(
                        [rea_bin, "remake", str(out_dir)],
                        capture_output=True,
                        text=True,
                        timeout=90,
                        env=crawler_service.build_tool_env(),
                        encoding="utf-8",
                        errors="replace",
                    )
                    if proc.returncode == 0:
                        for candidate in [out_dir / "remake" / "final.mp4", out_dir / "remake" / "remake.mp4"]:
                            if candidate.exists():
                                return str(candidate)
                    return None

                remade = await asyncio.to_thread(_try_remake)
                if remade:
                    remake_source_mp4 = remade
            else:
                await asyncio.sleep(0.2)

        # Phase 3: Render 100% Clean 9:16 Organic Viral MP4 (No Affiliate CTA Frames)
        database.update_clone_job(job_id, status="compositing_ffmpeg", progress=85)

        ffmpeg_bin = find_ffmpeg()
        if not ffmpeg_bin:
            database.update_clone_job(
                job_id,
                status="failed",
                progress=85,
                error_message="Không tìm thấy ffmpeg trên hệ thống.",
            )
            return

        output_mp4 = OUTPUTS_DIR / f"clone_{job_id}.mp4"
        hook_display = (job["prompt_script"].splitlines()[0] if job["prompt_script"] else video.get("hook_text") or "")[:110]

        hook_overlay_png: Optional[Path] = None
        if job.get("cta_position") == "hook_3s_only" and hook_display.strip():
            hook_overlay_png = OUTPUTS_DIR / f"hook_{job_id}.png"
            await asyncio.to_thread(_render_organic_hook_pill_png, hook_overlay_png, hook_display)

        ok, err = await asyncio.to_thread(
            _compose_organic_remake_video,
            ffmpeg_bin,
            remake_source_mp4,
            output_mp4,
            job["clone_mode"],
            bool(job["anti_duplicate"]),
            hook_overlay_png,
        )
        if not ok or not output_mp4.exists():
            database.update_clone_job(job_id, status="failed", progress=90, error_message=err or "Render thất bại")
            return

        platform_target = (
            "instagram_reels"
            if job["link_placement_mode"] == "bio_link"
            else "threads"
            if job["link_placement_mode"] == "threads_reply"
            else "facebook_reels"
        )
        pkg = publisher_service.build_affiliate_copy(product, platform_target, hook_display, video=video)

        database.update_clone_job(
            job_id,
            status="completed",
            progress=100,
            output_video_url=f"/media/outputs/{output_mp4.name}?v={int(time.time())}",
            generated_caption=pkg["caption"],
            generated_first_comment=pkg["first_comment"],
        )
    except BaseException as exc:
        if reserved_flow_acc is not None:
            try:
                database.update_flow_account(
                    int(reserved_flow_acc["id"]),
                    credits_remaining=int(reserved_flow_acc.get("credits_remaining") or 1000),
                    renders_used=max(0, int(reserved_flow_acc.get("renders_used") or 0)),
                )
            except BaseException:
                pass
        msg = (
            "Tiến trình bị huỷ khi máy chủ tải lại. Hãy bấm 'Chạy lại' để tiếp tục."
            if isinstance(exc, asyncio.CancelledError)
            else (str(exc)[:300] or "Lỗi không xác định khi xử lý Clone Job.")
        )
        database.update_clone_job(job_id, status="failed", error_message=msg)
        if isinstance(exc, asyncio.CancelledError):
            raise
