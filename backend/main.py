import asyncio
import html
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import crawler_service
import database
import muse_service
import publisher_service

database.init_db()

app = FastAPI(title="CloneVideo-Aff Studio API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MEDIA_DIR = Path(__file__).resolve().parent / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")


class CrawlRequest(BaseModel):
    keyword: str
    platform: str = "all"
    engine: str = "crawl4ai_free"
    country: str = "VN"


class InspectUrlRequest(BaseModel):
    url: str
    download: bool = True


class BulkTokensRequest(BaseModel):
    raw_tokens: str
    weekly_limit: int = 50


class ProductCreateRequest(BaseModel):
    code: str
    name: str
    platform_name: str = "Shopee"
    price: str
    original_price: str = ""
    affiliate_url: str
    image_url: str = ""
    cta_overlay_text: str = ""
    comment_template: str = ""
    bio_active: bool = True


class CloneJobCreateRequest(BaseModel):
    source_video_id: int
    product_id: int
    clone_mode: str = "muse_prompt_remap"
    prompt_script: str = ""
    cta_position: str = "bottom_banner"
    link_placement_mode: str = "both"
    anti_duplicate: bool = True
    batch_count: int = 1


class PublishTaskCreateRequest(BaseModel):
    clone_job_id: int
    product_id: int
    target_platform: str = "facebook_reels"
    account_name: str = "@aff_channel_01"
    caption: str = ""
    first_comment_text: str = ""


class SettingsUpdateRequest(BaseModel):
    treg_api_key: Optional[str] = None
    bio_brand_name: Optional[str] = None
    bio_brand_subtitle: Optional[str] = None
    default_crawl_country: Optional[str] = None


@app.get("/api/system/status")
def get_system_status():
    tokens = database.list_muse_tokens()
    active_tokens = [t for t in tokens if t["status"] == "active"]
    total_remaining = sum(int(t["tokens_remaining"]) for t in tokens)
    weekly_used = sum(int(t["weekly_used"]) for t in tokens)
    weekly_capacity = sum(int(t["weekly_limit"]) for t in tokens)

    return {
        "status": "online",
        "backend": "Python 3.11 + FastAPI",
        "ffmpeg_installed": bool(muse_service.find_ffmpeg()),
        "ffmpeg_path": muse_service.find_ffmpeg() or "",
        "ytdlp_installed": bool(crawler_service.find_ytdlp()),
        "ytdlp_path": crawler_service.find_ytdlp() or "",
        "playwright_installed": crawler_service.has_playwright(),
        "crawl4ai_installed": crawler_service.has_crawl4ai(),
        "counts": {
            "viral_videos": len(database.list_videos()),
            "products": len(database.list_products()),
            "clone_jobs": len(database.list_clone_jobs()),
            "publish_tasks": len(database.list_publish_tasks()),
        },
        "muse_pool": {
            "total_accounts": len(tokens),
            "active_accounts": len(active_tokens),
            "total_tokens_remaining": total_remaining,
            "weekly_used": weekly_used,
            "weekly_capacity": weekly_capacity,
        },
        "settings": database.get_settings(),
    }


@app.post("/api/system/settings")
def update_system_settings(req: SettingsUpdateRequest):
    if req.treg_api_key is not None:
        database.update_setting("treg_api_key", req.treg_api_key.strip())
    if req.bio_brand_name is not None:
        database.update_setting("bio_brand_name", req.bio_brand_name.strip())
    if req.bio_brand_subtitle is not None:
        database.update_setting("bio_brand_subtitle", req.bio_brand_subtitle.strip())
    if req.default_crawl_country is not None:
        database.update_setting("default_crawl_country", req.default_crawl_country.strip())
    return {"ok": True, "settings": database.get_settings()}


@app.get("/api/videos")
def get_videos(platform: Optional[str] = Query(default="all"), search: Optional[str] = Query(default=None)):
    return {"videos": database.list_videos(platform=platform, search=search)}


@app.post("/api/videos/crawl")
async def crawl_videos(req: CrawlRequest):
    return await crawler_service.crawl_viral_videos(
        keyword=req.keyword,
        platform=req.platform,
        engine=req.engine,
        country=req.country,
    )


@app.post("/api/videos/inspect-url")
async def inspect_url(req: InspectUrlRequest):
    if not req.url.strip():
        raise HTTPException(status_code=400, detail="Vui lòng nhập URL video hợp lệ.")
    return await crawler_service.inspect_or_download_url(req.url, download=req.download)


@app.get("/api/muse-tokens")
def get_muse_tokens():
    tokens = database.list_muse_tokens()
    return {
        "tokens": tokens,
        "summary": {
            "total_accounts": len(tokens),
            "active_accounts": sum(1 for t in tokens if t["status"] == "active"),
            "total_tokens_remaining": sum(int(t["tokens_remaining"]) for t in tokens),
            "weekly_used": sum(int(t["weekly_used"]) for t in tokens),
            "weekly_capacity": sum(int(t["weekly_limit"]) for t in tokens),
        },
    }


@app.post("/api/muse-tokens/bulk")
def import_muse_tokens_bulk(req: BulkTokensRequest):
    imported = muse_service.bulk_import_tokens(req.raw_tokens, default_weekly_limit=req.weekly_limit)
    if imported == 0:
        raise HTTPException(status_code=400, detail="Không tìm thấy token hợp lệ trong dữ liệu nhập.")
    return {"ok": True, "imported": imported, "tokens": database.list_muse_tokens()}


@app.patch("/api/muse-tokens/{token_id}/toggle")
def toggle_muse_token(token_id: int):
    updated = database.toggle_muse_token_status(token_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Không tìm thấy token.")
    return {"ok": True, "token": updated}


@app.delete("/api/muse-tokens/{token_id}")
def remove_muse_token(token_id: int):
    ok = database.delete_muse_token(token_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Không tìm thấy token.")
    return {"ok": True}


@app.get("/api/products")
def get_products():
    return {"products": database.list_products()}


@app.post("/api/products")
def create_product(req: ProductCreateRequest):
    try:
        product = database.insert_product(req.model_dump())
        return {"ok": True, "product": product}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Không thể thêm sản phẩm (mã SP có thể bị trùng): {exc}")


@app.patch("/api/products/{product_id}/toggle-bio")
def toggle_product_bio(product_id: int):
    updated = database.toggle_product_bio(product_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
    return {"ok": True, "product": updated}


@app.delete("/api/products/{product_id}")
def remove_product(product_id: int):
    ok = database.delete_product(product_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
    return {"ok": True}


@app.get("/api/clone-jobs")
def get_clone_jobs():
    return {"jobs": database.list_clone_jobs()}


@app.post("/api/clone-jobs")
async def create_clone_job(req: CloneJobCreateRequest, background_tasks: BackgroundTasks):
    video = database.get_video(req.source_video_id)
    product = database.get_product(req.product_id)
    if not video or not product:
        raise HTTPException(status_code=404, detail="Video gốc hoặc sản phẩm không tồn tại.")

    count = max(1, min(10, req.batch_count))
    created_jobs = []
    for _ in range(count):
        script = req.prompt_script.strip() or video.get("hook_text") or video.get("title")
        job = database.create_clone_job(
            {
                "source_video_id": req.source_video_id,
                "product_id": req.product_id,
                "clone_mode": req.clone_mode,
                "prompt_script": script,
                "cta_position": req.cta_position,
                "link_placement_mode": req.link_placement_mode,
                "anti_duplicate": req.anti_duplicate,
            }
        )
        created_jobs.append(job)
        background_tasks.add_task(muse_service.run_clone_job, job["id"])

    return {"ok": True, "jobs": created_jobs}


@app.get("/api/publish-tasks")
def get_publish_tasks():
    return {"tasks": database.list_publish_tasks()}


@app.post("/api/publish-tasks/preview")
def preview_publish_copy(product_id: int, target_platform: str = "facebook_reels", custom_hook: str = ""):
    product = database.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
    return publisher_service.build_affiliate_copy(product, target_platform, custom_hook)


@app.post("/api/publish-tasks")
def create_publish_task(req: PublishTaskCreateRequest):
    try:
        task = publisher_service.dispatch_publish_task(
            clone_job_id=req.clone_job_id,
            product_id=req.product_id,
            target_platform=req.target_platform,
            account_name=req.account_name,
            caption=req.caption,
            first_comment_text=req.first_comment_text,
        )
        return {"ok": True, "task": task}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/api/bio-page")
def get_bio_page_data():
    settings = database.get_settings()
    products = database.list_products(only_bio_active=True)
    return {
        "brand_name": settings.get("bio_brand_name", "Deal Ngon Mỗi Ngày"),
        "brand_subtitle": settings.get("bio_brand_subtitle", ""),
        "products": products,
    }


@app.get("/bio/go/{product_id}")
def redirect_bio_product(product_id: int):
    product = database.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại.")
    database.increment_product_click(product_id)
    return RedirectResponse(url=product["affiliate_url"])


@app.get("/bio", response_class=HTMLResponse)
def render_bio_html():
    data = get_bio_page_data()
    cards_html = ""
    for p in data["products"]:
        img = html.escape(p.get("image_url") or "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=300&q=80")
        cards_html += f"""
        <a href="/bio/go/{p['id']}" target="_blank" rel="noopener noreferrer"
           class="card" data-search="{html.escape((p['code'] + ' ' + p['name']).lower())}">
          <img src="{img}" alt="{html.escape(p['name'])}" />
          <div class="meta">
            <div class="badges">
              <span class="code">#{html.escape(p['code'])}</span>
              <span class="mall">{html.escape(p['platform_name'])}</span>
            </div>
            <h3>{html.escape(p['name'])}</h3>
            <div class="price-row">
              <span class="price">{html.escape(p['price'])}</span>
              <span class="orig">{html.escape(p.get('original_price') or '')}</span>
            </div>
          </div>
          <span class="btn">Mua ngay →</span>
        </a>
        """

    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{html.escape(data['brand_name'])} — Link Bio Affiliate</title>
<style>
  body {{ margin:0; font-family: system-ui, -apple-system, sans-serif; background: linear-gradient(160deg,#090d16,#111827,#1e1b4b); color:#f8fafc; min-height:100vh; padding:24px 16px; }}
  .wrap {{ max-width: 480px; margin: 0 auto; }}
  .header {{ text-align:center; margin-bottom:20px; }}
  .avatar {{ width:72px; height:72px; border-radius:999px; background:linear-gradient(135deg,#f97316,#ec4899); display:inline-flex; align-items:center; justify-content:center; font-size:28px; font-weight:800; margin-bottom:10px; }}
  h1 {{ font-size:20px; margin:4px 0; }}
  p {{ font-size:13px; color:#94a3b8; margin:0; }}
  input {{ width:100%; box-sizing:border-box; padding:12px 14px; border-radius:14px; border:1px solid #334155; background:#0f172a; color:#fff; margin:16px 0; outline:none; }}
  .card {{ display:flex; align-items:center; gap:12px; background:rgba(30,41,59,.82); border:1px solid rgba(148,163,184,.2); border-radius:16px; padding:10px; margin-bottom:12px; text-decoration:none; color:inherit; transition:.15s transform; }}
  .card:hover {{ transform:translateY(-2px); border-color:#f97316; }}
  .card img {{ width:64px; height:64px; border-radius:12px; object-fit:cover; flex-shrink:0; }}
  .meta {{ flex:1; min-width:0; }}
  .badges {{ display:flex; gap:6px; margin-bottom:4px; }}
  .code {{ background:#f97316; color:#fff; font-size:11px; font-weight:700; padding:2px 7px; border-radius:6px; }}
  .mall {{ background:#1e293b; color:#38bdf8; font-size:11px; padding:2px 7px; border-radius:6px; }}
  h3 {{ font-size:13px; margin:0 0 4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .price {{ color:#34d399; font-weight:700; font-size:14px; }}
  .orig {{ color:#64748b; text-decoration:line-through; font-size:11px; margin-left:6px; }}
  .btn {{ background:#10b981; color:#022c22; font-weight:700; font-size:12px; padding:8px 10px; border-radius:10px; white-space:nowrap; }}
</style>
</head>
<body>
  <div class="wrap">
    <div class="header">
      <div class="avatar">🔥</div>
      <h1>{html.escape(data['brand_name'])}</h1>
      <p>{html.escape(data['brand_subtitle'])}</p>
    </div>
    <input id="q" placeholder="Tìm nhanh theo mã #SP01 hoặc tên sản phẩm..." oninput="filterCards(this.value)" />
    <div id="list">{cards_html}</div>
  </div>
  <script>
    function filterCards(val) {{
      var q = val.toLowerCase().trim();
      document.querySelectorAll('.card').forEach(function(el) {{
        el.style.display = el.dataset.search.includes(q) ? 'flex' : 'none';
      }});
    }}
  </script>
</body>
</html>"""
