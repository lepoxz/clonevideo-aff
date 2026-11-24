from __future__ import annotations

import asyncio
import html
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import crawler_service
import database
import flow_service
import muse_service
import publisher_service

database.init_db()
database.fail_stale_running_jobs()

app = FastAPI(title="CloneVideo-Aff Studio API", version="0.1.0")
_active_job_tasks: Dict[int, asyncio.Task] = {}


def _spawn_clone_job_task(job_id: int) -> None:
    t = asyncio.create_task(muse_service.run_clone_job(job_id))
    _active_job_tasks[job_id] = t
    t.add_done_callback(lambda _: _active_job_tasks.pop(job_id, None))

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
    match_type: str = "broad"


class EvaluatePotentialRequest(BaseModel):
    custom_query: str = ""
    country: str = ""
    deep_spy: bool = True


class EvaluatePotentialBatchRequest(BaseModel):
    video_ids: Optional[List[int]] = None
    limit: int = 5
    country: str = ""


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
    product_id: int = 0
    clone_mode: str = "rea_video_remake"
    prompt_script: str = ""
    cta_position: str = "clean_organic"
    link_placement_mode: str = "both"
    anti_duplicate: bool = True
    batch_count: int = 1
    flow_account_id: Optional[int] = None
    flow_model: str = ""
    veo_prompt: str = ""
    scene_plan: Optional[List[Dict[str, Any]]] = None


class FlowBrowserLoginRequest(BaseModel):
    account_id: Optional[int] = None
    label: str = ""
    proxy: str = ""
    tier: str = "Flow Pro"


class FlowBulkImportRequest(BaseModel):
    raw_accounts: str
    weekly_limit: int = 50
    tier: str = "Flow Pro"


class FlowPromptRequest(BaseModel):
    video_id: int
    clone_mode: str = "flow_omni_ingredients"
    custom_hint: str = ""
    flow_model: str = "omni_1_2_flash_10s_portrait"


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
    rea_vlm_enabled: Optional[str] = None
    rea_vlm_base_url: Optional[str] = None
    rea_vlm_api_key: Optional[str] = None
    rea_vlm_model: Optional[str] = None
    rea_report_lang: Optional[str] = None


class AgentReachChannelActionRequest(BaseModel):
    channel: str
    operation: str


class AgentReachBrowserActionRequest(BaseModel):
    operation: str
    param: str = ""


class AgentReachConfigureRequest(BaseModel):
    key: str
    value: str = ""


class AgentReachExecuteRequest(BaseModel):
    channel: str
    action: str
    query: str = ""
    limit: int = 5
    save_to_videos: bool = True
    country: str = "VN"


class ReaDecomposeRequest(BaseModel):
    use_vlm: Optional[bool] = None


class ReaVlmFetchModelsRequest(BaseModel):
    base_url: str
    api_key: str = ""


class MetaShopSearchRequest(BaseModel):
    query: str = ""
    country: str = "VN"
    platform: str = "all"
    limit: int = 12


class MetaShopProductsScanRequest(BaseModel):
    page_id: str = ""
    shop_query: str = ""
    shop_id: Optional[int] = None
    country: str = "ALL"
    limit: int = 24


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
        "agent_reach_installed": bool(crawler_service.find_agent_reach()),
        "agent_reach_path": crawler_service.find_agent_reach() or "",
        "rea_video_installed": bool(muse_service.find_rea_video()),
        "rea_video_path": muse_service.find_rea_video() or "",
        "playwright_installed": crawler_service.has_playwright(),
        "crawl4ai_installed": crawler_service.has_crawl4ai(),
        "counts": {
            "viral_videos": len(database.list_videos()),
            "meta_shops": len(database.list_meta_shops()),
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
        "flow_pool": flow_service.get_flow_pool_summary(),
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
    if req.rea_vlm_enabled is not None:
        database.update_setting("rea_vlm_enabled", req.rea_vlm_enabled.strip())
    if req.rea_vlm_base_url is not None:
        database.update_setting("rea_vlm_base_url", req.rea_vlm_base_url.strip())
    if req.rea_vlm_api_key is not None:
        database.update_setting("rea_vlm_api_key", req.rea_vlm_api_key.strip())
    if req.rea_vlm_model is not None:
        database.update_setting("rea_vlm_model", req.rea_vlm_model.strip())
    if req.rea_report_lang is not None:
        database.update_setting("rea_report_lang", req.rea_report_lang.strip())
    return {"ok": True, "settings": database.get_settings()}


@app.post("/api/rea-video/fetch-models")
async def fetch_rea_video_vlm_models(req: ReaVlmFetchModelsRequest):
    return await muse_service.fetch_vlm_models(req.base_url, req.api_key)


@app.get("/api/agent-reach/status")
async def get_agent_reach_status():
    return await asyncio.to_thread(crawler_service.get_agent_reach_full_status)


@app.post("/api/agent-reach/channel-action")
async def agent_reach_channel_action(req: AgentReachChannelActionRequest):
    return await asyncio.to_thread(crawler_service.manage_agent_reach_channel, req.channel, req.operation)


@app.post("/api/agent-reach/browser-action")
async def agent_reach_browser_action(req: AgentReachBrowserActionRequest):
    return await asyncio.to_thread(crawler_service.manage_agent_reach_browser, req.operation, req.param)


@app.post("/api/agent-reach/configure")
async def agent_reach_configure(req: AgentReachConfigureRequest):
    return await asyncio.to_thread(crawler_service.configure_agent_reach_key, req.key, req.value)


@app.post("/api/agent-reach/execute")
async def agent_reach_execute(req: AgentReachExecuteRequest):
    return await asyncio.to_thread(
        crawler_service.execute_agent_reach_action,
        req.channel,
        req.action,
        req.query,
        req.limit,
        req.save_to_videos,
        req.country,
    )


@app.get("/api/videos")
def get_videos(platform: Optional[str] = Query(default="all"), search: Optional[str] = Query(default=None)):
    crawler_service.purge_invalid_and_mockup_videos()
    vids = database.list_videos(platform=platform, search=search)
    for v in vids:
        if not isinstance(v.get("market_intel"), dict):
            v["market_intel"] = crawler_service.build_market_intel_for_video(v, shops=[], spy_status="baseline")
    return {"videos": vids}


@app.post("/api/videos/evaluate-potential-batch")
async def evaluate_videos_potential_batch(req: EvaluatePotentialBatchRequest):
    return await asyncio.to_thread(
        crawler_service.evaluate_potential_videos_batch,
        req.video_ids,
        req.limit,
        req.country,
    )


@app.post("/api/videos/{video_id}/evaluate-potential")
async def evaluate_video_potential(video_id: int, req: EvaluatePotentialRequest):
    res = await asyncio.to_thread(
        crawler_service.evaluate_video_potential_sync,
        video_id,
        req.custom_query,
        req.country,
        req.deep_spy,
    )
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error") or "Không thể đánh giá & dò shop cho video này.")
    return res


@app.post("/api/videos/{video_id}/ensure-mp4")
async def ensure_video_mp4(video_id: int):
    res = await asyncio.to_thread(crawler_service.ensure_video_playable_mp4, video_id)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error") or "Không thể chuẩn bị luồng phát MP4.")
    return res


@app.post("/api/videos/{video_id}/analyze-ai")
async def analyze_video_ai(video_id: int):
    res = await asyncio.to_thread(crawler_service.analyze_single_video_ai, video_id)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error") or "Không thể phân tích AI cho video này.")
    return res


@app.post("/api/videos/crawl")
async def crawl_videos(req: CrawlRequest):
    return await crawler_service.crawl_viral_videos(
        keyword=req.keyword,
        platform=req.platform,
        engine=req.engine,
        country=req.country,
        match_type=req.match_type,
    )


@app.post("/api/videos/inspect-url")
async def inspect_url(req: InspectUrlRequest):
    if not req.url.strip():
        raise HTTPException(status_code=400, detail="Vui lòng nhập URL video hợp lệ.")
    return await crawler_service.inspect_or_download_url(req.url, download=req.download)


@app.post("/api/videos/{video_id}/rea-decompose")
async def rea_decompose_video(video_id: int, req: Optional[ReaDecomposeRequest] = None):
    res = await muse_service.decompose_video_with_rea(video_id, force_vlm=req.use_vlm if req else None)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res.get("error") or "rea-video decompose failed")
    return res


@app.get("/api/meta-shops")
def get_meta_shops(
    search: Optional[str] = Query(default=None),
    country: Optional[str] = Query(default=None),
    platform: Optional[str] = Query(default=None),
):
    return {"shops": database.list_meta_shops(search=search, country=country, platform=platform)}


@app.get("/api/meta-shops/{shop_id}")
def get_meta_shop_by_id(shop_id: int):
    detail = database.get_meta_shop_detail(shop_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Không tìm thấy Shop này trong dữ liệu Meta Ads.")
    return {"ok": True, "shop": detail, "products": detail.get("products") or []}


@app.post("/api/meta-shops/search")
async def search_meta_shops_endpoint(req: MetaShopSearchRequest):
    return await crawler_service.search_shops_on_meta_ads(
        query=req.query,
        country=req.country,
        platform=req.platform,
        limit=max(1, min(20, req.limit)),
    )


@app.post("/api/meta-shops/products")
async def scan_meta_shop_products_endpoint(req: MetaShopProductsScanRequest):
    res = await crawler_service.crawl_shop_products_on_meta_ads(
        page_id=req.page_id,
        shop_query=req.shop_query,
        shop_id=req.shop_id,
        country=req.country,
        limit=max(1, min(40, req.limit)),
    )
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error") or "Không thể quét danh sách sản phẩm của Shop trên Meta Ads.")
    return res


@app.post("/api/meta-shops/products/{shop_product_id}/import-video")
async def import_meta_shop_product_video_endpoint(shop_product_id: int):
    res = await asyncio.to_thread(crawler_service.import_shop_product_to_videos, shop_product_id)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error") or "Không thể lưu video sản phẩm này vào kho.")
    return res


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


@app.get("/api/flow-accounts")
def get_flow_accounts():
    return {
        "accounts": database.list_flow_accounts(),
        "models": flow_service.get_all_flow_models(),
        "summary": flow_service.get_flow_pool_summary(),
    }


@app.post("/api/flow/sync-models")
async def sync_flow_models_endpoint():
    return await asyncio.to_thread(flow_service.sync_latest_flow_models)


@app.post("/api/flow-accounts/login-browser")
async def login_flow_account_browser(req: FlowBrowserLoginRequest):
    res = await asyncio.to_thread(
        flow_service.start_flow_browser_login,
        req.account_id,
        req.label,
        req.proxy,
        req.tier,
    )
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error") or "Không mở được Chrome cho Google Flow.")
    return res


@app.post("/api/flow-accounts/{account_id}/open-browser")
async def open_flow_account_browser(account_id: int):
    res = await asyncio.to_thread(flow_service.open_flow_browser_workspace, account_id)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error") or "Không mở được trình duyệt Flow.")
    return res


@app.post("/api/flow-accounts/{account_id}/verify")
async def verify_flow_account_endpoint(account_id: int):
    res = await asyncio.to_thread(flow_service.verify_flow_account, account_id)
    if "error" in res and not res.get("account"):
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@app.post("/api/flow-accounts/bulk")
def import_flow_accounts_bulk(req: FlowBulkImportRequest):
    res = flow_service.bulk_import_flow_accounts(
        req.raw_accounts,
        weekly_limit=req.weekly_limit,
        tier=req.tier,
    )
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error") or "Không tìm thấy tài khoản Flow hợp lệ.")
    return {
        "ok": True,
        "imported": res["imported"],
        "accounts": database.list_flow_accounts(),
        "summary": flow_service.get_flow_pool_summary(),
    }


@app.patch("/api/flow-accounts/{account_id}/toggle")
def toggle_flow_account(account_id: int):
    updated = database.toggle_flow_account_status(account_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản Flow.")
    return {"ok": True, "account": updated}


@app.delete("/api/flow-accounts/{account_id}")
def delete_flow_account_endpoint(account_id: int):
    ok = database.delete_flow_account(account_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản Flow.")
    return {"ok": True}


@app.post("/api/flow/generate-prompt")
async def generate_flow_veo_prompt(req: FlowPromptRequest):
    res = await asyncio.to_thread(
        flow_service.generate_veo_prompt_for_video,
        req.video_id,
        req.clone_mode,
        req.custom_hint,
        muse_service.find_ffmpeg(),
        req.flow_model,
    )
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error") or "Không thể tạo Prompt Veo.")
    return res


@app.get("/api/clone-jobs")
def get_clone_jobs():
    return {"jobs": database.list_clone_jobs()}


@app.post("/api/clone-jobs")
async def create_clone_job(req: CloneJobCreateRequest):
    video = database.get_video(req.source_video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video gốc không tồn tại.")
    if req.product_id and req.product_id > 0:
        product = database.get_product(req.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Sản phẩm được chọn không tồn tại.")

    count = max(1, min(10, req.batch_count))
    created_jobs = []
    for _ in range(count):
        script = req.prompt_script.strip() or video.get("hook_text") or video.get("title")
        job = database.create_clone_job(
            {
                "source_video_id": req.source_video_id,
                "product_id": req.product_id if req.product_id and req.product_id > 0 else 0,
                "clone_mode": req.clone_mode,
                "prompt_script": script,
                "cta_position": req.cta_position,
                "link_placement_mode": req.link_placement_mode,
                "anti_duplicate": req.anti_duplicate,
                "flow_account_id": req.flow_account_id if req.flow_account_id and req.flow_account_id > 0 else None,
                "flow_model": req.flow_model.strip(),
                "veo_prompt": req.veo_prompt.strip(),
                "scene_plan": req.scene_plan or [],
            }
        )
        created_jobs.append(job)
        _spawn_clone_job_task(int(job["id"]))

    return {"ok": True, "jobs": created_jobs}


@app.post("/api/clone-jobs/{job_id}/retry")
async def retry_clone_job(job_id: int, refresh_plan: bool = Query(default=False)):
    job = database.get_clone_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy Clone Job.")
    running = _active_job_tasks.pop(job_id, None)
    if running and not running.done():
        running.cancel()
    upd: Dict[str, Any] = {
        "status": "queued",
        "progress": 5,
        "error_message": "",
        "output_video_url": "",
    }
    if refresh_plan or len(job.get("scene_plan") or []) <= 1:
        upd["scene_plan"] = []
    database.update_clone_job(job_id, **upd)
    _spawn_clone_job_task(job_id)
    return {"ok": True, "job": database.get_clone_job(job_id)}


@app.delete("/api/clone-jobs/{job_id}")
async def remove_or_cancel_clone_job(job_id: int):
    running = _active_job_tasks.pop(job_id, None)
    if running and not running.done():
        running.cancel()
    ok = database.delete_clone_job(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Không tìm thấy Clone Job.")
    return {"ok": True}


@app.get("/api/publish-tasks")
def get_publish_tasks():
    return {"tasks": database.list_publish_tasks()}


@app.post("/api/publish-tasks/preview")
def preview_publish_copy(product_id: int = 0, target_platform: str = "facebook_reels", custom_hook: str = ""):
    product = database.get_product(product_id) if product_id and product_id > 0 else None
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
