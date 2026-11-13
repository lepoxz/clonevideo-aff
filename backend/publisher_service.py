from typing import Any, Dict

import database


def build_affiliate_copy(
    product: Dict[str, Any],
    target_platform: str,
    custom_hook: str = "",
) -> Dict[str, Any]:
    """Generate platform-compliant caption + comment/bio link strategy so reach is not throttled."""
    code = product["code"]
    name = product["name"]
    price = product["price"]
    aff_url = product["affiliate_url"]
    hook = custom_hook.strip() or f"🔥 Review thực tế {name} đang sale chỉ còn {price}!"

    raw_comment = product.get("comment_template") or f"🛒 Đặt mua {name} chính hãng tại đây: {{affiliate_url}} 👇"
    first_comment = raw_comment.replace("{affiliate_url}", aff_url).replace("{code}", code)

    if target_platform == "instagram_reels":
        # Instagram Reels comments are not clickable -> direct users to Link-in-Bio with Product Code
        caption = (
            f"{hook}\n\n"
            f"✨ Xem chi tiết & săn giá {price} tại LINK TRÊN BIO đầu trang (Tìm mã: #{code}) 👇\n"
            f"#review #affiliate #{code.lower()} #reelsvietnam"
        )
        strategy = "bio_link_code"
        first_comment_out = f"Tìm mã #{code} trên Link Bio đầu trang để nhận giá {price} nha cả nhà ✨"
    elif target_platform == "threads":
        caption = (
            f"{hook}\n\n"
            f"📌 Video test thực tế bên trên — Link mua chính hãng ({price}) mình gắn ở Reply đầu tiên bên dưới 👇"
        )
        strategy = "direct_thread_reply"
        first_comment_out = first_comment
    else:
        # Facebook Reels: avoid placing raw affiliate URL inside main caption; put it in First Comment
        caption = (
            f"{hook}\n\n"
            f"👉 Mình để link sản phẩm chính hãng ({price}) ở BÌNH LUẬN ĐẦU TIÊN bên dưới để mọi người bấm cho tiện nhé! (Mã #{code})\n"
            f"#reels #reviewchanthat #sanphamhot"
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
    product = database.get_product(product_id)
    if not product:
        raise ValueError("Không tìm thấy sản phẩm Affiliate")

    pkg = build_affiliate_copy(product, target_platform)
    final_caption = caption.strip() or pkg["caption"]
    final_comment = first_comment_text.strip() or pkg["first_comment"]
    strategy = pkg["link_strategy"]

    # Ensure product is visible on Link-in-Bio storefront
    if not product.get("bio_active"):
        database.toggle_product_bio(product_id)

    status = "published_bio_synced" if strategy == "bio_link_code" else "published_with_comment"
    demo_slug = f"{target_platform}_{clone_job_id}"
    published_url = f"https://social-preview.local/{demo_slug}"
    comment_url = f"{published_url}#first-comment" if strategy != "bio_link_code" else "/bio"

    return database.create_publish_task(
        {
            "clone_job_id": clone_job_id,
            "product_id": product_id,
            "target_platform": target_platform,
            "account_name": account_name.strip() or "@aff_channel_01",
            "caption": final_caption,
            "link_strategy": strategy,
            "first_comment_text": final_comment,
            "bio_url_synced": True,
            "status": status,
            "published_url": published_url,
            "comment_url": comment_url,
        }
    )
