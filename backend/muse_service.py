import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

import database
import publisher_service

MEDIA_DIR = Path(__file__).resolve().parent / "media"
OUTPUTS_DIR = MEDIA_DIR / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

KNOWN_FFMPEG_PATHS = [
    shutil.which("ffmpeg"),
    r"C:\Users\Admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe",
]


def find_ffmpeg() -> Optional[str]:
    for p in KNOWN_FFMPEG_PATHS:
        if p and Path(p).exists():
            return str(p)
    return None


def _load_vn_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        [
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\tahoma.ttf",
        ]
        if bold
        else [
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


def _render_affiliate_overlay_png(
    output_png: Path,
    hook_text: str,
    product: Dict[str, Any],
    cta_position: str,
    link_placement_mode: str,
    clone_mode: str,
) -> None:
    """Render a crisp 720x1280 transparent PNG overlay with full Vietnamese UTF-8 CTA & hook."""
    width, height = 720, 1280
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_title = _load_vn_font(34, bold=True)
    font_sub = _load_vn_font(26, bold=True)
    font_small = _load_vn_font(22, bold=False)

    # Top Hook Banner
    draw.rounded_rectangle([(36, 70), (684, 240)], radius=24, fill=(15, 23, 42, 215), outline=(56, 189, 248, 220), width=3)
    draw.text((60, 88), "MUSE AI • VIRAL CLONE", font=font_small, fill=(56, 189, 248, 255))
    hook_lines = _wrap_text(draw, hook_text or product["name"], font_title, 590)
    y_cursor = 122
    for ln in hook_lines[:2]:
        draw.text((60, y_cursor), ln, font=font_title, fill=(255, 255, 255, 255))
        y_cursor += 42

    # Link destination label
    if link_placement_mode == "bio_link":
        cta_action = f"BẤM LINK BIO • TÌM MÃ #{product['code']}"
    elif link_placement_mode == "threads_reply":
        cta_action = f"XEM LINK TẠI REPLY ĐẦU • #{product['code']}"
    else:
        cta_action = f"BẤM LINK Ở BÌNH LUẬN ĐẦU TIÊN • #{product['code']}"

    # Product CTA Card position
    card_y1 = 960 if cta_position != "top_pill" else 270
    card_y2 = card_y1 + 215

    draw.rounded_rectangle(
        [(36, card_y1), (684, card_y2)],
        radius=26,
        fill=(17, 24, 39, 235),
        outline=(249, 115, 22, 255),
        width=4,
    )
    # Price badge
    draw.rounded_rectangle([(56, card_y1 + 20), (270, card_y1 + 72)], radius=14, fill=(234, 88, 12, 255))
    draw.text((74, card_y1 + 31), f"GIÁ {product['price']}", font=font_sub, fill=(255, 255, 255, 255))

    # Platform pill
    draw.rounded_rectangle([(286, card_y1 + 20), (500, card_y1 + 72)], radius=14, fill=(30, 41, 59, 255))
    draw.text((306, card_y1 + 32), f"{product['platform_name']} Mall", font=font_small, fill=(148, 163, 184, 255))

    prod_lines = _wrap_text(draw, product["name"], font_sub, 600)
    py = card_y1 + 88
    for ln in prod_lines[:2]:
        draw.text((56, py), ln, font=font_sub, fill=(248, 250, 252, 255))
        py += 32

    draw.rounded_rectangle([(56, card_y2 - 54), (664, card_y2 - 14)], radius=12, fill=(16, 185, 129, 230))
    draw.text((74, card_y2 - 46), cta_action, font=font_small, fill=(6, 78, 59, 255))

    # Subtle bottom watermark tag showing mode
    draw.text((48, 1225), f"Mode: {clone_mode} • Anti-Duplicate Ready", font=font_small, fill=(203, 213, 225, 200))
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


def _compose_ffmpeg_video(
    ffmpeg_bin: str,
    source_local_path: str,
    overlay_png: Path,
    output_mp4: Path,
    anti_duplicate: bool,
) -> Tuple[bool, str]:
    """Render a real playable 9:16 720x1280 H.264/AAC MP4 video using FFmpeg."""
    has_source = bool(source_local_path and Path(source_local_path).exists())
    if has_source:
        eq_filter = ",eq=contrast=1.04:saturation=1.06:brightness=0.01" if anti_duplicate else ""
        filter_complex = (
            f"[0:v]scale=720:1280:force_original_aspect_ratio=increase,"
            f"crop=720:1280{eq_filter}[bg];"
            f"[bg][1:v]overlay=0:0:format=auto[vout]"
        )
        cmd = [
            ffmpeg_bin,
            "-y",
            "-t",
            "15",
            "-i",
            source_local_path,
            "-i",
            str(overlay_png),
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
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(output_mp4),
        ]
    else:
        # Synthesize a sleek animated 9:16 6s demo preview video with silent/tone AAC audio
        filter_complex = (
            "[0:v][1:v]overlay=0:0:format=auto[vout]"
        )
        cmd = [
            ffmpeg_bin,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "gradients=s=720x1280:r=25:d=6:c0=0f172a:c1=1e1b4b:c2=312e81:speed=0.4",
            "-i",
            str(overlay_png),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-filter_complex",
            filter_complex,
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
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output_mp4),
        ]

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        # Fallback to simplest color source if gradients filter is unavailable
        fallback_cmd = [
            ffmpeg_bin,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x0f172a:s=720x1280:d=5:r=25",
            "-i",
            str(overlay_png),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-filter_complex",
            "[0:v][1:v]overlay=0:0[vout]",
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
        proc2 = subprocess.run(fallback_cmd, capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace")
        if proc2.returncode != 0:
            return False, (proc2.stderr or proc.stderr or "FFmpeg render failed")[-400:]
    return True, ""


async def run_clone_job(job_id: int) -> None:
    job = database.get_clone_job(job_id)
    if not job:
        return

    video = database.get_video(job["source_video_id"])
    product = database.get_product(job["product_id"])
    if not video or not product:
        database.update_clone_job(job_id, status="failed", error_message="Không tìm thấy video gốc hoặc sản phẩm.")
        return

    try:
        # Phase 1: Analyzing script & hook
        database.update_clone_job(job_id, status="analyzing", progress=20)
        await asyncio.sleep(0.5)

        # Phase 2: Acquire Muse Token from Pool & simulate/run Muse generation stage
        token = acquire_next_token()
        if not token:
            database.update_clone_job(
                job_id,
                status="failed",
                progress=25,
                error_message="Kho Token Muse đã hết tài khoản Active hoặc chạm giới hạn tuần. Hãy nạp thêm token!",
            )
            return

        database.update_clone_job(
            job_id,
            status="generating_muse",
            progress=55,
            muse_token_id=token["id"],
            muse_token_label=token["label"],
            tokens_spent=token["tokens_spent_now"],
        )
        await asyncio.sleep(0.7)

        # Phase 3: Compositing Affiliate CTA Overlay + Anti-Duplicate with FFmpeg
        database.update_clone_job(job_id, status="compositing_ffmpeg", progress=85)

        ffmpeg_bin = find_ffmpeg()
        if not ffmpeg_bin:
            database.update_clone_job(
                job_id,
                status="failed",
                progress=85,
                error_message="Không tìm thấy ffmpeg.exe trên hệ thống.",
            )
            return

        overlay_png = OUTPUTS_DIR / f"overlay_{job_id}.png"
        output_mp4 = OUTPUTS_DIR / f"clone_{job_id}.mp4"
        hook_display = (job["prompt_script"].splitlines()[0] if job["prompt_script"] else video["hook_text"])[:110]

        await asyncio.to_thread(
            _render_affiliate_overlay_png,
            overlay_png,
            hook_display,
            product,
            job["cta_position"],
            job["link_placement_mode"],
            job["clone_mode"],
        )

        ok, err = await asyncio.to_thread(
            _compose_ffmpeg_video,
            ffmpeg_bin,
            video.get("local_path", ""),
            overlay_png,
            output_mp4,
            bool(job["anti_duplicate"]),
        )
        if not ok or not output_mp4.exists():
            database.update_clone_job(job_id, status="failed", progress=90, error_message=err or "Render thất bại")
            return

        # Prepare smart Affiliate caption & first comment
        platform_target = (
            "instagram_reels"
            if job["link_placement_mode"] == "bio_link"
            else "threads"
            if job["link_placement_mode"] == "threads_reply"
            else "facebook_reels"
        )
        pkg = publisher_service.build_affiliate_copy(product, platform_target, hook_display)

        database.update_clone_job(
            job_id,
            status="completed",
            progress=100,
            output_video_url=f"/media/outputs/{output_mp4.name}",
            generated_caption=pkg["caption"],
            generated_first_comment=pkg["first_comment"],
        )
    except Exception as exc:
        database.update_clone_job(job_id, status="failed", error_message=str(exc)[:300])
