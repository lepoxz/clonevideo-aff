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
            CREATE TABLE IF NOT EXISTS clone_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_video_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                muse_token_id INTEGER DEFAULT NULL,
                muse_token_label TEXT DEFAULT '',
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
    return d


def list_videos(platform: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        query = "SELECT * FROM viral_videos WHERE 1=1"
        params: List[Any] = []
        if platform and platform != "all":
            query += " AND platform = ?"
            params.append(platform)
        if search:
            query += " AND (title LIKE ? OR caption LIKE ? OR hook_text LIKE ?)"
            like = f"%{search}%"
            params.extend([like, like, like])
        query += " ORDER BY viral_score DESC, id DESC"
        rows = conn.execute(query, params).fetchall()
        return [_row_to_video(r) for r in rows]


def get_video(video_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM viral_videos WHERE id = ?", (video_id,)).fetchone()
        return _row_to_video(row) if row else None


def insert_video(data: Dict[str, Any]) -> Dict[str, Any]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO viral_videos (
                platform, title, caption, author, source_url, video_url, thumbnail_url,
                local_path, views, likes, comments, shares, viral_score, sales_signals,
                hook_text, script_summary, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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


def create_clone_job(data: Dict[str, Any]) -> Dict[str, Any]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO clone_jobs (
                source_video_id, product_id, muse_token_id, muse_token_label, clone_mode,
                prompt_script, cta_position, link_placement_mode, anti_duplicate, status,
                progress, output_video_url, generated_caption, generated_first_comment,
                tokens_spent, error_message, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["source_video_id"],
                data["product_id"],
                data.get("muse_token_id"),
                data.get("muse_token_label", ""),
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
        return dict(row)


def update_clone_job(job_id: int, **fields: Any) -> None:
    if not fields:
        return
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
        return [dict(r) for r in rows]


def get_clone_job(job_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM clone_jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


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
