from typing import Any, Dict, Optional

import database


def build_affiliate_copy(
    product: Optional[Dict[str, Any]],
    target_platform: str,
    custom_hook: str = "",
    video: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate natural organic viral caption + engagement/optional product first comment."""
    video_title = (video or {}).get("title") or "Clip viral thực tế"
    hook = (
        custom_hook.strip()
        or (video or {}).get("hook_text", "").strip()
        or (f"🔥 Review thực tế {product['name']}!" if product else video_title)
    )

    if not product:
        if target_platform == "instagram_reels":
            caption = (
                f"{hook}\n\n"
                "✨ Giữ nguyên nhịp cắt 3 giây đầu từ bản viral gốc — xem hết clip để thấy đoạn kết bất ngờ nha!\n"
                "#reels #xuhuong #reviewchanthat #viral"
            )
            strategy = "organic_viral_reels"
            first_comment_out = (
                "Mình test kỹ từng góc quay rồi mới lên clip này — mọi người muốn hỏi chi tiết hay cần tìm món nào trong video thì cmt bên dưới nhé 👇"
            )
        elif target_platform == "threads":
            caption = (
                f"{hook}\n\n"
                "📌 Chia sẻ lại góc quay & trải nghiệm thực tế cho ai đang tìm hiểu 👇"
            )
            strategy = "organic_thread_story"
            first_comment_out = (
                "Ai muốn xem thêm hậu trường hoặc chi tiết mình dùng trong clip thì nhắn ở đây mình rep từng bạn nha 💬"
            )
        else:
            caption = (
                f"{hook}\n\n"
                "👉 Xem hết clip xem đoạn chuyển cảnh có mượt không nha cả nhà! Lưu lại khi cần nhé 🔥\n"
                "#reels #xuhuong #videohay #chiase"
            )
            strategy = "organic_engagement_comment"
            first_comment_out = (
                "Clip này quay theo đúng nhịp viral đang lên — anh chị em cần mình chia sẻ thêm thông tin trong video cứ bình luận bên dưới nhé 👇"
            )
        return {
            "caption": caption,
            "first_comment": first_comment_out,
            "link_strategy": strategy,
        }

    code = product["code"]
    name = product["name"]
    price = product["price"]
    aff_url = product["affiliate_url"]

    raw_comment = product.get("comment_template") or f"🛒 Chỗ mình lấy {name} ({price}) ở đây cho ai hỏi nè: {{affiliate_url}} 👇"
    first_comment = raw_comment.replace("{affiliate_url}", aff_url).replace("{code}", code)

    if target_platform == "instagram_reels":
        caption = (
            f"{hook}\n\n"
            f"✨ Ai cần xem thông tin món mình dùng trong clip thì ghé link đầu trang (tìm mã #{code}) nha 👇\n"
            f"#reels #reviewthucte #{code.lower()}"
        )
        strategy = "bio_link_code"
        first_comment_out = f"Ai hỏi chỗ lấy cứ vào link đầu trang tìm mã #{code} ({price}) nhé ✨"
    elif target_platform == "threads":
        caption = (
            f"{hook}\n\n"
            f"📌 Trải nghiệm thực tế bên trên — thông tin món mình dùng ({price}) mình để gọn dưới Reply cho ai cần 👇"
        )
        strategy = "direct_thread_reply"
        first_comment_out = first_comment
    else:
        caption = (
            f"{hook}\n\n"
            f"👉 Video trải nghiệm thực tế cho mọi người tham khảo. Ai cần xem chi tiết ({price}) mình để ở bình luận đầu nha!\n"
            f"#reels #reviewchanthat #xuhuong"
        )
        strategy = "auto_first_comment"
        first_comment_out = first_comment

    return {
        "caption": caption,
        "first_comment": first_comment_out,
        "link_strategy": strategy,
    }


def dispatch_publish_task(
    clone_job_id: int,
    product_id: int,
    target_platform: str,
    account_name: str,
    caption: str = "",
    first_comment_text: str = "",
) -> Dict[str, Any]:
    product = database.get_product(product_id) if product_id and product_id > 0 else None
    job = database.get_clone_job(clone_job_id)
    video = database.get_video(job["source_video_id"]) if job else None

    pkg = build_affiliate_copy(product, target_platform, custom_hook=(job or {}).get("prompt_script", ""), video=video)
    final_caption = caption.strip() or pkg["caption"]
    final_comment = first_comment_text.strip() or pkg["first_comment"]
    strategy = pkg["link_strategy"]

    if product and not product.get("bio_active"):
        database.toggle_product_bio(product_id)

    status = "published_bio_synced" if strategy == "bio_link_code" else "published_with_comment"
    demo_slug = f"{target_platform}_{clone_job_id}"
    published_url = f"https://social-preview.local/{demo_slug}"
    comment_url = f"{published_url}#first-comment" if strategy != "bio_link_code" else "/bio"

    return database.create_publish_task(
        {
            "clone_job_id": clone_job_id,
            "product_id": product["id"] if product else 0,
            "target_platform": target_platform,
            "account_name": account_name.strip() or "@creator_viral_01",
            "caption": final_caption,
            "link_strategy": strategy,
            "first_comment_text": final_comment,
            "bio_url_synced": bool(product),
            "status": status,
            "published_url": published_url,
            "comment_url": comment_url,
        }
    )
