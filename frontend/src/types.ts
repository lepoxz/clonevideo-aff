export interface ReaShot {
  index: number;
  start: number;
  end: number;
  duration: number;
  label: string;
  confidence: number;
  verdict: string;
  remake_route: string;
  prompt: string;
  thumb_url: string;
}

export interface FlowSceneUnit {
  unit_index: number;
  title_vi: string;
  shot_indices: number[];
  start: number;
  end: number;
  target_duration: number;
  same_scene_as_prev?: boolean;
  reuse_prev_end_as_start?: boolean;
  action_vi?: string;
  ai_product_anchor_prompt_en?: string;
  ai_start_image_prompt_en?: string;
  ai_end_image_prompt_en?: string;
  flow_prompt_en: string;
  frames_prompt_en?: string;
  ref_url?: string;
  start_frame_url?: string;
  end_frame_url?: string;
  clip_url?: string;
  engine_used?: string;
  status?: 'pending' | 'generating' | 'done' | 'failed' | string;
}

export interface ReaBreakdown {
  source_note: string;
  verdict: string;
  product_en?: string;
  character_and_room_style_en?: string;
  ai_product_anchor_prompt_en?: string;
  best_clean_shot_index?: number;
  best_clean_frame_pos?: string;
  clean_crop_box_pct?: number[];
  overlay_text_boxes_pct?: number[][];
  veo_prompt_en?: string;
  scene_units?: FlowSceneUnit[];
  shots_count: number;
  duration: number;
  confidence: number;
  avg_shot_s: number;
  vlm_note: string;
  production_mix: Array<{ label: string; label_zh?: string; seconds: number; ratio: number }>;
  storyboard_url: string;
  report_url: string;
  shots: ReaShot[];
  video_md_excerpt: string;
  remake_md_excerpt: string;
}

export interface AgentReachChannelStatus {
  channel: string;
  label: string;
  category: string;
  description: string;
  level: string;
  status: string;
  hint: string;
  problems: string[];
  supports_login: boolean;
  logged_in: boolean | null;
  login_via: string | null;
  login_command: string;
  actions: string[];
}

export interface AgentReachFullStatus {
  installed: boolean;
  path: string;
  version: string;
  browser: {
    profile_dir?: string;
    chrome?: string;
    backend?: string | null;
    running?: boolean;
    headless?: boolean | null;
    opencli_connected?: boolean | null;
    fallback_reason?: string | null;
  };
  channels: AgentReachChannelStatus[];
  error?: string;
}

export interface CompetitorShop {
  shop_name: string;
  shop_url: string;
  product_url?: string;
  domain: string;
  page_id?: string;
  page_url: string;
  ad_library_url: string;
  ads_count: number;
  selling_price: string;
  original_price?: string;
  product_title?: string;
  source: string;
}

export interface MetaShopProduct {
  id: number;
  shop_id: number;
  library_id: string;
  product_title: string;
  caption: string;
  product_url: string;
  shop_url: string;
  selling_price: string;
  original_price: string;
  video_url: string;
  thumbnail_url: string;
  cta_text: string;
  ads_duplication_count: number;
  video_age_days: number;
  started_running_at: string;
  placements: string[];
  created_at: string;
}

export interface MetaShop {
  id: number;
  shop_key: string;
  page_id: string;
  shop_name: string;
  ig_handle: string;
  page_url: string;
  shop_url: string;
  domain: string;
  avatar_url: string;
  ad_library_url: string;
  active_ads_count: number;
  products_count: number;
  price_range: string;
  placements: string[];
  country: string;
  is_inbox_only: boolean;
  last_scanned_at: string;
  preview_products?: MetaShopProduct[];
  products?: MetaShopProduct[];
}

export interface MarketIntel {
  evaluated_at: string;
  spy_status?: 'baseline' | 'deep_spied' | string;
  product_query: string;
  is_potential: boolean;
  potential_score: number;
  potential_tier: 'S' | 'A' | 'B' | 'C' | string;
  verdict: string;
  evaluation_reasons: string[];
  velocity_views_per_day: number;
  engagement_rate: number;
  video_age_days: number;
  total_active_ads: number;
  active_shops_count: number;
  price_range: string;
  primary_shop_url: string;
  primary_product_url?: string;
  shops: CompetitorShop[];
}

export interface ViralVideo {
  id: number;
  platform:
    | 'meta_ads'
    | 'instagram'
    | 'facebook'
    | 'threads'
    | 'youtube'
    | 'bilibili'
    | 'xiaohongshu'
    | 'twitter'
    | 'reddit'
    | 'tiktok'
    | 'douyin'
    | 'v2ex'
    | 'xueqiu'
    | string;
  title: string;
  caption: string;
  author: string;
  source_url: string;
  video_url: string;
  thumbnail_url: string;
  local_path: string;
  views: number;
  likes: number;
  comments: number;
  shares: number;
  viral_score: number;
  sales_signals: string[];
  hook_text: string;
  script_summary: string;
  rea_report_url?: string;
  rea_breakdown?: ReaBreakdown | null;
  market_intel?: MarketIntel | null;
  shop_name?: string;
  shop_url?: string;
  product_url?: string;
  selling_price?: string;
  original_price?: string;
  meta_library_id?: string;
  meta_page_id?: string;
  ig_handle?: string;
  ad_placements?: string[];
  cta_text?: string;
  created_at: string;
}

export interface MuseToken {
  id: number;
  label: string;
  account_identifier: string;
  auth_token_masked: string;
  proxy: string;
  tokens_remaining: number;
  tokens_total: number;
  weekly_used: number;
  weekly_limit: number;
  status: 'active' | 'cooldown' | 'expired' | 'busy';
  last_used_at: string;
  notes: string;
}

export interface AffiliateProduct {
  id: number;
  code: string;
  name: string;
  platform_name: string;
  price: string;
  original_price: string;
  affiliate_url: string;
  image_url: string;
  cta_overlay_text: string;
  comment_template: string;
  bio_active: number;
  clicks_count: number;
  created_at: string;
}

export interface FlowAccount {
  id: number;
  label: string;
  email: string;
  tier: string;
  auth_mode: 'browser_profile' | 'cookie_json' | 'bearer_token' | 'gemini_api_key' | string;
  profile_dir: string;
  project_url: string;
  proxy: string;
  credits_remaining: number;
  credits_total: number;
  renders_used: number;
  weekly_limit: number;
  status: 'active' | 'login_pending' | 'cooldown' | 'expired' | string;
  last_used_at: string;
  notes: string;
  created_at: string;
  credential_masked: string;
  has_cookies: boolean;
  cookie_count: number;
  has_bearer: boolean;
  has_profile: boolean;
}

export interface FlowModelOption {
  id: string;
  group?: string;
  label: string;
  gemini_model: string;
  duration_hint?: string;
  badge?: string;
}

export interface CloneJob {
  id: number;
  source_video_id: number;
  product_id: number;
  muse_token_id: number | null;
  muse_token_label: string;
  flow_account_id?: number | null;
  flow_model?: string;
  veo_prompt?: string;
  scene_plan?: FlowSceneUnit[];
  clone_mode: string;
  prompt_script: string;
  cta_position: string;
  link_placement_mode: string;
  anti_duplicate: number;
  status: 'queued' | 'analyzing' | 'generating_muse' | 'compositing_ffmpeg' | 'completed' | 'failed';
  progress: number;
  output_video_url: string;
  generated_caption: string;
  generated_first_comment: string;
  tokens_spent: number;
  error_message: string;
  created_at: string;
  source_title?: string;
  source_platform?: string;
  product_name?: string;
  product_code?: string;
  product_url?: string;
}

export interface PublishTask {
  id: number;
  clone_job_id: number;
  product_id: number;
  target_platform: 'facebook_reels' | 'instagram_reels' | 'threads';
  account_name: string;
  caption: string;
  link_strategy: string;
  first_comment_text: string;
  bio_url_synced: number;
  status: string;
  published_url: string;
  comment_url: string;
  created_at: string;
  product_code?: string;
  product_name?: string;
  product_url?: string;
}

export interface SystemStatus {
  status: string;
  backend: string;
  ffmpeg_installed: boolean;
  ffmpeg_path: string;
  ytdlp_installed: boolean;
  ytdlp_path: string;
  agent_reach_installed: boolean;
  agent_reach_path: string;
  rea_video_installed: boolean;
  rea_video_path: string;
  playwright_installed: boolean;
  crawl4ai_installed: boolean;
  counts: {
    viral_videos: number;
    meta_shops?: number;
    products: number;
    clone_jobs: number;
    publish_tasks: number;
  };
  muse_pool: {
    total_accounts: number;
    active_accounts: number;
    total_tokens_remaining: number;
    weekly_used: number;
    weekly_capacity: number;
  };
  flow_pool?: {
    total_accounts: number;
    active_accounts: number;
    total_credits_remaining: number;
    renders_used: number;
    weekly_capacity: number;
  };
  settings: Record<string, string>;
}
