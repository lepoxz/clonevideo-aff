export interface ViralVideo {
  id: number;
  platform: 'instagram' | 'facebook' | 'threads' | 'meta_ads';
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

export interface CloneJob {
  id: number;
  source_video_id: number;
  product_id: number;
  muse_token_id: number | null;
  muse_token_label: string;
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
  playwright_installed: boolean;
  crawl4ai_installed: boolean;
  counts: {
    viral_videos: number;
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
  settings: Record<string, string>;
}
