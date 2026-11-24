from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent / "clonevideo.db"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS viral_videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                title TEXT NOT NULL,
                caption TEXT NOT NULL,
                author TEXT NOT NULL,
                source_url TEXT NOT NULL,
                video_url TEXT DEFAULT '',
                thumbnail_url TEXT DEFAULT '',
                local_path TEXT DEFAULT '',
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                viral_score INTEGER DEFAULT 0,
                sales_signals TEXT DEFAULT '[]',
                hook_text TEXT DEFAULT '',
                script_summary TEXT DEFAULT '',
                rea_breakdown_json TEXT DEFAULT '',
                rea_report_url TEXT DEFAULT '',
                market_intel_json TEXT DEFAULT '',
                shop_name TEXT DEFAULT '',
                shop_url TEXT DEFAULT '',
                product_url TEXT DEFAULT '',
                selling_price TEXT DEFAULT '',
                original_price TEXT DEFAULT '',
                meta_library_id TEXT DEFAULT '',
                meta_page_id TEXT DEFAULT '',
                ig_handle TEXT DEFAULT '',
                ad_placements TEXT DEFAULT '[]',
                cta_text TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )

        # Safe column migration for existing SQLite databases
        for col_def in [
            "rea_breakdown_json TEXT DEFAULT ''",
            "rea_report_url TEXT DEFAULT ''",
            "market_intel_json TEXT DEFAULT ''",
            "shop_name TEXT DEFAULT ''",
            "shop_url TEXT DEFAULT ''",
            "product_url TEXT DEFAULT ''",
            "selling_price TEXT DEFAULT ''",
            "original_price TEXT DEFAULT ''",
            "meta_library_id TEXT DEFAULT ''",
            "meta_page_id TEXT DEFAULT ''",
            "ig_handle TEXT DEFAULT ''",
            "ad_placements TEXT DEFAULT '[]'",
            "cta_text TEXT DEFAULT ''",
        ]:
            try:
                cur.execute(f"ALTER TABLE viral_videos ADD COLUMN {col_def}")
            except sqlite3.OperationalError:
                pass

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS meta_shops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_key TEXT NOT NULL UNIQUE,
                page_id TEXT DEFAULT '',
                shop_name TEXT NOT NULL,
                ig_handle TEXT DEFAULT '',
                page_url TEXT DEFAULT '',
                shop_url TEXT DEFAULT '',
                domain TEXT DEFAULT '',
                avatar_url TEXT DEFAULT '',
                ad_library_url TEXT DEFAULT '',
                active_ads_count INTEGER DEFAULT 0,
                products_count INTEGER DEFAULT 0,
                price_range TEXT DEFAULT '',
                placements_json TEXT DEFAULT '[]',
                country TEXT DEFAULT 'VN',
                is_inbox_only INTEGER DEFAULT 0,
                last_scanned_at TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS meta_shop_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id INTEGER NOT NULL,
                product_key TEXT NOT NULL UNIQUE,
                library_id TEXT DEFAULT '',
                product_title TEXT NOT NULL,
                caption TEXT DEFAULT '',
                product_url TEXT DEFAULT '',
                shop_url TEXT DEFAULT '',
                selling_price TEXT DEFAULT '',
                original_price TEXT DEFAULT '',
                video_url TEXT DEFAULT '',
                thumbnail_url TEXT DEFAULT '',
                cta_text TEXT DEFAULT '',
                ads_duplication_count INTEGER DEFAULT 1,
                video_age_days INTEGER DEFAULT 1,
                started_running_at TEXT DEFAULT '',
                placements_json TEXT DEFAULT '[]',
                created_at TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS muse_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                account_identifier TEXT NOT NULL,
                auth_token TEXT NOT NULL,
                proxy TEXT DEFAULT '',
                tokens_remaining INTEGER DEFAULT 1000000000,
                tokens_total INTEGER DEFAULT 1000000000,
                weekly_used INTEGER DEFAULT 0,
                weekly_limit INTEGER DEFAULT 50,
                status TEXT DEFAULT 'active',
                last_used_at TEXT DEFAULT '',
                notes TEXT DEFAULT ''
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS affiliate_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                platform_name TEXT NOT NULL,
                price TEXT NOT NULL,
                original_price TEXT DEFAULT '',
                affiliate_url TEXT NOT NULL,
                image_url TEXT DEFAULT '',
                cta_overlay_text TEXT DEFAULT '',
                comment_template TEXT DEFAULT '',
                bio_active INTEGER DEFAULT 1,
                clicks_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS flow_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                email TEXT DEFAULT '',
                tier TEXT DEFAULT 'Flow Pro',
                auth_mode TEXT DEFAULT 'browser_profile',
                profile_dir TEXT DEFAULT '',
                cookies_json TEXT DEFAULT '',
                bearer_token TEXT DEFAULT '',
                project_url TEXT DEFAULT 'https://flow.google.com/',
                proxy TEXT DEFAULT '',
                credits_remaining INTEGER DEFAULT 1000,
                credits_total INTEGER DEFAULT 1000,
                renders_used INTEGER DEFAULT 0,
                weekly_limit INTEGER DEFAULT 50,
                status TEXT DEFAULT 'login_pending',
                last_used_at TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS clone_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_video_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                muse_token_id INTEGER DEFAULT NULL,
                muse_token_label TEXT DEFAULT '',
                flow_account_id INTEGER DEFAULT NULL,
                flow_model TEXT DEFAULT '',
                veo_prompt TEXT DEFAULT '',
                scene_plan_json TEXT DEFAULT '',
                clone_mode TEXT NOT NULL,
                prompt_script TEXT NOT NULL,
                cta_position TEXT DEFAULT 'bottom_banner',
                link_placement_mode TEXT DEFAULT 'both',
                anti_duplicate INTEGER DEFAULT 1,
                status TEXT DEFAULT 'queued',
                progress INTEGER DEFAULT 0,
                output_video_url TEXT DEFAULT '',
                generated_caption TEXT DEFAULT '',
                generated_first_comment TEXT DEFAULT '',
                tokens_spent INTEGER DEFAULT 0,
                error_message TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )

        for cj_col in [
            "flow_account_id INTEGER DEFAULT NULL",
            "flow_model TEXT DEFAULT ''",
            "veo_prompt TEXT DEFAULT ''",
            "scene_plan_json TEXT DEFAULT ''",
        ]:
            try:
                cur.execute(f"ALTER TABLE clone_jobs ADD COLUMN {cj_col}")
            except sqlite3.OperationalError:
                pass

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS publish_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clone_job_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                target_platform TEXT NOT NULL,
                account_name TEXT NOT NULL,
                caption TEXT NOT NULL,
                link_strategy TEXT NOT NULL,
                first_comment_text TEXT DEFAULT '',
                bio_url_synced INTEGER DEFAULT 1,
                status TEXT DEFAULT 'scheduled',
                published_url TEXT DEFAULT '',
                comment_url TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )

        _seed_if_empty(conn)

        # Ensure new settings keys exist for both fresh and existing DBs
        default_extra_settings = [
            ("rea_vlm_enabled", "0"),
            ("rea_vlm_base_url", "https://api.openai.com/v1"),
            ("rea_vlm_api_key", ""),
            ("rea_vlm_model", "gemini-2.5-pro,gpt-4o"),
            ("rea_report_lang", "en"),
        ]
        cur.executemany(
            "INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)",
            default_extra_settings,
        )
        _run_meta_ecosystem_focus_cleanup(conn)


def _run_meta_ecosystem_focus_cleanup(conn: sqlite3.Connection) -> None:
    """One-time cleanup to focus workspace strictly on Meta Ads + FB + IG + Threads and remove polluted cross-copied shop data."""
    cur = conn.cursor()
    done_row = cur.execute(
        "SELECT value FROM app_settings WHERE key = 'meta_ecosystem_focus_v1'"
    ).fetchone()
    if done_row and done_row[0] == "1":
        return

    # Keep any video referenced by clone_jobs so job history never breaks
    ref_ids = {
        int(r[0])
        for r in cur.execute("SELECT DISTINCT source_video_id FROM clone_jobs WHERE source_video_id IS NOT NULL").fetchall()
        if r[0] is not None
    }
    rows = cur.execute(
        "SELECT id, platform, sales_signals, market_intel_json, ad_placements FROM viral_videos"
    ).fetchall()
    allowed_pf = {"meta_ads", "facebook", "instagram", "threads"}

    for r in rows:
        vid = int(r["id"])
        pf = str(r["platform"] or "").lower().strip()
        if pf not in allowed_pf and vid not in ref_ids:
            cur.execute("DELETE FROM viral_videos WHERE id = ?", (vid,))
            continue

        # Clear legacy polluted cross-copied market_intel_json & fake shop signals on remaining rows
        sigs_raw = r["sales_signals"] or "[]"
        try:
            sigs = [
                s for s in json.loads(sigs_raw)
                if not str(s).startswith(("Shop bán:", "Giá: VND", "Giá: $11.99", "Giá: 440,000đ"))
            ]
        except Exception:
            sigs = []

        placements_raw = r["ad_placements"] or "[]"
        try:
            pl_list = json.loads(placements_raw)
        except Exception:
            pl_list = []
        if not pl_list and pf in {"facebook", "instagram", "threads"}:
            pl_list = [pf]
        elif not pl_list and pf == "meta_ads":
            pl_list = ["facebook", "instagram"]

        cur.execute(
            """
            UPDATE viral_videos
            SET market_intel_json = '',
                sales_signals = ?,
                ad_placements = ?
            WHERE id = ?
            """,
            (json.dumps(sigs, ensure_ascii=False), json.dumps(pl_list, ensure_ascii=False), vid),
        )

    cur.execute(
        "INSERT OR REPLACE INTO app_settings (key, value) VALUES ('meta_ecosystem_focus_v1', '1')"
    )


def _seed_if_empty(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    now = utc_now_iso()

    if cur.execute("SELECT COUNT(*) FROM viral_videos").fetchone()[0] == 0:
        videos = [
            (
                "instagram",
                "Unbox Máy Ép Chậm Mini 30 Giây - Ép Kiệt Bã 98%",
                "Sáng nào cũng 1 ly nước ép cần tây táo xanh chỉ tốn 30 giây rửa máy! Giá đang sale sập sàn, xem mã #SP01 trên link Bio nhé cả nhà ơi 🔥 #mayepcham #giadungthongminh #reels",
                "@linh.review.nhacua",
                "https://www.instagram.com/reel/C8DemoAff01/",
                "",
                "https://images.unsplash.com/photo-1622597467836-f3285f2131b8?auto=format&fit=crop&w=600&q=80",
                "",
                482000,
                28400,
                1420,
                3910,
                96,
                json.dumps(["Link ở Bio", "Mã #SP01", "Sale 45%", "Unbox cận cảnh"], ensure_ascii=False),
                "Đừng mua máy ép cồng kềnh nữa nếu bạn chưa xem con mini tháo lắp 3 giây này!",
                "Hook (0-3s): Bỏ quả táo vào máy ép mini siêu gọn.\nBody (3-11s): So sánh bã khô kiệt vs máy thường, xối nước rửa sạch trong 5s.\nCTA (11-15s): Chốt đơn mã #SP01 tại Link Bio để nhận voucher 45%.",
                now,
            ),
            (
                "meta_ads",
                "[Ad Library] Tai Nghe ANC Pro Pin 40 Giờ - Test Chống Ồn Quán Cafe",
                "Đang chạy 14 ngày liên tục | Đeo tai nghe này giữa quán cafe ồn ào mà im phăng phắc như phòng thu! Deal hời hôm nay chỉ còn 299k, bấm xem ngay dưới bình luận 👇",
                "TechGear Official Ads",
                "https://www.facebook.com/ads/library/?id=998877661",
                "",
                "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?auto=format&fit=crop&w=600&q=80",
                "",
                890000,
                41200,
                3180,
                5600,
                98,
                json.dumps(["Active Ad 14 ngày", "Comment Link", "Chỉ 299k", "Test thực tế"], ensure_ascii=False),
                "Test độ chống ồn 45dB giữa ngã tư giờ tan tầm — nghe không lọt 1 tiếng còi xe!",
                "Hook (0-3s): Đứng giữa ngã tư ồn ào, bật chế độ ANC âm thanh tắt phụt.\nBody (3-12s): Mic lọc gió gọi điện rõ nét, hộp sạc màn hình LED báo % pin.\nCTA (12-15s): Link mua chính hãng kèm freeship mình ghim ở bình luận đầu tiên!",
                now,
            ),
            (
                "facebook",
                "Setup Bàn Làm Việc & Đèn LED RGB Livestream Chống Cận",
                "Chỉ hơn 100k mà biến góc bàn làm việc u tối thành studio triệu view! Ai hay quay TikTok/Reels chốt liền kẻo hết mã giảm giá dưới cmt nha 💥",
                "Minh Decor Setup",
                "https://www.facebook.com/reel/10293847561",
                "",
                "https://images.unsplash.com/photo-1593640408182-31c70c8268f5?auto=format&fit=crop&w=600&q=80",
                "",
                315000,
                16700,
                980,
                2150,
                91,
                json.dumps(["Giá 100k+", "Link ở Comment", "Before/After"], ensure_ascii=False),
                "Biến góc phòng trọ 10m2 thành studio quay video triệu view chỉ với 1 cây đèn!",
                "Hook (0-3s): Tắt đèn phòng tối om -> Bật đèn RGB studio sáng bừng mịn da.\nBody (3-11s): Chỉnh 3 nhiệt độ màu + app đổi màu RGB theo nhạc.\nCTA (11-15s): Bấm link Shopee ở bình luận đầu tiên đang trợ giá 50%.",
                now,
            ),
            (
                "threads",
                "Thread Review: Top 3 Món Gia Dụng Dưới 200k Đáng Tiền Nhất Tháng",
                "Mình test hơn 20 món đồ decor trên Shopee rồi, đây là 3 món dùng mỗi ngày không phí 1 xu. Video demo chi tiết bên dưới, link từng món mình để ở reply đầu nha ✨",
                "@trang.decor.daily",
                "https://www.threads.net/@trang.decor.daily/post/C9DemoThread04",
                "",
                "https://images.unsplash.com/photo-1556911220-bff31c812dba?auto=format&fit=crop&w=600&q=80",
                "",
                194000,
                12300,
                840,
                1720,
                89,
                json.dumps(["Reply Link", "Top 3 Review", "Dưới 200k"], ensure_ascii=False),
                "3 món dưới 200k giúp căn bếp gọn gàng gấp 5 lần — món số 2 ai cũng cần!",
                "Hook (0-3s): Cảnh tủ bếp lộn xộn vs sau khi gắn kệ xoay 360.\nBody (3-11s): Quay nhanh 3 góc sử dụng thực tế mỗi sáng.\nCTA (11-15s): Link mua chuẩn shop Mall ở ngay Thread Reply bên dưới.",
                now,
            ),
            (
                "instagram",
                "Nồi Chiên Không Dầu Mini Trong Suốt — Nhìn Thấy Đồ Ăn Chín Giòn",
                "Từ ngày có em nồi lòng kính trong suốt này không bao giờ lo cháy khét nữa! Đang có deal flash sale 48%, tìm mã #SP01 hoặc #SP04 trong Bio nha 🥰",
                "@bepnha.hana",
                "https://www.instagram.com/reel/C9DemoKitchen05/",
                "",
                "https://images.unsplash.com/photo-1585515320310-259814833e62?auto=format&fit=crop&w=600&q=80",
                "",
                620000,
                35900,
                1950,
                4800,
                95,
                json.dumps(["Flash Sale 48%", "Link Bio", "Lòng kính trong suốt"], ensure_ascii=False),
                "Tại sao 90% người mới nấu ăn chuyển sang nồi chiên lòng kính trong suốt?",
                "Hook (0-3s): Zoom cận cảnh gà nướng vàng giòn sủi bọt qua lớp kính.\nBody (3-11s): Không cần mở nồi kiểm tra, không ám mùi nhựa.\nCTA (11-15s): Check ngay link Bio đầu trang lấy mã giảm độc quyền.",
                now,
            ),
            (
                "meta_ads",
                "[Ad Library] Bàn Chải Điện Sóng Âm Tặng 4 Đầu Thay — Deal 199k",
                "Chạy scale 8 page | Răng sạch mảng bám sau 7 ngày, chống nước IPX7 tắm rửa thoải mái. Nhấn nút mua hoặc xem link ghim dưới bình luận!",
                "SmileCare Vietnam",
                "https://www.facebook.com/ads/library/?id=554433221",
                "",
                "https://images.unsplash.com/photo-1559591937-abc501f98600?auto=format&fit=crop&w=600&q=80",
                "",
                530000,
                22100,
                1670,
                2890,
                93,
                json.dumps(["Scale 8 Page", "Tặng 4 đầu", "Comment Link"], ensure_ascii=False),
                "Đừng đánh răng bằng bàn chải thường nữa — thử nghiệm làm sạch hạt ngô trong 10 giây!",
                "Hook (0-3s): Rung sóng âm 42.000 lần/phút đánh bay vết cà phê trên bắp ngô.\nBody (3-11s): Ngâm nước trực tiếp, pin dùng 60 ngày mới sạc 1 lần.\nCTA (11-15s): Đặt ngay ở link bình luận để được tặng kèm 4 đầu thay.",
                now,
            ),
        ]
        cur.executemany(
            """
            INSERT INTO viral_videos (
                platform, title, caption, author, source_url, video_url, thumbnail_url,
                local_path, views, likes, comments, shares, viral_score, sales_signals,
                hook_text, script_summary, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            videos,
        )

    if cur.execute("SELECT COUNT(*) FROM muse_tokens").fetchone()[0] == 0:
        tokens = [
            (
                "Muse_Acc_US_01 (1B Pool)",
                "muse_aff_us01@proton.me",
                "muse_sess_demo_token_us01_1000000000_x9a8b7c6",
                "http://103.145.x.x:8080",
                984500000,
                1000000000,
                4,
                50,
                "active",
                now,
                "Tài khoản US Invite 1 tỷ token - ưu tiên render scene 9:16",
            ),
            (
                "Muse_Acc_US_02 (1B Pool)",
                "muse_aff_us02@gmail.com",
                "muse_sess_demo_token_us02_1000000000_k3m4n5p6",
                "http://103.145.x.x:8081",
                996200000,
                1000000000,
                1,
                50,
                "active",
                now,
                "Tài khoản backup rotation tự động",
            ),
            (
                "Muse_Acc_CA_03 (1B Pool)",
                "muse_aff_ca03@outlook.com",
                "muse_sess_demo_token_ca03_1000000000_q1w2e3r4",
                "",
                1000000000,
                1000000000,
                0,
                50,
                "active",
                "",
                "Tài khoản mới chưa dùng trong tuần",
            ),
        ]
        cur.executemany(
            """
            INSERT INTO muse_tokens (
                label, account_identifier, auth_token, proxy, tokens_remaining,
                tokens_total, weekly_used, weekly_limit, status, last_used_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            tokens,
        )

    if cur.execute("SELECT COUNT(*) FROM affiliate_products").fetchone()[0] == 0:
        products = [
            (
                "SP01",
                "Máy Ép Chậm Mini Kalite KL-531 Siêu Gọn",
                "Shopee",
                "489.000đ",
                "890.000đ",
                "https://shope.ee/aff-kalite-sp01-demo",
                "https://images.unsplash.com/photo-1622597467836-f3285f2131b8?auto=format&fit=crop&w=400&q=80",
                "MÃ #SP01 • SALE 45% • LINK Ở CMT / BIO",
                "🛒 Mua Máy Ép Chậm Kalite chính hãng (Sale 45% còn 489k) tại đây nhé cả nhà: {affiliate_url} 👇",
                1,
                1248,
                now,
            ),
            (
                "SP02",
                "Tai Nghe Bluetooth ANC Pro Chống Ồn 45dB",
                "TikTok Shop",
                "299.000đ",
                "590.000đ",
                "https://vt.tiktok.com/aff-anc-pro-sp02-demo",
                "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?auto=format&fit=crop&w=400&q=80",
                "MÃ #SP02 • CHỈ 299K • FREESHIP TOÀN QUỐC",
                "🎧 Link săn Tai Nghe ANC Pro chính hãng chỉ 299k + Freeship ở đây nha: {affiliate_url} 🔥",
                1,
                892,
                now,
            ),
            (
                "SP03",
                "Đèn LED Livestream RGB Studio Kèm Tripod 2m",
                "Shopee",
                "165.000đ",
                "320.000đ",
                "https://shope.ee/aff-led-rgb-sp03-demo",
                "https://images.unsplash.com/photo-1593640408182-31c70c8268f5?auto=format&fit=crop&w=400&q=80",
                "MÃ #SP03 • COMBO ĐÈN + CHÂN 165K",
                "💡 Combo Đèn LED Livestream + Tripod 2m đang trợ giá còn 165k: {affiliate_url} ✨",
                1,
                634,
                now,
            ),
        ]
        cur.executemany(
            """
            INSERT INTO affiliate_products (
                code, name, platform_name, price, original_price, affiliate_url,
                image_url, cta_overlay_text, comment_template, bio_active, clicks_count, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            products,
        )

    if cur.execute("SELECT COUNT(*) FROM app_settings").fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO app_settings (key, value) VALUES (?, ?)",
            [
                ("treg_api_key", ""),
                ("bio_brand_name", "Deal Ngon Mỗi Ngày • Review Thật"),
                ("bio_brand_subtitle", "Tìm đúng mã #SP01, #SP02... trong video để nhận giá Sale chính hãng"),
                ("default_crawl_country", "VN"),
            ],
        )


def _row_to_video(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    try:
        d["sales_signals"] = json.loads(d.get("sales_signals") or "[]")
    except json.JSONDecodeError:
        d["sales_signals"] = []
    try:
        raw_pl = json.loads(d.get("ad_placements") or "[]")
        d["ad_placements"] = [str(x).lower() for x in raw_pl] if isinstance(raw_pl, list) else []
    except json.JSONDecodeError:
        d["ad_placements"] = []
    raw_rea = d.get("rea_breakdown_json") or ""
    if raw_rea:
        try:
            d["rea_breakdown"] = json.loads(raw_rea)
        except json.JSONDecodeError:
            d["rea_breakdown"] = None
    else:
        d["rea_breakdown"] = None
    raw_intel = d.get("market_intel_json") or ""
    if raw_intel:
        try:
            d["market_intel"] = json.loads(raw_intel)
        except json.JSONDecodeError:
            d["market_intel"] = None
    else:
        d["market_intel"] = None
    return d


def list_videos(platform: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        query = "SELECT * FROM viral_videos WHERE 1=1"
        params: List[Any] = []
        if platform and platform != "all":
            pf_low = platform.strip().lower()
            if pf_low in {"facebook", "instagram", "threads"}:
                query += " AND (platform = ? OR LOWER(ad_placements) LIKE ?)"
                params.extend([pf_low, f'%"{pf_low}"%'])
            elif pf_low == "meta_ads":
                query += " AND (platform = 'meta_ads' OR COALESCE(meta_library_id, '') != '')"
            else:
                query += " AND platform = ?"
                params.append(pf_low)
        if search:
            query += (
                " AND (title LIKE ? OR caption LIKE ? OR hook_text LIKE ? "
                "OR author LIKE ? OR shop_name LIKE ? OR shop_url LIKE ? OR product_url LIKE ?)"
            )
            like = f"%{search}%"
            params.extend([like, like, like, like, like, like, like])
        query += " ORDER BY viral_score DESC, id DESC"
        rows = conn.execute(query, params).fetchall()
        return [_row_to_video(r) for r in rows]


def get_video(video_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM viral_videos WHERE id = ?", (video_id,)).fetchone()
        return _row_to_video(row) if row else None


def update_video(video_id: int, **fields: Any) -> Optional[Dict[str, Any]]:
    if not fields:
        return get_video(video_id)
    keys = ", ".join(f"{k} = ?" for k in fields.keys())
    values = list(fields.values()) + [video_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE viral_videos SET {keys} WHERE id = ?", values)
        row = conn.execute("SELECT * FROM viral_videos WHERE id = ?", (video_id,)).fetchone()
        return _row_to_video(row) if row else None


def insert_video(data: Dict[str, Any]) -> Dict[str, Any]:
    market_intel_raw = data.get("market_intel_json") or ""
    if not market_intel_raw and isinstance(data.get("market_intel"), dict):
        market_intel_raw = json.dumps(data["market_intel"], ensure_ascii=False)
    placements_val = data.get("ad_placements") or []
    if isinstance(placements_val, str):
        placements_raw = placements_val
    else:
        placements_raw = json.dumps([str(x).lower() for x in placements_val if x], ensure_ascii=False)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO viral_videos (
                platform, title, caption, author, source_url, video_url, thumbnail_url,
                local_path, views, likes, comments, shares, viral_score, sales_signals,
                hook_text, script_summary, market_intel_json,
                shop_name, shop_url, product_url, selling_price, original_price,
                meta_library_id, meta_page_id, ig_handle, ad_placements, cta_text,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["platform"],
                data["title"],
                data["caption"],
                data["author"],
                data["source_url"],
                data.get("video_url", ""),
                data.get("thumbnail_url", ""),
                data.get("local_path", ""),
                int(data.get("views", 0)),
                int(data.get("likes", 0)),
                int(data.get("comments", 0)),
                int(data.get("shares", 0)),
                int(data.get("viral_score", 75)),
                json.dumps(data.get("sales_signals", []), ensure_ascii=False),
                data.get("hook_text", ""),
                data.get("script_summary", ""),
                market_intel_raw,
                str(data.get("shop_name") or ""),
                str(data.get("shop_url") or ""),
                str(data.get("product_url") or ""),
                str(data.get("selling_price") or ""),
                str(data.get("original_price") or ""),
                str(data.get("meta_library_id") or ""),
                str(data.get("meta_page_id") or ""),
                str(data.get("ig_handle") or ""),
                placements_raw,
                str(data.get("cta_text") or ""),
                utc_now_iso(),
            ),
        )
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM viral_videos WHERE id = ?", (new_id,)).fetchone()
        return _row_to_video(row)


def list_muse_tokens() -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM muse_tokens ORDER BY id DESC").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            tok = d["auth_token"]
            d["auth_token_masked"] = (tok[:10] + "..." + tok[-6:]) if len(tok) > 18 else "****"
            result.append(d)
        return result


def get_muse_token(token_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM muse_tokens WHERE id = ?", (token_id,)).fetchone()
        return dict(row) if row else None


def insert_muse_tokens_bulk(items: List[Dict[str, Any]]) -> int:
    with get_conn() as conn:
        conn.executemany(
            """
            INSERT INTO muse_tokens (
                label, account_identifier, auth_token, proxy, tokens_remaining,
                tokens_total, weekly_used, weekly_limit, status, last_used_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item["label"],
                    item.get("account_identifier", item["label"]),
                    item["auth_token"],
                    item.get("proxy", ""),
                    int(item.get("tokens_remaining", 1000000000)),
                    int(item.get("tokens_total", 1000000000)),
                    int(item.get("weekly_used", 0)),
                    int(item.get("weekly_limit", 50)),
                    item.get("status", "active"),
                    "",
                    item.get("notes", "Bulk imported"),
                )
                for item in items
            ],
        )
        return len(items)


def toggle_muse_token_status(token_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM muse_tokens WHERE id = ?", (token_id,)).fetchone()
        if not row:
            return None
        next_status = "cooldown" if row["status"] == "active" else "active"
        conn.execute("UPDATE muse_tokens SET status = ? WHERE id = ?", (next_status, token_id))
        updated = conn.execute("SELECT * FROM muse_tokens WHERE id = ?", (token_id,)).fetchone()
        d = dict(updated)
        tok = d["auth_token"]
        d["auth_token_masked"] = (tok[:10] + "..." + tok[-6:]) if len(tok) > 18 else "****"
        return d


def delete_muse_token(token_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM muse_tokens WHERE id = ?", (token_id,))
        return cur.rowcount > 0


def _format_flow_account_public(row: sqlite3.Row | Dict[str, Any]) -> Dict[str, Any]:
    d = dict(row)
    bearer = str(d.pop("bearer_token", "") or "")
    cookies_raw = str(d.pop("cookies_json", "") or "")
    cookie_count = 0
    if cookies_raw:
        try:
            arr = json.loads(cookies_raw)
            if isinstance(arr, list):
                cookie_count = len(arr)
        except Exception:
            cookie_count = 0
    if bearer:
        d["credential_masked"] = (bearer[:10] + "..." + bearer[-6:]) if len(bearer) > 18 else "****"
    elif cookie_count > 0:
        d["credential_masked"] = f"{cookie_count} Google cookies"
    elif d.get("profile_dir"):
        d["credential_masked"] = "Chrome Profile"
    else:
        d["credential_masked"] = "Chưa xác thực"
    d["has_cookies"] = cookie_count > 0
    d["cookie_count"] = cookie_count
    d["has_bearer"] = bool(bearer)
    d["has_profile"] = bool(d.get("profile_dir"))
    return d


def list_flow_accounts() -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM flow_accounts ORDER BY id DESC").fetchall()
        return [_format_flow_account_public(r) for r in rows]


def get_flow_account(account_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM flow_accounts WHERE id = ?", (account_id,)).fetchone()
        return dict(row) if row else None


def create_flow_account(data: Dict[str, Any]) -> Dict[str, Any]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO flow_accounts (
                label, email, tier, auth_mode, profile_dir, cookies_json, bearer_token,
                project_url, proxy, credits_remaining, credits_total, renders_used,
                weekly_limit, status, last_used_at, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(data.get("label") or "Flow Account")[:80],
                str(data.get("email") or "")[:120],
                str(data.get("tier") or "Flow Pro")[:40],
                str(data.get("auth_mode") or "browser_profile")[:40],
                str(data.get("profile_dir") or ""),
                str(data.get("cookies_json") or ""),
                str(data.get("bearer_token") or ""),
                str(data.get("project_url") or "https://flow.google.com/"),
                str(data.get("proxy") or ""),
                int(data.get("credits_remaining", 1000)),
                int(data.get("credits_total", 1000)),
                int(data.get("renders_used", 0)),
                int(data.get("weekly_limit", 50)),
                str(data.get("status") or "login_pending"),
                str(data.get("last_used_at") or ""),
                str(data.get("notes") or "")[:300],
                utc_now_iso(),
            ),
        )
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM flow_accounts WHERE id = ?", (new_id,)).fetchone()
        return _format_flow_account_public(row)


def update_flow_account(account_id: int, **fields: Any) -> Optional[Dict[str, Any]]:
    if not fields:
        row = get_flow_account(account_id)
        return _format_flow_account_public(row) if row else None
    keys = ", ".join(f"{k} = ?" for k in fields.keys())
    vals = list(fields.values()) + [account_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE flow_accounts SET {keys} WHERE id = ?", vals)
        row = conn.execute("SELECT * FROM flow_accounts WHERE id = ?", (account_id,)).fetchone()
        return _format_flow_account_public(row) if row else None


def toggle_flow_account_status(account_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM flow_accounts WHERE id = ?", (account_id,)).fetchone()
        if not row:
            return None
        next_st = "cooldown" if row["status"] == "active" else "active"
        conn.execute("UPDATE flow_accounts SET status = ? WHERE id = ?", (next_st, account_id))
        updated = conn.execute("SELECT * FROM flow_accounts WHERE id = ?", (account_id,)).fetchone()
        return _format_flow_account_public(updated)


def delete_flow_account(account_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM flow_accounts WHERE id = ?", (account_id,))
        return cur.rowcount > 0


def list_products(only_bio_active: bool = False) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        query = "SELECT * FROM affiliate_products"
        if only_bio_active:
            query += " WHERE bio_active = 1"
        query += " ORDER BY id DESC"
        rows = conn.execute(query).fetchall()
        return [dict(r) for r in rows]


def get_product(product_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM affiliate_products WHERE id = ?", (product_id,)).fetchone()
        return dict(row) if row else None


def insert_product(data: Dict[str, Any]) -> Dict[str, Any]:
    with get_conn() as conn:
        cur = conn.cursor()
        code = data["code"].strip().upper().lstrip("#")
        cur.execute(
            """
            INSERT INTO affiliate_products (
                code, name, platform_name, price, original_price, affiliate_url,
                image_url, cta_overlay_text, comment_template, bio_active, clicks_count, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                code,
                data["name"].strip(),
                data["platform_name"].strip(),
                data["price"].strip(),
                data.get("original_price", "").strip(),
                data["affiliate_url"].strip(),
                data.get("image_url", "").strip(),
                data.get("cta_overlay_text") or f"MÃ #{code} • LINK Ở CMT / BIO",
                data.get("comment_template")
                or f"🛒 Đặt mua {data['name'].strip()} chính hãng tại đây: {{affiliate_url}} 👇",
                1 if data.get("bio_active", True) else 0,
                0,
                utc_now_iso(),
            ),
        )
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM affiliate_products WHERE id = ?", (new_id,)).fetchone()
        return dict(row)


def toggle_product_bio(product_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM affiliate_products WHERE id = ?", (product_id,)).fetchone()
        if not row:
            return None
        new_val = 0 if row["bio_active"] else 1
        conn.execute("UPDATE affiliate_products SET bio_active = ? WHERE id = ?", (new_val, product_id))
        updated = conn.execute("SELECT * FROM affiliate_products WHERE id = ?", (product_id,)).fetchone()
        return dict(updated)


def increment_product_click(product_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE affiliate_products SET clicks_count = clicks_count + 1 WHERE id = ?",
            (product_id,),
        )


def delete_product(product_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM affiliate_products WHERE id = ?", (product_id,))
        return cur.rowcount > 0


def _enrich_clone_job_row(row: Any) -> Dict[str, Any]:
    d = dict(row)
    sp_raw = d.get("scene_plan_json") or ""
    scene_plan: List[Dict[str, Any]] = []
    if sp_raw:
        try:
            parsed = json.loads(sp_raw)
            if isinstance(parsed, list):
                scene_plan = parsed
        except Exception:
            scene_plan = []
    d["scene_plan"] = scene_plan
    return d


def create_clone_job(data: Dict[str, Any]) -> Dict[str, Any]:
    scene_plan_str = data.get("scene_plan_json") or ""
    if not scene_plan_str and isinstance(data.get("scene_plan"), list):
        scene_plan_str = json.dumps(data["scene_plan"], ensure_ascii=False)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO clone_jobs (
                source_video_id, product_id, muse_token_id, muse_token_label,
                flow_account_id, flow_model, veo_prompt, scene_plan_json, clone_mode,
                prompt_script, cta_position, link_placement_mode, anti_duplicate, status,
                progress, output_video_url, generated_caption, generated_first_comment,
                tokens_spent, error_message, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["source_video_id"],
                data["product_id"],
                data.get("muse_token_id"),
                data.get("muse_token_label", ""),
                data.get("flow_account_id"),
                data.get("flow_model", ""),
                data.get("veo_prompt", ""),
                scene_plan_str,
                data["clone_mode"],
                data["prompt_script"],
                data.get("cta_position", "bottom_banner"),
                data.get("link_placement_mode", "both"),
                1 if data.get("anti_duplicate", True) else 0,
                "queued",
                5,
                "",
                "",
                "",
                0,
                "",
                utc_now_iso(),
            ),
        )
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM clone_jobs WHERE id = ?", (new_id,)).fetchone()
        return _enrich_clone_job_row(row)


def update_clone_job(job_id: int, **fields: Any) -> None:
    if not fields:
        return
    if "scene_plan" in fields:
        sp_val = fields.pop("scene_plan")
        fields["scene_plan_json"] = json.dumps(sp_val, ensure_ascii=False) if isinstance(sp_val, list) else str(sp_val or "")
    keys = ", ".join(f"{k} = ?" for k in fields.keys())
    values = list(fields.values()) + [job_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE clone_jobs SET {keys} WHERE id = ?", values)


def list_clone_jobs() -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT cj.*, vv.title AS source_title, vv.platform AS source_platform,
                   ap.name AS product_name, ap.code AS product_code, ap.affiliate_url AS product_url
            FROM clone_jobs cj
            LEFT JOIN viral_videos vv ON vv.id = cj.source_video_id
            LEFT JOIN affiliate_products ap ON ap.id = cj.product_id
            ORDER BY cj.id DESC
            """
        ).fetchall()
        return [_enrich_clone_job_row(r) for r in rows]


def get_clone_job(job_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM clone_jobs WHERE id = ?", (job_id,)).fetchone()
        return _enrich_clone_job_row(row) if row else None


def delete_clone_job(job_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM clone_jobs WHERE id = ?", (job_id,))
        return cur.rowcount > 0


def fail_stale_running_jobs(
    reason: str = "Tiến trình trước đó bị gián đoạn khi máy chủ tải lại. Hãy bấm 'Chạy lại' để tiếp tục.",
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            UPDATE clone_jobs
            SET status = 'failed',
                error_message = CASE WHEN error_message != '' THEN error_message ELSE ? END
            WHERE status IN ('queued', 'analyzing', 'generating_muse', 'compositing_ffmpeg')
            """,
            (reason,),
        )
        return int(cur.rowcount or 0)


def create_publish_task(data: Dict[str, Any]) -> Dict[str, Any]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO publish_tasks (
                clone_job_id, product_id, target_platform, account_name, caption,
                link_strategy, first_comment_text, bio_url_synced, status,
                published_url, comment_url, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["clone_job_id"],
                data["product_id"],
                data["target_platform"],
                data["account_name"],
                data["caption"],
                data["link_strategy"],
                data.get("first_comment_text", ""),
                1 if data.get("bio_url_synced", True) else 0,
                data.get("status", "published_with_comment"),
                data.get("published_url", ""),
                data.get("comment_url", ""),
                utc_now_iso(),
            ),
        )
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM publish_tasks WHERE id = ?", (new_id,)).fetchone()
        return dict(row)


def list_publish_tasks() -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT pt.*, ap.code AS product_code, ap.name AS product_name, ap.affiliate_url AS product_url
            FROM publish_tasks pt
            LEFT JOIN affiliate_products ap ON ap.id = pt.product_id
            ORDER BY pt.id DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]


def get_settings() -> Dict[str, str]:
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
        return {r["key"]: r["value"] for r in rows}


def update_setting(key: str, value: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO app_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


set_setting = update_setting


def _row_to_meta_shop(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    try:
        d["placements"] = [str(x).lower() for x in json.loads(d.get("placements_json") or "[]") if x]
    except Exception:
        d["placements"] = []
    d["is_inbox_only"] = bool(d.get("is_inbox_only"))
    return d


def _row_to_meta_shop_product(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    try:
        d["placements"] = [str(x).lower() for x in json.loads(d.get("placements_json") or "[]") if x]
    except Exception:
        d["placements"] = []
    return d


def upsert_meta_shop(data: Dict[str, Any]) -> Dict[str, Any]:
    shop_key = str(data.get("shop_key") or data.get("page_id") or data.get("domain") or data.get("shop_name") or "").strip().lower()
    if not shop_key:
        shop_key = f"shop_{int(datetime.now(timezone.utc).timestamp())}"
    placements = data.get("placements") or []
    placements_raw = placements if isinstance(placements, str) else json.dumps(
        sorted({str(x).lower() for x in placements if x}),
        ensure_ascii=False,
    )
    now = utc_now_iso()
    with get_conn() as conn:
        existing = conn.execute("SELECT * FROM meta_shops WHERE shop_key = ?", (shop_key,)).fetchone()
        if existing:
            sid = int(existing["id"])
            old_pl = set()
            try:
                old_pl = set(json.loads(existing["placements_json"] or "[]"))
            except Exception:
                pass
            new_pl = set()
            try:
                new_pl = set(json.loads(placements_raw))
            except Exception:
                pass
            merged_pl = json.dumps(sorted(old_pl | new_pl), ensure_ascii=False)
            conn.execute(
                """
                UPDATE meta_shops
                SET page_id = ?,
                    shop_name = ?,
                    ig_handle = ?,
                    page_url = ?,
                    shop_url = ?,
                    domain = ?,
                    avatar_url = ?,
                    ad_library_url = ?,
                    active_ads_count = ?,
                    products_count = ?,
                    price_range = ?,
                    placements_json = ?,
                    country = ?,
                    is_inbox_only = ?,
                    last_scanned_at = ?
                WHERE id = ?
                """,
                (
                    str(data.get("page_id") or existing["page_id"] or ""),
                    str(data.get("shop_name") or existing["shop_name"] or ""),
                    str(data.get("ig_handle") or existing["ig_handle"] or ""),
                    str(data.get("page_url") or existing["page_url"] or ""),
                    str(data.get("shop_url") or existing["shop_url"] or ""),
                    str(data.get("domain") or existing["domain"] or ""),
                    str(data.get("avatar_url") or existing["avatar_url"] or ""),
                    str(data.get("ad_library_url") or existing["ad_library_url"] or ""),
                    max(int(data.get("active_ads_count") or 0), int(existing["active_ads_count"] or 0)),
                    max(int(data.get("products_count") or 0), int(existing["products_count"] or 0)),
                    str(data.get("price_range") or existing["price_range"] or ""),
                    merged_pl,
                    str(data.get("country") or existing["country"] or "VN"),
                    1 if data.get("is_inbox_only") else 0,
                    now,
                    sid,
                ),
            )
            row = conn.execute("SELECT * FROM meta_shops WHERE id = ?", (sid,)).fetchone()
            return _row_to_meta_shop(row)

        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO meta_shops (
                shop_key, page_id, shop_name, ig_handle, page_url, shop_url, domain,
                avatar_url, ad_library_url, active_ads_count, products_count,
                price_range, placements_json, country, is_inbox_only, last_scanned_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                shop_key,
                str(data.get("page_id") or ""),
                str(data.get("shop_name") or shop_key),
                str(data.get("ig_handle") or ""),
                str(data.get("page_url") or ""),
                str(data.get("shop_url") or ""),
                str(data.get("domain") or ""),
                str(data.get("avatar_url") or ""),
                str(data.get("ad_library_url") or ""),
                int(data.get("active_ads_count") or 0),
                int(data.get("products_count") or 0),
                str(data.get("price_range") or ""),
                placements_raw,
                str(data.get("country") or "VN"),
                1 if data.get("is_inbox_only") else 0,
                now,
            ),
        )
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM meta_shops WHERE id = ?", (new_id,)).fetchone()
        return _row_to_meta_shop(row)


def upsert_meta_shop_products(shop_id: int, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    now = utc_now_iso()
    with get_conn() as conn:
        for idx, it in enumerate(items):
            p_url = str(it.get("product_url") or "").strip()
            lib_id = str(it.get("library_id") or "").strip()
            title = str(it.get("product_title") or "Sản phẩm đang chạy Ads").strip()
            raw_key = p_url.lower() if p_url else (lib_id or f"{title.lower()}_{idx}")
            pkey = f"{shop_id}::{raw_key}"[:240]
            pl = it.get("placements") or []
            pl_raw = pl if isinstance(pl, str) else json.dumps(
                sorted({str(x).lower() for x in pl if x}),
                ensure_ascii=False,
            )
            conn.execute(
                """
                INSERT INTO meta_shop_products (
                    shop_id, product_key, library_id, product_title, caption,
                    product_url, shop_url, selling_price, original_price,
                    video_url, thumbnail_url, cta_text, ads_duplication_count,
                    video_age_days, started_running_at, placements_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(product_key) DO UPDATE SET
                    library_id = CASE WHEN excluded.library_id != '' THEN excluded.library_id ELSE meta_shop_products.library_id END,
                    product_title = excluded.product_title,
                    caption = CASE WHEN excluded.caption != '' THEN excluded.caption ELSE meta_shop_products.caption END,
                    product_url = CASE WHEN excluded.product_url != '' THEN excluded.product_url ELSE meta_shop_products.product_url END,
                    shop_url = CASE WHEN excluded.shop_url != '' THEN excluded.shop_url ELSE meta_shop_products.shop_url END,
                    selling_price = CASE WHEN excluded.selling_price != '' THEN excluded.selling_price ELSE meta_shop_products.selling_price END,
                    original_price = CASE WHEN excluded.original_price != '' THEN excluded.original_price ELSE meta_shop_products.original_price END,
                    video_url = CASE WHEN excluded.video_url != '' THEN excluded.video_url ELSE meta_shop_products.video_url END,
                    thumbnail_url = CASE WHEN excluded.thumbnail_url != '' THEN excluded.thumbnail_url ELSE meta_shop_products.thumbnail_url END,
                    cta_text = CASE WHEN excluded.cta_text != '' THEN excluded.cta_text ELSE meta_shop_products.cta_text END,
                    ads_duplication_count = MAX(meta_shop_products.ads_duplication_count, excluded.ads_duplication_count),
                    video_age_days = excluded.video_age_days,
                    started_running_at = CASE WHEN excluded.started_running_at != '' THEN excluded.started_running_at ELSE meta_shop_products.started_running_at END,
                    placements_json = excluded.placements_json
                """,
                (
                    shop_id,
                    pkey,
                    lib_id,
                    title[:160],
                    str(it.get("caption") or "")[:600],
                    p_url,
                    str(it.get("shop_url") or ""),
                    str(it.get("selling_price") or ""),
                    str(it.get("original_price") or ""),
                    str(it.get("video_url") or ""),
                    str(it.get("thumbnail_url") or ""),
                    str(it.get("cta_text") or ""),
                    max(1, int(it.get("ads_duplication_count") or 1)),
                    max(1, int(it.get("video_age_days") or 1)),
                    str(it.get("started_running_at") or ""),
                    pl_raw,
                    now,
                ),
            )
        cnt_row = conn.execute(
            "SELECT COUNT(*) FROM meta_shop_products WHERE shop_id = ?", (shop_id,)
        ).fetchone()
        prod_cnt = int(cnt_row[0]) if cnt_row else 0
        conn.execute("UPDATE meta_shops SET products_count = ? WHERE id = ?", (prod_cnt, shop_id))
        rows = conn.execute(
            """
            SELECT * FROM meta_shop_products
            WHERE shop_id = ?
            ORDER BY (product_url != '') DESC, (selling_price != '') DESC, ads_duplication_count DESC, id DESC
            """,
            (shop_id,),
        ).fetchall()
        return [_row_to_meta_shop_product(r) for r in rows]


def list_meta_shops(
    search: Optional[str] = None,
    country: Optional[str] = None,
    platform: Optional[str] = None,
) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        q = "SELECT * FROM meta_shops WHERE 1=1"
        params: List[Any] = []
        if country and country.upper() not in {"ALL", "AUTO", ""}:
            q += " AND UPPER(country) = ?"
            params.append(country.upper())
        if platform and platform.lower() not in {"all", "meta_ads", ""}:
            q += " AND LOWER(placements_json) LIKE ?"
            params.append(f'%"{platform.lower()}"%')
        if search and search.strip():
            lk = f"%{search.strip()}%"
            q += " AND (shop_name LIKE ? OR domain LIKE ? OR shop_url LIKE ? OR ig_handle LIKE ? OR page_id LIKE ?)"
            params.extend([lk, lk, lk, lk, lk])
        q += " ORDER BY (shop_url != '' AND is_inbox_only = 0) DESC, active_ads_count DESC, products_count DESC, id DESC"
        rows = conn.execute(q, params).fetchall()
        shops = [_row_to_meta_shop(r) for r in rows]
        for sh in shops:
            prods = conn.execute(
                """
                SELECT * FROM meta_shop_products
                WHERE shop_id = ?
                ORDER BY (product_url != '') DESC, (selling_price != '') DESC, ads_duplication_count DESC, id DESC
                LIMIT 6
                """,
                (sh["id"],),
            ).fetchall()
            sh["preview_products"] = [_row_to_meta_shop_product(p) for p in prods]
        return shops


def get_meta_shop_detail(shop_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM meta_shops WHERE id = ?", (shop_id,)).fetchone()
        if not row:
            return None
        sh = _row_to_meta_shop(row)
        prods = conn.execute(
            """
            SELECT * FROM meta_shop_products
            WHERE shop_id = ?
            ORDER BY (product_url != '') DESC, (selling_price != '') DESC, ads_duplication_count DESC, id DESC
            """,
            (shop_id,),
        ).fetchall()
        sh["products"] = [_row_to_meta_shop_product(p) for p in prods]
        return sh


def find_meta_shop(page_id: str = "", domain: str = "", shop_name: str = "") -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        if page_id and page_id.strip():
            r = conn.execute("SELECT * FROM meta_shops WHERE page_id = ?", (page_id.strip(),)).fetchone()
            if r:
                return _row_to_meta_shop(r)
        if domain and domain.strip() and domain.strip() not in {"shopee.vn", "lazada.vn", "tiktok.com", "amazon.com"}:
            r = conn.execute("SELECT * FROM meta_shops WHERE LOWER(domain) = ?", (domain.strip().lower(),)).fetchone()
            if r:
                return _row_to_meta_shop(r)
        if shop_name and shop_name.strip():
            r = conn.execute("SELECT * FROM meta_shops WHERE LOWER(shop_name) = ?", (shop_name.strip().lower(),)).fetchone()
            if r:
                return _row_to_meta_shop(r)
    return None
