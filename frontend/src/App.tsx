import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Award,
  CheckCircle2,
  ClipboardCopy,
  Cpu,
  Database,
  Download,
  ExternalLink,
  EyeOff,
  Film,
  Flame,
  FlaskConical,
  Globe,
  Info,
  KeyRound,
  Layers,
  LayoutGrid,
  Link2,
  List,
  LogIn,
  LogOut,
  MessageSquare,
  Moon,
  Play,
  Plus,
  RefreshCw,
  Scissors,
  Search,
  Send,
  Settings,
  ShieldCheck,
  ShoppingBag,
  Smartphone,
  Sparkles,
  Star,
  Sun,
  Terminal,
  Trash2,
  TrendingUp,
  Video,
  X,
  Zap,
} from 'lucide-react';
import { api } from './api';
import type {
  AffiliateProduct,
  AgentReachFullStatus,
  CloneJob,
  CompetitorShop,
  FlowAccount,
  FlowModelOption,
  FlowSceneUnit,
  MarketIntel,
  MetaShop,
  MetaShopProduct,
  MuseToken,
  PublishTask,
  SystemStatus,
  ViralVideo,
} from './types';

type SidebarTab =
  | 'quet-tu-khoa'
  | 'do-shop-meta'
  | 'dao-sau'
  | 'video-tiem-nang'
  | 'video-win'
  | 'video-scale'
  | 'sp-bo-sua'
  | 'video-da-quet'
  | 'theo-doi'
  | 'video-test'
  | 'clone-flow'
  | 'clone-muse'
  | 'kho-san-pham'
  | 'dang-bai'
  | 'cai-dat';

type KeywordSourceTab = 'tu-dao' | 'pinterest' | 'google';
type DeepDigFilter = 'all' | 'da-dao' | 'dang-dao' | 'cho-dao';
type SortMode = 'strongest' | 'newest' | 'shops';
type ViewMode = 'grid' | 'table';
type ScanStage = 'idle' | 'scanning' | 'digging' | 'done';
type FlowCloneMode =
  | 'flow_frames_start_end'
  | 'flow_ai_frames_remake'
  | 'flow_agent_auto'
  | 'flow_agent'
  | 'flow_omni_ingredients'
  | 'flow_veo_i2v'
  | 'flow_veo_t2v';

interface EnrichedVideo {
  raw: ViralVideo;
  videoAgeDays: number;
  storeAgeDays: number;
  isOldStoreWarning: boolean;
  winCount: number;
  scaleCount: number;
  oldAdsCount: number;
  shopActive: number;
  shopTotal: number;
  fanpageActive: number;
  fanpageTotal: number;
  totalAdsSameVideo: number;
  priceLabel: string;
  originalPriceLabel: string;
  sparkline14d: number[];
  categoryTab: 'video-tiem-nang' | 'video-win' | 'video-scale' | 'sp-bo-sua';
  categoryLabel: string;
  digStatus: 'da-dao' | 'dang-dao' | 'cho-dao';
  localMediaUrl: string;
  marketIntel: MarketIntel | null;
  potentialScore: number;
  potentialTier: string;
  isPotential: boolean;
  velocityViewsPerDay: number;
  engagementRate: number;
  primaryShopUrl: string;
  primaryProductUrl: string;
  placements: string[];
  metaPageId: string;
  shops: CompetitorShop[];
  isDeepSpied: boolean;
}

const PLATFORM_META: Record<string, { label: string; short: string; pillBg: string; pillColor: string }> = {
  meta_ads: { label: 'Meta Ads', short: 'FB Ads', pillBg: 'var(--xanh-bg)', pillColor: 'var(--link)' },
  instagram: { label: 'IG Reels', short: 'IG Reels', pillBg: '#fbe9f2', pillColor: '#b91c6e' },
  facebook: { label: 'FB Reels', short: 'FB Reels', pillBg: 'var(--xanh-bg)', pillColor: '#1d4ed8' },
  threads: { label: 'Threads', short: 'Threads', pillBg: 'var(--o)', pillColor: 'var(--chu)' },
  youtube: { label: 'YouTube', short: 'YouTube', pillBg: '#fee2e2', pillColor: '#dc2626' },
  bilibili: { label: 'Bilibili', short: 'Bilibili', pillBg: '#e0f2fe', pillColor: '#0284c7' },
  xiaohongshu: { label: 'Xiaohongshu', short: 'XHS', pillBg: '#ffe4e6', pillColor: '#e11d48' },
  twitter: { label: 'X / Twitter', short: 'X', pillBg: 'var(--o)', pillColor: 'var(--chu)' },
  reddit: { label: 'Reddit', short: 'Reddit', pillBg: '#ffedd5', pillColor: '#ea580c' },
  tiktok: { label: 'TikTok', short: 'TikTok', pillBg: '#f3e8ff', pillColor: '#7e22ce' },
  douyin: { label: 'Douyin', short: 'Douyin', pillBg: '#ecfeff', pillColor: '#0f766e' },
  v2ex: { label: 'V2EX', short: 'V2EX', pillBg: 'var(--xam)', pillColor: 'var(--mo)' },
  xueqiu: { label: 'Xueqiu', short: 'Xueqiu', pillBg: 'var(--xanh-bg)', pillColor: 'var(--link)' },
  web: { label: 'Web Search', short: 'Web', pillBg: 'var(--xam)', pillColor: 'var(--mo)' },
};

const VIDEO_TAB_INFO: Record<
  string,
  { title: string; subtitle: string; ruleTitle: string; rules: string[] }
> = {
  'video-tiem-nang': {
    title: 'Video Tiềm Năng (Đa Nền Tảng)',
    subtitle:
      'Tự đánh giá video đang viral ở mọi nền tảng · Bóc tách các Shop đang chạy, Link shop đang bán, Số lượng Ads & Giá đang bán thực tế',
    ruleTitle: 'Cơ chế Tự Đánh Giá Video Tiềm Năng & Dò Shop Đang Bán',
    rules: [
      'Tự động chấm điểm Tiềm Năng (0–100đ, Hạng S/A/B/C) trên mọi nền tảng (Meta Ads, IG Reels, TikTok, YouTube, Xiaohongshu, Bilibili...) theo tốc độ view/ngày, tỷ lệ tương tác và tín hiệu thương mại.',
      'Đối chiếu trực tiếp trên Meta Ad Library & Web Storefront để xác định chính xác các Shop đang chạy là ai và mở thẳng Link trang bán hàng thực tế.',
      'Đếm số lượng quảng cáo đang active thực tế của từng shop và bóc tách trực tiếp Giá đang bán trên trang sản phẩm (Shopify / WooCommerce / Sàn TMĐT / Ad Copy).',
    ],
  },
  'video-win': {
    title: 'Video Win',
    subtitle: 'Video 7–14 ngày tuổi · Đã vượt qua bài test và đang cắn tiền ổn định',
    ruleTitle: 'Luật lọc Video Win (SpyWinAds)',
    rules: [
      'Tuổi file video nằm trong khoảng 7 đến 14 ngày tuổi.',
      'Tỉ lệ QC giữ được từ 7 ngày trở lên (QC Win) chiếm ưu thế.',
      'Kiểm tra cảnh báo Ô tuổi trang bán: nếu trang bán cũng mới thì đây là Win thật.',
    ],
  },
  'video-scale': {
    title: 'Video scale',
    subtitle: 'Video 14–30 ngày tuổi · Đang được nhiều shop & fanpage nhân bản mạnh',
    ruleTitle: 'Luật lọc Video Scale (SpyWinAds)',
    rules: [
      'Tuổi video từ 14 đến 30 ngày với nhiều trang bán/fanpage cùng chạy một creative.',
      'Biểu đồ cột 14 ngày có xu hướng dựng lên liên tục trong tuần gần nhất.',
      'Rất phù hợp để Clone bằng Muse AI đổi Hook 3s đầu và gắn link Affiliate.',
    ],
  },
  'sp-bo-sua': {
    title: 'SP bò sữa',
    subtitle: 'Video > 30 ngày tuổi · Sản phẩm chạy bền bỉ, doanh thu đều đặn dài hạn',
    ruleTitle: 'Luật lọc SP Bò Sữa (SpyWinAds)',
    rules: [
      'Tuổi video trên 30 ngày mà vẫn duy trì lượng quảng cáo active đều đặn.',
      'Chứng minh nhu cầu thị trường thật, dễ bán quanh năm cho kênh Affiliate.',
    ],
  },
  'video-da-quet': {
    title: 'Video đã quét',
    subtitle: 'Toàn bộ video viral & winning ads đã thu thập từ giỏ quét và URL',
    ruleTitle: 'Kho lưu trữ toàn bộ Video đã quét',
    rules: [
      'Gồm tất cả video từ Meta Ads Library, Instagram Reels, Facebook Reels và Threads.',
      'Hỗ trợ tìm nhanh, tải MP4 sạch bằng yt-dlp và phân tích trước khi Clone.',
    ],
  },
  'theo-doi': {
    title: 'Theo dõi đặc biệt',
    subtitle: 'Danh sách video bạn gắn dấu ★ để theo dõi diễn biến Win / Scale hàng ngày',
    ruleTitle: 'Danh sách Theo dõi đặc biệt',
    rules: [
      'Bấm biểu tượng ★ trên thẻ video hoặc trong Khung Phân tích để ghim vào đây.',
      'Lưu cục bộ trên trình duyệt để so sánh các đối thủ đang test cùng ngách.',
    ],
  },
  'video-test': {
    title: 'Video test',
    subtitle: 'Video bạn đưa vào hàng đợi kiểm thử kịch bản & tỷ lệ chuyển đổi Affiliate',
    ruleTitle: 'Hàng đợi Video Test',
    rules: [
      'Lưu các ý tưởng chuẩn bị đưa sang Muse AI render hàng loạt biến thể.',
    ],
  },
};

const TRENDING_KEYWORDS: Record<KeywordSourceTab, { keyword: string; tag: string; heat: string }[]> = {
  'tu-dao': [
    { keyword: 'máy ép chậm mini', tag: 'Gia dụng hot', heat: '142 QC' },
    { keyword: 'serum rau má dịu da', tag: 'Skincare VN', heat: '98 QC' },
    { keyword: 'đèn ngủ hoàng hôn chill', tag: 'Decor', heat: '84 QC' },
    { keyword: 'bàn chải điện sóng âm', tag: 'Personal Care', heat: '76 QC' },
    { keyword: 'son kem lì lâu trôi', tag: 'Beauty', heat: '119 QC' },
    { keyword: 'quạt tích điện mini kẹp bàn', tag: 'Mùa hè', heat: '67 QC' },
    { keyword: 'kẹp tóc hàn quốc ngọc trai', tag: 'Phụ kiện', heat: '54 QC' },
    { keyword: 'tai nghe bluetooth gaming pin trâu', tag: 'Tech', heat: '108 QC' },
  ],
  pinterest: [
    { keyword: 'decor phòng ngủ chill', tag: 'Pinterest #1', heat: '+310%' },
    { keyword: 'kệ mỹ phẩm xoay 360', tag: 'Pinterest', heat: '+240%' },
    { keyword: 'đèn bàn học chống cận cảm ứng', tag: 'Pinterest', heat: '+195%' },
    { keyword: 'túi đeo chéo nữ minimalist', tag: 'Fashion', heat: '+180%' },
    { keyword: 'outfit công sở mùa hè', tag: 'Lookbook', heat: '+165%' },
    { keyword: 'cốc giữ nhiệt pastel cute', tag: 'Lifestyle', heat: '+140%' },
  ],
  google: [
    { keyword: 'kem chống nắng nâng tông', tag: 'Google Peak', heat: '90K/tháng' },
    { keyword: 'nồi chiên không dầu mini', tag: 'Google Trend', heat: '74K/tháng' },
    { keyword: 'máy lọc không khí phòng ngủ', tag: 'Google Trend', heat: '52K/tháng' },
    { keyword: 'gối công thái học chống mỏi cổ', tag: 'Sức khoẻ', heat: '41K/tháng' },
    { keyword: 'máy tăm nước cầm tay', tag: 'Nha khoa', heat: '63K/tháng' },
  ],
};

function formatCompact(n: number): string {
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(2)}B`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function resolveLocalMediaUrl(v: ViralVideo): string {
  if (v.local_path) {
    const normalized = v.local_path.replace(/\\/g, '/');
    const idx = normalized.indexOf('/media/');
    if (idx !== -1) return normalized.slice(idx);
    const relIdx = normalized.indexOf('media/');
    if (relIdx !== -1) return `/${normalized.slice(relIdx)}`;
  }
  if (v.video_url) {
    const vu = v.video_url.trim();
    if (
      vu.startsWith('/media/') ||
      vu.includes('.mp4') ||
      vu.includes('fbcdn.net') ||
      vu.includes('tiktokcdn.com') ||
      vu.includes('googlevideo.com')
    ) {
      return vu;
    }
  }
  return '';
}

function resolveEmbedUrl(v: ViralVideo): string {
  const s = (v.source_url || '').trim();
  if (!s) return '';
  const ytMatch =
    s.match(/[?&]v=([A-Za-z0-9_-]{6,})/) ||
    s.match(/youtu\.be\/([A-Za-z0-9_-]{6,})/) ||
    s.match(/youtube\.com\/shorts\/([A-Za-z0-9_-]{6,})/);
  if (ytMatch) {
    return `https://www.youtube.com/embed/${ytMatch[1]}?autoplay=1&rel=0`;
  }
  const ttMatch = s.match(/tiktok\.com\/@[^/]+\/video\/(\d+)/);
  if (ttMatch) {
    return `https://www.tiktok.com/embed/v2/${ttMatch[1]}`;
  }
  const igMatch = s.match(/instagram\.com\/(?:[^/]+\/)?(?:reel|p)\/([A-Za-z0-9_-]+)/);
  if (igMatch) {
    return '';
  }
  const biliMatch = s.match(/bilibili\.com\/video\/(BV[A-Za-z0-9]+)/i);
  if (biliMatch) {
    return `https://player.bilibili.com/player.html?bvid=${biliMatch[1]}&high_quality=1&autoplay=1`;
  }
  return '';
}

function enrichVideo(v: ViralVideo): EnrichedVideo {
  const mi = v.market_intel || null;
  const sigText = (v.sales_signals || []).join(' | ');
  const fullText = `${v.title} ${v.caption} ${sigText}`;

  // 1. Real Video File Age
  const ageMatch = sigText.match(/File\s+(\d+)\s*ngày/i);
  let videoAgeDays = mi?.video_age_days || (ageMatch ? Math.max(1, parseInt(ageMatch[1], 10)) : 0);
  if (!videoAgeDays) {
    const createdMs = Date.parse(v.created_at || '');
    const diffDays = Number.isFinite(createdMs)
      ? Math.max(1, Math.round((Date.now() - createdMs) / 86400000))
      : 5;
    videoAgeDays = diffDays;
  }

  // 2. Real Active Ads & Competitor Shops (Zero fake math formulas)
  const scaleMatch = sigText.match(/Scale\s+(\d+)\s*QC/i);
  const rawScaleAds = scaleMatch ? Math.max(1, parseInt(scaleMatch[1], 10)) : v.platform === 'meta_ads' ? 1 : 0;

  const views = Math.max(1, v.views || 0);
  const likes = Math.max(0, v.likes || 0);
  const comments = Math.max(0, v.comments || 0);
  const shares = Math.max(0, v.shares || 0);
  const engRate = mi?.engagement_rate ?? Number((((likes + comments * 3 + shares * 4) / views) * 100).toFixed(2));
  const velocityViewsPerDay = mi?.velocity_views_per_day ?? Math.max(1, Math.round(views / Math.max(1, videoAgeDays)));

  const shops: CompetitorShop[] = Array.isArray(mi?.shops) ? mi!.shops : [];
  const totalAdsSameVideo = mi ? Math.max(mi.total_active_ads || 0, rawScaleAds) : rawScaleAds;
  const shopActive = mi ? Math.max(mi.active_shops_count || 0, shops.length) : v.platform === 'meta_ads' ? 1 : 0;
  const shopTotal = shopActive;
  const fanpageActive = shopActive;
  const fanpageTotal = shopTotal;

  const scaleCount = videoAgeDays <= 7 ? totalAdsSameVideo : rawScaleAds;
  const winCount = videoAgeDays > 7 && videoAgeDays <= 30 ? totalAdsSameVideo : 0;
  const oldAdsCount = videoAgeDays > 30 ? totalAdsSameVideo : 0;

  const potentialScore = mi?.potential_score ?? Math.min(95, Math.max(35, v.viral_score || 75));
  const potentialTier = mi?.potential_tier || (potentialScore >= 82 ? 'S' : potentialScore >= 68 ? 'A' : potentialScore >= 52 ? 'B' : 'C');
  const isPotential = mi ? Boolean(mi.is_potential) : potentialScore >= 68 && videoAgeDays <= 45;
  const isDeepSpied = Boolean(mi && (mi.spy_status === 'deep_spied' || shops.length > 0 || v.product_url || v.shop_url));
  const primaryShopUrl = v.shop_url || mi?.primary_shop_url || shops.find((s) => s.shop_url)?.shop_url || '';
  const primaryProductUrl = v.product_url || mi?.primary_product_url || shops.find((s) => s.product_url)?.product_url || '';
  const placements =
    Array.isArray(v.ad_placements) && v.ad_placements.length > 0
      ? v.ad_placements.map((p) => p.toLowerCase())
      : ['facebook', 'instagram', 'threads'].includes((v.platform || '').toLowerCase())
      ? [(v.platform || '').toLowerCase()]
      : ['facebook', 'instagram'];
  const metaPageId = v.meta_page_id || shops.find((s) => s.page_id)?.page_id || '';

  // 3. Real Category Classification (Tiềm năng / Win / Scale / Bò sữa)
  let categoryTab: EnrichedVideo['categoryTab'] = 'video-win';
  let categoryLabel = 'Video Win';
  if (rawScaleAds >= 2 || totalAdsSameVideo >= 10) {
    categoryTab = 'video-scale';
    categoryLabel = 'Video scale';
  } else if (isPotential && videoAgeDays <= 14) {
    categoryTab = 'video-tiem-nang';
    categoryLabel = `Tiềm Năng (${potentialTier})`;
  } else if (videoAgeDays > 30) {
    categoryTab = 'sp-bo-sua';
    categoryLabel = 'SP bò sữa';
  } else {
    categoryTab = 'video-win';
    categoryLabel = 'Video Win';
  }

  const isOldStoreWarning = videoAgeDays > 90;
  const storeAgeDays = videoAgeDays;

  // 4. Real Selling Price Detection
  const priceSig = (v.sales_signals || []).find((s) => s.startsWith('Giá:'));
  const priceRegex =
    fullText.match(/(?:₫|vnđ|vnd)\s*\d{1,3}(?:[.,]\d{3})+/i) ||
    fullText.match(/\b\d{1,3}(?:[.,]\d{3})+\s*(?:₫|đ|vnđ|vnd)\b/i) ||
    fullText.match(/\b(?:chỉ|giá|sale|còn)\s+\d{2,4}\s*k\b/i) ||
    fullText.match(/\$\s*\d+(?:\.\d{1,2})?\b/);
  const miPrice = mi?.price_range && mi.price_range !== 'Chưa niêm yết giá' ? mi.price_range : '';
  const priceLabel = v.selling_price
    ? v.selling_price
    : miPrice
    ? miPrice
    : priceSig
    ? priceSig.replace(/^Giá:\s*/i, '')
    : priceRegex
    ? priceRegex[0]
    : 'Chưa niêm yết giá';
  const originalPriceLabel = v.original_price || shops.find((s) => s.original_price)?.original_price || '';

  // 5. Momentum curve derived from real potentialScore & velocity
  const baseMomentum = Math.min(78, Math.max(22, Math.round(potentialScore * 0.68)));
  const sparkline14d: number[] = [];
  for (let i = 0; i < 14; i++) {
    const growth = isPotential || categoryTab === 'video-scale' ? i * 2.1 : i * 0.8;
    const val = Math.min(100, Math.max(16, Math.round(baseMomentum + growth - (13 - i) * 1.1)));
    sparkline14d.push(val);
  }

  const localMediaUrl = resolveLocalMediaUrl(v);
  const digStatus: EnrichedVideo['digStatus'] = localMediaUrl ? 'da-dao' : 'cho-dao';

  return {
    raw: v,
    videoAgeDays,
    storeAgeDays,
    isOldStoreWarning,
    winCount,
    scaleCount,
    oldAdsCount,
    shopActive,
    shopTotal,
    fanpageActive,
    fanpageTotal,
    totalAdsSameVideo,
    priceLabel,
    originalPriceLabel,
    sparkline14d,
    categoryTab,
    categoryLabel,
    digStatus,
    localMediaUrl,
    marketIntel: mi,
    potentialScore,
    potentialTier,
    isPotential,
    velocityViewsPerDay,
    engagementRate: engRate,
    primaryShopUrl,
    primaryProductUrl,
    placements,
    metaPageId,
    shops,
    isDeepSpied,
  };
}

function SpyWinLogo({ size = 28 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="shrink-0 shadow-sm"
    >
      <rect width="100" height="100" rx="24" fill="#0b0b0d" />
      <path
        d="M140 18H43A13 13 0 0 0 36.53 42.27L63.47 57.73A13 13 0 0 1 57 82H-40"
        stroke="#ffffff"
        strokeWidth="12"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function Sparkline({
  bars,
  highlightColor = 'var(--xanh)',
  tall = false,
}: {
  bars: number[];
  highlightColor?: string;
  tall?: boolean;
}) {
  return (
    <div className="spk" style={tall ? { height: 52, gap: 4 } : undefined} title="Lịch sử 14 ngày gần nhất">
      {bars.map((val, idx) => {
        const isRecent = idx >= bars.length - 4;
        return (
          <div
            key={idx}
            className="spk-bar"
            style={{
              height: `${Math.max(15, val)}%`,
              background: isRecent ? highlightColor : 'var(--vien)',
              opacity: isRecent ? 0.95 : 0.72,
            }}
            title={`Ngày ${idx + 1}: ${val} tín hiệu`}
          />
        );
      })}
    </div>
  );
}

type FlowEngineKind = 'agent' | 'frames' | 'ingredients' | 't2v';

interface FlowEngineBadge {
  label: string;
  bg: string;
  color: string;
  title: string;
}

function detectFlowEngineKind(rawText: string, allowLooseModels = false): FlowEngineKind | null {
  const text = rawText.toLowerCase();
  if (!text) return null;
  if (
    text.includes('frame') ||
    text.includes('start_end') ||
    text.includes('first_end') ||
    text.includes('first-end') ||
    text.includes('first→end') ||
    text.includes('đầu→cuối') ||
    text.includes('đầu → cuối') ||
    text.includes('khung đầu')
  ) {
    return 'frames';
  }
  if (text.includes('agent') || text.includes('tác nhân') || text.includes('tac nhan')) {
    return 'agent';
  }
  if (allowLooseModels) {
    if (text.includes('ingredient')) return 'ingredients';
    if (text.includes('t2v') || text.includes('text')) return 't2v';
  }
  return null;
}

function mapFlowEngineKindToBadge(kind: FlowEngineKind, title: string): FlowEngineBadge {
  switch (kind) {
    case 'frames':
      return { label: '🎨 AI Remake Đầu → Cuối', bg: 'var(--la-bg)', color: 'var(--la)', title };
    case 'agent':
      return { label: '🤖 Tác nhân Google Flow', bg: 'var(--xanh-bg)', color: 'var(--link)', title };
    case 'ingredients':
      return { label: '🧩 AI Ingredients Remake', bg: 'var(--cam-bg)', color: 'var(--cam)', title };
    case 't2v':
      return { label: '✍️ Text-to-Video', bg: 'var(--xam)', color: 'var(--chu)', title };
  }
}

function getFlowJobEngineBadge(job: CloneJob): FlowEngineBadge | null {
  const sceneEngine = (job.scene_plan?.find((s) => s.engine_used)?.engine_used || '').trim();
  const sceneKind = detectFlowEngineKind(sceneEngine, true);
  if (sceneKind) {
    return mapFlowEngineKindToBadge(sceneKind, `Engine thực thi: ${sceneEngine}`);
  }

  const tokenLabel = (job.muse_token_label || '').trim();
  const tokenKind = detectFlowEngineKind(tokenLabel, false);
  if (tokenKind) {
    return mapFlowEngineKindToBadge(tokenKind, tokenLabel);
  }

  const mode = (job.clone_mode || '').trim().toLowerCase();
  const modeMap: Record<string, FlowEngineKind> = {
    flow_frames_start_end: 'frames',
    flow_ai_frames_remake: 'frames',
    flow_agent_auto: 'frames',
    flow_agent: 'agent',
    flow_omni_ingredients: 'ingredients',
    flow_veo_t2v: 't2v',
  };
  const fallbackKind = modeMap[mode];
  return fallbackKind ? mapFlowEngineKindToBadge(fallbackKind, `Chế độ: ${job.clone_mode}`) : null;
}

export default function App() {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    const saved = localStorage.getItem('spywin_theme');
    return saved === 'dark' ? 'dark' : 'light';
  });
  const [activeTab, setActiveTab] = useState<SidebarTab>('video-win');
  const [toast, setToast] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);

  // Backend Data
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [videos, setVideos] = useState<ViralVideo[]>([]);
  const [tokens, setTokens] = useState<MuseToken[]>([]);
  const [products, setProducts] = useState<AffiliateProduct[]>([]);
  const [jobs, setJobs] = useState<CloneJob[]>([]);
  const [publishTasks, setPublishTasks] = useState<PublishTask[]>([]);

  // Global Header & Video Tab Controls
  const [globalSearch, setGlobalSearch] = useState('');
  const [filterPlatform, setFilterPlatform] = useState('all');
  const [sortMode, setSortMode] = useState<SortMode>('strongest');
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [showRulesBox, setShowRulesBox] = useState(false);

  // Personal SpyWinAds Lists (persisted locally)
  const [watchlistIds, setWatchlistIds] = useState<number[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('spywin_watchlist') || '[1]');
    } catch {
      return [1];
    }
  });
  const [testlistIds, setTestlistIds] = useState<number[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('spywin_testlist') || '[2]');
    } catch {
      return [2];
    }
  });
  const [hiddenIds, setHiddenIds] = useState<number[]>([]);

  // Right-side Slide-Over Analysis Drawer
  const [drawerVideoId, setDrawerVideoId] = useState<number | null>(null);

  // View 1: Quét từ khoá
  const [kwSourceTab, setKwSourceTab] = useState<KeywordSourceTab>('tu-dao');
  const [scanBasket, setScanBasket] = useState('máy ép chậm mini\nserum rau má dịu da');
  const [matchType, setMatchType] = useState<'exact' | 'broad'>('exact');
  const [marketCountry, setMarketCountry] = useState('VN');
  const [crawlPlatform, setCrawlPlatform] = useState('all');
  const [crawlEngine, setCrawlEngine] = useState('agent_reach');
  const [scanStage, setScanStage] = useState<ScanStage>('idle');
  const [inspectUrlInput, setInspectUrlInput] = useState('');
  const [isInspecting, setIsInspecting] = useState(false);
  const [crawlNotes, setCrawlNotes] = useState<string[]>([]);

  // Agent-Reach Direct Action Explorer (View 1) & Account/Channel Manager (View 7)
  const [arExecChannel, setArExecChannel] = useState('youtube');
  const [arExecAction, setArExecAction] = useState('search');
  const [arExecQuery, setArExecQuery] = useState('');
  const [arExecRunning, setArExecRunning] = useState(false);
  const [arExecResult, setArExecResult] = useState<string>('');
  const [arStatus, setArStatus] = useState<AgentReachFullStatus | null>(null);
  const [arLoading, setArLoading] = useState(false);
  const [arBusyKey, setArBusyKey] = useState<string | null>(null);
  const [arActionOutput, setArActionOutput] = useState<string>('');
  const [arCfgKey, setArCfgKey] = useState('openai-key');
  const [arCfgVal, setArCfgVal] = useState('');

  // rea-video Decompose & Market Spy state
  const [reaBusyVideoId, setReaBusyVideoId] = useState<number | null>(null);
  const [spyingVideoId, setSpyingVideoId] = useState<number | null>(null);
  const [batchSpyRunning, setBatchSpyRunning] = useState(false);
  const [potentialTierFilter, setPotentialTierFilter] = useState<'all' | 'S' | 'A' | 'has_shop'>('all');
  const [potentialSpyCountry, setPotentialSpyCountry] = useState<'AUTO' | 'VN' | 'US'>('AUTO');
  const [customSpyQuery, setCustomSpyQuery] = useState('');

  // View 2: Đào sâu
  const [deepFilter, setDeepFilter] = useState<DeepDigFilter>('all');

  // View 4: Organic Remake & Muse Studio
  const [selectedVideoId, setSelectedVideoId] = useState<number>(1);
  const [selectedProductId, setSelectedProductId] = useState<number>(0);
  const [cloneMode, setCloneMode] = useState('rea_video_remake');
  const [ctaPosition, setCtaPosition] = useState('clean_organic');
  const [linkPlacementMode, setLinkPlacementMode] = useState('both');
  const [promptScript, setPromptScript] = useState('');
  const [antiDuplicate, setAntiDuplicate] = useState(true);
  const [batchCount, setBatchCount] = useState(1);
  const [isLaunchingClone, setIsLaunchingClone] = useState(false);
  const [activeCloneJobId, setActiveCloneJobId] = useState<number | null>(null);
  const [activeFlowJobId, setActiveFlowJobId] = useState<number | null>(null);
  const knownCompletedJobIdsRef = useRef<Set<number> | null>(null);
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [bulkTokenText, setBulkTokenText] = useState(
    'Muse_VN_04|muse_sess_demo_token_vn04_1b_xyz|http://103.1.1.10:8080\nMuse_VN_05|muse_sess_demo_token_vn05_1b_abc|'
  );
  const [bulkWeeklyLimit, setBulkWeeklyLimit] = useState(50);

  // View 5: Products & Bio
  const [prodForm, setProdForm] = useState({
    code: '',
    name: '',
    platform_name: 'Shopee',
    price: '',
    original_price: '',
    affiliate_url: '',
    image_url: '',
    comment_template: '',
  });
  const [bioSearch, setBioSearch] = useState('');

  // View 6: Publish & Auto-Comment
  const [pubJobId, setPubJobId] = useState<number | null>(null);
  const [pubPlatform, setPubPlatform] = useState<'facebook_reels' | 'instagram_reels' | 'threads'>('facebook_reels');
  const [pubAccount, setPubAccount] = useState('@deal.ngon.aff');
  const [pubCaption, setPubCaption] = useState('');
  const [pubFirstComment, setPubFirstComment] = useState('');

  // Settings & VLM Model Fetcher
  const [tregApiKey, setTregApiKey] = useState('');
  const [bioBrandName, setBioBrandName] = useState('');
  const [bioBrandSub, setBioBrandSub] = useState('');
  const [reaVlmEnabled, setReaVlmEnabled] = useState('0');
  const [reaVlmBaseUrl, setReaVlmBaseUrl] = useState('https://api.openai.com/v1');
  const [reaVlmApiKey, setReaVlmApiKey] = useState('');
  const [reaVlmModel, setReaVlmModel] = useState('gemini-2.5-pro,gpt-4o');
  const [reaReportLang, setReaReportLang] = useState('en');
  const [vlmFetchedModels, setVlmFetchedModels] = useState<string[]>([]);
  const [vlmRecommendedModels, setVlmRecommendedModels] = useState<string[]>([]);
  const [vlmFetchingModels, setVlmFetchingModels] = useState(false);

  // Google Flow (flow.google.com) Accounts & Studio state
  const [flowAccounts, setFlowAccounts] = useState<FlowAccount[]>([]);
  const [flowModels, setFlowModels] = useState<FlowModelOption[]>([]);
  const [selectedFlowAccountId, setSelectedFlowAccountId] = useState<number>(0);
  const [flowCloneMode, setFlowCloneMode] = useState<FlowCloneMode>('flow_frames_start_end');
  const [flowModelId, setFlowModelId] = useState<string>('omni_1_2_flash_10s_portrait');
  const [customFlowModelId, setCustomFlowModelId] = useState<string>('');
  const [syncingFlowModels, setSyncingFlowModels] = useState(false);
  const [flowVeoPrompt, setFlowVeoPrompt] = useState<string>('');
  const [flowScenePlan, setFlowScenePlan] = useState<FlowSceneUnit[]>([]);
  const [flowRefFrameUrl, setFlowRefFrameUrl] = useState<string>('');
  const [previewFlowClipUrl, setPreviewFlowClipUrl] = useState<string>('');
  const [flowGeneratingPrompt, setFlowGeneratingPrompt] = useState(false);
  const [showFlowImportModal, setShowFlowImportModal] = useState(false);
  const [flowBulkText, setFlowBulkText] = useState('');
  const [flowBulkLimit, setFlowBulkLimit] = useState(50);
  const [flowBulkTier, setFlowBulkTier] = useState('Flow Pro');
  const [flowLoginLabel, setFlowLoginLabel] = useState('');
  const [flowLoginProxy, setFlowLoginProxy] = useState('');
  const [flowBusyAccId, setFlowBusyAccId] = useState<number | null>(null);

  const availableFlowModels = useMemo<FlowModelOption[]>(() => {
    if (flowModels.length > 0) return flowModels;
    return [
      {
        id: 'omni_1_2_flash_10s_portrait',
        group: 'OmniFlash / Gemini Omni (Mới nhất 2026)',
        label: '⚡ Omni 1.2 Flash (≤10s) — Dọc 9:16 (Mới nhất · Nhanh & Có Free 50/ngày)',
        gemini_model: 'veo-3.1-fast-generate-preview',
        duration_hint: '8-10s',
        badge: 'Mới nhất · OmniFlash',
      },
      {
        id: 'omni_1_2_flash_15s_portrait',
        group: 'OmniFlash / Gemini Omni (Mới nhất 2026)',
        label: '🔥 Omni 1.2 Flash (11–15s) — Dọc 9:16 (Video dài · AI Plus/Pro/Ultra)',
        gemini_model: 'veo-3.1-generate-preview',
        duration_hint: '11-15s',
        badge: '15s Extended',
      },
      {
        id: 'gemini_omni_multimodal_portrait',
        group: 'OmniFlash / Gemini Omni (Mới nhất 2026)',
        label: '✨ Gemini Omni Multimodal — Ingredients / Scenebuilder 9:16',
        gemini_model: 'veo-3.1-generate-preview',
        duration_hint: '8-15s',
        badge: 'Ingredients AI',
      },
      {
        id: 'veo_3_1_lite_portrait',
        group: 'Veo 3.1 (Thế hệ mới nhất)',
        label: '🚀 Veo 3.1 Lite — Dọc 9:16 (Siêu nhanh · Có trong gói Free)',
        gemini_model: 'veo-3.1-fast-generate-preview',
        duration_hint: '8s',
        badge: 'Tiết kiệm Credit',
      },
      {
        id: 'veo_3_1_t2v_fast_portrait',
        group: 'Veo 3.1 (Thế hệ mới nhất)',
        label: '⚡ Veo 3.1 Fast — Dọc 9:16 (Chuẩn Ads / Affiliate)',
        gemini_model: 'veo-3.1-fast-generate-preview',
        duration_hint: '8s',
        badge: 'Khuyên dùng Ads',
      },
      {
        id: 'veo_3_1_t2v_fast_portrait_ultra',
        group: 'Veo 3.1 (Thế hệ mới nhất)',
        label: '💎 Veo 3.1 Fast Ultra — Dọc 9:16 (Độ nét cao · AI Ultra)',
        gemini_model: 'veo-3.1-fast-generate-preview',
        duration_hint: '8s',
        badge: 'Ultra 1080p+',
      },
      {
        id: 'veo_3_1_t2v_portrait',
        group: 'Veo 3.1 (Thế hệ mới nhất)',
        label: '🎬 Veo 3.1 Quality / Pro — Dọc 9:16 (Điện ảnh cao cấp + Audio)',
        gemini_model: 'veo-3.1-generate-preview',
        duration_hint: '8s',
        badge: 'Max Quality',
      },
      {
        id: 'nano_banana_pro_omni_flash',
        group: 'Nano Banana + Flow Hybrid (Ingredients 2026)',
        label: '🍌 Nano Banana Pro + Omni 1.2 Flash — Giữ chuẩn SP & Nhân vật 9:16',
        gemini_model: 'veo-3.1-fast-generate-preview',
        duration_hint: '10s',
        badge: 'Giữ mẫu SP 99%',
      },
      {
        id: 'nano_banana_2_1_veo_3_1',
        group: 'Nano Banana + Flow Hybrid (Ingredients 2026)',
        label: '🍌 Nano Banana 2.1 + Veo 3.1 — Dựng cảnh SP Studio 9:16',
        gemini_model: 'veo-3.1-generate-preview',
        duration_hint: '8s',
        badge: 'Studio SP',
      },
      {
        id: 'veo_3_0_fast_portrait',
        group: 'Veo 3.0 & Veo 2 (Tương thích rộng)',
        label: 'Veo 3.0 Fast — Dọc 9:16',
        gemini_model: 'veo-3.0-fast-generate-001',
        duration_hint: '8s',
        badge: 'Veo 3.0',
      },
      {
        id: 'veo_3_0_portrait',
        group: 'Veo 3.0 & Veo 2 (Tương thích rộng)',
        label: 'Veo 3.0 Standard — Dọc 9:16',
        gemini_model: 'veo-3.0-generate-001',
        duration_hint: '8s',
        badge: 'Veo 3.0',
      },
      {
        id: 'veo_2_1_fast_d_15_t2v',
        group: 'Veo 3.0 & Veo 2 (Tương thích rộng)',
        label: 'Veo 2.1 Fast — Dọc 9:16 (Ổn định / Nhẹ credit)',
        gemini_model: 'veo-2.0-generate-001',
        duration_hint: '8s',
        badge: 'Legacy',
      },
    ];
  }, [flowModels]);

  const groupedFlowModels = useMemo(() => {
    const map = new Map<string, FlowModelOption[]>();
    for (const m of availableFlowModels) {
      const grp = m.group || 'Mô hình Google Flow khác';
      if (!map.has(grp)) map.set(grp, []);
      map.get(grp)!.push(m);
    }
    return Array.from(map.entries());
  }, [availableFlowModels]);

  const selectedFlowModelMeta = useMemo(
    () => availableFlowModels.find((m) => m.id === flowModelId) || null,
    [availableFlowModels, flowModelId]
  );

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('spywin_theme', theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem('spywin_watchlist', JSON.stringify(watchlistIds));
  }, [watchlistIds]);

  useEffect(() => {
    localStorage.setItem('spywin_testlist', JSON.stringify(testlistIds));
  }, [testlistIds]);

  // Dedicated Module: Dò Shop & Sản Phẩm Đang Bán (Meta Ads -> FB / IG / Threads)
  const [metaShops, setMetaShops] = useState<MetaShop[]>([]);
  const [metaShopQuery, setMetaShopQuery] = useState('dây chuyền bạc');
  const [metaShopCountry, setMetaShopCountry] = useState<'VN' | 'US' | 'ALL'>('VN');
  const [metaShopPlatform, setMetaShopPlatform] = useState<'all' | 'facebook' | 'instagram' | 'threads'>('all');
  const [metaShopSearching, setMetaShopSearching] = useState(false);
  const [metaTotalMarketAds, setMetaTotalMarketAds] = useState(0);
  const [selectedMetaShop, setSelectedMetaShop] = useState<MetaShop | null>(null);
  const [selectedMetaShopProducts, setSelectedMetaShopProducts] = useState<MetaShopProduct[]>([]);
  const [scanningShopKey, setScanningShopKey] = useState<string | null>(null);
  const [importingShopProdId, setImportingShopProdId] = useState<number | null>(null);

  const notify = (text: string, type: 'ok' | 'err' = 'ok') => {
    setToast({ text, type });
    setTimeout(() => setToast(null), 4000);
  };

  const refreshAll = async () => {
    try {
      const [st, vd, ms, tk, fl, pr, jb, pt] = await Promise.all([
        api.getStatus(),
        api.getVideos('all', ''),
        api.getMetaShops(),
        api.getMuseTokens(),
        api.getFlowAccounts(),
        api.getProducts(),
        api.getCloneJobs(),
        api.getPublishTasks(),
      ]);
      setStatus(st);
      setVideos(vd.videos);
      setMetaShops(ms.shops || []);
      if (!selectedMetaShop && ms.shops && ms.shops.length > 0) {
        setSelectedMetaShop(ms.shops[0]);
        setSelectedMetaShopProducts(ms.shops[0].preview_products || []);
      }
      setTokens(tk.tokens);
      setFlowAccounts(fl.accounts);
      if (fl.models && fl.models.length > 0) setFlowModels(fl.models);
      setProducts(pr.products);
      setJobs(jb.jobs);
      setPublishTasks(pt.tasks);

      setTregApiKey(st.settings?.treg_api_key || '');
      setBioBrandName(st.settings?.bio_brand_name || '');
      setBioBrandSub(st.settings?.bio_brand_subtitle || '');
      setReaVlmEnabled(st.settings?.rea_vlm_enabled || '0');
      setReaVlmBaseUrl(st.settings?.rea_vlm_base_url || 'https://api.openai.com/v1');
      setReaVlmApiKey(st.settings?.rea_vlm_api_key || '');
      setReaVlmModel(st.settings?.rea_vlm_model || 'gemini-2.5-pro,gpt-4o');
      setReaReportLang(st.settings?.rea_report_lang || 'en');

      if (vd.videos.length > 0 && !vd.videos.some((v) => v.id === selectedVideoId)) {
        setSelectedVideoId(vd.videos[0].id);
        setPromptScript(vd.videos[0].hook_text || vd.videos[0].title);
      }
      if (selectedProductId > 0 && pr.products.length > 0 && !pr.products.some((p) => p.id === selectedProductId)) {
        setSelectedProductId(0);
      }
      const completed = jb.jobs.find((j) => j.status === 'completed');
      const completedFlow = jb.jobs.find((j) => j.clone_mode.startsWith('flow_') && j.status === 'completed');
      const completedMuse = jb.jobs.find((j) => !j.clone_mode.startsWith('flow_') && j.status === 'completed');
      if (completed && pubJobId === null) {
        setPubJobId(completed.id);
      }
      if (completedFlow && activeFlowJobId === null) {
        setActiveFlowJobId(completedFlow.id);
      }
      if (completedMuse && activeCloneJobId === null) {
        setActiveCloneJobId(completedMuse.id);
      }
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : 'Lỗi kết nối backend', 'err');
    }
  };

  useEffect(() => {
    refreshAll();
  }, []);

  // Auto-poll when clone jobs or Flow browser logins are actively processing
  useEffect(() => {
    const hasRunningJob = jobs.some((j) => !['completed', 'failed'].includes(j.status));
    const hasPendingFlowLogin = flowAccounts.some((a) => a.status === 'login_pending');
    if (!hasRunningJob && !hasPendingFlowLogin) return;
    const timer = setInterval(async () => {
      try {
        const [jb, tk, fl, st] = await Promise.all([
          api.getCloneJobs(),
          api.getMuseTokens(),
          api.getFlowAccounts(),
          api.getStatus(),
        ]);
        setJobs(jb.jobs);
        setTokens(tk.tokens);
        setFlowAccounts(fl.accounts);
        setStatus(st);
      } catch {
        // ignore transient poll error
      }
    }, 1500);
    return () => clearInterval(timer);
  }, [jobs, flowAccounts]);

  const enrichedVideos = useMemo(
    () => videos.filter((v) => !hiddenIds.includes(v.id)).map(enrichVideo),
    [videos, hiddenIds]
  );

  // Counts for Sidebar Navigation
  const tabCounts = useMemo(() => {
    return {
      'video-tiem-nang': enrichedVideos.filter((e) => e.isPotential || e.categoryTab === 'video-tiem-nang').length,
      'video-win': enrichedVideos.filter((e) => e.categoryTab === 'video-win').length,
      'video-scale': enrichedVideos.filter((e) => e.categoryTab === 'video-scale').length,
      'sp-bo-sua': enrichedVideos.filter((e) => e.categoryTab === 'sp-bo-sua').length,
      'video-da-quet': enrichedVideos.length,
      'theo-doi': enrichedVideos.filter((e) => watchlistIds.includes(e.raw.id)).length,
      'video-test': enrichedVideos.filter((e) => testlistIds.includes(e.raw.id)).length,
    };
  }, [enrichedVideos, watchlistIds, testlistIds]);

  const potentialSummary = useMemo(() => {
    const potList = enrichedVideos.filter((e) => e.isPotential || e.categoryTab === 'video-tiem-nang');
    const uniqueDomains = new Set<string>();
    let shopsWithLinks = 0;
    let totalAds = 0;
    let pricedCount = 0;
    const platformsSet = new Set<string>();

    for (const item of potList) {
      platformsSet.add(item.raw.platform);
      totalAds += item.totalAdsSameVideo;
      if (item.priceLabel && item.priceLabel !== 'Chưa niêm yết giá') pricedCount += 1;
      for (const s of item.shops) {
        const key = (s.domain || s.shop_name || '').toLowerCase();
        if (key && !uniqueDomains.has(key)) {
          uniqueDomains.add(key);
          if (s.shop_url) shopsWithLinks += 1;
        }
      }
    }
    return {
      totalPotential: potList.length,
      tierSCount: potList.filter((e) => e.potentialTier === 'S').length,
      platformsCount: platformsSet.size,
      uniqueShopsCount: uniqueDomains.size,
      shopsWithLinks,
      totalActiveAds: totalAds,
      pricedCount,
      unspiedCount: potList.filter((e) => !e.isDeepSpied).length,
    };
  }, [enrichedVideos]);

  const isVideoTab = (tab: SidebarTab) =>
    [
      'video-tiem-nang',
      'video-win',
      'video-scale',
      'sp-bo-sua',
      'video-da-quet',
      'theo-doi',
      'video-test',
    ].includes(tab);

  const displayedVideos = useMemo(() => {
    let list = enrichedVideos;
    if (activeTab === 'video-tiem-nang') {
      list = list.filter((e) => e.isPotential || e.categoryTab === 'video-tiem-nang');
      if (potentialTierFilter === 'S') list = list.filter((e) => e.potentialTier === 'S');
      else if (potentialTierFilter === 'A') list = list.filter((e) => e.potentialTier === 'A');
      else if (potentialTierFilter === 'has_shop') list = list.filter((e) => e.shops.length > 0 || Boolean(e.primaryShopUrl));
    } else if (activeTab === 'video-win') list = list.filter((e) => e.categoryTab === 'video-win');
    else if (activeTab === 'video-scale') list = list.filter((e) => e.categoryTab === 'video-scale');
    else if (activeTab === 'sp-bo-sua') list = list.filter((e) => e.categoryTab === 'sp-bo-sua');
    else if (activeTab === 'theo-doi') list = list.filter((e) => watchlistIds.includes(e.raw.id));
    else if (activeTab === 'video-test') list = list.filter((e) => testlistIds.includes(e.raw.id));

    if (filterPlatform !== 'all') {
      const fp = filterPlatform.toLowerCase();
      list = list.filter((e) => {
        const rawPf = (e.raw.platform || '').toLowerCase();
        if (rawPf === fp) return true;
        if (['facebook', 'instagram', 'threads'].includes(fp) && e.placements.includes(fp)) return true;
        if (fp === 'meta_ads' && Boolean(e.raw.meta_library_id)) return true;
        return false;
      });
    }

    if (globalSearch.trim()) {
      const q = globalSearch.toLowerCase();
      list = list.filter((e) => {
        const shopNames = e.shops.map((s) => `${s.shop_name} ${s.domain} ${s.selling_price} ${s.product_url || ''}`).join(' ');
        return `${e.raw.title} ${e.raw.caption} ${e.raw.author} ${e.raw.hook_text} ${e.primaryShopUrl} ${e.primaryProductUrl} ${e.priceLabel} ${shopNames}`
          .toLowerCase()
          .includes(q);
      });
    }

    return [...list].sort((a, b) => {
      if (activeTab === 'video-tiem-nang' && sortMode === 'strongest') {
        return (
          b.potentialScore - a.potentialScore ||
          b.shops.length - a.shops.length ||
          b.totalAdsSameVideo - a.totalAdsSameVideo
        );
      }
      if (sortMode === 'strongest') return b.raw.viral_score - a.raw.viral_score || b.totalAdsSameVideo - a.totalAdsSameVideo;
      if (sortMode === 'newest') return a.videoAgeDays - b.videoAgeDays;
      return b.shopTotal - a.shopTotal || b.totalAdsSameVideo - a.totalAdsSameVideo;
    });
  }, [enrichedVideos, activeTab, potentialTierFilter, filterPlatform, watchlistIds, testlistIds, globalSearch, sortMode]);

  const drawerVideo = useMemo(
    () => enrichedVideos.find((e) => e.raw.id === drawerVideoId) || null,
    [enrichedVideos, drawerVideoId]
  );

  useEffect(() => {
    if (drawerVideo) {
      setCustomSpyQuery(drawerVideo.marketIntel?.product_query || '');
    }
  }, [drawerVideoId]);

  const selectedVideo = useMemo(
    () => videos.find((v) => v.id === selectedVideoId) || videos[0],
    [videos, selectedVideoId]
  );
  const selectedProduct = useMemo(
    () => (selectedProductId > 0 ? products.find((p) => p.id === selectedProductId) || null : null),
    [products, selectedProductId]
  );
  const flowJobs = useMemo(() => jobs.filter((j) => j.clone_mode.startsWith('flow_')), [jobs]);
  const museJobs = useMemo(() => jobs.filter((j) => !j.clone_mode.startsWith('flow_')), [jobs]);
  const completedJobs = useMemo(() => jobs.filter((j) => j.status === 'completed'), [jobs]);
  const completedFlowJobs = useMemo(() => flowJobs.filter((j) => j.status === 'completed'), [flowJobs]);
  const completedMuseJobs = useMemo(() => museJobs.filter((j) => j.status === 'completed'), [museJobs]);
  const activeCloneJob = useMemo(
    () => completedMuseJobs.find((j) => j.id === activeCloneJobId) || completedMuseJobs[0] || null,
    [completedMuseJobs, activeCloneJobId]
  );
  const activeFlowJob = useMemo(
    () => flowJobs.find((j) => j.id === activeFlowJobId) || completedFlowJobs[0] || flowJobs[0] || null,
    [flowJobs, completedFlowJobs, activeFlowJobId]
  );
  const activeFlowEngineBadge = useMemo(
    () => (activeFlowJob ? getFlowJobEngineBadge(activeFlowJob) : null),
    [activeFlowJob]
  );

  useEffect(() => {
    setPreviewFlowClipUrl('');
  }, [activeFlowJob?.id, activeFlowJob?.output_video_url]);
  const selectedPubJob = useMemo(
    () => completedJobs.find((j) => j.id === pubJobId) || completedJobs[0],
    [completedJobs, pubJobId]
  );

  // Auto-focus the 9:16 Video Player onto any job the moment it transitions to 'completed'
  useEffect(() => {
    if (jobs.length === 0) return;
    const nowDone = jobs.filter((j) => j.status === 'completed');
    if (knownCompletedJobIdsRef.current === null) {
      knownCompletedJobIdsRef.current = new Set(nowDone.map((j) => j.id));
      return;
    }
    const newlyCompleted = nowDone.filter((j) => !knownCompletedJobIdsRef.current!.has(j.id));
    for (const j of nowDone) {
      knownCompletedJobIdsRef.current.add(j.id);
    }
    // Remove any job that was retried (no longer in nowDone) so its next completion triggers auto-focus too
    const nowDoneSet = new Set(nowDone.map((j) => j.id));
    for (const oldId of Array.from(knownCompletedJobIdsRef.current)) {
      if (!nowDoneSet.has(oldId)) {
        knownCompletedJobIdsRef.current.delete(oldId);
      }
    }
    if (newlyCompleted.length > 0) {
      const latestNew = newlyCompleted[0]; // jobs are ordered DESC by id
      setPubJobId(latestNew.id);
      const latestFlow = newlyCompleted.find((j) => j.clone_mode.startsWith('flow_'));
      if (latestFlow) setActiveFlowJobId(latestFlow.id);
      const latestMuse = newlyCompleted.find((j) => !j.clone_mode.startsWith('flow_'));
      if (latestMuse) setActiveCloneJobId(latestMuse.id);
    }
  }, [jobs]);

  useEffect(() => {
    if (!selectedPubJob) return;
    api
      .previewPublishCopy(selectedPubJob.product_id, pubPlatform, selectedPubJob.prompt_script)
      .then((res) => {
        setPubCaption(res.caption);
        setPubFirstComment(res.first_comment);
      })
      .catch(() => {});
  }, [selectedPubJob?.id, pubPlatform]);

  const basketLines = useMemo(
    () =>
      scanBasket
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean),
    [scanBasket]
  );

  const toggleWatchlist = (id: number) => {
    setWatchlistIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const toggleTestlist = (id: number) => {
    setTestlistIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const hideFromTable = (id: number) => {
    setHiddenIds((prev) => [...prev, id]);
    if (drawerVideoId === id) setDrawerVideoId(null);
    notify('Đã ẩn video khỏi bảng kết quả hiện tại');
  };

  const addKeywordToBasket = (kw: string) => {
    if (basketLines.includes(kw)) {
      notify(`Từ khoá "${kw}" đã có trong giỏ quét`);
      return;
    }
    setScanBasket((prev) => (prev.trim() ? `${prev.trim()}\n${kw}` : kw));
    notify(`Đã thêm "${kw}" vào giỏ quét`);
  };

  const addAllKeywordsToBasket = () => {
    const kws = TRENDING_KEYWORDS[kwSourceTab].map((k) => k.keyword);
    const merged = Array.from(new Set([...basketLines, ...kws]));
    setScanBasket(merged.join('\n'));
    notify(`Đã nạp ${kws.length} từ khoá xu hướng vào giỏ quét`);
  };

  const loadAgentReachStatus = async () => {
    setArLoading(true);
    try {
      const data = await api.getAgentReachStatus();
      setArStatus(data);
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Không tải được trạng thái Agent-Reach', 'err');
    } finally {
      setArLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'cai-dat' && !arStatus) {
      loadAgentReachStatus();
    }
  }, [activeTab]);

  const loginPollRef = useRef<number | null>(null);
  const [ensuringVideoId, setEnsuringVideoId] = useState<number | null>(null);
  const [analyzingAiVideoId, setAnalyzingAiVideoId] = useState<number | null>(null);
  const [playingCardId, setPlayingCardId] = useState<number | null>(null);

  const handleEnsureVideoMp4 = async (videoId: number) => {
    setEnsuringVideoId(videoId);
    try {
      const res = await api.ensureVideoMp4(videoId);
      if (res.ok) {
        notify(`Đã sẵn sàng phát MP4 gốc cho video #${videoId}!`);
        await refreshAll();
      }
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Không tải được luồng MP4 trực tiếp', 'err');
    } finally {
      setEnsuringVideoId(null);
    }
  };

  const handleAnalyzeVideoAi = async (videoId: number) => {
    setAnalyzingAiVideoId(videoId);
    try {
      const res = await api.analyzeVideoAi(videoId);
      if (res.ok) {
        notify(`Đã phân tích AI chuyên sâu cho video #${videoId}!`);
        await refreshAll();
      }
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi phân tích AI', 'err');
    } finally {
      setAnalyzingAiVideoId(null);
    }
  };

  useEffect(() => {
    if (!drawerVideo) return;
    if (!drawerVideo.localMediaUrl && ensuringVideoId !== drawerVideo.raw.id) {
      handleEnsureVideoMp4(drawerVideo.raw.id);
    }
  }, [drawerVideo?.raw.id]);

  useEffect(() => {
    return () => {
      if (loginPollRef.current) window.clearInterval(loginPollRef.current);
    };
  }, []);

  const handleAgentReachChannelOp = async (channel: string, operation: string) => {
    const busy = `${channel}:${operation}`;
    setArBusyKey(busy);
    try {
      const res = await api.agentReachChannelAction(channel, operation);
      if (res.ok) {
        notify(res.message || `Đã chạy "${operation}" cho kênh ${channel}`);
        setArActionOutput(JSON.stringify(res, null, 2));
        if (operation === 'login' && res.status === 'browser_opened') {
          if (loginPollRef.current) window.clearInterval(loginPollRef.current);
          let attempts = 0;
          loginPollRef.current = window.setInterval(async () => {
            attempts += 1;
            if (attempts > 60) {
              if (loginPollRef.current) {
                window.clearInterval(loginPollRef.current);
                loginPollRef.current = null;
              }
              return;
            }
            try {
              const updated = await api.getAgentReachStatus();
              setArStatus(updated);
              const target = updated.channels?.find((c) => c.channel === channel);
              if (target?.logged_in && !updated.browser?.running) {
                if (loginPollRef.current) {
                  window.clearInterval(loginPollRef.current);
                  loginPollRef.current = null;
                }
                notify(`Đã tự động đóng Chrome & lưu Cookie đăng nhập cho ${channel}!`);
              }
            } catch {
              // ignore transient poll error
            }
          }, 2500);
        }
      } else {
        const msg = res.error?.message || `Thao tác ${operation} trên ${channel} thất bại`;
        notify(msg, 'err');
        setArActionOutput(JSON.stringify(res, null, 2));
      }
      await loadAgentReachStatus();
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi gọi Agent-Reach', 'err');
    } finally {
      setArBusyKey(null);
    }
  };

  const handleAgentReachBrowserOp = async (operation: string, param = '') => {
    setArBusyKey(`browser:${operation}`);
    try {
      const res = await api.agentReachBrowserAction(operation, param);
      if (res.ok) {
        notify(`Browser "${operation}" thành công!`);
      } else {
        notify(res.error?.message || `Lỗi browser ${operation}`, 'err');
      }
      setArActionOutput(JSON.stringify(res, null, 2));
      await loadAgentReachStatus();
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi browser Agent-Reach', 'err');
    } finally {
      setArBusyKey(null);
    }
  };

  const handleAgentReachConfigure = async () => {
    if (!arCfgVal.trim()) {
      notify('Vui lòng nhập giá trị cấu hình', 'err');
      return;
    }
    setArBusyKey('configure');
    try {
      const res = await api.agentReachConfigure(arCfgKey, arCfgVal.trim());
      if (res.ok) {
        notify(`Đã cấu hình ${arCfgKey} cho Agent-Reach!`);
        setArCfgVal('');
      } else {
        notify(res.error?.message || 'Lỗi cấu hình Agent-Reach', 'err');
      }
      setArActionOutput(JSON.stringify(res, null, 2));
      await loadAgentReachStatus();
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi configure Agent-Reach', 'err');
    } finally {
      setArBusyKey(null);
    }
  };

  const handleAgentReachExecute = async (e: React.FormEvent) => {
    e.preventDefault();
    setArExecRunning(true);
    try {
      const res = await api.agentReachExecute({
        channel: arExecChannel,
        action: arExecAction,
        query: arExecQuery,
        limit: 5,
        save_to_videos: true,
        country: marketCountry,
      });
      setArExecResult(
        `${res.command}\n` +
          (res.diagnostic ? `Chẩn đoán: ${res.diagnostic}\n` : '') +
          `Đã lưu: ${res.saved_count} video.\n` +
          JSON.stringify(res.raw_response, null, 2).slice(0, 1200)
      );
      if (res.saved_count > 0) {
        notify(`Agent-Reach [${arExecChannel}] đã quét & lưu ${res.saved_count} video mới!`);
        await refreshAll();
      } else if (res.diagnostic) {
        notify(res.diagnostic, 'err');
      } else {
        notify('Đã chạy Agent-Reach (xem chi tiết JSON bên dưới)');
      }
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi chạy Agent-Reach', 'err');
    } finally {
      setArExecRunning(false);
    }
  };

  const handleReaDecompose = async (videoId: number, useVlm?: boolean, autoFillMuseScript = false) => {
    setReaBusyVideoId(videoId);
    notify(`Đang chạy rea-video decompose phân tích shot-by-shot cho video #${videoId}...`);
    try {
      const res = await api.decomposeVideoRea(videoId, useVlm);
      const bd = res.breakdown;
      if (autoFillMuseScript && bd) {
        const shotLines = (bd.shots || [])
          .slice(0, 5)
          .map((s) => `[${s.start.toFixed(1)}s-${s.end.toFixed(1)}s ${s.label} · ${s.remake_route}] ${s.prompt || bd.verdict}`)
          .join('\n');
        setPromptScript(shotLines || bd.remake_md_excerpt || bd.video_md_excerpt || bd.verdict);
        setCloneMode('rea_video_remake');
      }
      if (videoId === selectedVideoId && bd) {
        if (bd.veo_prompt_en) setFlowVeoPrompt(bd.veo_prompt_en);
        if (bd.scene_units && bd.scene_units.length > 0) setFlowScenePlan(bd.scene_units);
      }
      notify(
        `Phân tích xong #${videoId}: ${bd.shots_count} shots · ${bd.verdict.slice(0, 70)}`
      );
      await refreshAll();
      return res;
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi khi chạy rea-video decompose', 'err');
      return null;
    } finally {
      setReaBusyVideoId(null);
    }
  };

  const handleEvaluateSingleVideo = async (videoId: number, queryOverride = '') => {
    setSpyingVideoId(videoId);
    notify(`Đang tự đánh giá & dò Shop đang bán, Link bán, Số lượng Ads & Giá cho video #${videoId}...`);
    try {
      const res = await api.evaluateVideoPotential(videoId, {
        custom_query: queryOverride.trim(),
        country: potentialSpyCountry === 'AUTO' ? '' : potentialSpyCountry,
        deep_spy: true,
      });
      setVideos((prev) => prev.map((v) => (v.id === videoId ? res.video : v)));
      const mi = res.market_intel;
      notify(
        `Xong #${videoId} [Hạng ${mi.potential_tier} · ${mi.potential_score}đ]: ${mi.active_shops_count} shop · ${mi.total_active_ads} QC active · Giá: ${mi.price_range}`
      );
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi khi dò Shop & đánh giá tiềm năng', 'err');
    } finally {
      setSpyingVideoId(null);
    }
  };

  const handleEvaluatePotentialBatch = async () => {
    setBatchSpyRunning(true);
    const unspiedVisible = displayedVideos.filter((e) => !e.isDeepSpied).map((e) => e.raw.id);
    const targetIds = (unspiedVisible.length > 0 ? unspiedVisible : displayedVideos.map((e) => e.raw.id)).slice(0, 5);
    notify(`Đang tự động đánh giá đa nền tảng & dò Shop/Link/Giá/Ads cho ${targetIds.length || 5} video đầu...`);
    try {
      const res = await api.evaluateVideosPotentialBatch({
        video_ids: targetIds.length > 0 ? targetIds : undefined,
        limit: 5,
        country: potentialSpyCountry === 'AUTO' ? '' : potentialSpyCountry,
      });
      setVideos(res.videos);
      notify(
        `Đã tự đánh giá ${res.evaluated_count} video & dò sâu Shop/Link bán/Giá thực tế cho ${res.deep_spied_count} video!`
      );
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi chạy tự đánh giá hàng loạt', 'err');
    } finally {
      setBatchSpyRunning(false);
    }
  };

  const handleFetchReaVlmModels = async () => {
    if (!reaVlmBaseUrl.trim()) {
      notify('Vui lòng nhập VLM Endpoint Base URL trước khi Fetch Model', 'err');
      return;
    }
    setVlmFetchingModels(true);
    try {
      const res = await api.fetchReaVlmModels(reaVlmBaseUrl.trim(), reaVlmApiKey.trim());
      if (!res.ok || res.models.length === 0) {
        notify(res.error || 'Không tìm thấy model nào từ endpoint này', 'err');
        return;
      }
      setVlmFetchedModels(res.models);
      setVlmRecommendedModels(res.recommended || []);
      if (res.base_url) setReaVlmBaseUrl(res.base_url);
      setReaVlmEnabled('1');
      const preferred = (res.recommended && res.recommended[0]) || res.models[0];
      const currentList = reaVlmModel
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
      const hasMatch = currentList.some((m) => res.models.includes(m));
      if (!hasMatch && preferred) {
        setReaVlmModel(preferred);
      }
      notify(`Đã tải thành công ${res.count} models từ endpoint! Hãy chọn model và bấm Lưu Cấu Hình.`);
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi kết nối API để fetch model', 'err');
    } finally {
      setVlmFetchingModels(false);
    }
  };

  const handleBatchCrawl = async (e: React.FormEvent) => {
    e.preventDefault();
    if (basketLines.length === 0) {
      notify('Vui lòng nhập ít nhất 1 từ khoá vào Giỏ quét', 'err');
      return;
    }
    setScanStage('scanning');
    let totalNew = 0;
    const allNotes: string[] = [];
    const apiEngine = crawlEngine === 'treg_api' ? 'treg_api' : 'agent_reach';

    try {
      for (let i = 0; i < basketLines.length; i++) {
        const kw = basketLines[i].replace(/^["“']+|["”']+$/g, '').trim();
        if (!kw) continue;
        if (i > 0) setScanStage('digging');
        const res = await api.crawlVideos({
          keyword: kw,
          platform: crawlPlatform,
          engine: apiEngine,
          country: marketCountry,
          match_type: matchType,
        });
        totalNew += res.count;
        if (res.diagnostics) allNotes.push(...res.diagnostics);
      }
      setScanStage('digging');
      setCrawlNotes(allNotes.slice(0, 10));
      await refreshAll();
      setScanStage('done');
      if (totalNew > 0) {
        notify(`Quét xong ${basketLines.length} từ khoá! Đã nạp ${totalNew} video vào kho SpyWinAds.`);
      } else {
        notify(allNotes[0] || `Đã quét ${basketLines.length} từ khoá nhưng chưa tìm thấy video khớp.`, 'err');
      }
    } catch (err: unknown) {
      setScanStage('idle');
      notify(err instanceof Error ? err.message : 'Lỗi khi quét từ khoá', 'err');
    }
  };

  const handleInspectUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inspectUrlInput.trim()) return;
    setIsInspecting(true);
    try {
      const res = await api.inspectUrl(inspectUrlInput, true);
      notify(res.warning ? res.warning : 'Đã tải & đào sâu video thành công bằng yt-dlp!');
      setInspectUrlInput('');
      await refreshAll();
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Không thể kiểm tra URL', 'err');
    } finally {
      setIsInspecting(false);
    }
  };

  const handleDownloadVideoSource = async (v: ViralVideo) => {
    const localUrl = resolveLocalMediaUrl(v);
    if (localUrl) {
      const a = document.createElement('a');
      a.href = localUrl;
      a.download = `spywin_video_${v.id}.mp4`;
      a.click();
      notify(`Đang tải file MP4 gốc của video #${v.id}`);
      return;
    }
    notify(`Đang gọi yt-dlp tải video #${v.id}...`);
    try {
      const res = await api.inspectUrl(v.source_url, true);
      notify(res.warning ? res.warning : 'Đã tải xong video sạch về máy!');
      await refreshAll();
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Không thể tải video từ URL này', 'err');
    }
  };

  const handleSelectForClone = (v: ViralVideo) => {
    setSelectedVideoId(v.id);
    setPromptScript(v.hook_text || v.title);
    setDrawerVideoId(null);
    setActiveTab('clone-muse');
  };

  const handleSearchMetaShops = async (e?: React.FormEvent, overrideQuery?: string) => {
    if (e) e.preventDefault();
    const q = (overrideQuery !== undefined ? overrideQuery : metaShopQuery).trim();
    if (!q) {
      notify('Vui lòng nhập từ khoá sản phẩm, tên Shop, domain hoặc link Fanpage để tìm trên Meta Ads', 'err');
      return;
    }
    setMetaShopSearching(true);
    notify(`Đang quét Meta Ad Library tìm các Shop đang bán "${q}" (FB / IG / Threads)...`);
    try {
      const res = await api.searchMetaShops({
        query: q,
        country: metaShopCountry,
        platform: metaShopPlatform,
        limit: 12,
      });
      setMetaTotalMarketAds(res.total_market_ads || 0);
      const allSaved = await api.getMetaShops();
      const mergedList = res.shops && res.shops.length > 0 ? res.shops : allSaved.shops;
      setMetaShops(allSaved.shops.length >= (res.shops?.length || 0) ? allSaved.shops : mergedList);
      if (res.shops && res.shops.length > 0) {
        const top = res.shops[0];
        setSelectedMetaShop(top);
        setSelectedMetaShopProducts(top.preview_products || []);
        notify(`Tìm thấy ${res.shops.length} Shop đang chạy quảng cáo "${q}" trên Meta Ads!`);
      } else {
        notify(`Chưa tìm thấy Shop nào đang chạy quảng cáo khớp "${q}".`, 'err');
      }
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi khi dò Shop trên Meta Ads', 'err');
    } finally {
      setMetaShopSearching(false);
    }
  };

  const handleInspectMetaShopProducts = async (target: {
    id?: number;
    page_id?: string;
    shop_name?: string;
  }) => {
    const key = String(target.id || target.page_id || target.shop_name || 'scan');
    setScanningShopKey(key);
    setDrawerVideoId(null);
    setActiveTab('do-shop-meta');
    notify(`Đang quét toàn bộ kệ Sản Phẩm & Video Ads của shop "${target.shop_name || target.page_id}" trên Meta Ads...`);
    try {
      const res = await api.scanMetaShopProducts({
        shop_id: target.id,
        page_id: target.page_id || '',
        shop_query: target.shop_name || '',
        country: metaShopCountry,
        limit: 24,
      });
      setSelectedMetaShop(res.shop);
      setSelectedMetaShopProducts(res.products || []);
      const refreshed = await api.getMetaShops();
      setMetaShops(refreshed.shops || []);
      notify(`Đã bóc tách ${res.products.length} sản phẩm/mẫu quảng cáo đang bán của "${res.shop.shop_name}"!`);
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Không quét được kệ sản phẩm của Shop này', 'err');
    } finally {
      setScanningShopKey(null);
    }
  };

  const handleImportShopProductToVideos = async (prod: MetaShopProduct) => {
    setImportingShopProdId(prod.id);
    try {
      const res = await api.importMetaShopProductVideo(prod.id);
      if (res.ok) {
        await refreshAll();
        notify(`Đã nạp video sản phẩm "${prod.product_title.slice(0, 45)}" vào Kho Video!`);
      }
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Không thể lưu video sản phẩm này', 'err');
    } finally {
      setImportingShopProdId(null);
    }
  };

  const handleQuickAddShopProductToAffiliate = (prod: MetaShopProduct, shopName: string) => {
    const nextNum = String(products.length + 1).padStart(2, '0');
    const urlTarget = prod.product_url || prod.shop_url;
    const lowU = urlTarget.toLowerCase();
    const pfName = lowU.includes('shopee')
      ? 'Shopee'
      : lowU.includes('tiktok')
      ? 'TikTok Shop'
      : lowU.includes('lazada')
      ? 'Lazada'
      : 'ClickBank';
    setProdForm({
      code: `SP${nextNum}`,
      name: (prod.product_title || shopName).slice(0, 90),
      platform_name: pfName,
      price: prod.selling_price || 'Liên hệ',
      original_price: prod.original_price || '',
      affiliate_url: urlTarget,
      image_url: prod.thumbnail_url || '',
      comment_template: '',
    });
    setActiveTab('kho-san-pham');
    notify(`Đã điền sẵn thông tin SP từ shop "${shopName}" vào form Kho Sản Phẩm!`);
  };

  const effectiveFlowModelId =
    flowModelId === '__custom__' ? customFlowModelId.trim() || 'omni_1_2_flash_10s_portrait' : flowModelId;

  const handleSyncFlowModels = async () => {
    setSyncingFlowModels(true);
    try {
      const res = await api.syncFlowModels();
      if (res.models && res.models.length > 0) {
        setFlowModels(res.models);
      }
      notify(
        res.new_discovered > 0
          ? `Đã đồng bộ thành công ${res.count} model Flow (phát hiện ${res.new_discovered} model mới)!`
          : `Đã cập nhật đầy đủ ${res.count} model mới nhất trên Google Flow (OmniFlash / Veo 3.1 / Nano Banana)!`
      );
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi đồng bộ danh sách model Google Flow', 'err');
    } finally {
      setSyncingFlowModels(false);
    }
  };

  const handleReaAndGenerateFlowPrompt = async (forceReanalyze = false) => {
    const vid = selectedVideo;
    if (!vid) {
      notify('Vui lòng chọn video viral gốc trước', 'err');
      return;
    }
    try {
      let shotsCount = vid.rea_breakdown?.shots_count || 0;
      if (forceReanalyze || !vid.rea_breakdown || !vid.rea_breakdown.scene_units?.length) {
        setReaBusyVideoId(vid.id);
        notify(`Bước 1/2: Đang mổ xẻ 4-frame/shot & lập kế hoạch Cụm Cảnh bằng rea-video cho video #${vid.id}...`);
        const reaRes = await api.decomposeVideoRea(vid.id);
        shotsCount = reaRes.breakdown.shots_count;
        await refreshAll();
        setReaBusyVideoId(null);
      }
      setFlowGeneratingPrompt(true);
      notify(
        `Bước 2/2: Đang dựng Kế Hoạch Cụm Cảnh & Ảnh Thành Phần sạch từ rea-video cho model ${effectiveFlowModelId}...`
      );
      const res = await api.generateFlowPrompt({
        video_id: vid.id,
        clone_mode: flowCloneMode,
        custom_hint: promptScript,
        flow_model: effectiveFlowModelId,
      });
      setFlowVeoPrompt(res.veo_prompt);
      if (res.scene_units && res.scene_units.length > 0) setFlowScenePlan(res.scene_units);
      if (res.reference_frame_url) setFlowRefFrameUrl(res.reference_frame_url);
      notify(
        `Đã mổ xẻ ${shotsCount} shots → ${res.scene_units?.length || 1} Cụm Cảnh Google Flow (${effectiveFlowModelId})!`
      );
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi mổ xẻ rea-video & tạo Prompt Flow', 'err');
    } finally {
      setReaBusyVideoId(null);
      setFlowGeneratingPrompt(false);
    }
  };

  const handleGenerateFlowVeoPrompt = async (targetVidId?: number, modeOverride?: string) => {
    const vidId = targetVidId ?? selectedVideo?.id;
    if (!vidId) {
      notify('Vui lòng chọn video viral gốc trước', 'err');
      return;
    }
    setFlowGeneratingPrompt(true);
    try {
      const res = await api.generateFlowPrompt({
        video_id: vidId,
        clone_mode: modeOverride || flowCloneMode,
        custom_hint: promptScript,
        flow_model: effectiveFlowModelId,
      });
      setFlowVeoPrompt(res.veo_prompt);
      if (res.scene_units && res.scene_units.length > 0) setFlowScenePlan(res.scene_units);
      if (res.reference_frame_url) setFlowRefFrameUrl(res.reference_frame_url);
      notify(
        `Đã dựng Kế Hoạch ${res.scene_units?.length || 1} Cụm Cảnh 9:16 (${effectiveFlowModelId}) từ video #${vidId}!`
      );
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi tạo Prompt Flow', 'err');
    } finally {
      setFlowGeneratingPrompt(false);
    }
  };

  const handleSelectForFlowClone = (v: ViralVideo) => {
    setSelectedVideoId(v.id);
    setPromptScript(v.hook_text || v.title);
    setFlowRefFrameUrl(v.thumbnail_url || '');
    setFlowScenePlan(v.rea_breakdown?.scene_units || []);
    setDrawerVideoId(null);
    setActiveTab('clone-flow');
    void handleGenerateFlowVeoPrompt(v.id, flowCloneMode);
  };

  const handleFlowBrowserLogin = async (accountId?: number) => {
    try {
      const res = await api.loginFlowBrowser({
        account_id: accountId,
        label: flowLoginLabel.trim(),
        proxy: flowLoginProxy.trim(),
        tier: flowBulkTier,
      });
      notify(res.message);
      setFlowLoginLabel('');
      await refreshAll();
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi mở Chrome đăng nhập Google Flow', 'err');
    }
  };

  const handleFlowOpenBrowser = async (accountId: number) => {
    setFlowBusyAccId(accountId);
    try {
      const res = await api.openFlowBrowser(accountId);
      notify(res.message);
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi mở trình duyệt Flow', 'err');
    } finally {
      setFlowBusyAccId(null);
    }
  };

  const handleFlowVerify = async (accountId: number) => {
    setFlowBusyAccId(accountId);
    try {
      const res = await api.verifyFlowAccount(accountId);
      setFlowAccounts((prev) => prev.map((a) => (a.id === accountId ? res.account : a)));
      notify(res.message, res.ok ? 'ok' : 'err');
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi kiểm tra tài khoản Flow', 'err');
    } finally {
      setFlowBusyAccId(null);
    }
  };

  const handleFlowBulkImport = async () => {
    if (!flowBulkText.trim()) {
      notify('Vui lòng dán Cookie JSON / Cookie chuỗi / Bearer Token / Gemini Veo Key', 'err');
      return;
    }
    try {
      const res = await api.bulkImportFlowAccounts(flowBulkText, flowBulkLimit, flowBulkTier);
      notify(`Đã nạp thành công ${res.imported} tài khoản Google Flow!`);
      setFlowBulkText('');
      setShowFlowImportModal(false);
      await refreshAll();
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi nhập tài khoản Flow', 'err');
    }
  };

  const handleLaunchFlowClone = async () => {
    if (!selectedVideo) {
      notify('Vui lòng chọn video viral gốc cần clone bằng Google Flow', 'err');
      return;
    }
    if (flowModelId === '__custom__' && !customFlowModelId.trim()) {
      notify('Vui lòng nhập mã Model Google Flow / Gemini tuỳ chỉnh trước khi chạy', 'err');
      return;
    }
    if (flowAccounts.filter((a) => a.status === 'active').length === 0) {
      notify('Chưa có tài khoản Google Flow nào Active! Hãy bấm Đăng nhập Chrome hoặc Nhập Cookie/Key trước.', 'err');
      return;
    }
    setIsLaunchingClone(true);
    try {
      const res = await api.createCloneJob({
        source_video_id: selectedVideo.id,
        product_id: selectedProductId || 0,
        clone_mode: flowCloneMode,
        prompt_script: promptScript || selectedVideo.hook_text || selectedVideo.title,
        cta_position: ctaPosition,
        link_placement_mode: linkPlacementMode,
        anti_duplicate: antiDuplicate,
        batch_count: batchCount,
        flow_account_id: selectedFlowAccountId > 0 ? selectedFlowAccountId : null,
        flow_model: effectiveFlowModelId,
        veo_prompt: flowVeoPrompt.trim(),
        scene_plan: flowScenePlan.length > 0 ? flowScenePlan : undefined,
      });
      if (res.jobs[0]) setActiveFlowJobId(res.jobs[0].id);
      notify(`Đã gửi ${res.jobs.length} tiến trình Clone (${effectiveFlowModelId}) sang Google Flow!`);
      await refreshAll();
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi khởi tạo job Google Flow', 'err');
    } finally {
      setIsLaunchingClone(false);
    }
  };

  const handleLaunchClone = async () => {
    if (!selectedVideo) {
      notify('Vui lòng chọn video viral gốc cần remake', 'err');
      return;
    }
    setIsLaunchingClone(true);
    try {
      const res = await api.createCloneJob({
        source_video_id: selectedVideo.id,
        product_id: selectedProductId || 0,
        clone_mode: cloneMode,
        prompt_script: promptScript || selectedVideo.hook_text || selectedVideo.title,
        cta_position: ctaPosition,
        link_placement_mode: linkPlacementMode,
        anti_duplicate: antiDuplicate,
        batch_count: batchCount,
      });
      if (res.jobs[0]) setActiveCloneJobId(res.jobs[0].id);
      notify(`Đã đưa ${res.jobs.length} video vào hàng đợi Remake Organic 9:16!`);
      await refreshAll();
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi tạo job remake', 'err');
    } finally {
      setIsLaunchingClone(false);
    }
  };

  const handleBulkImport = async () => {
    try {
      const res = await api.bulkImportTokens(bulkTokenText, bulkWeeklyLimit);
      notify(`Đã nạp thành công ${res.imported} tài khoản Muse vào Kho Token!`);
      setShowBulkModal(false);
      await refreshAll();
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi nhập token', 'err');
    }
  };

  const handleCreateProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prodForm.code || !prodForm.name || !prodForm.price || !prodForm.affiliate_url) {
      notify('Điền đủ Mã SP, Tên, Giá và Link Affiliate nhé!', 'err');
      return;
    }
    try {
      await api.createProduct({ ...prodForm, bio_active: 1 });
      notify(`Đã thêm sản phẩm #${prodForm.code.toUpperCase()} và đồng bộ Link Bio!`);
      setProdForm({
        code: '',
        name: '',
        platform_name: 'Shopee',
        price: '',
        original_price: '',
        affiliate_url: '',
        image_url: '',
        comment_template: '',
      });
      await refreshAll();
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi thêm sản phẩm', 'err');
    }
  };

  const handlePublish = async () => {
    if (!selectedPubJob) {
      notify('Chưa có video đã clone hoàn tất để đăng!', 'err');
      return;
    }
    try {
      await api.createPublishTask({
        clone_job_id: selectedPubJob.id,
        product_id: selectedPubJob.product_id,
        target_platform: pubPlatform,
        account_name: pubAccount,
        caption: pubCaption,
        first_comment_text: pubFirstComment,
      });
      notify('Đã xuất bản & kích hoạt Auto-Comment / Sync Bio thành công!');
      await refreshAll();
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi đăng bài', 'err');
    }
  };

  const copyText = (txt: string, label: string) => {
    navigator.clipboard.writeText(txt);
    notify(`Đã copy ${label} vào clipboard!`);
  };

  const filteredBioProducts = products.filter(
    (p) =>
      p.bio_active === 1 &&
      (`${p.code} ${p.name}`.toLowerCase().includes(bioSearch.toLowerCase()) || !bioSearch.trim())
  );

  const deepQueueStats = useMemo(() => {
    const waiting = enrichedVideos.filter((e) => e.digStatus === 'cho-dao').length;
    const running = scanStage === 'digging' ? 1 : 0;
    const ready = enrichedVideos.length;
    return { waiting, running, ready };
  }, [enrichedVideos, scanStage]);

  const filteredDeepQueue = useMemo(() => {
    if (deepFilter === 'all') return enrichedVideos;
    return enrichedVideos.filter((e) => e.digStatus === deepFilter);
  }, [enrichedVideos, deepFilter]);

  const activeTabInfo = VIDEO_TAB_INFO[activeTab];

  return (
    <div className="sw-shell min-h-screen flex flex-col selection:bg-[#0071e3] selection:text-white">
      {/* Toast Notification */}
      {toast && (
        <div
          className="fixed bottom-5 right-5 z-[60] px-4 py-2.5 rounded-full text-xs font-semibold flex items-center gap-2 border"
          style={{
            background: toast.type === 'ok' ? 'var(--nen)' : 'var(--do-bg)',
            color: toast.type === 'ok' ? 'var(--la)' : 'var(--do)',
            borderColor: toast.type === 'ok' ? 'var(--la)' : 'var(--do)',
            boxShadow: 'var(--shadow-float)',
          }}
        >
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{toast.text}</span>
        </div>
      )}

      {/* TOP FRAMELESS DESKTOP TITLEBAR */}
      <header
        className="sticky top-0 z-30 h-12 px-4 flex items-center justify-between gap-3 border-b"
        style={{
          background: 'var(--nen)',
          borderColor: 'var(--vien-nhe)',
        }}
      >
        {/* Left: SpyWinAds Brand & Version */}
        <div className="flex items-center gap-2.5 min-w-0">
          <SpyWinLogo size={26} />
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-[14px] font-bold tracking-tight truncate" style={{ color: 'var(--chu)' }}>
              SpyWinAds
            </span>
            <span
              className="hidden sm:inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold"
              style={{ background: 'var(--xam)', color: 'var(--mo)', border: '1px solid var(--vien-nhe)' }}
            >
              CloneVideo-Aff · 0.7.5
            </span>
          </div>
        </div>

        {/* Center: Global Search + Engine Indicator */}
        <div className="flex-1 max-w-xl flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--mo2)' }} />
            <input
              value={globalSearch}
              onChange={(e) => setGlobalSearch(e.target.value)}
              placeholder="Tìm nhanh từ khoá, fanpage, hook hoặc mã #SP01..."
              className="w-full pl-8 pr-3 py-1.5 rounded-full text-xs border transition focus:outline-none"
              style={{
                background: 'var(--xam)',
                borderColor: 'var(--vien-nhe)',
                color: 'var(--chu)',
              }}
            />
          </div>
          <button
            type="button"
            onClick={() => setActiveTab('cai-dat')}
            className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium shrink-0 cursor-pointer hover:opacity-85 transition"
            style={{ background: 'var(--la-bg)', color: 'var(--la)' }}
            title="Mở Cài đặt Agent-Reach & rea-video"
          >
            <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: 'var(--la)' }} />
            Agent-Reach + rea-video + yt-dlp · Mạng nhà
          </button>
        </div>

        {/* Right: Flow Pool + Muse Pool Pill + /bio + Settings + Theme Switcher */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={() => setActiveTab('clone-flow')}
            className="hidden md:flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-semibold border transition"
            style={{
              background: 'var(--la-bg)',
              color: 'var(--la)',
              borderColor: 'transparent',
            }}
            title="Clone Video bằng tài khoản Google Flow (flow.google.com — Veo 3.1)"
          >
            <Film className="w-3.5 h-3.5" />
            <span>Google Flow</span>
            <span style={{ opacity: 0.8 }}>
              ({flowAccounts.filter((a) => a.status === 'active').length}/{flowAccounts.length} acc)
            </span>
          </button>

          <button
            onClick={() => setActiveTab('clone-muse')}
            className="hidden md:flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-semibold border transition"
            style={{
              background: 'var(--cam-bg)',
              color: 'var(--cam)',
              borderColor: 'transparent',
            }}
            title="Kho Token Muse AI 1 Tỷ Token"
          >
            <KeyRound className="w-3.5 h-3.5" />
            <span>{status ? formatCompact(status.muse_pool.total_tokens_remaining) : '1.00B'} Tokens</span>
            <span style={{ opacity: 0.75 }}>({status?.muse_pool.active_accounts ?? 0} acc)</span>
          </button>

          <a
            href="/bio"
            target="_blank"
            rel="noreferrer"
            className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-semibold transition"
            style={{
              background: 'var(--xanh-bg)',
              color: 'var(--link)',
            }}
          >
            <Smartphone className="w-3.5 h-3.5" />
            <span>/bio</span>
            <ExternalLink className="w-3 h-3" />
          </a>

          <button
            type="button"
            onClick={() => setActiveTab('cai-dat')}
            className="flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-semibold border transition"
            style={{
              background: activeTab === 'cai-dat' ? 'var(--xanh)' : 'var(--xam)',
              borderColor: activeTab === 'cai-dat' ? 'transparent' : 'var(--vien-nhe)',
              color: activeTab === 'cai-dat' ? '#ffffff' : 'var(--chu)',
            }}
            title="Mở Cài đặt & Login Agent-Reach, rea-video VLM"
          >
            <Settings className="w-3.5 h-3.5" />
            <span>Cài đặt &amp; Agent-Reach</span>
          </button>

          <div className="sw-seg" title="Giao diện Sáng / Tối">
            <button
              onClick={() => setTheme('light')}
              className={`sw-seg-item flex items-center gap-1 !py-1 !px-2 text-[11px] ${
                theme === 'light' ? 'active' : ''
              }`}
            >
              <Sun className="w-3 h-3" />
              <span className="hidden xl:inline">Sáng</span>
            </button>
            <button
              onClick={() => setTheme('dark')}
              className={`sw-seg-item flex items-center gap-1 !py-1 !px-2 text-[11px] ${
                theme === 'dark' ? 'active' : ''
              }`}
            >
              <Moon className="w-3 h-3" />
              <span className="hidden xl:inline">Tối</span>
            </button>
          </div>

          <button
            onClick={refreshAll}
            className="p-1.5 rounded-full border transition hover:opacity-80"
            style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)', color: 'var(--mo)' }}
            title="Làm mới dữ liệu"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </header>

      {/* BODY: LEFT SIDEBAR + WORKSPACE */}
      <div className="flex-1 flex min-h-0">
        {/* LEFT SIDEBAR (Exact SpyWinAds Hierarchy) */}
        <aside
          className="w-[244px] shrink-0 border-r flex flex-col justify-between p-3 overflow-y-auto sticky top-12 h-[calc(100vh-3rem)]"
          style={{
            background: 'var(--nen)',
            borderColor: 'var(--vien-nhe)',
          }}
        >
          <div className="space-y-5">
            {/* Group 1: THU THẬP */}
            <div>
              <div
                className="px-2.5 mb-1.5 text-[10px] font-bold uppercase tracking-wider"
                style={{ color: 'var(--mo2)' }}
              >
                Thu thập
              </div>
              <div className="space-y-0.5">
                {[
                  {
                    id: 'quet-tu-khoa' as SidebarTab,
                    label: 'Quét từ khoá',
                    icon: Search,
                    badge: basketLines.length > 0 ? `${basketLines.length} KW` : undefined,
                  },
                  {
                    id: 'do-shop-meta' as SidebarTab,
                    label: 'Dò Shop & SP (Meta)',
                    icon: ShoppingBag,
                    badge: metaShops.length > 0 ? `${metaShops.length} shop` : '3 kênh',
                  },
                  {
                    id: 'dao-sau' as SidebarTab,
                    label: 'Đào sâu',
                    icon: Layers,
                    badge: enrichedVideos.length,
                  },
                ].map((item) => {
                  const Icon = item.icon;
                  const active = activeTab === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => setActiveTab(item.id)}
                      className="w-full flex items-center justify-between px-2.5 py-2 rounded-xl text-[13px] transition"
                      style={{
                        background: active ? 'var(--xanh)' : 'transparent',
                        color: active ? '#ffffff' : 'var(--chu)',
                        fontWeight: active ? 600 : 500,
                      }}
                    >
                      <span className="flex items-center gap-2.5 truncate">
                        <Icon className="w-4 h-4 shrink-0" style={{ opacity: active ? 1 : 0.72 }} />
                        <span className="truncate">{item.label}</span>
                      </span>
                      {item.badge !== undefined && (
                        <span
                          className="text-[10px] px-1.5 py-0.5 rounded-full font-semibold"
                          style={{
                            background: active ? 'rgba(255,255,255,0.2)' : 'var(--xam)',
                            color: active ? '#ffffff' : 'var(--mo)',
                          }}
                        >
                          {item.badge}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Group 2: KẾT QUẢ VIDEO */}
            <div>
              <div
                className="px-2.5 mb-1.5 text-[10px] font-bold uppercase tracking-wider"
                style={{ color: 'var(--mo2)' }}
              >
                Kết quả Video
              </div>
              <div className="space-y-0.5">
                {[
                  {
                    id: 'video-tiem-nang' as SidebarTab,
                    label: 'Video Tiềm Năng',
                    icon: TrendingUp,
                    badge: tabCounts['video-tiem-nang'],
                    accentBg: 'var(--xanh-bg)',
                    accentText: 'var(--link)',
                  },
                  {
                    id: 'video-win' as SidebarTab,
                    label: 'Video Win',
                    icon: Flame,
                    badge: tabCounts['video-win'],
                    accentBg: 'var(--la-bg)',
                    accentText: 'var(--la)',
                  },
                  {
                    id: 'video-scale' as SidebarTab,
                    label: 'Video scale',
                    icon: Zap,
                    badge: tabCounts['video-scale'],
                    accentBg: 'var(--cam-bg)',
                    accentText: 'var(--cam)',
                  },
                  {
                    id: 'sp-bo-sua' as SidebarTab,
                    label: 'SP bò sữa',
                    icon: Award,
                    badge: tabCounts['sp-bo-sua'],
                    accentBg: 'var(--o)',
                    accentText: 'var(--mo)',
                  },
                  {
                    id: 'video-da-quet' as SidebarTab,
                    label: 'Video đã quét',
                    icon: Database,
                    badge: tabCounts['video-da-quet'],
                    accentBg: 'var(--xam)',
                    accentText: 'var(--mo)',
                  },
                ].map((item) => {
                  const Icon = item.icon;
                  const active = activeTab === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => {
                        setActiveTab(item.id);
                        setShowRulesBox(false);
                      }}
                      className="w-full flex items-center justify-between px-2.5 py-2 rounded-xl text-[13px] transition"
                      style={{
                        background: active ? 'var(--xanh)' : 'transparent',
                        color: active ? '#ffffff' : 'var(--chu)',
                        fontWeight: active ? 600 : 500,
                      }}
                    >
                      <span className="flex items-center gap-2.5 truncate">
                        <Icon className="w-4 h-4 shrink-0" style={{ opacity: active ? 1 : 0.72 }} />
                        <span className="truncate">{item.label}</span>
                      </span>
                      <span
                        className="text-[10px] px-1.5 py-0.5 rounded-full font-semibold"
                        style={{
                          background: active ? 'rgba(255,255,255,0.22)' : item.accentBg,
                          color: active ? '#ffffff' : item.accentText,
                        }}
                      >
                        {item.badge}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Group 3: CỦA RIÊNG BẠN & AFFILIATE */}
            <div>
              <div
                className="px-2.5 mb-1.5 text-[10px] font-bold uppercase tracking-wider"
                style={{ color: 'var(--mo2)' }}
              >
                Của riêng bạn & Affiliate
              </div>
              <div className="space-y-0.5">
                {[
                  {
                    id: 'theo-doi' as SidebarTab,
                    label: 'Theo dõi đặc biệt',
                    icon: Star,
                    badge: tabCounts['theo-doi'],
                  },
                  {
                    id: 'video-test' as SidebarTab,
                    label: 'Video test',
                    icon: FlaskConical,
                    badge: tabCounts['video-test'],
                  },
                  {
                    id: 'clone-flow' as SidebarTab,
                    label: 'Clone Google Flow',
                    icon: Film,
                    badge: `${flowAccounts.filter((a) => a.status === 'active').length} acc`,
                  },
                  {
                    id: 'clone-muse' as SidebarTab,
                    label: 'Clone Video (Muse AI)',
                    icon: Sparkles,
                    badge: jobs.length,
                  },
                  {
                    id: 'kho-san-pham' as SidebarTab,
                    label: 'Kho Sản Phẩm & Bio',
                    icon: ShoppingBag,
                    badge: products.length,
                  },
                  {
                    id: 'dang-bai' as SidebarTab,
                    label: 'Đăng Bài & Auto-Link',
                    icon: Send,
                    badge: publishTasks.length,
                  },
                  {
                    id: 'cai-dat' as SidebarTab,
                    label: 'Cài đặt & Agent-Reach',
                    icon: Settings,
                    badge: arStatus?.channels?.length ? `${arStatus.channels.length} kênh` : '14 kênh',
                  },
                ].map((item) => {
                  const Icon = item.icon;
                  const active = activeTab === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => setActiveTab(item.id)}
                      className="w-full flex items-center justify-between px-2.5 py-2 rounded-xl text-[13px] transition"
                      style={{
                        background: active ? 'var(--xanh)' : 'transparent',
                        color: active ? '#ffffff' : 'var(--chu)',
                        fontWeight: active ? 600 : 500,
                      }}
                    >
                      <span className="flex items-center gap-2.5 truncate">
                        <Icon className="w-4 h-4 shrink-0" style={{ opacity: active ? 1 : 0.72 }} />
                        <span className="truncate">{item.label}</span>
                      </span>
                      <span
                        className="text-[10px] px-1.5 py-0.5 rounded-full font-semibold"
                        style={{
                          background: active ? 'rgba(255,255,255,0.22)' : 'var(--xam)',
                          color: active ? '#ffffff' : 'var(--mo)',
                        }}
                      >
                        {item.badge}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Sidebar Footer */}
          <div className="pt-4 mt-4 border-t space-y-2" style={{ borderColor: 'var(--vien-nhe)' }}>
            <button
              type="button"
              onClick={() => setActiveTab('cai-dat')}
              className="sw-card-subtle w-full text-left p-2.5 space-y-1.5 text-[11px] hover:opacity-90 transition cursor-pointer"
              title="Bấm để mở Cài đặt Agent-Reach & rea-video"
            >
              <div className="flex items-center justify-between font-semibold">
                <span className="flex items-center gap-1.5" style={{ color: 'var(--la)' }}>
                  <span className="w-2 h-2 rounded-full" style={{ background: 'var(--la)' }} />
                  Đang hoạt động
                </span>
                <span style={{ color: 'var(--mo)' }}>Mạng nhà</span>
              </div>
              <div className="flex items-center justify-between" style={{ color: 'var(--mo)' }}>
                <span>Agent-Reach</span>
                <span style={{ color: status?.agent_reach_installed ? 'var(--la)' : 'var(--cam)', fontWeight: 600 }}>
                  {status?.agent_reach_installed ? 'Sẵn sàng' : 'Chưa cài'}
                </span>
              </div>
              <div className="flex items-center justify-between" style={{ color: 'var(--mo)' }}>
                <span>rea-video</span>
                <span style={{ color: status?.rea_video_installed ? 'var(--la)' : 'var(--cam)', fontWeight: 600 }}>
                  {status?.rea_video_installed ? 'Sẵn sàng' : 'Chưa cài'}
                </span>
              </div>
              <div className="flex items-center justify-between" style={{ color: 'var(--mo)' }}>
                <span>FFmpeg 9:16</span>
                <span style={{ color: status?.ffmpeg_installed ? 'var(--la)' : 'var(--cam)', fontWeight: 600 }}>
                  {status?.ffmpeg_installed ? 'Sẵn sàng' : 'Fallback'}
                </span>
              </div>
              <div className="flex items-center justify-between" style={{ color: 'var(--mo)' }}>
                <span>yt-dlp Engine</span>
                <span style={{ color: status?.ytdlp_installed ? 'var(--la)' : 'var(--cam)', fontWeight: 600 }}>
                  {status?.ytdlp_installed ? 'Sẵn sàng' : 'Fallback'}
                </span>
              </div>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('cai-dat')}
              className="w-full flex items-center justify-between px-2.5 py-2 rounded-xl text-xs font-semibold border transition"
              style={{
                background: activeTab === 'cai-dat' ? 'var(--xanh)' : 'var(--xam)',
                borderColor: activeTab === 'cai-dat' ? 'transparent' : 'var(--vien-nhe)',
                color: activeTab === 'cai-dat' ? '#ffffff' : 'var(--chu)',
              }}
            >
              <span className="flex items-center gap-2">
                <Settings className="w-3.5 h-3.5" />
                <span>Cài đặt Agent-Reach &amp; rea-video</span>
              </span>
              <span className="text-[10px] font-semibold">VI</span>
            </button>
          </div>
        </aside>

        {/* MAIN WORKSPACE CONTENT */}
        <main className="flex-1 min-w-0 p-5 md:p-6 overflow-y-auto">
          <div className="max-w-[1440px] mx-auto space-y-5">
            {/* ==============================================================
                VIEW 1: QUÉT TỪ KHOÁ (Exact 2-Column SpyWinAds Layout)
               ============================================================== */}
            {activeTab === 'quet-tu-khoa' && (
              <div className="space-y-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--chu)' }}>
                      Quét từ khoá
                    </h1>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--mo)' }}>
                      Tìm từ khoá từ sản phẩm đang thắng, Pinterest Trends, Google Trends và quét video đa nền tảng bằng
                      Crawl4AI + yt-dlp miễn phí.
                    </p>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <span
                      className="px-3 py-1 rounded-full font-semibold"
                      style={{ background: 'var(--la-bg)', color: 'var(--la)' }}
                    >
                      Miễn phí 100% (Mạng nhà)
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                  {/* LEFT COLUMN: Keyword Discovery + Live Videos Found */}
                  <div className="lg:col-span-6 space-y-5">
                    <div className="sw-card p-5 space-y-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <h2 className="text-sm font-bold" style={{ color: 'var(--chu)' }}>
                          Khám phá từ khoá xu hướng
                        </h2>
                        <div className="sw-seg">
                          {[
                            { id: 'tu-dao' as KeywordSourceTab, label: 'Tự đào' },
                            { id: 'pinterest' as KeywordSourceTab, label: 'Pinterest Trends' },
                            { id: 'google' as KeywordSourceTab, label: 'Google Trends' },
                          ].map((sub) => (
                            <button
                              key={sub.id}
                              onClick={() => setKwSourceTab(sub.id)}
                              className={`sw-seg-item ${kwSourceTab === sub.id ? 'active' : ''}`}
                            >
                              {sub.label}
                            </button>
                          ))}
                        </div>
                      </div>

                      <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                        {TRENDING_KEYWORDS[kwSourceTab].map((item) => {
                          const inBasket = basketLines.includes(item.keyword);
                          return (
                            <div
                              key={item.keyword}
                              className="flex items-center justify-between gap-3 px-3.5 py-2.5 rounded-2xl border transition"
                              style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}
                            >
                              <div className="min-w-0">
                                <div className="text-[13px] font-semibold truncate" style={{ color: 'var(--chu)' }}>
                                  {item.keyword}
                                </div>
                                <div className="flex items-center gap-2 text-[11px] mt-0.5" style={{ color: 'var(--mo)' }}>
                                  <span>{item.tag}</span>
                                  <span>•</span>
                                  <span style={{ color: 'var(--la)', fontWeight: 600 }}>{item.heat}</span>
                                </div>
                              </div>
                              <button
                                onClick={() => addKeywordToBasket(item.keyword)}
                                className="sw-pill-btn px-3 py-1 text-xs border shrink-0"
                                style={{
                                  background: inBasket ? 'var(--la-bg)' : 'var(--nen)',
                                  borderColor: inBasket ? 'transparent' : 'var(--vien)',
                                  color: inBasket ? 'var(--la)' : 'var(--link)',
                                }}
                              >
                                {inBasket ? '✓ Trong giỏ' : '+ Thêm vào giỏ'}
                              </button>
                            </div>
                          );
                        })}
                      </div>

                      <div className="flex items-center justify-between pt-1">
                        <span className="text-[11px]" style={{ color: 'var(--mo2)' }}>
                          Chọn từ khoá để đưa sang Giỏ quét bên phải
                        </span>
                        <button
                          onClick={addAllKeywordsToBasket}
                          className="text-xs font-semibold hover:underline"
                          style={{ color: 'var(--link)' }}
                        >
                          + Thêm hết nhóm này
                        </button>
                      </div>
                    </div>

                    {/* Bottom Left: Video tìm được đến giờ */}
                    <div className="sw-card p-5 space-y-3">
                      <div className="flex items-center justify-between">
                        <h3 className="text-sm font-bold" style={{ color: 'var(--chu)' }}>
                          Video tìm được đến giờ ({enrichedVideos.length})
                        </h3>
                        <button
                          onClick={() => setActiveTab('video-da-quet')}
                          className="text-xs font-semibold hover:underline"
                          style={{ color: 'var(--link)' }}
                        >
                          Mở tất cả →
                        </button>
                      </div>

                      <div className="space-y-2.5 max-h-[300px] overflow-y-auto pr-1">
                        {enrichedVideos.slice(0, 6).map((item) => (
                          <div
                            key={item.raw.id}
                            className="flex items-center justify-between gap-3 p-2.5 rounded-2xl border"
                            style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}
                          >
                            <div
                              onClick={() => setDrawerVideoId(item.raw.id)}
                              className="flex items-center gap-3 min-w-0 cursor-pointer"
                            >
                              {item.localMediaUrl ? (
                                <video
                                  src={item.localMediaUrl}
                                  poster={item.raw.thumbnail_url || undefined}
                                  muted
                                  preload="metadata"
                                  playsInline
                                  className="w-11 h-14 rounded-xl object-cover shrink-0 bg-black"
                                />
                              ) : (
                                <img
                                  src={
                                    item.raw.thumbnail_url ||
                                    'https://images.unsplash.com/photo-1611162617474-5b21e879e113?auto=format&fit=crop&w=200&q=80'
                                  }
                                  alt={item.raw.title}
                                  className="w-11 h-14 rounded-xl object-cover shrink-0 bg-black"
                                />
                              )}
                              <div className="min-w-0">
                                <div className="text-xs font-semibold truncate" style={{ color: 'var(--chu)' }}>
                                  {item.raw.title}
                                </div>
                                <div className="flex items-center gap-2 text-[11px] mt-0.5" style={{ color: 'var(--mo)' }}>
                                  <span>{item.videoAgeDays} ngày</span>
                                  <span>•</span>
                                  <span>Win {item.winCount}</span>
                                  <span>•</span>
                                  <span>Scale {item.scaleCount}</span>
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center gap-1.5 shrink-0">
                              <button
                                onClick={() => setDrawerVideoId(item.raw.id)}
                                className="sw-pill-btn px-2.5 py-1 text-[11px] border flex items-center gap-1 font-semibold"
                                style={{ background: 'var(--xanh-bg)', borderColor: 'transparent', color: 'var(--link)' }}
                              >
                                <Play className="w-3 h-3 fill-current" />
                                Xem &amp; Phân tích
                              </button>
                              <button
                                onClick={() => handleSelectForClone(item.raw)}
                                className="sw-pill-btn-primary px-2.5 py-1 text-[11px]"
                              >
                                Clone
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* RIGHT COLUMN: Giỏ quét + Settings + Progress + URL Import */}
                  <div className="lg:col-span-6 space-y-5">
                    <form onSubmit={handleBatchCrawl} className="sw-card p-5 space-y-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <h2 className="text-sm font-bold" style={{ color: 'var(--chu)' }}>
                            Giỏ quét
                          </h2>
                          <span
                            className="px-2 py-0.5 rounded-full text-[11px] font-semibold"
                            style={{ background: 'var(--xanh-bg)', color: 'var(--link)' }}
                          >
                            {basketLines.length} từ khoá
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => setScanBasket('')}
                          className="text-xs font-medium hover:underline"
                          style={{ color: 'var(--mo)' }}
                        >
                          Xoá trắng
                        </button>
                      </div>

                      <textarea
                        rows={4}
                        value={scanBasket}
                        onChange={(e) => setScanBasket(e.target.value)}
                        placeholder="Nhập mỗi dòng 1 từ khoá cần tìm video (vd: máy ép chậm mini)..."
                        className="sw-input w-full p-3.5 text-[13px] leading-relaxed"
                      />

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-[11px] font-semibold mb-1.5" style={{ color: 'var(--mo)' }}>
                            Kiểu tìm
                          </label>
                          <div className="sw-seg w-full">
                            <button
                              type="button"
                              onClick={() => setMatchType('exact')}
                              className={`sw-seg-item flex-1 text-center ${matchType === 'exact' ? 'active' : ''}`}
                            >
                              Đúng cụm từ
                            </button>
                            <button
                              type="button"
                              onClick={() => setMatchType('broad')}
                              className={`sw-seg-item flex-1 text-center ${matchType === 'broad' ? 'active' : ''}`}
                            >
                              Chữ rời rạc
                            </button>
                          </div>
                        </div>

                        <div>
                          <label className="block text-[11px] font-semibold mb-1.5" style={{ color: 'var(--mo)' }}>
                            Thị trường & Ngôn ngữ
                          </label>
                          <select
                            value={marketCountry}
                            onChange={(e) => setMarketCountry(e.target.value)}
                            className="sw-input w-full px-3 py-2 text-xs font-medium"
                          >
                            <option value="VN">VN · Việt Nam (Shopee / Reels / Ads)</option>
                            <option value="US">US · Mỹ (TikTok / Meta US / Dropship)</option>
                            <option value="GLOBAL">GLOBAL · Toàn cầu (Tiếng Anh)</option>
                          </select>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-[11px] font-semibold mb-1.5" style={{ color: 'var(--mo)' }}>
                            Nền tảng nguồn (Trọng tâm Hệ Meta)
                          </label>
                          <select
                            value={crawlPlatform}
                            onChange={(e) => setCrawlPlatform(e.target.value)}
                            className="sw-input w-full px-3 py-2 text-xs font-medium"
                          >
                            <optgroup label="Trọng tâm: Hệ Meta (Miễn phí · Tự lấy Link Shop/SP & Giá)">
                              <option value="all">Tất cả 3 kênh Meta (Facebook + Instagram + Threads Ads)</option>
                              <option value="facebook">Facebook Video Ads &amp; Reels (Meta Library)</option>
                              <option value="instagram">Instagram Video Ads &amp; Reels (Meta Library + Session)</option>
                              <option value="threads">Threads Video Ads &amp; Posts (Meta Library)</option>
                              <option value="meta_ads">Meta Ads Library (Tổng hợp mọi vị trí)</option>
                            </optgroup>
                            <optgroup label="Mở rộng sau (Thử nghiệm)">
                              <option value="tiktok">TikTok Viral (Agent-Reach Web)</option>
                              <option value="youtube">YouTube &amp; Shorts (Agent-Reach)</option>
                              <option value="xiaohongshu">Xiaohongshu / Tiểu Hồng Thư (Agent-Reach)</option>
                              <option value="bilibili">Bilibili / B站 (Agent-Reach)</option>
                            </optgroup>
                          </select>
                        </div>

                        <div>
                          <label className="block text-[11px] font-semibold mb-1.5" style={{ color: 'var(--mo)' }}>
                            Crawler Engine
                          </label>
                          <select
                            value={crawlEngine}
                            onChange={(e) => setCrawlEngine(e.target.value)}
                            className="sw-input w-full px-3 py-2 text-xs font-medium"
                          >
                            <option value="agent_reach">Agent-Reach Multi-Social + Playwright + yt-dlp</option>
                            <option value="treg_api">treg.to Meta Ads Connector (API Key)</option>
                          </select>
                        </div>
                      </div>

                      <button
                        type="submit"
                        disabled={scanStage === 'scanning' || scanStage === 'digging'}
                        className="sw-pill-btn-primary w-full py-3 text-sm flex items-center justify-center gap-2"
                      >
                        {scanStage === 'scanning' || scanStage === 'digging' ? (
                          <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                          <Search className="w-4 h-4" />
                        )}
                        {scanStage === 'scanning'
                          ? 'Đang quét từ khoá...'
                          : scanStage === 'digging'
                          ? 'Đang đào sâu video...'
                          : `Quét ${basketLines.length} từ khoá`}
                      </button>

                      {/* SpyWinAds Progress Box */}
                      <div
                        className="p-3.5 rounded-2xl border flex items-center justify-between text-xs"
                        style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}
                      >
                        <div className="flex items-center gap-2 font-medium">
                          <span
                            className="w-2 h-2 rounded-full"
                            style={{
                              background:
                                scanStage === 'done'
                                  ? 'var(--la)'
                                  : scanStage === 'idle'
                                  ? 'var(--mo2)'
                                  : 'var(--xanh)',
                            }}
                          />
                          <span>
                            {scanStage === 'idle' && 'Sẵn sàng quét · Mạng nhà'}
                            {scanStage === 'scanning' && 'Bước 1/3: Đang quét bảng quảng cáo & Reels...'}
                            {scanStage === 'digging' && 'Bước 2/3: Đang đào sâu video & phân tab Win/Scale...'}
                            {scanStage === 'done' && 'Bước 3/3: Xong — Video mới đã lên các tab kết quả!'}
                          </span>
                        </div>
                        {scanStage === 'done' && (
                          <button
                            type="button"
                            onClick={() => setActiveTab('video-win')}
                            className="font-semibold hover:underline"
                            style={{ color: 'var(--link)' }}
                          >
                            Xem Video Win →
                          </button>
                        )}
                      </div>

                      {crawlNotes.length > 0 && (
                        <div className="text-[11px] space-y-1 pt-1" style={{ color: 'var(--mo)' }}>
                          {crawlNotes.map((n, i) => (
                            <div key={i}>• {n}</div>
                          ))}
                        </div>
                      )}
                    </form>

                    {/* Direct URL Import Card */}
                    <form onSubmit={handleInspectUrl} className="sw-card p-5 space-y-3">
                      <div className="flex items-center justify-between">
                        <h3 className="text-sm font-bold flex items-center gap-2" style={{ color: 'var(--chu)' }}>
                          <Link2 className="w-4 h-4" style={{ color: 'var(--link)' }} />
                          Dán link trực tiếp (Mọi nền tảng Social)
                        </h3>
                        <span className="text-[11px]" style={{ color: 'var(--mo)' }}>
                          Agent-Reach + yt-dlp MP4
                        </span>
                      </div>
                      <div className="flex flex-col sm:flex-row gap-2">
                        <input
                          value={inspectUrlInput}
                          onChange={(e) => setInspectUrlInput(e.target.value)}
                          placeholder="Dán link YouTube, Bilibili, Xiaohongshu, TikTok, IG, FB, X, Threads..."
                          className="sw-input flex-1 px-3.5 py-2 text-xs"
                        />
                        <button
                          type="submit"
                          disabled={isInspecting}
                          className="sw-pill-btn px-4 py-2 text-xs font-semibold flex items-center justify-center gap-1.5 border shrink-0"
                          style={{
                            background: 'var(--xanh-bg)',
                            color: 'var(--link)',
                            borderColor: 'transparent',
                          }}
                        >
                          <Download className="w-3.5 h-3.5" />
                          {isInspecting ? 'Đang tải...' : 'Tải MP4 & Phân tích'}
                        </button>
                      </div>
                    </form>

                    {/* Agent-Reach Deep Action Explorer */}
                    <form onSubmit={handleAgentReachExecute} className="sw-card p-5 space-y-3">
                      <div className="flex items-center justify-between">
                        <h3 className="text-sm font-bold flex items-center gap-2" style={{ color: 'var(--chu)' }}>
                          <Globe className="w-4 h-4" style={{ color: 'var(--la)' }} />
                          Trình Quét Sâu Agent-Reach (Hot Trend / Profile / Phụ đề / Bình luận)
                        </h3>
                        <button
                          type="button"
                          onClick={() => setActiveTab('cai-dat')}
                          className="text-[11px] font-semibold hover:underline"
                          style={{ color: 'var(--link)' }}
                        >
                          Login tài khoản →
                        </button>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-12 gap-2">
                        <select
                          value={arExecChannel}
                          onChange={(e) => setArExecChannel(e.target.value)}
                          className="sw-input sm:col-span-4 px-3 py-2 text-xs font-medium"
                        >
                          <option value="youtube">YouTube</option>
                          <option value="xiaohongshu">Xiaohongshu (XHS)</option>
                          <option value="bilibili">Bilibili</option>
                          <option value="instagram">Instagram</option>
                          <option value="facebook">Facebook</option>
                          <option value="twitter">X / Twitter</option>
                          <option value="reddit">Reddit</option>
                          <option value="v2ex">V2EX</option>
                          <option value="web">Web (TikTok/Douyin/Threads)</option>
                        </select>
                        <select
                          value={arExecAction}
                          onChange={(e) => setArExecAction(e.target.value)}
                          className="sw-input sm:col-span-3 px-3 py-2 text-xs font-medium"
                        >
                          <option value="search">search (Tìm kiếm)</option>
                          <option value="hot">hot (Đang thịnh hành)</option>
                          <option value="posts">posts (Bài của User)</option>
                          <option value="tweets">tweets (Tweet của User)</option>
                          <option value="profile">profile (Thông tin kênh)</option>
                          <option value="subtitle">subtitle (Lấy phụ đề)</option>
                          <option value="comments">comments (Đọc bình luận)</option>
                          <option value="subreddit">subreddit (Nhóm Reddit)</option>
                          <option value="read">read (Đọc chi tiết URL)</option>
                        </select>
                        <input
                          value={arExecQuery}
                          onChange={(e) => setArExecQuery(e.target.value)}
                          placeholder="Từ khoá, @username hoặc URL..."
                          className="sw-input sm:col-span-5 px-3 py-2 text-xs"
                        />
                      </div>
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[11px]" style={{ color: 'var(--mo2)' }}>
                          Hỗ trợ lấy video, phụ đề & bình luận trực tiếp bằng phiên đã đăng nhập trong Agent-Reach.
                        </span>
                        <button
                          type="submit"
                          disabled={arExecRunning}
                          className="sw-pill-btn-primary px-4 py-2 text-xs flex items-center gap-1.5 shrink-0"
                        >
                          {arExecRunning ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Terminal className="w-3.5 h-3.5" />}
                          {arExecRunning ? 'Đang chạy...' : 'Chạy Agent-Reach & Lưu Video'}
                        </button>
                      </div>
                      {arExecResult && (
                        <pre
                          className="p-3 rounded-xl text-[11px] overflow-x-auto max-h-40 whitespace-pre-wrap"
                          style={{ background: 'var(--xam)', color: 'var(--mo)' }}
                        >
                          {arExecResult}
                        </pre>
                      )}
                    </form>
                  </div>
                </div>
              </div>
            )}

            {/* ==============================================================
                VIEW 1B: DÒ SHOP & SẢN PHẨM ĐANG BÁN (META ADS -> FB / IG / THREADS)
               ============================================================== */}
            {activeTab === 'do-shop-meta' && (
              <div className="space-y-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--chu)' }}>
                      Dò Shop &amp; Sản Phẩm Đang Bán (Meta Ads)
                    </h1>
                    <p className="text-xs mt-1" style={{ color: 'var(--mo)' }}>
                      Nguồn công khai miễn phí 100% từ Meta Ad Library · Tự động liên kết Video Ads trên{' '}
                      <strong style={{ color: 'var(--chu)' }}>Facebook · Instagram · Threads</strong> và bóc tách đồng thời{' '}
                      <strong style={{ color: 'var(--la)' }}>Link Shop + Link Sản Phẩm + Giá Đang Bán</strong>.
                    </p>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <span
                      className="px-3 py-1 rounded-full font-semibold"
                      style={{ background: 'var(--la-bg)', color: 'var(--la)' }}
                    >
                      Meta Ads GraphQL · Free 100%
                    </span>
                    {metaTotalMarketAds > 0 && (
                      <span
                        className="px-3 py-1 rounded-full font-semibold"
                        style={{ background: 'var(--xanh-bg)', color: 'var(--link)' }}
                      >
                        ~{formatCompact(metaTotalMarketAds)} QC toàn thị trường
                      </span>
                    )}
                  </div>
                </div>

                {/* Search Bar Card */}
                <form onSubmit={(e) => handleSearchMetaShops(e)} className="sw-card p-5 space-y-3.5">
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
                    <div className="lg:col-span-6">
                      <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                        Từ khoá sản phẩm / Tên Shop / Domain / Link Fanpage Facebook
                      </label>
                      <input
                        value={metaShopQuery}
                        onChange={(e) => setMetaShopQuery(e.target.value)}
                        placeholder="VD: dây chuyền bạc, máy ép chậm, Wander Prints, shopee.vn/..., hoặc link Fanpage..."
                        className="sw-input w-full px-3.5 py-2.5 text-xs"
                      />
                    </div>
                    <div className="lg:col-span-2">
                      <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                        Thị trường
                      </label>
                      <select
                        value={metaShopCountry}
                        onChange={(e) => setMetaShopCountry(e.target.value as 'VN' | 'US' | 'ALL')}
                        className="sw-input w-full px-3 py-2.5 text-xs font-medium"
                      >
                        <option value="VN">VN · Việt Nam</option>
                        <option value="US">US · Mỹ / Global</option>
                        <option value="ALL">ALL · Toàn cầu</option>
                      </select>
                    </div>
                    <div className="lg:col-span-2">
                      <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                        Nền tảng liên kết
                      </label>
                      <select
                        value={metaShopPlatform}
                        onChange={(e) => setMetaShopPlatform(e.target.value as 'all' | 'facebook' | 'instagram' | 'threads')}
                        className="sw-input w-full px-3 py-2.5 text-xs font-medium"
                      >
                        <option value="all">Cả 3 (FB + IG + Threads)</option>
                        <option value="facebook">Facebook Ads</option>
                        <option value="instagram">Instagram Ads</option>
                        <option value="threads">Threads Ads</option>
                      </select>
                    </div>
                    <div className="lg:col-span-2 flex items-end">
                      <button
                        type="submit"
                        disabled={metaShopSearching}
                        className="sw-pill-btn-primary w-full py-2.5 px-4 text-xs font-semibold flex items-center justify-center gap-1.5"
                      >
                        {metaShopSearching ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
                        {metaShopSearching ? 'Đang dò...' : 'Tìm Shop & SP'}
                      </button>
                    </div>
                  </div>

                  {/* Quick Niche Chips */}
                  <div className="flex flex-wrap items-center gap-1.5 pt-0.5 text-[11px]">
                    <span style={{ color: 'var(--mo2)' }}>Gợi ý dò nhanh:</span>
                    {[
                      'dây chuyền bạc',
                      'máy ép chậm mini',
                      'kem chống nắng',
                      'đèn ngủ decor',
                      'bàn chải điện',
                      'ergonomic chair',
                    ].map((kw) => (
                      <button
                        key={kw}
                        type="button"
                        onClick={() => {
                          setMetaShopQuery(kw);
                          handleSearchMetaShops(undefined, kw);
                        }}
                        className="px-2.5 py-1 rounded-full border transition hover:opacity-85"
                        style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)', color: 'var(--chu)' }}
                      >
                        {kw}
                      </button>
                    ))}
                  </div>
                </form>

                {/* 2-Column Master-Detail: Left = Discovered Shops | Right = Active Products & Video Ads of Selected Shop */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                  {/* LEFT: Discovered Meta Ads Shops */}
                  <div className="lg:col-span-5 sw-card p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <h2 className="text-sm font-bold flex items-center gap-2" style={{ color: 'var(--chu)' }}>
                        <ShoppingBag className="w-4 h-4" style={{ color: 'var(--link)' }} />
                        Danh sách Shop trên Meta Ads ({metaShops.length})
                      </h2>
                      <span className="text-[11px]" style={{ color: 'var(--mo2)' }}>
                        Bấm chọn Shop để xem kệ SP
                      </span>
                    </div>

                    {metaShops.length === 0 ? (
                      <div className="py-12 text-center text-xs space-y-2" style={{ color: 'var(--mo)' }}>
                        <p className="font-semibold" style={{ color: 'var(--chu)' }}>
                          Chưa có Shop nào được lưu trong phiên này.
                        </p>
                        <p>Nhập từ khoá ngách hoặc tên thương hiệu ở trên rồi bấm &ldquo;Tìm Shop &amp; SP&rdquo; nhé!</p>
                      </div>
                    ) : (
                      <div className="space-y-2.5 max-h-[680px] overflow-y-auto pr-1">
                        {metaShops.map((sh) => {
                          const isSelected = selectedMetaShop?.id === sh.id;
                          const isScanningThis =
                            scanningShopKey === String(sh.id) || (sh.page_id && scanningShopKey === sh.page_id);
                          return (
                            <div
                              key={sh.id}
                              onClick={async () => {
                                setSelectedMetaShop(sh);
                                try {
                                  const det = await api.getMetaShopDetail(sh.id);
                                  setSelectedMetaShop(det.shop);
                                  setSelectedMetaShopProducts(det.products || []);
                                } catch {
                                  setSelectedMetaShopProducts(sh.preview_products || []);
                                }
                              }}
                              className="p-3.5 rounded-2xl border cursor-pointer transition space-y-2"
                              style={{
                                background: isSelected ? 'var(--xanh-bg)' : 'var(--xam)',
                                borderColor: isSelected ? 'var(--xanh)' : 'var(--vien-nhe)',
                              }}
                            >
                              <div className="flex items-start justify-between gap-2">
                                <div className="min-w-0">
                                  <div className="font-bold text-xs truncate flex items-center gap-1.5" style={{ color: 'var(--chu)' }}>
                                    <span>{sh.shop_name}</span>
                                    {sh.is_inbox_only && (
                                      <span
                                        className="px-1.5 py-0.5 rounded text-[9px] font-semibold"
                                        style={{ background: 'var(--cam-bg)', color: 'var(--cam)' }}
                                      >
                                        Bán qua Inbox
                                      </span>
                                    )}
                                  </div>
                                  <div className="text-[11px] truncate mt-0.5" style={{ color: 'var(--mo)' }}>
                                    {sh.domain || (sh.page_id ? `Page ID: ${sh.page_id}` : 'Meta Advertiser')}
                                    {sh.ig_handle ? ` · @${sh.ig_handle}` : ''}
                                  </div>
                                </div>
                                <span
                                  className="px-2 py-0.5 rounded-full text-[10px] font-bold shrink-0"
                                  style={{ background: 'var(--nen)', color: 'var(--link)' }}
                                >
                                  {sh.active_ads_count} QC active
                                </span>
                              </div>

                              {/* Price + 3-Platform Badges */}
                              <div className="flex flex-wrap items-center justify-between gap-2 text-[11px]">
                                <div className="flex items-center gap-1.5">
                                  <span
                                    className="font-bold"
                                    style={{ color: sh.price_range ? 'var(--la)' : 'var(--mo2)' }}
                                  >
                                    {sh.price_range || 'Xem giá từng SP'}
                                  </span>
                                  <span style={{ color: 'var(--mo2)' }}>· {sh.products_count || 0} SP</span>
                                </div>
                                <div className="flex items-center gap-1">
                                  {(sh.placements || ['facebook']).map((pl) => (
                                    <span
                                      key={pl}
                                      className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase"
                                      style={{ background: 'var(--nen)', color: 'var(--chu)' }}
                                    >
                                      {pl === 'facebook' ? 'FB' : pl === 'instagram' ? 'IG' : pl === 'threads' ? 'Threads' : pl}
                                    </span>
                                  ))}
                                </div>
                              </div>

                              {/* Quick Links & Deep Product Catalog Scan */}
                              <div className="flex flex-wrap items-center justify-between gap-1.5 pt-1" onClick={(e) => e.stopPropagation()}>
                                <div className="flex items-center gap-1.5">
                                  {sh.shop_url && (
                                    <a
                                      href={sh.shop_url}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="px-2 py-1 rounded-lg text-[10px] font-bold flex items-center gap-1 hover:opacity-90"
                                      style={{ background: 'var(--la-bg)', color: 'var(--la)' }}
                                      title={sh.shop_url}
                                    >
                                      <ShoppingBag className="w-3 h-3" />
                                      Link Shop
                                      <ExternalLink className="w-2.5 h-2.5" />
                                    </a>
                                  )}
                                  {sh.ad_library_url && (
                                    <a
                                      href={sh.ad_library_url}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="px-2 py-1 rounded-lg text-[10px] font-semibold border flex items-center gap-1"
                                      style={{ background: 'var(--nen)', borderColor: 'var(--vien-nhe)', color: 'var(--mo)' }}
                                    >
                                      Ad Library
                                      <ExternalLink className="w-2.5 h-2.5" />
                                    </a>
                                  )}
                                </div>

                                <button
                                  type="button"
                                  disabled={Boolean(isScanningThis)}
                                  onClick={() =>
                                    handleInspectMetaShopProducts({
                                      id: sh.id,
                                      page_id: sh.page_id,
                                      shop_name: sh.shop_name,
                                    })
                                  }
                                  className="px-2.5 py-1 rounded-lg text-[10px] font-bold border flex items-center gap-1"
                                  style={{ background: 'var(--nen)', borderColor: 'var(--vien)', color: 'var(--link)' }}
                                >
                                  <RefreshCw className={`w-2.5 h-2.5 ${isScanningThis ? 'animate-spin' : ''}`} />
                                  {isScanningThis ? 'Đang quét kệ SP...' : 'Quét toàn bộ SP của Shop'}
                                </button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* RIGHT: Selected Shop's Advertised Products & Video Creatives */}
                  <div className="lg:col-span-7 sw-card p-5 space-y-4">
                    {selectedMetaShop ? (
                      <>
                        <div className="flex flex-wrap items-start justify-between gap-3 pb-3 border-b" style={{ borderColor: 'var(--vien-nhe)' }}>
                          <div className="space-y-1 min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                              <h2 className="text-base font-bold" style={{ color: 'var(--chu)' }}>
                                Kệ Sản Phẩm Đang Bán: {selectedMetaShop.shop_name}
                              </h2>
                              <span
                                className="px-2.5 py-0.5 rounded-full text-[11px] font-bold"
                                style={{ background: 'var(--xanh-bg)', color: 'var(--link)' }}
                              >
                                {selectedMetaShopProducts.length} sản phẩm/mẫu Ads
                              </span>
                            </div>
                            <div className="flex flex-wrap items-center gap-2 text-xs" style={{ color: 'var(--mo)' }}>
                              {selectedMetaShop.shop_url && (
                                <a
                                  href={selectedMetaShop.shop_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="font-semibold hover:underline flex items-center gap-1"
                                  style={{ color: 'var(--la)' }}
                                >
                                  <ShoppingBag className="w-3.5 h-3.5" />
                                  Link Shop: {selectedMetaShop.domain || selectedMetaShop.shop_url.slice(0, 42)}
                                  <ExternalLink className="w-3 h-3" />
                                </a>
                              )}
                              {selectedMetaShop.page_url && (
                                <a
                                  href={selectedMetaShop.page_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="hover:underline flex items-center gap-1"
                                  style={{ color: 'var(--link)' }}
                                >
                                  Fanpage FB
                                  <ExternalLink className="w-3 h-3" />
                                </a>
                              )}
                              {selectedMetaShop.ig_handle && (
                                <a
                                  href={`https://www.instagram.com/${selectedMetaShop.ig_handle}/`}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="hover:underline flex items-center gap-1"
                                  style={{ color: '#b91c6e' }}
                                >
                                  IG @{selectedMetaShop.ig_handle}
                                  <ExternalLink className="w-3 h-3" />
                                </a>
                              )}
                            </div>
                          </div>

                          <button
                            type="button"
                            disabled={scanningShopKey !== null}
                            onClick={() =>
                              handleInspectMetaShopProducts({
                                id: selectedMetaShop.id,
                                page_id: selectedMetaShop.page_id,
                                shop_name: selectedMetaShop.shop_name,
                              })
                            }
                            className="sw-pill-btn-primary px-3.5 py-2 text-xs font-semibold flex items-center gap-1.5 shrink-0"
                          >
                            <RefreshCw className={`w-3.5 h-3.5 ${scanningShopKey !== null ? 'animate-spin' : ''}`} />
                            Quét Sâu Toàn Bộ Kệ SP ({selectedMetaShop.active_ads_count} QC)
                          </button>
                        </div>

                        {selectedMetaShopProducts.length === 0 ? (
                          <div className="py-12 text-center text-xs space-y-2" style={{ color: 'var(--mo)' }}>
                            <p>Chưa tải danh sách sản phẩm chi tiết cho shop này.</p>
                            <p>Bấm nút &ldquo;Quét Sâu Toàn Bộ Kệ SP&rdquo; phía trên để mở toàn bộ sản phẩm đang chạy Ads của shop!</p>
                          </div>
                        ) : (
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 max-h-[620px] overflow-y-auto pr-1">
                            {selectedMetaShopProducts.map((prod) => (
                              <div
                                key={prod.id}
                                className="p-3.5 rounded-2xl border flex flex-col justify-between gap-3"
                                style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}
                              >
                                <div className="space-y-2.5">
                                  {/* Top Row: Scale Count + Placements (FB / IG / Threads) */}
                                  <div className="flex items-center justify-between gap-2 text-[10px]">
                                    <span
                                      className="px-2 py-0.5 rounded-full font-bold"
                                      style={{ background: 'var(--xanh-bg)', color: 'var(--link)' }}
                                    >
                                      Scale {prod.ads_duplication_count} QC · {prod.video_age_days} ngày
                                    </span>
                                    <div className="flex items-center gap-1">
                                      {(prod.placements || ['facebook']).map((pl) => (
                                        <span
                                          key={pl}
                                          className="px-1.5 py-0.5 rounded font-bold uppercase"
                                          style={{ background: 'var(--nen)', color: 'var(--chu)' }}
                                        >
                                          {pl === 'facebook' ? 'FB' : pl === 'instagram' ? 'IG' : pl === 'threads' ? 'Threads' : pl}
                                        </span>
                                      ))}
                                    </div>
                                  </div>

                                  {/* Media Preview + Product Title + Selling Price */}
                                  <div className="flex gap-3">
                                    <div className="w-20 h-28 rounded-xl overflow-hidden bg-black shrink-0 relative">
                                      {prod.video_url ? (
                                        <video
                                          src={prod.video_url}
                                          poster={prod.thumbnail_url || undefined}
                                          muted
                                          loop
                                          playsInline
                                          onMouseEnter={(e) => e.currentTarget.play().catch(() => {})}
                                          onMouseLeave={(e) => {
                                            e.currentTarget.pause();
                                            e.currentTarget.currentTime = 0;
                                          }}
                                          className="w-full h-full object-cover"
                                        />
                                      ) : prod.thumbnail_url ? (
                                        <img src={prod.thumbnail_url} alt={prod.product_title} className="w-full h-full object-cover" />
                                      ) : (
                                        <div className="w-full h-full flex items-center justify-center text-[10px] text-white/60">
                                          Ad Card
                                        </div>
                                      )}
                                      {prod.video_url && (
                                        <span className="absolute bottom-1 left-1 px-1 py-0.5 rounded bg-black/75 text-white text-[9px] font-bold">
                                          MP4
                                        </span>
                                      )}
                                    </div>

                                    <div className="min-w-0 flex-1 space-y-1">
                                      <div className="font-bold text-xs line-clamp-2 leading-snug" style={{ color: 'var(--chu)' }}>
                                        {prod.product_title}
                                      </div>
                                      <div className="flex flex-wrap items-baseline gap-1.5">
                                        <span
                                          className="text-xs font-bold"
                                          style={{ color: prod.selling_price ? 'var(--la)' : 'var(--mo2)' }}
                                        >
                                          {prod.selling_price || 'Chưa niêm yết giá'}
                                        </span>
                                        {prod.original_price && (
                                          <span className="text-[10px] line-through" style={{ color: 'var(--mo2)' }}>
                                            {prod.original_price}
                                          </span>
                                        )}
                                      </div>
                                      <p className="text-[11px] line-clamp-2" style={{ color: 'var(--mo)' }}>
                                        {prod.caption || prod.cta_text}
                                      </p>
                                    </div>
                                  </div>

                                  {/* Separated Link Sản Phẩm & Link Shop */}
                                  <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
                                    {prod.product_url && (
                                      <a
                                        href={prod.product_url}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="px-2.5 py-1 rounded-lg text-[10px] font-bold flex items-center gap-1 hover:opacity-90"
                                        style={{ background: 'var(--xanh-bg)', color: 'var(--link)' }}
                                        title={prod.product_url}
                                      >
                                        <Link2 className="w-3 h-3" />
                                        Link Sản Phẩm
                                        <ExternalLink className="w-2.5 h-2.5" />
                                      </a>
                                    )}
                                    {prod.shop_url && (
                                      <a
                                        href={prod.shop_url}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="px-2.5 py-1 rounded-lg text-[10px] font-bold flex items-center gap-1 hover:opacity-90"
                                        style={{ background: 'var(--la-bg)', color: 'var(--la)' }}
                                        title={prod.shop_url}
                                      >
                                        <ShoppingBag className="w-3 h-3" />
                                        Link Shop
                                        <ExternalLink className="w-2.5 h-2.5" />
                                      </a>
                                    )}
                                    {prod.library_id && (
                                      <a
                                        href={`https://www.facebook.com/ads/library/?id=${prod.library_id}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="px-2 py-1 rounded-lg text-[10px] border flex items-center gap-1"
                                        style={{ background: 'var(--nen)', borderColor: 'var(--vien-nhe)', color: 'var(--mo)' }}
                                      >
                                        Ad #{prod.library_id.slice(-6)}
                                      </a>
                                    )}
                                  </div>
                                </div>

                                {/* Bottom Action Buttons: Save Video to Kho Video | Add to Affiliate Products */}
                                <div className="flex items-center gap-1.5 pt-2 border-t" style={{ borderColor: 'var(--vien-nhe)' }}>
                                  {prod.video_url && (
                                    <button
                                      type="button"
                                      disabled={importingShopProdId === prod.id}
                                      onClick={() => handleImportShopProductToVideos(prod)}
                                      className="sw-pill-btn-primary flex-1 py-1.5 px-2.5 text-[11px] flex items-center justify-center gap-1"
                                    >
                                      <Download className="w-3 h-3" />
                                      {importingShopProdId === prod.id ? 'Đang nạp MP4...' : 'Lưu Video & Clone'}
                                    </button>
                                  )}
                                  {(prod.product_url || prod.shop_url) && (
                                    <button
                                      type="button"
                                      onClick={() =>
                                        handleQuickAddShopProductToAffiliate(prod, selectedMetaShop.shop_name)
                                      }
                                      className="sw-pill-btn py-1.5 px-2.5 text-[11px] font-semibold border flex items-center justify-center gap-1"
                                      style={{ background: 'var(--nen)', borderColor: 'var(--vien)', color: 'var(--chu)' }}
                                    >
                                      <Plus className="w-3 h-3" />
                                      Tạo Mã Bio
                                    </button>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="py-16 text-center text-xs" style={{ color: 'var(--mo)' }}>
                        Chọn một Shop ở cột bên trái để xem toàn bộ danh sách sản phẩm &amp; video quảng cáo đang chạy của shop đó.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* ==============================================================
                VIEW 2: ĐÀO SÂU (SpyWinAds Deep Dig Queue)
               ============================================================== */}
            {activeTab === 'dao-sau' && (
              <div className="space-y-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--chu)' }}>
                      Đào sâu
                    </h1>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--mo)' }}>
                      Hàng đợi bóc tách file video MP4, kiểm tra tuổi trang bán và chia vào 4 tab Tiềm Năng / Win / Scale /
                      Bò Sữa.
                    </p>
                  </div>
                  <button
                    onClick={() => setActiveTab('quet-tu-khoa')}
                    className="sw-pill-btn-primary px-4 py-2 text-xs flex items-center gap-1.5"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    Đào sâu thêm video mới
                  </button>
                </div>

                {/* 3 Top Metric Boxes */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="sw-card p-5">
                    <div className="text-xs font-medium" style={{ color: 'var(--mo)' }}>
                      Video chờ đào
                    </div>
                    <div className="text-3xl font-bold mt-1" style={{ color: 'var(--cam)' }}>
                      {deepQueueStats.waiting}
                    </div>
                    <div className="text-[11px] mt-1" style={{ color: 'var(--mo2)' }}>
                      Chưa tải file MP4 gốc về máy
                    </div>
                  </div>
                  <div className="sw-card p-5">
                    <div className="text-xs font-medium" style={{ color: 'var(--mo)' }}>
                      Video đang đào
                    </div>
                    <div className="text-3xl font-bold mt-1" style={{ color: 'var(--xanh)' }}>
                      {deepQueueStats.running}
                    </div>
                    <div className="text-[11px] mt-1" style={{ color: 'var(--mo2)' }}>
                      Worker Crawl4AI / yt-dlp nền
                    </div>
                  </div>
                  <div className="sw-card p-5">
                    <div className="text-xs font-medium" style={{ color: 'var(--mo)' }}>
                      Video lên tab sau khi đào
                    </div>
                    <div className="text-3xl font-bold mt-1" style={{ color: 'var(--la)' }}>
                      {deepQueueStats.ready}
                    </div>
                    <div className="text-[11px] mt-1" style={{ color: 'var(--mo2)' }}>
                      Đã phân loại vào Tiềm Năng / Win / Scale
                    </div>
                  </div>
                </div>

                {/* Queue Filter + Table */}
                <div className="sw-card p-5 space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="sw-seg">
                      {[
                        { id: 'all' as DeepDigFilter, label: 'Tất cả' },
                        { id: 'da-dao' as DeepDigFilter, label: 'Đã đào' },
                        { id: 'dang-dao' as DeepDigFilter, label: 'Đang đào' },
                        { id: 'cho-dao' as DeepDigFilter, label: 'Chờ đào' },
                      ].map((f) => (
                        <button
                          key={f.id}
                          onClick={() => setDeepFilter(f.id)}
                          className={`sw-seg-item ${deepFilter === f.id ? 'active' : ''}`}
                        >
                          {f.label}
                        </button>
                      ))}
                    </div>
                    <span className="text-xs" style={{ color: 'var(--mo)' }}>
                      Hiển thị {filteredDeepQueue.length} tác vụ đào sâu
                    </span>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="border-b" style={{ borderColor: 'var(--vien-nhe)', color: 'var(--mo)' }}>
                          <th className="py-2.5 pr-3 font-semibold">Video</th>
                          <th className="py-2.5 px-3 font-semibold">Nguồn</th>
                          <th className="py-2.5 px-3 font-semibold">File MP4</th>
                          <th className="py-2.5 px-3 font-semibold">Tuổi & Tab đích</th>
                          <th className="py-2.5 px-3 font-semibold">Viral Score</th>
                          <th className="py-2.5 pl-3 font-semibold text-right">Thao tác</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredDeepQueue.map((item) => {
                          const pf = PLATFORM_META[item.raw.platform] || PLATFORM_META.facebook;
                          return (
                            <tr
                              key={item.raw.id}
                              className="border-b last:border-b-0"
                              style={{ borderColor: 'var(--vien-nhe)' }}
                            >
                              <td className="py-3 pr-3 max-w-[300px]">
                                <div className="font-semibold truncate" style={{ color: 'var(--chu)' }}>
                                  {item.raw.title}
                                </div>
                                <div className="text-[11px] truncate" style={{ color: 'var(--mo2)' }}>
                                  {item.raw.author} · {item.raw.source_url}
                                </div>
                              </td>
                              <td className="py-3 px-3">
                                <span
                                  className="px-2 py-0.5 rounded-full text-[11px] font-semibold"
                                  style={{ background: pf.pillBg, color: pf.pillColor }}
                                >
                                  {pf.short}
                                </span>
                              </td>
                              <td className="py-3 px-3">
                                <span
                                  className="px-2 py-0.5 rounded-full text-[11px] font-semibold"
                                  style={{
                                    background: item.localMediaUrl ? 'var(--la-bg)' : 'var(--o)',
                                    color: item.localMediaUrl ? 'var(--la)' : 'var(--mo)',
                                  }}
                                >
                                  {item.localMediaUrl ? 'Đã tải MP4' : 'Stream Preview'}
                                </span>
                              </td>
                              <td className="py-3 px-3">
                                <span className="font-semibold">{item.videoAgeDays} ngày</span>
                                <span className="ml-1.5 text-[11px]" style={{ color: 'var(--mo)' }}>
                                  → {item.categoryLabel}
                                </span>
                              </td>
                              <td className="py-3 px-3 font-bold" style={{ color: 'var(--link)' }}>
                                {item.raw.viral_score}/100
                              </td>
                              <td className="py-3 pl-3 text-right space-x-1.5 whitespace-nowrap">
                                <button
                                  onClick={() => handleReaDecompose(item.raw.id)}
                                  disabled={reaBusyVideoId === item.raw.id}
                                  className="sw-pill-btn px-2.5 py-1 text-[11px] border"
                                  style={{ background: 'var(--xanh-bg)', borderColor: 'transparent', color: 'var(--link)' }}
                                >
                                  {reaBusyVideoId === item.raw.id ? 'Đang mổ xẻ...' : item.raw.rea_breakdown ? '✓ Đã mổ xẻ' : 'Mổ xẻ (rea)'}
                                </button>
                                <button
                                  onClick={() => setDrawerVideoId(item.raw.id)}
                                  className="sw-pill-btn px-2.5 py-1 text-[11px] border"
                                  style={{ background: 'var(--xam)', borderColor: 'var(--vien)', color: 'var(--chu)' }}
                                >
                                  Phân tích
                                </button>
                                <button
                                  onClick={() => handleDownloadVideoSource(item.raw)}
                                  className="sw-pill-btn px-2.5 py-1 text-[11px] border"
                                  style={{ background: 'var(--nen)', borderColor: 'var(--vien)', color: 'var(--chu)' }}
                                >
                                  Tải MP4
                                </button>
                                <button
                                  onClick={() => handleSelectForClone(item.raw)}
                                  className="sw-pill-btn-primary px-3 py-1 text-[11px]"
                                >
                                  Clone ngay
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* ==============================================================
                VIEW 3: VIDEO TABS (Tiềm năng / Win / Scale / Bò sữa / Đã quét / Theo dõi / Test)
               ============================================================== */}
            {isVideoTab(activeTab) && activeTabInfo && (
              <div className="space-y-4">
                {/* Header & Toolbar */}
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--chu)' }}>
                        {activeTabInfo.title}
                      </h1>
                      <span
                        className="px-2.5 py-0.5 rounded-full text-xs font-semibold"
                        style={{ background: 'var(--nen)', border: '1px solid var(--vien-nhe)', color: 'var(--mo)' }}
                      >
                        {displayedVideos.length} video
                      </span>
                      <button
                        onClick={() => setShowRulesBox((v) => !v)}
                        className="sw-pill-btn px-2.5 py-1 text-[11px] flex items-center gap-1 border"
                        style={{
                          background: showRulesBox ? 'var(--xanh-bg)' : 'var(--nen)',
                          borderColor: showRulesBox ? 'transparent' : 'var(--vien-nhe)',
                          color: showRulesBox ? 'var(--link)' : 'var(--mo)',
                        }}
                      >
                        <Info className="w-3.5 h-3.5" />
                        Luật lọc
                      </button>
                    </div>
                    <p className="text-xs mt-1" style={{ color: 'var(--mo)' }}>
                      {activeTabInfo.subtitle}
                    </p>
                  </div>

                  {/* Right Controls: Sort + View Mode */}
                  <div className="flex flex-wrap items-center gap-2.5">
                    <select
                      value={sortMode}
                      onChange={(e) => setSortMode(e.target.value as SortMode)}
                      className="sw-input px-3 py-1.5 text-xs font-medium"
                    >
                      <option value="strongest">Sắp xếp: Mạnh nhất</option>
                      <option value="newest">Sắp xếp: Mới lên nhất</option>
                      <option value="shops">Sắp xếp: Nhiều shop chạy</option>
                    </select>

                    <div className="sw-seg">
                      <button
                        onClick={() => setViewMode('grid')}
                        className={`sw-seg-item flex items-center gap-1 ${viewMode === 'grid' ? 'active' : ''}`}
                      >
                        <LayoutGrid className="w-3.5 h-3.5" />
                        <span>Lưới</span>
                      </button>
                      <button
                        onClick={() => setViewMode('table')}
                        className={`sw-seg-item flex items-center gap-1 ${viewMode === 'table' ? 'active' : ''}`}
                      >
                        <List className="w-3.5 h-3.5" />
                        <span>Bảng</span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* Collapsible Filter Rules Callout */}
                {showRulesBox && (
                  <div
                    className="sw-card p-4 text-xs space-y-1.5 border-l-4"
                    style={{ borderLeftColor: 'var(--xanh)' }}
                  >
                    <div className="font-bold flex items-center gap-1.5" style={{ color: 'var(--chu)' }}>
                      <Info className="w-4 h-4" style={{ color: 'var(--xanh)' }} />
                      {activeTabInfo.ruleTitle}
                    </div>
                    <ul className="list-disc pl-5 space-y-1" style={{ color: 'var(--mo)' }}>
                      {activeTabInfo.rules.map((r, idx) => (
                        <li key={idx}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Platform Filter Pills — Focused on Meta Ecosystem (FB · IG · Threads) */}
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="sw-seg flex-wrap">
                    {[
                      { id: 'all', label: 'Tất cả Hệ Meta' },
                      { id: 'facebook', label: 'Facebook (Ads & Reels)' },
                      { id: 'instagram', label: 'Instagram (Ads & Reels)' },
                      { id: 'threads', label: 'Threads (Ads & Posts)' },
                      { id: 'meta_ads', label: 'Meta Ads Library' },
                    ].map((pf) => (
                      <button
                        key={pf.id}
                        onClick={() => setFilterPlatform(pf.id)}
                        className={`sw-seg-item ${filterPlatform === pf.id ? 'active' : ''}`}
                      >
                        {pf.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* =========================================================
                    DEDICATED POTENTIAL VIDEOS & COMPETITOR SHOP SPY PANEL
                   ========================================================= */}
                {activeTab === 'video-tiem-nang' && (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                      <div className="sw-card p-4">
                        <div className="text-[11px] font-medium" style={{ color: 'var(--mo)' }}>
                          Video Tiềm Năng Đạt Chuẩn
                        </div>
                        <div className="text-2xl font-bold mt-1 flex items-baseline gap-2" style={{ color: 'var(--link)' }}>
                          <span>{potentialSummary.totalPotential}</span>
                          <span className="text-xs font-semibold" style={{ color: 'var(--la)' }}>
                            ({potentialSummary.tierSCount} Hạng S · {potentialSummary.platformsCount} nền tảng)
                          </span>
                        </div>
                      </div>
                      <div className="sw-card p-4">
                        <div className="text-[11px] font-medium" style={{ color: 'var(--mo)' }}>
                          Shop Đang Chạy &amp; Link Bán
                        </div>
                        <div className="text-2xl font-bold mt-1 flex items-baseline gap-2" style={{ color: 'var(--chu)' }}>
                          <span>{potentialSummary.uniqueShopsCount} shop</span>
                          <span className="text-xs font-semibold" style={{ color: 'var(--la)' }}>
                            ({potentialSummary.shopsWithLinks} có link bán)
                          </span>
                        </div>
                      </div>
                      <div className="sw-card p-4">
                        <div className="text-[11px] font-medium" style={{ color: 'var(--mo)' }}>
                          Tổng Quảng Cáo Đang Chạy
                        </div>
                        <div className="text-2xl font-bold mt-1 flex items-baseline gap-2" style={{ color: 'var(--xanh)' }}>
                          <span>{formatCompact(potentialSummary.totalActiveAds)} QC</span>
                          <span className="text-xs font-normal" style={{ color: 'var(--mo2)' }}>
                            trên Meta Ad Library
                          </span>
                        </div>
                      </div>
                      <div className="sw-card p-4">
                        <div className="text-[11px] font-medium" style={{ color: 'var(--mo)' }}>
                          Đã Bóc Tách Giá Đang Bán
                        </div>
                        <div className="text-2xl font-bold mt-1 flex items-baseline gap-2" style={{ color: 'var(--la)' }}>
                          <span>
                            {potentialSummary.pricedCount}/{potentialSummary.totalPotential}
                          </span>
                          <span className="text-xs font-normal" style={{ color: 'var(--mo2)' }}>
                            video có giá thực
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="sw-card p-3.5 flex flex-wrap items-center justify-between gap-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <div className="sw-seg">
                          {[
                            { id: 'all' as const, label: 'Tất cả Tiềm Năng' },
                            { id: 'S' as const, label: 'Hạng S (≥82đ)' },
                            { id: 'A' as const, label: 'Hạng A (68–81đ)' },
                            { id: 'has_shop' as const, label: 'Đã lấy được Link Shop' },
                          ].map((tf) => (
                            <button
                              key={tf.id}
                              type="button"
                              onClick={() => setPotentialTierFilter(tf.id)}
                              className={`sw-seg-item ${potentialTierFilter === tf.id ? 'active' : ''}`}
                            >
                              {tf.label}
                            </button>
                          ))}
                        </div>
                        <select
                          value={potentialSpyCountry}
                          onChange={(e) => setPotentialSpyCountry(e.target.value as 'AUTO' | 'VN' | 'US')}
                          className="sw-input px-2.5 py-1.5 text-xs font-medium"
                          title="Chọn thị trường ưu tiên khi dò Shop & Ads"
                        >
                          <option value="AUTO">Thị trường dò Shop: Tự nhận diện (VN/US)</option>
                          <option value="VN">Thị trường Việt Nam (Shopee / Web VN / FB VN)</option>
                          <option value="US">Thị trường Mỹ &amp; Global (Shopify / Amazon / US Ads)</option>
                        </select>
                      </div>

                      <button
                        type="button"
                        disabled={batchSpyRunning || displayedVideos.length === 0}
                        onClick={handleEvaluatePotentialBatch}
                        className="sw-pill-btn-primary px-4 py-2 text-xs font-semibold flex items-center gap-1.5"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${batchSpyRunning ? 'animate-spin' : ''}`} />
                        {batchSpyRunning
                          ? 'Đang tự đánh giá & dò Shop / Link / Giá / Ads...'
                          : `⚡ Tự Đánh Giá & Dò Shop / Giá / Ads (${Math.min(5, displayedVideos.length)} Video)`}
                      </button>
                    </div>
                  </div>
                )}

                {/* Empty State */}
                {displayedVideos.length === 0 ? (
                  <div className="sw-card p-12 text-center space-y-3">
                    <div className="text-sm font-semibold" style={{ color: 'var(--chu)' }}>
                      Chưa có video nào trong tab "{activeTabInfo.title}" với bộ lọc hiện tại.
                    </div>
                    <p className="text-xs max-w-md mx-auto" style={{ color: 'var(--mo)' }}>
                      Bạn có thể xem toàn bộ video đã thu thập hoặc sang màn Quét từ khoá để tìm thêm quảng cáo và Reels mới.
                    </p>
                    <div className="flex items-center justify-center gap-2 pt-1">
                      <button
                        onClick={() => setActiveTab('video-da-quet')}
                        className="sw-pill-btn px-4 py-2 text-xs border"
                        style={{ background: 'var(--xam)', borderColor: 'var(--vien)', color: 'var(--chu)' }}
                      >
                        Xem tất cả Video đã quét ({enrichedVideos.length})
                      </button>
                      <button
                        onClick={() => setActiveTab('quet-tu-khoa')}
                        className="sw-pill-btn-primary px-4 py-2 text-xs"
                      >
                        Quét thêm từ khoá
                      </button>
                    </div>
                  </div>
                ) : viewMode === 'grid' ? (
                  /* GRID VIEW — Exact SpyWinAds Video Card Anatomy + Live Competitor Shop Spy */
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                    {displayedVideos.map((item) => {
                      const v = item.raw;
                      const pf = PLATFORM_META[v.platform] || PLATFORM_META.facebook;
                      const isWatch = watchlistIds.includes(v.id);
                      const isTest = testlistIds.includes(v.id);
                      const isSpyingThis = spyingVideoId === v.id;
                      return (
                        <div key={v.id} className="sw-card p-4 flex flex-col justify-between gap-3 transition hover:shadow-md">
                          <div className="space-y-3">
                            {/* 1. TOP ROW BADGES: Hạng Tiềm Năng + Tuổi video + Tốc độ view */}
                            <div className="flex items-center justify-between gap-2">
                              <div className="flex items-center gap-1.5 min-w-0">
                                <span
                                  className="px-2.5 py-1 rounded-full text-[11px] font-bold shrink-0"
                                  style={{
                                    background:
                                      item.potentialTier === 'S'
                                        ? 'var(--la-bg)'
                                        : item.potentialTier === 'A'
                                        ? 'var(--xanh-bg)'
                                        : 'var(--o)',
                                    color:
                                      item.potentialTier === 'S'
                                        ? 'var(--la)'
                                        : item.potentialTier === 'A'
                                        ? 'var(--link)'
                                        : 'var(--chu)',
                                  }}
                                  title={item.marketIntel?.verdict || 'Điểm đánh giá tiềm năng đa nền tảng'}
                                >
                                  Hạng {item.potentialTier} · {item.potentialScore}đ
                                </span>
                                <span className="text-[11px] truncate" style={{ color: 'var(--mo2)' }}>
                                  {item.videoAgeDays}d · {formatCompact(item.velocityViewsPerDay)}/ngày
                                </span>
                              </div>

                              <div className="flex items-center gap-1.5 shrink-0">
                                <span
                                  className="px-2 py-0.5 rounded-full text-[10px] font-semibold flex items-center gap-1"
                                  style={{
                                    background: item.shopActive > 0 ? 'var(--xanh-bg)' : 'var(--xam)',
                                    color: item.shopActive > 0 ? 'var(--link)' : 'var(--mo)',
                                  }}
                                  title="Số lượng Shop đang chạy & tổng Quảng cáo active phát hiện được"
                                >
                                  {item.shopActive > 0
                                    ? `${item.shopActive} shop · ${item.totalAdsSameVideo} QC`
                                    : `${item.videoAgeDays} ngày`}
                                </span>
                                <button
                                  onClick={() => toggleWatchlist(v.id)}
                                  className="p-1 rounded-full transition"
                                  style={{ color: isWatch ? '#f59e0b' : 'var(--mo2)' }}
                                  title={isWatch ? 'Bỏ Theo dõi đặc biệt' : 'Thêm Theo dõi đặc biệt'}
                                >
                                  <Star className="w-3.5 h-3.5" fill={isWatch ? '#f59e0b' : 'none'} />
                                </button>
                              </div>
                            </div>

                            {/* 2. 9:16 PREVIEW + RIGHT SIDE TITLE/INFO */}
                            <div className="flex gap-3">
                              <div
                                onClick={() => {
                                  if (item.localMediaUrl) {
                                    setPlayingCardId((prev) => (prev === v.id ? null : v.id));
                                  } else {
                                    setDrawerVideoId(v.id);
                                  }
                                }}
                                className="relative w-[112px] h-[176px] shrink-0 rounded-2xl overflow-hidden bg-black group cursor-pointer"
                                title={item.localMediaUrl ? 'Bấm để phát/dừng video trực tiếp' : 'Bấm để mở trình phát & phân tích'}
                              >
                                {item.localMediaUrl ? (
                                  <video
                                    src={item.localMediaUrl}
                                    poster={v.thumbnail_url || undefined}
                                    muted={playingCardId !== v.id}
                                    controls={playingCardId === v.id}
                                    autoPlay={playingCardId === v.id}
                                    loop
                                    playsInline
                                    onMouseEnter={(e) => {
                                      if (playingCardId !== v.id) e.currentTarget.play().catch(() => {});
                                    }}
                                    onMouseLeave={(e) => {
                                      if (playingCardId !== v.id) {
                                        e.currentTarget.pause();
                                        e.currentTarget.currentTime = 0;
                                      }
                                    }}
                                    className="w-full h-full object-cover"
                                  />
                                ) : (
                                  <img
                                    src={
                                      v.thumbnail_url ||
                                      'https://images.unsplash.com/photo-1611162617474-5b21e879e113?auto=format&fit=crop&w=400&q=80'
                                    }
                                    alt={v.title}
                                    className="w-full h-full object-cover opacity-90 group-hover:scale-105 transition duration-300"
                                  />
                                )}
                                <span
                                  className="absolute top-1.5 left-1.5 px-1.5 py-0.5 rounded-md text-[9px] font-bold pointer-events-none"
                                  style={{ background: pf.pillBg, color: pf.pillColor }}
                                >
                                  {pf.short}
                                </span>
                                {playingCardId !== v.id && (
                                  <div className="absolute inset-0 flex items-center justify-center bg-black/25 opacity-90 group-hover:bg-black/40 transition pointer-events-none">
                                    <span className="w-9 h-9 rounded-full bg-black/70 text-white flex items-center justify-center shadow-md">
                                      <Play className="w-4 h-4 fill-white ml-0.5" />
                                    </span>
                                  </div>
                                )}
                                <span className="absolute bottom-1.5 left-1.5 px-1.5 py-0.5 rounded-md bg-black/70 text-white text-[9px] font-semibold flex items-center gap-0.5 pointer-events-none">
                                  <Play className="w-2.5 h-2.5 fill-white" />
                                  {formatCompact(v.views)}
                                </span>
                              </div>

                              {/* 3. TITLE, SELLING PRICE, PRODUCT LINK + SHOP LINK & PLACEMENTS */}
                              <div className="min-w-0 flex-1 flex flex-col justify-between py-0.5">
                                <div className="space-y-1">
                                  <h3
                                    onClick={() => setDrawerVideoId(v.id)}
                                    className="text-[13px] font-bold leading-snug line-clamp-2 cursor-pointer hover:underline"
                                    style={{ color: 'var(--chu)' }}
                                  >
                                    {v.title}
                                  </h3>
                                  <div className="flex flex-wrap items-center gap-1.5 text-xs">
                                    <span
                                      className="font-bold"
                                      style={{
                                        color: item.priceLabel !== 'Chưa niêm yết giá' ? 'var(--la)' : 'var(--mo)',
                                      }}
                                    >
                                      {item.priceLabel}
                                    </span>
                                    {item.originalPriceLabel && (
                                      <span className="text-[10px] line-through" style={{ color: 'var(--mo2)' }}>
                                        {item.originalPriceLabel}
                                      </span>
                                    )}
                                  </div>
                                  <div className="flex flex-wrap items-center gap-1 pt-0.5">
                                    {item.primaryProductUrl && (
                                      <a
                                        href={item.primaryProductUrl}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="px-1.5 py-0.5 rounded-md text-[10px] font-bold flex items-center gap-0.5 hover:underline"
                                        style={{ background: 'var(--xanh-bg)', color: 'var(--link)' }}
                                        title={`Link Sản Phẩm: ${item.primaryProductUrl}`}
                                      >
                                        <Link2 className="w-2.5 h-2.5" />
                                        Link SP
                                        <ExternalLink className="w-2.5 h-2.5" />
                                      </a>
                                    )}
                                    {item.primaryShopUrl && (
                                      <a
                                        href={item.primaryShopUrl}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="px-1.5 py-0.5 rounded-md text-[10px] font-semibold flex items-center gap-0.5 hover:underline"
                                        style={{ background: 'var(--la-bg)', color: 'var(--la)' }}
                                        title={`Link Shop: ${item.primaryShopUrl}`}
                                      >
                                        <ShoppingBag className="w-2.5 h-2.5" />
                                        Link Shop
                                        <ExternalLink className="w-2.5 h-2.5" />
                                      </a>
                                    )}
                                  </div>
                                  <p className="text-[11px] truncate" style={{ color: 'var(--mo2)' }}>
                                    {v.author}
                                    {v.ig_handle && !v.author.includes(v.ig_handle) ? ` (@${v.ig_handle})` : ''}
                                  </p>
                                  <div className="flex flex-wrap items-center gap-1 text-[10px]" style={{ color: 'var(--mo)' }}>
                                    <span>Liên kết:</span>
                                    {item.placements.map((pl) => (
                                      <span
                                        key={pl}
                                        className="px-1.5 py-0.5 rounded font-bold uppercase"
                                        style={{ background: 'var(--xam)', color: 'var(--chu)' }}
                                      >
                                        {pl === 'facebook' ? 'FB' : pl === 'instagram' ? 'IG' : pl === 'threads' ? 'Threads' : pl}
                                      </span>
                                    ))}
                                  </div>
                                </div>

                                <div className="flex flex-wrap gap-1 pt-1">
                                  {isTest && (
                                    <span
                                      className="px-1.5 py-0.5 rounded-md text-[10px] font-semibold"
                                      style={{ background: 'var(--xanh-bg)', color: 'var(--link)' }}
                                    >
                                      Đang Test
                                    </span>
                                  )}
                                  {v.sales_signals.slice(0, 2).map((sig, i) => (
                                    <span
                                      key={i}
                                      className="px-1.5 py-0.5 rounded-md text-[10px] truncate max-w-[140px]"
                                      style={{ background: 'var(--xam)', color: 'var(--mo)' }}
                                    >
                                      {sig}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            </div>

                            {/* 4. REAL COMPETITOR SHOPS RUNNING THIS PRODUCT */}
                            <div
                              className="p-2.5 rounded-xl border space-y-1.5"
                              style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}
                            >
                              <div className="flex items-center justify-between gap-2 text-[10px]">
                                <span className="font-bold flex items-center gap-1" style={{ color: 'var(--chu)' }}>
                                  <ShoppingBag className="w-3 h-3" style={{ color: 'var(--link)' }} />
                                  {item.shops.length > 0
                                    ? `Shop Meta Ads (${item.shops.length} shop):`
                                    : 'Chưa dò Shop trên Meta Ads:'}
                                </span>
                                <div className="flex items-center gap-1">
                                  {item.metaPageId && (
                                    <button
                                      type="button"
                                      onClick={() =>
                                        handleInspectMetaShopProducts({
                                          page_id: item.metaPageId,
                                          shop_name: v.shop_name || v.author,
                                        })
                                      }
                                      className="px-2 py-0.5 rounded-md font-bold border transition hover:opacity-90"
                                      style={{ background: 'var(--la-bg)', borderColor: 'transparent', color: 'var(--la)' }}
                                      title="Mở toàn bộ kệ Sản Phẩm mà Shop này đang chạy Ads bán"
                                    >
                                      Kệ SP Shop
                                    </button>
                                  )}
                                  <button
                                    type="button"
                                    disabled={isSpyingThis}
                                    onClick={() => handleEvaluateSingleVideo(v.id)}
                                    className="px-2 py-0.5 rounded-md font-semibold flex items-center gap-1 border transition hover:opacity-90"
                                    style={{ background: 'var(--nen)', borderColor: 'var(--vien-nhe)', color: 'var(--link)' }}
                                  >
                                    <Search className="w-2.5 h-2.5" />
                                    {isSpyingThis ? 'Đang dò...' : item.shops.length > 0 ? 'Cập nhật' : 'Dò Meta Ads'}
                                  </button>
                                </div>
                              </div>

                              {item.shops.length > 0 ? (
                                <div className="space-y-1">
                                  {item.shops.slice(0, 2).map((sh, sIdx) => (
                                    <div
                                      key={sIdx}
                                      className="flex items-center justify-between gap-1.5 text-[11px] px-2 py-1 rounded-lg"
                                      style={{ background: 'var(--nen)' }}
                                    >
                                      <div className="min-w-0 flex-1 truncate">
                                        <span className="font-semibold" style={{ color: 'var(--chu)' }}>
                                          {sh.shop_name}
                                        </span>
                                        {sh.selling_price && (
                                          <span className="ml-1.5 font-bold" style={{ color: 'var(--la)' }}>
                                            {sh.selling_price}
                                          </span>
                                        )}
                                      </div>
                                      <div className="flex items-center gap-1 shrink-0">
                                        {sh.ads_count > 0 && (
                                          <a
                                            href={sh.ad_library_url}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="px-1.5 py-0.5 rounded text-[10px] font-bold hover:underline"
                                            style={{ background: 'var(--xanh-bg)', color: 'var(--link)' }}
                                            title="Xem toàn bộ quảng cáo của shop này trên Meta Ad Library"
                                          >
                                            {sh.ads_count} QC
                                          </a>
                                        )}
                                        {sh.product_url && (
                                          <a
                                            href={sh.product_url}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="px-1.5 py-0.5 rounded text-[10px] font-bold flex items-center gap-0.5 hover:underline"
                                            style={{ background: 'var(--xanh-bg)', color: 'var(--link)' }}
                                            title={`Link sản phẩm: ${sh.product_url}`}
                                          >
                                            SP
                                            <ExternalLink className="w-2.5 h-2.5" />
                                          </a>
                                        )}
                                        {sh.shop_url ? (
                                          <a
                                            href={sh.shop_url}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="px-1.5 py-0.5 rounded text-[10px] font-semibold flex items-center gap-0.5 hover:underline"
                                            style={{ background: 'var(--la-bg)', color: 'var(--la)' }}
                                            title={`Link shop: ${sh.shop_url}`}
                                          >
                                            Shop
                                            <ExternalLink className="w-2.5 h-2.5" />
                                          </a>
                                        ) : sh.page_url ? (
                                          <a
                                            href={sh.page_url}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="px-1.5 py-0.5 rounded text-[10px] font-medium flex items-center gap-0.5 hover:underline"
                                            style={{ background: 'var(--o)', color: 'var(--mo)' }}
                                          >
                                            Page
                                            <ExternalLink className="w-2.5 h-2.5" />
                                          </a>
                                        ) : null}
                                      </div>
                                    </div>
                                  ))}
                                  {item.shops.length > 2 && (
                                    <button
                                      type="button"
                                      onClick={() => setDrawerVideoId(v.id)}
                                      className="text-[10px] font-semibold hover:underline pl-1"
                                      style={{ color: 'var(--link)' }}
                                    >
                                      + Xem thêm {item.shops.length - 2} shop khác trong khung Phân tích →
                                    </button>
                                  )}
                                </div>
                              ) : (
                                <div className="text-[10px]" style={{ color: 'var(--mo2)' }}>
                                  Bấm &ldquo;Dò Meta Ads&rdquo; để tìm Shop đang chạy trên Meta Ad Library, lấy Link SP, Link Shop và Giá bán.
                                </div>
                              )}
                            </div>

                            {/* 5. 4 METRIC BOXES + SPARKLINE */}
                            <div className="grid grid-cols-4 gap-1.5">
                              <div className="p-2 rounded-xl text-center" style={{ background: 'var(--xam)' }}>
                                <div className="text-[10px]" style={{ color: 'var(--mo)' }}>
                                  Điểm TN
                                </div>
                                <div className="text-sm font-bold" style={{ color: 'var(--la)' }}>
                                  {item.potentialScore}
                                </div>
                              </div>
                              <div className="p-2 rounded-xl text-center" style={{ background: 'var(--xam)' }}>
                                <div className="text-[10px]" style={{ color: 'var(--mo)' }}>
                                  Số Ads
                                </div>
                                <div className="text-sm font-bold" style={{ color: 'var(--xanh)' }}>
                                  {item.totalAdsSameVideo}
                                </div>
                              </div>
                              <div className="p-2 rounded-xl text-center" style={{ background: 'var(--xam)' }}>
                                <div className="text-[10px]" style={{ color: 'var(--mo)' }}>
                                  Shop chạy
                                </div>
                                <div className="text-xs font-bold mt-0.5" style={{ color: 'var(--chu)' }}>
                                  {item.shopActive}
                                </div>
                              </div>
                              <div className="p-2 rounded-xl text-center" style={{ background: 'var(--xam)' }}>
                                <div className="text-[10px]" style={{ color: 'var(--mo)' }}>
                                  View/ngày
                                </div>
                                <div className="text-xs font-bold mt-0.5" style={{ color: 'var(--chu)' }}>
                                  {formatCompact(item.velocityViewsPerDay)}
                                </div>
                              </div>
                            </div>

                            {/* Mini 14-day Sparkline Bar Row */}
                            <div
                              className="px-2.5 py-2 rounded-xl flex items-center justify-between gap-3"
                              style={{ background: 'var(--xam)' }}
                            >
                              <span className="text-[10px] font-medium shrink-0" style={{ color: 'var(--mo2)' }}>
                                Đà 14d
                              </span>
                              <div className="flex-1">
                                <Sparkline
                                  bars={item.sparkline14d}
                                  highlightColor={
                                    item.potentialTier === 'S' ? 'var(--la)' : 'var(--xanh)'
                                  }
                                />
                              </div>
                              <span className="text-[10px] font-bold shrink-0" style={{ color: 'var(--chu)' }}>
                                Viral {v.viral_score}
                              </span>
                            </div>
                          </div>

                          {/* 6. BOTTOM ACTION BUTTONS FOOTER: Phân tích | Tải video | Clone */}
                          <div className="flex items-center gap-2 pt-2 border-t" style={{ borderColor: 'var(--vien-nhe)' }}>
                            <button
                              onClick={() => setDrawerVideoId(v.id)}
                              className="sw-pill-btn flex-1 py-2 px-3 text-xs font-semibold border"
                              style={{
                                background: 'var(--xam)',
                                borderColor: 'var(--vien-nhe)',
                                color: 'var(--chu)',
                              }}
                            >
                              Phân tích &amp; Shop
                            </button>
                            <button
                              onClick={() => handleDownloadVideoSource(v)}
                              className="sw-pill-btn py-2 px-3 text-xs font-medium border flex items-center gap-1"
                              style={{
                                background: 'var(--nen)',
                                borderColor: 'var(--vien-nhe)',
                                color: 'var(--mo)',
                              }}
                              title="Tải MP4 bằng yt-dlp"
                            >
                              <Download className="w-3.5 h-3.5" />
                              <span className="hidden sm:inline">Tải</span>
                            </button>
                            <button
                              onClick={() => handleSelectForFlowClone(v)}
                              className="sw-pill-btn py-2 px-2.5 text-xs font-semibold border flex items-center justify-center gap-1"
                              style={{
                                background: 'var(--la-bg)',
                                borderColor: 'transparent',
                                color: 'var(--la)',
                              }}
                              title="Clone video này bằng tài khoản Google Flow (flow.google.com)"
                            >
                              <Film className="w-3.5 h-3.5" />
                              Flow
                            </button>
                            <button
                              onClick={() => handleSelectForClone(v)}
                              className="sw-pill-btn-primary flex-1 py-2 px-3 text-xs flex items-center justify-center gap-1"
                            >
                              <Sparkles className="w-3.5 h-3.5" />
                              Clone
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  /* TABLE VIEW (Bảng) — Full Competitor Shops, Links, Ads Count & Live Price */
                  <div className="sw-card p-4 overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="border-b" style={{ borderColor: 'var(--vien-nhe)', color: 'var(--mo)' }}>
                          <th className="py-2.5 pr-3 font-semibold">Sản phẩm &amp; Nguồn Viral</th>
                          <th className="py-2.5 px-2 font-semibold">Tiềm Năng</th>
                          <th className="py-2.5 px-2 font-semibold">Các Shop Đang Chạy &amp; Link Bán</th>
                          <th className="py-2.5 px-2 font-semibold">Số Lượng Ads</th>
                          <th className="py-2.5 px-2 font-semibold">Giá Đang Bán</th>
                          <th className="py-2.5 pl-2 font-semibold text-right">Thao tác</th>
                        </tr>
                      </thead>
                      <tbody>
                        {displayedVideos.map((item) => {
                          const v = item.raw;
                          const pf = PLATFORM_META[v.platform] || PLATFORM_META.facebook;
                          return (
                            <tr
                              key={v.id}
                              className="border-b last:border-b-0"
                              style={{ borderColor: 'var(--vien-nhe)' }}
                            >
                              <td className="py-3 pr-3 max-w-[260px]">
                                <div className="flex items-center gap-2.5">
                                  <img
                                    src={
                                      v.thumbnail_url ||
                                      'https://images.unsplash.com/photo-1611162617474-5b21e879e113?auto=format&fit=crop&w=120&q=80'
                                    }
                                    alt={v.title}
                                    className="w-9 h-12 rounded-lg object-cover shrink-0 bg-black"
                                  />
                                  <div className="min-w-0">
                                    <div
                                      onClick={() => setDrawerVideoId(v.id)}
                                      className="font-semibold truncate cursor-pointer hover:underline"
                                      style={{ color: 'var(--chu)' }}
                                    >
                                      {v.title}
                                    </div>
                                    <div className="text-[11px] flex items-center gap-1.5 mt-0.5" style={{ color: 'var(--mo2)' }}>
                                      <span
                                        className="px-1.5 py-0.5 rounded text-[10px] font-bold"
                                        style={{ background: pf.pillBg, color: pf.pillColor }}
                                      >
                                        {pf.short}
                                      </span>
                                      <span className="truncate">{v.author}</span>
                                      <span>· {item.videoAgeDays}d</span>
                                    </div>
                                  </div>
                                </div>
                              </td>
                              <td className="py-3 px-2 whitespace-nowrap">
                                <span
                                  className="px-2 py-0.5 rounded-full text-[11px] font-bold"
                                  style={{
                                    background: item.potentialTier === 'S' ? 'var(--la-bg)' : 'var(--xanh-bg)',
                                    color: item.potentialTier === 'S' ? 'var(--la)' : 'var(--link)',
                                  }}
                                >
                                  Hạng {item.potentialTier} · {item.potentialScore}đ
                                </span>
                                <div className="text-[10px] mt-0.5" style={{ color: 'var(--mo2)' }}>
                                  {formatCompact(item.velocityViewsPerDay)} view/ngày
                                </div>
                              </td>
                              <td className="py-3 px-2 max-w-[290px]">
                                {item.shops.length > 0 ? (
                                  <div className="space-y-1">
                                    {item.shops.slice(0, 2).map((sh, idxS) => (
                                      <div key={idxS} className="flex flex-wrap items-center gap-1 text-[11px]">
                                        <span className="font-semibold truncate max-w-[120px]" style={{ color: 'var(--chu)' }}>
                                          {sh.shop_name}
                                        </span>
                                        {sh.product_url && (
                                          <a
                                            href={sh.product_url}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="px-1.5 py-0.5 rounded text-[10px] font-bold flex items-center gap-0.5 shrink-0 hover:underline"
                                            style={{ background: 'var(--xanh-bg)', color: 'var(--link)' }}
                                            title={sh.product_url}
                                          >
                                            Link SP
                                            <ExternalLink className="w-2.5 h-2.5" />
                                          </a>
                                        )}
                                        {sh.shop_url && (
                                          <a
                                            href={sh.shop_url}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="px-1.5 py-0.5 rounded text-[10px] font-semibold flex items-center gap-0.5 shrink-0 hover:underline"
                                            style={{ background: 'var(--la-bg)', color: 'var(--la)' }}
                                            title={sh.shop_url}
                                          >
                                            Link Shop
                                            <ExternalLink className="w-2.5 h-2.5" />
                                          </a>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                ) : (
                                  <span className="text-[11px]" style={{ color: 'var(--mo2)' }}>
                                    Chưa dò shop
                                  </span>
                                )}
                              </td>
                              <td className="py-3 px-2 font-bold whitespace-nowrap" style={{ color: 'var(--xanh)' }}>
                                {item.totalAdsSameVideo > 0 ? `${item.totalAdsSameVideo} QC active` : '0 QC'}
                              </td>
                              <td
                                className="py-3 px-2 font-bold whitespace-nowrap"
                                style={{ color: item.priceLabel !== 'Chưa niêm yết giá' ? 'var(--la)' : 'var(--mo2)' }}
                              >
                                {item.priceLabel}
                              </td>
                              <td className="py-3 pl-2 text-right space-x-1.5 whitespace-nowrap">
                                <button
                                  type="button"
                                  disabled={spyingVideoId === v.id}
                                  onClick={() => handleEvaluateSingleVideo(v.id)}
                                  className="sw-pill-btn px-2.5 py-1 text-[11px] border"
                                  style={{ background: 'var(--xanh-bg)', borderColor: 'transparent', color: 'var(--link)' }}
                                >
                                  {spyingVideoId === v.id ? 'Đang dò...' : 'Dò Shop'}
                                </button>
                                <button
                                  onClick={() => setDrawerVideoId(v.id)}
                                  className="sw-pill-btn px-2.5 py-1 text-[11px] border"
                                  style={{ background: 'var(--xam)', borderColor: 'var(--vien)', color: 'var(--chu)' }}
                                >
                                  Chi tiết
                                </button>
                                <button
                                  onClick={() => handleSelectForClone(v)}
                                  className="sw-pill-btn-primary px-3 py-1 text-[11px]"
                                >
                                  Clone
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* ==============================================================
                VIEW 4: CLONE VIDEO (MUSE AI) + KHO TOKEN 1 TỶ + FFMPEG 9:16
               ============================================================== */}
            {activeTab === 'clone-muse' && (
              <div className="space-y-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--chu)' }}>
                      Clone Video (Muse AI) & Kho Token 1 Tỷ
                    </h1>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--mo)' }}>
                      Xoay vòng tự động cụm tài khoản Muse 1 Billion Tokens kết hợp FFmpeg 9:16 Anti-Duplicate & gắn Banner
                      Affiliate.
                    </p>
                  </div>
                  <button
                    onClick={() => setShowBulkModal(true)}
                    className="sw-pill-btn px-4 py-2 text-xs font-semibold flex items-center gap-1.5 border"
                    style={{ background: 'var(--nen)', borderColor: 'var(--vien)', color: 'var(--chu)' }}
                  >
                    <KeyRound className="w-3.5 h-3.5" style={{ color: 'var(--cam)' }} />
                    + Nhập hàng loạt Token ({tokens.length} Acc)
                  </button>
                </div>

                {/* Muse Pool Telemetry Strip */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="sw-card p-4">
                    <div className="text-[11px]" style={{ color: 'var(--mo)' }}>
                      Tổng Token còn lại
                    </div>
                    <div className="text-xl font-bold mt-1" style={{ color: 'var(--cam)' }}>
                      {status ? formatCompact(status.muse_pool.total_tokens_remaining) : '1.00B'}
                    </div>
                  </div>
                  <div className="sw-card p-4">
                    <div className="text-[11px]" style={{ color: 'var(--mo)' }}>
                      Tài khoản Active
                    </div>
                    <div className="text-xl font-bold mt-1" style={{ color: 'var(--la)' }}>
                      {status?.muse_pool.active_accounts ?? 0} / {status?.muse_pool.total_accounts ?? 0}
                    </div>
                  </div>
                  <div className="sw-card p-4">
                    <div className="text-[11px]" style={{ color: 'var(--mo)' }}>
                      Lượt render tuần này
                    </div>
                    <div className="text-xl font-bold mt-1" style={{ color: 'var(--xanh)' }}>
                      {status?.muse_pool.weekly_used ?? 0} / {status?.muse_pool.weekly_capacity ?? 0}
                    </div>
                  </div>
                  <div className="sw-card p-4">
                    <div className="text-[11px]" style={{ color: 'var(--mo)' }}>
                      Video 9:16 đã render
                    </div>
                    <div className="text-xl font-bold mt-1" style={{ color: 'var(--chu)' }}>
                      {completedJobs.length} / {jobs.length} jobs
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                  {/* Left: Configuration Form */}
                  <div className="lg:col-span-5 sw-card p-5 space-y-4">
                    <h2 className="text-sm font-bold flex items-center gap-2" style={{ color: 'var(--chu)' }}>
                      <Video className="w-4 h-4" style={{ color: 'var(--xanh)' }} />
                      Cấu hình Remake Video Viral (Organic 9:16)
                    </h2>

                    <div
                      className="p-3 rounded-2xl border text-[11px] leading-relaxed"
                      style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)', color: 'var(--mo)' }}
                    >
                      Xuất video <strong style={{ color: 'var(--la)' }}>100% sạch kiểu creator organic</strong> (đã gỡ bỏ hoàn toàn khung banner CTA sản phẩm &amp; watermark khỏi video) để tối ưu thuật toán đề xuất tự nhiên.
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                        1. Video viral gốc (Từ kho quét Agent-Reach)
                      </label>
                      <select
                        value={selectedVideoId}
                        onChange={(e) => {
                          const id = Number(e.target.value);
                          setSelectedVideoId(id);
                          const found = videos.find((x) => x.id === id);
                          if (found) setPromptScript(found.hook_text || found.title);
                        }}
                        className="sw-input w-full px-3 py-2 text-xs"
                      >
                        {videos.map((v) => (
                          <option key={v.id} value={v.id}>
                            [{v.platform.toUpperCase()}] {v.title} (Score {v.viral_score})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                        2. Điều hướng Comment / Bio sau khi Viral (Tuỳ chọn — KHÔNG chèn lên video)
                      </label>
                      <select
                        value={selectedProductId}
                        onChange={(e) => setSelectedProductId(Number(e.target.value))}
                        className="sw-input w-full px-3 py-2 text-xs"
                      >
                        <option value={0}>-- Không gắn sản phẩm (100% Remake Viral Organic thuần) --</option>
                        {products.map((p) => (
                          <option key={p.id} value={p.id}>
                            #{p.code} — {p.name} ({p.price} · {p.platform_name})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                          Chế độ Remake Video
                        </label>
                        <select
                          value={cloneMode}
                          onChange={(e) => setCloneMode(e.target.value)}
                          className="sw-input w-full px-3 py-2 text-xs"
                        >
                          <option value="rea_video_remake">rea-video Shot-by-Shot Decompose &amp; Remake + FFmpeg 9:16</option>
                          <option value="muse_prompt_remap">Muse Scene &amp; Script Remap</option>
                          <option value="muse_avatar_motion">Muse Avatar &amp; LipSync</option>
                          <option value="smart_reedit">Smart FFmpeg Re-edit</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                          Hiển thị trên Video (Không khung CTA)
                        </label>
                        <select
                          value={ctaPosition}
                          onChange={(e) => setCtaPosition(e.target.value)}
                          className="sw-input w-full px-3 py-2 text-xs"
                        >
                          <option value="clean_organic">Video sạch 100% (Không khung / Không chữ)</option>
                          <option value="hook_3s_only">Chỉ hiện chữ Hook 3s đầu (Kiểu Creator)</option>
                        </select>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                          Chiến lược Gắn Link
                        </label>
                        <select
                          value={linkPlacementMode}
                          onChange={(e) => setLinkPlacementMode(e.target.value)}
                          className="sw-input w-full px-3 py-2 text-xs"
                        >
                          <option value="both">Auto Smart (Comment + Bio)</option>
                          <option value="comment_first">Comment đầu (Facebook)</option>
                          <option value="bio_link">Link Bio #MãSP (Instagram)</option>
                          <option value="threads_reply">Chuỗi Reply (Threads)</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                          Số biến thể (Batch)
                        </label>
                        <input
                          type="number"
                          min={1}
                          max={10}
                          value={batchCount}
                          onChange={(e) => setBatchCount(Math.max(1, Math.min(10, Number(e.target.value) || 1)))}
                          className="sw-input w-full px-3 py-2 text-xs"
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
                        <label className="block text-[11px] font-semibold" style={{ color: 'var(--mo)' }}>
                          Kịch bản 3 phần (0-3s Hook · Nội dung giữ nhịp · Chốt organic)
                        </label>
                        {selectedVideo && (
                          <div className="flex items-center gap-1.5">
                            {selectedVideo.rea_breakdown ? (
                              <button
                                type="button"
                                onClick={() => {
                                  const bd = selectedVideo.rea_breakdown;
                                  if (!bd) return;
                                  const shotLines = (bd.shots || [])
                                    .slice(0, 5)
                                    .map(
                                      (s) =>
                                        `[${s.start.toFixed(1)}s-${s.end.toFixed(1)}s ${s.label} · ${s.remake_route}] ${
                                          s.prompt || bd.verdict
                                        }`
                                    )
                                    .join('\n');
                                  setPromptScript(shotLines || bd.remake_md_excerpt || bd.video_md_excerpt || bd.verdict);
                                  setCloneMode('rea_video_remake');
                                  notify(`Đã nạp kịch bản ${bd.shots_count} shots từ rea-video!`);
                                }}
                                className="sw-pill-btn px-2.5 py-1 text-[10px] font-bold flex items-center gap-1"
                                style={{ background: 'var(--xanh-bg)', color: 'var(--link)' }}
                              >
                                <Scissors className="w-3 h-3" />
                                Nạp {selectedVideo.rea_breakdown.shots_count} shots rea-video
                              </button>
                            ) : (
                              <button
                                type="button"
                                disabled={reaBusyVideoId === selectedVideo.id}
                                onClick={() => handleReaDecompose(selectedVideo.id, undefined, true)}
                                className="sw-pill-btn px-2.5 py-1 text-[10px] font-bold border flex items-center gap-1"
                                style={{
                                  background: 'var(--xanh-bg)',
                                  borderColor: 'transparent',
                                  color: 'var(--link)',
                                }}
                              >
                                <Scissors className="w-3 h-3" />
                                {reaBusyVideoId === selectedVideo.id ? 'Đang mổ xẻ & nạp Shot...' : '🎬 Mổ xẻ & Nạp Shot (rea-video)'}
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                      <textarea
                        rows={3}
                        value={promptScript}
                        onChange={(e) => setPromptScript(e.target.value)}
                        placeholder="Nhập câu Hook 3 giây đầu (sẽ dùng cho caption hoặc hiện tối giản 3s đầu nếu bật)..."
                        className="sw-input w-full p-3 text-xs"
                      />
                    </div>

                    <label className="flex items-center gap-2 text-xs cursor-pointer" style={{ color: 'var(--chu)' }}>
                      <input
                        type="checkbox"
                        checked={antiDuplicate}
                        onChange={(e) => setAntiDuplicate(e.target.checked)}
                        className="rounded"
                      />
                      Bật Anti-Duplicate (FFmpeg Micro-Crop + Chỉnh màu + Xoá Metadata)
                    </label>

                    <button
                      onClick={handleLaunchClone}
                      disabled={isLaunchingClone}
                      className="sw-pill-btn-primary w-full py-3 text-sm flex items-center justify-center gap-2"
                    >
                      <Sparkles className="w-4 h-4" />
                      {isLaunchingClone
                        ? 'Đang khởi tạo...'
                        : `Remake Video Viral 9:16 Sạch (Organic) ${batchCount > 1 ? `(${batchCount}x)` : ''}`}
                    </button>
                  </div>

                  {/* Right: Active 9:16 Player + Render Queue */}
                  <div className="lg:col-span-7 sw-card p-5 space-y-4">
                    <div className="flex items-center justify-between">
                      <h2 className="text-sm font-bold" style={{ color: 'var(--chu)' }}>
                        Danh sách Video đã Clone & Trình phát 9:16 ({jobs.length})
                      </h2>
                      <button
                        onClick={refreshAll}
                        className="text-xs flex items-center gap-1 font-medium"
                        style={{ color: 'var(--link)' }}
                      >
                        <RefreshCw className="w-3.5 h-3.5" /> Làm mới
                      </button>
                    </div>

                    {/* Active Video Spotlight */}
                    {activeCloneJob && activeCloneJob.output_video_url && (
                      <div
                        className="p-4 rounded-2xl border grid grid-cols-1 sm:grid-cols-12 gap-4"
                        style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}
                      >
                        <div className="sm:col-span-5 bg-black rounded-2xl overflow-hidden aspect-[9/16] max-h-72 mx-auto w-full">
                          <video
                            key={activeCloneJob.output_video_url}
                            src={activeCloneJob.output_video_url}
                            controls
                            playsInline
                            className="w-full h-full object-contain"
                          />
                        </div>
                        <div className="sm:col-span-7 flex flex-col justify-between gap-3 text-xs">
                          <div className="space-y-2">
                            <div className="flex items-center gap-2">
                              <span className="font-bold">Job #{activeCloneJob.id}</span>
                              <span
                                className="px-2 py-0.5 rounded-full text-[10px] font-bold"
                                style={{ background: 'var(--la-bg)', color: 'var(--la)' }}
                              >
                                {activeCloneJob.product_code ? `Hoàn tất · #${activeCloneJob.product_code}` : 'Hoàn tất · Organic Viral'}
                              </span>
                              {activeCloneJob.muse_token_label && (
                                <span
                                  className="px-2 py-0.5 rounded-full text-[10px] font-semibold"
                                  style={{ background: 'var(--xanh-bg)', color: 'var(--link)' }}
                                >
                                  {activeCloneJob.muse_token_label}
                                </span>
                              )}
                            </div>
                            <div className="p-2.5 rounded-xl border" style={{ background: 'var(--nen)', borderColor: 'var(--vien-nhe)' }}>
                              <div className="text-[10px] font-semibold mb-0.5" style={{ color: 'var(--mo)' }}>
                                Caption đề xuất
                              </div>
                              <p className="line-clamp-3 whitespace-pre-line">{activeCloneJob.generated_caption}</p>
                            </div>
                            <div className="p-2.5 rounded-xl" style={{ background: 'var(--la-bg)', color: 'var(--la)' }}>
                              <div className="text-[10px] font-bold mb-0.5">Auto First-Comment Link</div>
                              <p className="line-clamp-2">{activeCloneJob.generated_first_comment}</p>
                            </div>
                          </div>

                          <div className="flex flex-wrap gap-2">
                            <a
                              href={activeCloneJob.output_video_url}
                              download={`clone_${activeCloneJob.id}.mp4`}
                              className="sw-pill-btn px-3.5 py-2 text-xs font-semibold border flex items-center gap-1.5"
                              style={{ background: 'var(--nen)', borderColor: 'var(--vien)', color: 'var(--chu)' }}
                            >
                              <Download className="w-3.5 h-3.5" /> Tải MP4
                            </a>
                            <button
                              onClick={() => {
                                setPubJobId(activeCloneJob.id);
                                setActiveTab('dang-bai');
                              }}
                              className="sw-pill-btn-primary flex-1 px-3.5 py-2 text-xs flex items-center justify-center gap-1.5"
                            >
                              <Send className="w-3.5 h-3.5" /> Đưa sang Đăng Bài & Auto-Comment
                            </button>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Muse Jobs List */}
                    <div className="space-y-2.5 max-h-[340px] overflow-y-auto pr-1">
                      {museJobs.length === 0 ? (
                        <div className="py-10 text-center text-xs" style={{ color: 'var(--mo)' }}>
                          Chưa có job clone nào. Chọn video & bấm "Remake Video Viral 9:16" bên trái!
                        </div>
                      ) : (
                        museJobs.map((job) => (
                          <div
                            key={job.id}
                            onClick={() => job.status === 'completed' && setActiveCloneJobId(job.id)}
                            className="p-3 rounded-2xl border cursor-pointer transition space-y-2"
                            style={{
                              background: activeCloneJob?.id === job.id ? 'var(--xanh-bg)' : 'var(--xam)',
                              borderColor: activeCloneJob?.id === job.id ? 'var(--xanh)' : 'var(--vien-nhe)',
                            }}
                          >
                            <div className="flex items-center justify-between gap-2 text-xs">
                              <div className="flex items-center gap-2 min-w-0">
                                <span className="font-bold">Job #{job.id}</span>
                                <span
                                  className="px-2 py-0.5 rounded-full text-[10px] font-semibold"
                                  style={{ background: 'var(--nen)', color: job.product_code ? 'var(--cam)' : 'var(--la)' }}
                                >
                                  {job.product_code ? `#${job.product_code}` : 'Organic Viral'}
                                </span>
                                <span className="truncate" style={{ color: 'var(--mo)' }}>
                                  {job.source_title || job.prompt_script}
                                </span>
                              </div>
                              <div className="flex items-center gap-1.5 shrink-0" onClick={(e) => e.stopPropagation()}>
                                <span
                                  className="px-2.5 py-0.5 rounded-full text-[10px] font-bold"
                                  style={{
                                    background:
                                      job.status === 'completed'
                                        ? 'var(--la-bg)'
                                        : job.status === 'failed'
                                        ? 'var(--do-bg)'
                                        : 'var(--cam-bg)',
                                    color:
                                      job.status === 'completed'
                                        ? 'var(--la)'
                                        : job.status === 'failed'
                                        ? 'var(--do)'
                                        : 'var(--cam)',
                                  }}
                                >
                                  {job.status === 'completed'
                                    ? 'Hoàn tất (100%)'
                                    : job.status === 'failed'
                                    ? `Thất bại (${job.progress}%)`
                                    : job.status === 'analyzing'
                                    ? `Đang chuẩn bị Frame & Prompt (${job.progress}%)`
                                    : job.status === 'generating_muse'
                                    ? `Đang tạo Video trên Google Flow (${job.progress}%)`
                                    : job.status === 'compositing_ffmpeg'
                                    ? `Hậu kỳ FFmpeg 9:16 (${job.progress}%)`
                                    : `Đang xếp hàng (${job.progress}%)`}
                                </span>
                                {job.status === 'failed' && (
                                  <button
                                    type="button"
                                    onClick={async () => {
                                      try {
                                        await api.retryCloneJob(job.id);
                                        notify(`Đã chạy lại Job #${job.id}!`);
                                        await refreshAll();
                                      } catch (err: unknown) {
                                        notify(err instanceof Error ? err.message : 'Lỗi chạy lại Job', 'err');
                                      }
                                    }}
                                    className="sw-pill-btn px-2 py-0.5 text-[10px] font-bold border"
                                    style={{ background: 'var(--xanh-bg)', borderColor: 'transparent', color: 'var(--link)' }}
                                    title="Chạy lại Job này"
                                  >
                                    Chạy lại
                                  </button>
                                )}
                                <button
                                  type="button"
                                  onClick={async () => {
                                    try {
                                      await api.deleteCloneJob(job.id);
                                      if (activeCloneJobId === job.id) setActiveCloneJobId(null);
                                      if (activeFlowJobId === job.id) setActiveFlowJobId(null);
                                      notify(job.status === 'completed' || job.status === 'failed' ? `Đã xoá Job #${job.id}` : `Đã huỷ Job #${job.id}`);
                                      await refreshAll();
                                    } catch (err: unknown) {
                                      notify(err instanceof Error ? err.message : 'Lỗi xoá Job', 'err');
                                    }
                                  }}
                                  className="p-1 rounded-lg"
                                  style={{ background: 'var(--do-bg)', color: 'var(--do)' }}
                                  title={job.status === 'completed' || job.status === 'failed' ? 'Xoá Job' : 'Huỷ tiến trình'}
                                >
                                  <Trash2 className="w-3 h-3" />
                                </button>
                              </div>
                            </div>

                            {job.status !== 'completed' && (
                              <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--o)' }}>
                                <div
                                  className="h-full transition-all duration-300"
                                  style={{
                                    width: `${job.progress}%`,
                                    background: job.status === 'failed' ? 'var(--do)' : 'var(--xanh)',
                                  }}
                                />
                              </div>
                            )}

                            {job.error_message && (
                              <div className="text-[11px]" style={{ color: 'var(--do)' }}>
                                {job.error_message}
                              </div>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ==============================================================
                VIEW 4B: CLONE VIDEO BẰNG GOOGLE FLOW (flow.google.com · VEO 3.1)
               ============================================================== */}
            {activeTab === 'clone-flow' && (
              <div className="space-y-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--chu)' }}>
                        Clone Video bằng Google Flow (flow.google.com)
                      </h1>
                      <a
                        href="https://flow.google.com/"
                        target="_blank"
                        rel="noreferrer"
                        className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold flex items-center gap-1 hover:underline"
                        style={{ background: 'var(--xanh-bg)', color: 'var(--link)' }}
                      >
                        flow.google.com
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--mo)' }}>
                      Quản lý kho tài khoản Google Flow (Chrome Cookie / Session / Gemini API) &amp; xoay vòng tự động để Remake Video Viral dọc 9:16 sạch bằng OmniFlash (Omni 1.2 Flash), Veo 3.1 &amp; Nano Banana.
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleFlowBrowserLogin()}
                      className="sw-pill-btn-primary px-4 py-2 text-xs font-semibold flex items-center gap-1.5"
                    >
                      <LogIn className="w-3.5 h-3.5" />
                      Đăng nhập Acc Flow trên Chrome (Tự lấy Cookie)
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowFlowImportModal(true)}
                      className="sw-pill-btn px-4 py-2 text-xs font-semibold flex items-center gap-1.5 border"
                      style={{ background: 'var(--nen)', borderColor: 'var(--vien)', color: 'var(--chu)' }}
                    >
                      <KeyRound className="w-3.5 h-3.5" style={{ color: 'var(--la)' }} />
                      + Nhập Cookie / Bearer / Key ({flowAccounts.length} Acc)
                    </button>
                  </div>
                </div>

                {/* Google Flow Pool Telemetry Strip */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="sw-card p-4">
                    <div className="text-[11px]" style={{ color: 'var(--mo)' }}>
                      Tài khoản Flow Active
                    </div>
                    <div className="text-xl font-bold mt-1" style={{ color: 'var(--la)' }}>
                      {flowAccounts.filter((a) => a.status === 'active').length} / {flowAccounts.length} acc
                    </div>
                  </div>
                  <div className="sw-card p-4">
                    <div className="text-[11px]" style={{ color: 'var(--mo)' }}>
                      Tổng AI Credits ước tính
                    </div>
                    <div className="text-xl font-bold mt-1" style={{ color: 'var(--xanh)' }}>
                      {formatCompact(
                        flowAccounts.reduce((acc, item) => acc + (item.credits_remaining || 0), 0)
                      )}{' '}
                      credits
                    </div>
                  </div>
                  <div className="sw-card p-4">
                    <div className="text-[11px]" style={{ color: 'var(--mo)' }}>
                      Lượt Render Flow đã chạy
                    </div>
                    <div className="text-xl font-bold mt-1" style={{ color: 'var(--cam)' }}>
                      {flowAccounts.reduce((s, a) => s + (a.renders_used || 0), 0)} /{' '}
                      {flowAccounts.reduce((s, a) => s + (a.weekly_limit || 0), 0)}
                    </div>
                  </div>
                  <div className="sw-card p-4">
                    <div className="text-[11px]" style={{ color: 'var(--mo)' }}>
                      Jobs Google Flow hoàn tất
                    </div>
                    <div className="text-xl font-bold mt-1" style={{ color: 'var(--chu)' }}>
                      {jobs.filter((j) => j.clone_mode.startsWith('flow_') && j.status === 'completed').length} /{' '}
                      {jobs.filter((j) => j.clone_mode.startsWith('flow_')).length} jobs
                    </div>
                  </div>
                </div>

                {/* Flow Account Pool Manager Card */}
                <div className="sw-card p-5 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h2 className="text-sm font-bold flex items-center gap-2" style={{ color: 'var(--chu)' }}>
                        <ShieldCheck className="w-4 h-4" style={{ color: 'var(--la)' }} />
                        Kho Tài Khoản Google Flow (http://flow.google.com/)
                      </h2>
                      <p className="text-[11px] mt-0.5" style={{ color: 'var(--mo)' }}>
                        Mỗi tài khoản lưu một Chrome Profile &amp; bộ Cookie riêng biệt. Khi đăng nhập xong trên Chrome, hệ thống tự động thu Cookie và đóng trình duyệt.
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <input
                        value={flowLoginLabel}
                        onChange={(e) => setFlowLoginLabel(e.target.value)}
                        placeholder="Ghi chú tên Acc (tuỳ chọn)..."
                        className="sw-input px-3 py-1.5 text-xs w-44"
                      />
                      <input
                        value={flowLoginProxy}
                        onChange={(e) => setFlowLoginProxy(e.target.value)}
                        placeholder="Proxy http://ip:port (tuỳ chọn)"
                        className="sw-input px-3 py-1.5 text-xs w-48"
                      />
                      <button
                        type="button"
                        onClick={() => handleFlowBrowserLogin()}
                        className="sw-pill-btn px-3 py-1.5 text-xs font-semibold border flex items-center gap-1"
                        style={{ background: 'var(--la-bg)', borderColor: 'transparent', color: 'var(--la)' }}
                      >
                        <Plus className="w-3.5 h-3.5" />
                        Thêm &amp; Mở Chrome Login
                      </button>
                    </div>
                  </div>

                  {flowAccounts.length === 0 ? (
                    <div
                      className="p-6 rounded-2xl border text-center space-y-2 text-xs"
                      style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)', color: 'var(--mo)' }}
                    >
                      <div className="font-bold" style={{ color: 'var(--chu)' }}>
                        Chưa có tài khoản flow.google.com nào trong kho.
                      </div>
                      <p>
                        Bấm <strong>&ldquo;Đăng nhập Acc Flow trên Chrome&rdquo;</strong> để mở trình duyệt đăng nhập trực tiếp, hoặc bấm <strong>&ldquo;+ Nhập Cookie / Bearer / Key&rdquo;</strong> để nạp nhanh hàng loạt tài khoản.
                      </p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                      {flowAccounts.map((acc) => (
                        <div
                          key={acc.id}
                          className="p-3.5 rounded-2xl border flex flex-col justify-between gap-2.5 text-xs"
                          style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}
                        >
                          <div className="space-y-1">
                            <div className="flex items-center justify-between gap-2">
                              <div className="font-bold truncate" style={{ color: 'var(--chu)' }}>
                                {acc.email || acc.label}
                              </div>
                              <span
                                className="px-2 py-0.5 rounded-full text-[10px] font-bold shrink-0"
                                style={{
                                  background:
                                    acc.status === 'active'
                                      ? 'var(--la-bg)'
                                      : acc.status === 'login_pending'
                                      ? 'var(--xanh-bg)'
                                      : 'var(--cam-bg)',
                                  color:
                                    acc.status === 'active'
                                      ? 'var(--la)'
                                      : acc.status === 'login_pending'
                                      ? 'var(--link)'
                                      : 'var(--cam)',
                                }}
                              >
                                {acc.status === 'login_pending' ? 'Đang chờ Login...' : acc.status}
                              </span>
                            </div>

                            <div className="text-[11px] flex flex-wrap items-center gap-1.5" style={{ color: 'var(--mo)' }}>
                              <span className="px-1.5 py-0.5 rounded text-[10px]" style={{ background: 'var(--nen)' }}>
                                {acc.auth_mode}
                              </span>
                              <span>{acc.credential_masked}</span>
                              <span>
                                · {acc.renders_used}/{acc.weekly_limit} lượt
                              </span>
                            </div>

                            {acc.notes && (
                              <div className="text-[10px] line-clamp-2 pt-0.5" style={{ color: 'var(--mo2)' }}>
                                {acc.notes}
                              </div>
                            )}
                          </div>

                          <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t" style={{ borderColor: 'var(--vien-nhe)' }}>
                            <button
                              type="button"
                              disabled={flowBusyAccId === acc.id}
                              onClick={() => handleFlowVerify(acc.id)}
                              className="sw-pill-btn px-2.5 py-1 text-[10px] font-semibold border"
                              style={{ background: 'var(--nen)', borderColor: 'var(--vien-nhe)', color: 'var(--chu)' }}
                            >
                              {flowBusyAccId === acc.id ? 'Đang check...' : 'Kiểm tra'}
                            </button>
                            <button
                              type="button"
                              onClick={() => handleFlowBrowserLogin(acc.id)}
                              className="sw-pill-btn px-2.5 py-1 text-[10px] font-semibold border"
                              style={{ background: 'var(--xanh-bg)', borderColor: 'transparent', color: 'var(--link)' }}
                            >
                              Login lại
                            </button>
                            <button
                              type="button"
                              disabled={flowBusyAccId === acc.id}
                              onClick={() => handleFlowOpenBrowser(acc.id)}
                              className="sw-pill-btn px-2.5 py-1 text-[10px] font-semibold border"
                              style={{ background: 'var(--nen)', borderColor: 'var(--vien-nhe)', color: 'var(--mo)' }}
                              title="Mở cửa sổ Chrome của tài khoản này trên flow.google.com"
                            >
                              Mở Flow Web
                            </button>
                            <button
                              type="button"
                              onClick={() => api.toggleFlowAccount(acc.id).then(refreshAll)}
                              className="sw-pill-btn px-2 py-1 text-[10px] font-semibold border"
                              style={{ background: 'var(--nen)', borderColor: 'var(--vien-nhe)', color: 'var(--mo)' }}
                            >
                              {acc.status === 'active' ? 'Tạm dừng' : 'Kích hoạt'}
                            </button>
                            <button
                              type="button"
                              onClick={() => api.deleteFlowAccount(acc.id).then(refreshAll)}
                              className="p-1 rounded-lg ml-auto"
                              style={{ background: 'var(--do-bg)', color: 'var(--do)' }}
                              title="Xoá tài khoản Flow"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Main Studio Grid: Left Flow Remake Config + Right 9:16 Output & Queue */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                  <div className="lg:col-span-5 sw-card p-5 space-y-4">
                    <h2 className="text-sm font-bold flex items-center gap-2" style={{ color: 'var(--chu)' }}>
                      <Film className="w-4 h-4" style={{ color: 'var(--la)' }} />
                      Studio Clone Video bằng Google Flow (OmniFlash · Veo 3.1 · 9:16)
                    </h2>

                    <div
                      className="p-3 rounded-2xl border text-[11px] space-y-1 leading-relaxed"
                      style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)', color: 'var(--mo)' }}
                    >
                      <div className="font-bold" style={{ color: 'var(--chu)' }}>
                        📌 Cơ chế Remake Viral Sạch Chính Sách (0% chụp ảnh từ video gốc):
                      </div>
                      <div>
                        <strong>Bước 1:</strong> Chọn Video gốc + Chế độ{' '}
                        <code>🎨 AI Remake First → End Frame</code> + Mô hình Flow.
                      </div>
                      <div>
                        <strong>Bước 2:</strong> Bấm{' '}
                        <strong style={{ color: 'var(--link)' }}>🎬 Mổ xẻ rea-video &amp; Tự viết Prompt</strong> — Vision chỉ đọc góc máy &amp; hành động để tự viết <code>Prompt Ảnh Đầu (First Frame)</code> + <code>Prompt Ảnh Cuối (End Frame)</code> mới hoàn toàn.
                      </div>
                      <div>
                        <strong>Bước 3:</strong> Bấm <strong style={{ color: 'var(--la)' }}>Chạy Clone Video bằng Google Flow</strong> — Agent tự dùng <code>🍌 Nano Banana 2.1</code> vẽ bộ Ảnh Đầu → Cuối mới, gắn vào khung rồi xuất &amp; ghép MP4 9:16 chuẩn beat (không dính mặt người/bản quyền gốc).
                      </div>
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                        1. Chọn Video Viral Gốc cần Clone
                      </label>
                      <select
                        value={selectedVideoId}
                        onChange={(e) => {
                          const id = Number(e.target.value);
                          setSelectedVideoId(id);
                          const found = videos.find((x) => x.id === id);
                          if (found) {
                            setPromptScript(found.hook_text || found.title);
                            setFlowRefFrameUrl('');
                            setFlowVeoPrompt(found.rea_breakdown?.veo_prompt_en || '');
                            setFlowScenePlan(found.rea_breakdown?.scene_units || []);
                          } else {
                            setFlowVeoPrompt('');
                            setFlowScenePlan([]);
                          }
                        }}
                        className="sw-input w-full px-3 py-2 text-xs"
                      >
                        {videos.map((v) => (
                          <option key={v.id} value={v.id}>
                            [{v.platform.toUpperCase()}] #{v.id} — {v.title}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                          2. Tài khoản Google Flow sử dụng
                        </label>
                        <select
                          value={selectedFlowAccountId}
                          onChange={(e) => setSelectedFlowAccountId(Number(e.target.value))}
                          className="sw-input w-full px-3 py-2 text-xs"
                        >
                          <option value={0}>⚡ Tự động xoay vòng Acc Active ({flowAccounts.filter((a) => a.status === 'active').length} acc)</option>
                          {flowAccounts.map((acc) => (
                            <option key={acc.id} value={acc.id}>
                              #{acc.id} {acc.email || acc.label} ({acc.status})
                            </option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                          3. Chế độ Clone trên Flow
                        </label>
                        <select
                          value={flowCloneMode}
                          onChange={(e) => setFlowCloneMode(e.target.value as FlowCloneMode)}
                          className="sw-input w-full px-3 py-2 text-xs"
                        >
                          <option value="flow_frames_start_end">
                            🎨 AI Remake First → End Frame 9:16 (Agent tự tạo Ảnh Đầu – Cuối mới · Khuyên dùng)
                          </option>
                          <option value="flow_agent">
                            🤖 Tác nhân Google Flow Remake + Tự dự phòng AI First–End Frame
                          </option>
                          <option value="flow_omni_ingredients">
                            🧩 AI Ingredients Remake 9:16 (Tự tạo Ảnh SP mới làm Thành Phần)
                          </option>
                          <option value="flow_veo_t2v">
                            ✍️ Text-to-Video 9:16 (Dựng mới từ kịch bản)
                          </option>
                        </select>
                        <p className="mt-1 text-[10px] leading-snug" style={{ color: 'var(--mo)' }}>
                          {flowCloneMode === 'flow_frames_start_end' || flowCloneMode === 'flow_agent_auto' || flowCloneMode === 'flow_ai_frames_remake'
                            ? 'Agent tự dùng Nano Banana 2.1 tạo Ảnh Đầu → Ảnh Cuối mới khớp đúng góc máy gốc rồi gắn vào Khung hình (0% lấy ảnh video gốc · Không vi phạm chính sách).'
                            : flowCloneMode === 'flow_agent'
                              ? 'Giao kịch bản Remake cho Tác nhân Google Flow tự tạo ảnh & video mới; tự dự phòng AI First–End Frame nếu Agent thiếu clip.'
                              : flowCloneMode === 'flow_omni_ingredients'
                                ? 'Agent tự tạo Ảnh Sản Phẩm AI mới làm Thành Phần (Ingredients) xuyên suốt các cụm cảnh.'
                                : 'Dựng mới hoàn toàn từ kịch bản Text-to-Video 9:16 theo từng cụm cảnh.'}
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
                      <div className="sm:col-span-8 space-y-1.5">
                        <div className="flex items-center justify-between gap-2">
                          <label className="block text-[11px] font-semibold" style={{ color: 'var(--mo)' }}>
                            Mô hình Google Flow (OmniFlash / Veo 3.1 / Nano Banana — 9:16)
                          </label>
                          <button
                            type="button"
                            disabled={syncingFlowModels}
                            onClick={handleSyncFlowModels}
                            className="text-[10px] font-semibold flex items-center gap-1 hover:underline"
                            style={{ color: 'var(--link)' }}
                            title="Đồng bộ danh sách model mới nhất trực tiếp từ flow.google.com & Gemini API"
                          >
                            <RefreshCw className={`w-3 h-3 ${syncingFlowModels ? 'animate-spin' : ''}`} />
                            {syncingFlowModels ? 'Đang quét model...' : 'Cập nhật Model mới'}
                          </button>
                        </div>
                        <select
                          value={flowModelId}
                          onChange={(e) => setFlowModelId(e.target.value)}
                          className="sw-input w-full px-3 py-2 text-xs font-medium"
                        >
                          {groupedFlowModels.map(([groupName, items]) => (
                            <optgroup key={groupName} label={groupName}>
                              {items.map((m) => (
                                <option key={m.id} value={m.id}>
                                  {m.label}
                                </option>
                              ))}
                            </optgroup>
                          ))}
                          <optgroup label="Tuỳ chỉnh nâng cao">
                            <option value="__custom__">✍️ Nhập mã Model tuỳ chỉnh khác (Flow / Gemini API)...</option>
                          </optgroup>
                        </select>

                        {flowModelId === '__custom__' ? (
                          <input
                            value={customFlowModelId}
                            onChange={(e) => setCustomFlowModelId(e.target.value)}
                            placeholder="Nhập mã model (VD: omni_1_2_flash_15s_portrait hoặc veo-3.1-generate-preview)..."
                            className="sw-input w-full px-3 py-1.5 text-xs font-mono"
                          />
                        ) : (
                          selectedFlowModelMeta && (
                            <div className="flex flex-wrap items-center gap-1.5 text-[10px]" style={{ color: 'var(--mo)' }}>
                              {selectedFlowModelMeta.badge && (
                                <span
                                  className="px-1.5 py-0.5 rounded font-bold"
                                  style={{ background: 'var(--la-bg)', color: 'var(--la)' }}
                                >
                                  {selectedFlowModelMeta.badge}
                                </span>
                              )}
                              {selectedFlowModelMeta.duration_hint && (
                                <span
                                  className="px-1.5 py-0.5 rounded font-semibold"
                                  style={{ background: 'var(--xanh-bg)', color: 'var(--link)' }}
                                >
                                  Thời lượng: {selectedFlowModelMeta.duration_hint}
                                </span>
                              )}
                              <span className="truncate font-mono opacity-80">ID: {selectedFlowModelMeta.id}</span>
                            </div>
                          )
                        )}
                      </div>

                      <div className="sm:col-span-4">
                        <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                          Số biến thể (Batch)
                        </label>
                        <input
                          type="number"
                          min={1}
                          max={5}
                          value={batchCount}
                          onChange={(e) => setBatchCount(Math.max(1, Math.min(5, Number(e.target.value) || 1)))}
                          className="sw-input w-full px-3 py-2 text-xs"
                        />
                      </div>
                    </div>

                    {/* OmniFlash / Veo 3.1 Cinematic Prompt Builder + rea-video 1-Click Integration */}
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <label className="block text-[11px] font-semibold" style={{ color: 'var(--mo)' }}>
                          4. Mổ xẻ Góc Máy (rea-video) &amp; Prompt Google Flow 9:16
                        </label>
                        <div className="flex flex-wrap items-center gap-1.5">
                          <button
                            type="button"
                            disabled={Boolean(reaBusyVideoId) || flowGeneratingPrompt || !selectedVideo}
                            onClick={() => handleReaAndGenerateFlowPrompt(false)}
                            className="sw-pill-btn px-2.5 py-1 text-[10px] font-bold flex items-center gap-1 border"
                            style={{ background: 'var(--xanh-bg)', borderColor: 'transparent', color: 'var(--link)' }}
                            title="Tự động chạy rea-video mổ xẻ các shot góc máy (nếu chưa mổ xẻ) rồi viết luôn Prompt tối ưu theo Model đang chọn"
                          >
                            <Scissors className="w-3 h-3" />
                            {reaBusyVideoId === selectedVideo?.id
                              ? '1/2 Đang mổ xẻ Shot (rea-video)...'
                              : flowGeneratingPrompt
                              ? '2/2 Đang viết Prompt theo Model...'
                              : '🎬 Mổ xẻ rea-video & Tự viết Prompt'}
                          </button>

                          {selectedVideo?.rea_breakdown && (
                            <button
                              type="button"
                              disabled={Boolean(reaBusyVideoId) || flowGeneratingPrompt}
                              onClick={() => handleGenerateFlowVeoPrompt()}
                              className="sw-pill-btn px-2 py-1 text-[10px] font-bold flex items-center gap-1"
                              style={{ background: 'var(--la-bg)', color: 'var(--la)' }}
                              title="Dùng lại các shot rea-video đã mổ xẻ để đổi lại Prompt khi bạn vừa đổi sang Model khác (nhanh hơn, không cần mổ xẻ lại)"
                            >
                              <Sparkles className="w-3 h-3" />
                              Đổi theo Model mới
                            </button>
                          )}
                        </div>
                      </div>

                      {selectedVideo?.rea_breakdown && (
                        <div
                          className="px-3 py-2 rounded-xl border text-[11px] flex flex-wrap items-center justify-between gap-2"
                          style={{ background: 'var(--la-bg)', borderColor: 'var(--vien-nhe)', color: 'var(--chu)' }}
                        >
                          <div className="min-w-0 flex-1 truncate">
                            <strong style={{ color: 'var(--la)' }}>
                              ✓ Đã mổ xẻ {selectedVideo.rea_breakdown.shots_count} shots ({selectedVideo.rea_breakdown.duration.toFixed(1)}s):
                            </strong>{' '}
                            <span style={{ color: 'var(--mo)' }}>{selectedVideo.rea_breakdown.verdict}</span>
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            {(selectedVideo.rea_report_url || selectedVideo.rea_breakdown.report_url) && (
                              <a
                                href={selectedVideo.rea_report_url || selectedVideo.rea_breakdown.report_url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-[10px] font-bold hover:underline flex items-center gap-0.5"
                                style={{ color: 'var(--link)' }}
                              >
                                Report HTML <ExternalLink className="w-2.5 h-2.5" />
                              </a>
                            )}
                            <button
                              type="button"
                              disabled={Boolean(reaBusyVideoId) || flowGeneratingPrompt}
                              onClick={() => handleReaAndGenerateFlowPrompt(true)}
                              className="text-[10px] font-semibold hover:underline"
                              style={{ color: 'var(--mo)' }}
                              title="Chạy mổ xẻ rea-video lại từ đầu cho video này"
                            >
                              Mổ xẻ lại
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Multi-scene rea-video AI Remake Execution Plan (100% AI First->End Frames + Exact Beat Cut) */}
                      {(flowScenePlan.length > 0 || (selectedVideo?.rea_breakdown?.scene_units && selectedVideo.rea_breakdown.scene_units.length > 0)) ? (
                        <div className="space-y-2">
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="font-bold" style={{ color: 'var(--chu)' }}>
                              🎞️ Kế Hoạch Remake theo Góc Máy rea-video ({(flowScenePlan.length > 0 ? flowScenePlan : selectedVideo?.rea_breakdown?.scene_units || []).length} cảnh → tự ghép 1 video)
                            </span>
                            <span className="text-[10px] font-semibold" style={{ color: 'var(--la)' }}>
                              🛡️ Tự tạo Ảnh Đầu → Cuối bằng AI (0% ảnh gốc)
                            </span>
                          </div>
                          <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                            {(flowScenePlan.length > 0 ? flowScenePlan : selectedVideo?.rea_breakdown?.scene_units || []).map((sc, idx) => {
                              const aiStartFrameSrc = sc.start_frame_url && sc.start_frame_url.includes('_ai_') ? sc.start_frame_url : '';
                              const aiEndFrameSrc = sc.end_frame_url && sc.end_frame_url.includes('_ai_') ? sc.end_frame_url : '';
                              const useFramesPrompt =
                                flowCloneMode === 'flow_frames_start_end' ||
                                flowCloneMode === 'flow_ai_frames_remake' ||
                                flowCloneMode === 'flow_agent_auto';
                              const scenePromptValue = useFramesPrompt
                                ? sc.frames_prompt_en || sc.flow_prompt_en
                                : sc.flow_prompt_en;

                              return (
                                <div
                                  key={sc.unit_index || idx}
                                  className="p-2.5 rounded-xl border space-y-1.5"
                                  style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}
                                >
                                  <div className="flex items-center justify-between gap-2 text-[11px]">
                                    <span className="font-bold truncate" style={{ color: 'var(--chu)' }}>
                                      {sc.title_vi}
                                    </span>
                                    <div className="flex items-center gap-1.5 shrink-0">
                                      {sc.reuse_prev_end_as_start ? (
                                        <span
                                          className="px-1.5 py-0.5 rounded text-[9px] font-bold"
                                          style={{ background: 'var(--xanh-bg)', color: 'var(--link)' }}
                                          title="Dùng lại chính xác Ảnh Cuối AI của cảnh trước làm Ảnh Đầu của cảnh này để cắt chuyển mượt 100%"
                                        >
                                          🔗 Nối liền Ảnh Cuối trước
                                        </span>
                                      ) : (
                                        <span
                                          className="px-1.5 py-0.5 rounded text-[9px] font-bold"
                                          style={{ background: 'var(--la-bg)', color: 'var(--la)' }}
                                          title="Nano Banana 2.1 tự vẽ cặp Ảnh Đầu → Ảnh Cuối mới (không lấy từ video gốc)"
                                        >
                                          🎨 AI vẽ Đầu → Cuối
                                        </span>
                                      )}
                                      <span
                                        className="px-2 py-0.5 rounded-full text-[10px] font-bold"
                                        style={{ background: 'var(--la-bg)', color: 'var(--la)' }}
                                      >
                                        {sc.target_duration.toFixed(1)}s
                                      </span>
                                    </div>
                                  </div>
                                  {sc.action_vi && (
                                    <div className="text-[10px]" style={{ color: 'var(--mo)' }}>
                                      Hành động Remake: {sc.action_vi}
                                    </div>
                                  )}
                                  <div className="flex gap-2">
                                    {flowCloneMode !== 'flow_veo_t2v' && (aiStartFrameSrc || aiEndFrameSrc) && (
                                      <div className="flex items-center gap-1 shrink-0">
                                        {aiStartFrameSrc && (
                                          <div
                                            className="relative w-11 h-16 rounded-lg overflow-hidden bg-black shrink-0 border"
                                            style={{ borderColor: 'var(--vien-nhe)' }}
                                            title="Ảnh Đầu (First Frame) tự tạo mới 100% bằng Nano Banana AI"
                                          >
                                            <img
                                              src={aiStartFrameSrc}
                                              alt={`Scene ${idx + 1} AI start frame`}
                                              className="w-full h-full object-cover"
                                            />
                                            <span className="absolute bottom-0 inset-x-0 bg-black/75 text-white text-[8px] font-bold text-center leading-tight py-0.5">
                                              AI Đầu
                                            </span>
                                          </div>
                                        )}
                                        {aiEndFrameSrc && (
                                          <>
                                            <span className="text-[10px] font-bold shrink-0" style={{ color: 'var(--mo)' }}>
                                              →
                                            </span>
                                            <div
                                              className="relative w-11 h-16 rounded-lg overflow-hidden bg-black shrink-0 border"
                                              style={{ borderColor: 'var(--vien-nhe)' }}
                                              title="Ảnh Cuối (End Frame) tự tạo mới 100% bằng Nano Banana AI"
                                            >
                                              <img
                                                src={aiEndFrameSrc}
                                                alt={`Scene ${idx + 1} AI end frame`}
                                                className="w-full h-full object-cover"
                                              />
                                              <span className="absolute bottom-0 inset-x-0 bg-black/75 text-white text-[8px] font-bold text-center leading-tight py-0.5">
                                                AI Cuối
                                              </span>
                                            </div>
                                          </>
                                        )}
                                      </div>
                                    )}
                                    <textarea
                                      rows={2}
                                      value={scenePromptValue}
                                      onChange={(e) => {
                                        const nextVal = e.target.value;
                                        const baseList =
                                          flowScenePlan.length > 0
                                            ? [...flowScenePlan]
                                            : [...(selectedVideo?.rea_breakdown?.scene_units || [])];
                                        baseList[idx] = useFramesPrompt
                                          ? { ...baseList[idx], frames_prompt_en: nextVal, flow_prompt_en: nextVal }
                                          : { ...baseList[idx], flow_prompt_en: nextVal };
                                        setFlowScenePlan(baseList);
                                      }}
                                      className="sw-input flex-1 p-2 text-[11px] leading-snug"
                                      title="Prompt chuyển động Video nối từ Ảnh Đầu AI sang Ảnh Cuối AI"
                                    />
                                  </div>

                                  {(sc.ai_start_image_prompt_en || sc.ai_end_image_prompt_en) && (
                                    <details className="text-[10px] pt-0.5">
                                      <summary className="cursor-pointer font-semibold select-none" style={{ color: 'var(--link)' }}>
                                        🎨 Xem / Sửa Prompt tự vẽ Ảnh Đầu (First Frame) &amp; Ảnh Cuối (End Frame)
                                      </summary>
                                      <div className="mt-1.5 space-y-1.5">
                                        {!sc.reuse_prev_end_as_start && (
                                          <div>
                                            <div className="font-semibold mb-0.5" style={{ color: 'var(--mo)' }}>
                                              Ảnh Đầu AI (First Frame — Nano Banana 2.1):
                                            </div>
                                            <textarea
                                              rows={2}
                                              value={sc.ai_start_image_prompt_en || ''}
                                              onChange={(e) => {
                                                const val = e.target.value;
                                                const baseList =
                                                  flowScenePlan.length > 0
                                                    ? [...flowScenePlan]
                                                    : [...(selectedVideo?.rea_breakdown?.scene_units || [])];
                                                baseList[idx] = { ...baseList[idx], ai_start_image_prompt_en: val };
                                                setFlowScenePlan(baseList);
                                              }}
                                              className="sw-input w-full p-1.5 text-[10px] leading-snug"
                                            />
                                          </div>
                                        )}
                                        <div>
                                          <div className="font-semibold mb-0.5" style={{ color: 'var(--mo)' }}>
                                            Ảnh Cuối AI (End Frame — Nano Banana 2.1):
                                          </div>
                                          <textarea
                                            rows={2}
                                            value={sc.ai_end_image_prompt_en || ''}
                                            onChange={(e) => {
                                              const val = e.target.value;
                                              const baseList =
                                                flowScenePlan.length > 0
                                                  ? [...flowScenePlan]
                                                  : [...(selectedVideo?.rea_breakdown?.scene_units || [])];
                                              baseList[idx] = { ...baseList[idx], ai_end_image_prompt_en: val };
                                              setFlowScenePlan(baseList);
                                            }}
                                            className="sw-input w-full p-1.5 text-[10px] leading-snug"
                                          />
                                        </div>
                                      </div>
                                    </details>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      ) : (
                        <div className="flex gap-3">
                          <textarea
                            rows={4}
                            value={flowVeoPrompt}
                            onChange={(e) => setFlowVeoPrompt(e.target.value)}
                            placeholder="Bấm '🎬 Mổ xẻ rea-video & Tự viết Prompt' ở góc trên phải để lập Kế Hoạch Remake Cụm Cảnh & Prompt tự tạo Ảnh Đầu → Ảnh Cuối bằng AI (0% lấy ảnh từ video gốc)..."
                            className="sw-input flex-1 p-3 text-xs leading-relaxed"
                          />
                        </div>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                          Hiển thị trên Video
                        </label>
                        <select
                          value={ctaPosition}
                          onChange={(e) => setCtaPosition(e.target.value)}
                          className="sw-input w-full px-3 py-2 text-xs"
                        >
                          <option value="clean_organic">Sạch 100% (Không khung / Không chữ)</option>
                          <option value="hook_3s_only">Hiện Hook 3s đầu (Kiểu Creator)</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                          Điều hướng Link (Comment / Bio)
                        </label>
                        <select
                          value={selectedProductId}
                          onChange={(e) => setSelectedProductId(Number(e.target.value))}
                          className="sw-input w-full px-3 py-2 text-xs"
                        >
                          <option value={0}>-- Không gắn SP (Organic thuần) --</option>
                          {products.map((p) => (
                            <option key={p.id} value={p.id}>
                              #{p.code} — {p.name} ({p.price})
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    {ctaPosition === 'hook_3s_only' && (
                      <div>
                        <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                          Câu Hook hiển thị 3 giây đầu
                        </label>
                        <input
                          value={promptScript}
                          onChange={(e) => setPromptScript(e.target.value)}
                          placeholder="Nhập câu Hook 3 giây đầu..."
                          className="sw-input w-full px-3 py-2 text-xs"
                        />
                      </div>
                    )}

                    <label className="flex items-center gap-2 text-xs cursor-pointer" style={{ color: 'var(--chu)' }}>
                      <input
                        type="checkbox"
                        checked={antiDuplicate}
                        onChange={(e) => setAntiDuplicate(e.target.checked)}
                        className="rounded"
                      />
                      Bật hậu kỳ FFmpeg 9:16 Anti-Duplicate (Micro-Crop + Chỉnh màu + Xoá Metadata)
                    </label>

                    <button
                      type="button"
                      onClick={handleLaunchFlowClone}
                      disabled={isLaunchingClone}
                      className="sw-pill-btn-primary w-full py-3 text-sm font-semibold flex items-center justify-center gap-2"
                    >
                      <Film className="w-4 h-4" />
                      {isLaunchingClone
                        ? 'Đang gửi sang Google Flow...'
                        : `Chạy Clone Video bằng Google Flow ${batchCount > 1 ? `(${batchCount}x)` : ''}`}
                    </button>
                  </div>

                  {/* Right: 9:16 Player + Google Flow Render Queue */}
                  <div className="lg:col-span-7 sw-card p-5 space-y-4">
                    <div className="flex items-center justify-between">
                      <h2 className="text-sm font-bold" style={{ color: 'var(--chu)' }}>
                        Kết Quả Render Google Flow &amp; Hàng Đợi ({jobs.filter((j) => j.clone_mode.startsWith('flow_')).length} Flow jobs)
                      </h2>
                      <button
                        onClick={refreshAll}
                        className="text-xs flex items-center gap-1 font-medium"
                        style={{ color: 'var(--link)' }}
                      >
                        <RefreshCw className="w-3.5 h-3.5" /> Làm mới
                      </button>
                    </div>

                    {activeFlowJob && (activeFlowJob.output_video_url || (activeFlowJob.scene_plan && activeFlowJob.scene_plan.length > 0)) && (
                      <div
                        className="p-4 rounded-2xl border space-y-3"
                        style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}
                      >
                        <div className="grid grid-cols-1 sm:grid-cols-12 gap-4">
                          <div className="sm:col-span-5 bg-black rounded-2xl overflow-hidden aspect-[9/16] max-h-72 mx-auto w-full flex items-center justify-center">
                            {(previewFlowClipUrl || activeFlowJob.output_video_url || activeFlowJob.scene_plan?.find((s) => s.clip_url)?.clip_url) ? (
                              <video
                                key={`${activeFlowJob.id}-${previewFlowClipUrl || activeFlowJob.output_video_url || activeFlowJob.scene_plan?.find((s) => s.clip_url)?.clip_url}`}
                                src={previewFlowClipUrl || activeFlowJob.output_video_url || activeFlowJob.scene_plan?.find((s) => s.clip_url)?.clip_url || ''}
                                controls
                                playsInline
                                className="w-full h-full object-contain"
                              />
                            ) : (
                              <div className="p-4 text-center text-[11px] text-white/80 space-y-1">
                                <RefreshCw className="w-5 h-5 mx-auto animate-spin" />
                                <div>Đang tạo các cảnh thành phần trên Google Flow ({activeFlowJob.progress}%)...</div>
                              </div>
                            )}
                          </div>
                          <div className="sm:col-span-7 flex flex-col justify-between gap-3 text-xs">
                            <div className="space-y-2">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="font-bold">Job #{activeFlowJob.id}</span>
                                <span
                                  className="px-2 py-0.5 rounded-full text-[10px] font-bold"
                                  style={{
                                    background: activeFlowJob.status === 'completed' ? 'var(--la-bg)' : 'var(--cam-bg)',
                                    color: activeFlowJob.status === 'completed' ? 'var(--la)' : 'var(--cam)',
                                  }}
                                >
                                  {activeFlowJob.status === 'completed'
                                    ? 'Hoàn tất · Video Ghép 9:16'
                                    : `Đang chạy (${activeFlowJob.progress}%)`}
                                </span>
                                {activeFlowJob.muse_token_label && (
                                  <span
                                    className="px-2 py-0.5 rounded-full text-[10px] font-semibold"
                                    style={{ background: 'var(--xanh-bg)', color: 'var(--link)' }}
                                  >
                                    {activeFlowJob.muse_token_label}
                                  </span>
                                )}
                                {(!activeFlowJob.scene_plan || activeFlowJob.scene_plan.length === 0) && activeFlowEngineBadge && (
                                  <span
                                    className="px-2 py-0.5 rounded-full text-[10px] font-bold border"
                                    style={{
                                      background: activeFlowEngineBadge.bg,
                                      borderColor: 'var(--vien-nhe)',
                                      color: activeFlowEngineBadge.color,
                                    }}
                                    title={activeFlowEngineBadge.title}
                                  >
                                    {activeFlowEngineBadge.label}
                                  </span>
                                )}
                              </div>

                              {activeFlowJob.scene_plan && activeFlowJob.scene_plan.length > 0 && (
                                <div className="p-2.5 rounded-xl border space-y-1.5" style={{ background: 'var(--nen)', borderColor: 'var(--vien-nhe)' }}>
                                  <div className="text-[10px] font-bold flex items-center justify-between" style={{ color: 'var(--mo)' }}>
                                    <span>Các Cảnh Thành Phần đã tạo &amp; ghép ({activeFlowJob.scene_plan.length} cảnh)</span>
                                    <span>Bấm để xem từng cảnh</span>
                                  </div>
                                  <div className="flex flex-wrap items-center gap-1.5">
                                    {activeFlowEngineBadge && (
                                      <span
                                        className="px-2.5 py-1 rounded-lg text-[10px] font-bold border"
                                        style={{
                                          background: activeFlowEngineBadge.bg,
                                          borderColor: 'var(--vien-nhe)',
                                          color: activeFlowEngineBadge.color,
                                        }}
                                        title={activeFlowEngineBadge.title}
                                      >
                                        {activeFlowEngineBadge.label}
                                      </span>
                                    )}
                                    {activeFlowJob.output_video_url && (
                                      <button
                                        type="button"
                                        onClick={() => setPreviewFlowClipUrl('')}
                                        className="px-2.5 py-1 rounded-lg text-[10px] font-bold border transition"
                                        style={{
                                          background: !previewFlowClipUrl ? 'var(--la-bg)' : 'var(--xam)',
                                          borderColor: !previewFlowClipUrl ? 'var(--la)' : 'var(--vien-nhe)',
                                          color: !previewFlowClipUrl ? 'var(--la)' : 'var(--chu)',
                                        }}
                                      >
                                        🎬 Video Ghép Hoàn Chỉnh
                                      </button>
                                    )}
                                    {activeFlowJob.scene_plan.map((sc) => {
                                      const isSel = Boolean(sc.clip_url && previewFlowClipUrl === sc.clip_url);
                                      const stBadge =
                                        sc.status === 'done'
                                          ? '✓'
                                          : sc.status === 'generating'
                                          ? '⏳'
                                          : sc.status === 'failed'
                                          ? '✕'
                                          : '•';
                                      return (
                                        <button
                                          key={sc.unit_index}
                                          type="button"
                                          disabled={!sc.clip_url}
                                          onClick={() => sc.clip_url && setPreviewFlowClipUrl(sc.clip_url)}
                                          className="px-2 py-1 rounded-lg text-[10px] font-semibold border transition disabled:opacity-60"
                                          style={{
                                            background: isSel ? 'var(--xanh-bg)' : 'var(--xam)',
                                            borderColor: isSel ? 'var(--xanh)' : 'var(--vien-nhe)',
                                            color: isSel ? 'var(--link)' : 'var(--chu)',
                                          }}
                                          title={sc.engine_used ? `${sc.title_vi} · Engine: ${sc.engine_used}` : sc.title_vi}
                                        >
                                          {stBadge} Cảnh {sc.unit_index} ({sc.target_duration.toFixed(1)}s)
                                        </button>
                                      );
                                    })}
                                  </div>
                                  {activeFlowJob.scene_plan.some(
                                    (s) => (s.start_frame_url && s.start_frame_url.includes('_ai_')) || (s.end_frame_url && s.end_frame_url.includes('_ai_'))
                                  ) && (
                                    <div className="pt-1.5 border-t flex flex-wrap items-center gap-2" style={{ borderColor: 'var(--vien-nhe)' }}>
                                      <span className="text-[9px] font-bold" style={{ color: 'var(--la)' }}>
                                        🎨 Ảnh Đầu → Cuối do AI tự tạo:
                                      </span>
                                      {activeFlowJob.scene_plan.map((sc) =>
                                        (sc.start_frame_url?.includes('_ai_') || sc.end_frame_url?.includes('_ai_')) ? (
                                          <div key={sc.unit_index} className="flex items-center gap-1 rounded-lg p-1 border" style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}>
                                            <span className="text-[9px] font-bold px-1" style={{ color: 'var(--mo)' }}>
                                              C{sc.unit_index}
                                            </span>
                                            {sc.start_frame_url?.includes('_ai_') && (
                                              <img
                                                src={sc.start_frame_url}
                                                alt={`C${sc.unit_index} AI start`}
                                                className="w-7 h-10 rounded object-cover border"
                                                style={{ borderColor: 'var(--vien-nhe)' }}
                                                title={`Cảnh ${sc.unit_index} — Ảnh Đầu (Nano Banana AI tự tạo)`}
                                              />
                                            )}
                                            <span className="text-[9px]" style={{ color: 'var(--mo)' }}>→</span>
                                            {sc.end_frame_url?.includes('_ai_') && (
                                              <img
                                                src={sc.end_frame_url}
                                                alt={`C${sc.unit_index} AI end`}
                                                className="w-7 h-10 rounded object-cover border"
                                                style={{ borderColor: 'var(--vien-nhe)' }}
                                                title={`Cảnh ${sc.unit_index} — Ảnh Cuối (Nano Banana AI tự tạo)`}
                                              />
                                            )}
                                          </div>
                                        ) : null
                                      )}
                                    </div>
                                  )}
                                </div>
                              )}

                              {activeFlowJob.veo_prompt && (
                                <div className="p-2.5 rounded-xl border" style={{ background: 'var(--nen)', borderColor: 'var(--vien-nhe)' }}>
                                  <div className="text-[10px] font-semibold mb-0.5" style={{ color: 'var(--mo)' }}>
                                    Kịch bản Prompt theo Cụm Cảnh rea-video
                                  </div>
                                  <p className="line-clamp-3 whitespace-pre-line text-[11px]">{activeFlowJob.veo_prompt}</p>
                                </div>
                              )}
                            </div>

                            {activeFlowJob.output_video_url && (
                              <div className="flex flex-wrap gap-2">
                                <a
                                  href={activeFlowJob.output_video_url}
                                  download={`flow_clone_${activeFlowJob.id}.mp4`}
                                  className="sw-pill-btn px-3.5 py-2 text-xs font-semibold border flex items-center gap-1.5"
                                  style={{ background: 'var(--nen)', borderColor: 'var(--vien)', color: 'var(--chu)' }}
                                >
                                  <Download className="w-3.5 h-3.5" /> Tải Video Hoàn Chỉnh
                                </a>
                                <button
                                  onClick={() => {
                                    setPubJobId(activeFlowJob.id);
                                    setActiveTab('dang-bai');
                                  }}
                                  className="sw-pill-btn-primary flex-1 px-3.5 py-2 text-xs flex items-center justify-center gap-1.5"
                                >
                                  <Send className="w-3.5 h-3.5" /> Đưa sang Đăng Bài &amp; Auto-Comment
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
                      {flowJobs.length === 0 ? (
                        <div className="py-10 text-center text-xs" style={{ color: 'var(--mo)' }}>
                          Chưa có tiến trình nào. Hãy thêm tài khoản Google Flow và bấm &ldquo;Chạy Clone Video bằng Google Flow&rdquo;!
                        </div>
                      ) : (
                        flowJobs.map((job) => (
                          <div
                            key={job.id}
                            onClick={() => setActiveFlowJobId(job.id)}
                            className="p-3 rounded-2xl border cursor-pointer transition space-y-2"
                            style={{
                              background: activeFlowJob?.id === job.id ? 'var(--xanh-bg)' : 'var(--xam)',
                              borderColor: activeFlowJob?.id === job.id ? 'var(--xanh)' : 'var(--vien-nhe)',
                            }}
                          >
                            <div className="flex items-center justify-between gap-2 text-xs">
                              <div className="flex items-center gap-2 min-w-0">
                                <span className="font-bold">Job #{job.id}</span>
                                <span
                                  className="px-2 py-0.5 rounded-full text-[10px] font-semibold"
                                  style={{
                                    background: job.clone_mode.startsWith('flow_') ? 'var(--la-bg)' : 'var(--nen)',
                                    color: job.clone_mode.startsWith('flow_') ? 'var(--la)' : 'var(--mo)',
                                  }}
                                >
                                  {job.clone_mode.startsWith('flow_') ? 'Google Flow' : job.clone_mode}
                                </span>
                                {job.muse_token_label && (
                                  <span className="text-[11px] truncate" style={{ color: 'var(--link)' }}>
                                    {job.muse_token_label}
                                  </span>
                                )}
                                <span className="truncate" style={{ color: 'var(--mo)' }}>
                                  {job.source_title || job.prompt_script}
                                </span>
                              </div>
                              <div className="flex items-center gap-1.5 shrink-0" onClick={(e) => e.stopPropagation()}>
                                <span
                                  className="px-2.5 py-0.5 rounded-full text-[10px] font-bold"
                                  style={{
                                    background:
                                      job.status === 'completed'
                                        ? 'var(--la-bg)'
                                        : job.status === 'failed'
                                        ? 'var(--do-bg)'
                                        : 'var(--cam-bg)',
                                    color:
                                      job.status === 'completed'
                                        ? 'var(--la)'
                                        : job.status === 'failed'
                                        ? 'var(--do)'
                                        : 'var(--cam)',
                                  }}
                                >
                                  {job.status === 'completed'
                                    ? 'Hoàn tất (100%)'
                                    : job.status === 'failed'
                                    ? `Thất bại (${job.progress}%)`
                                    : job.status === 'analyzing'
                                    ? `Đang chuẩn bị Frame & Prompt (${job.progress}%)`
                                    : job.status === 'generating_muse'
                                    ? `Đang tạo Video trên Google Flow (${job.progress}%)`
                                    : job.status === 'compositing_ffmpeg'
                                    ? `Hậu kỳ FFmpeg 9:16 (${job.progress}%)`
                                    : `Đang xếp hàng (${job.progress}%)`}
                                </span>
                                {job.status === 'failed' && (
                                  <button
                                    type="button"
                                    onClick={async () => {
                                      try {
                                        await api.retryCloneJob(job.id);
                                        notify(`Đã chạy lại Job #${job.id}!`);
                                        await refreshAll();
                                      } catch (err: unknown) {
                                        notify(err instanceof Error ? err.message : 'Lỗi chạy lại Job', 'err');
                                      }
                                    }}
                                    className="sw-pill-btn px-2 py-0.5 text-[10px] font-bold border"
                                    style={{ background: 'var(--xanh-bg)', borderColor: 'transparent', color: 'var(--link)' }}
                                    title="Chạy lại Job này"
                                  >
                                    Chạy lại
                                  </button>
                                )}
                                <button
                                  type="button"
                                  onClick={async () => {
                                    try {
                                      await api.deleteCloneJob(job.id);
                                      if (activeCloneJobId === job.id) setActiveCloneJobId(null);
                                      if (activeFlowJobId === job.id) setActiveFlowJobId(null);
                                      notify(job.status === 'completed' || job.status === 'failed' ? `Đã xoá Job #${job.id}` : `Đã huỷ Job #${job.id}`);
                                      await refreshAll();
                                    } catch (err: unknown) {
                                      notify(err instanceof Error ? err.message : 'Lỗi xoá Job', 'err');
                                    }
                                  }}
                                  className="p-1 rounded-lg"
                                  style={{ background: 'var(--do-bg)', color: 'var(--do)' }}
                                  title={job.status === 'completed' || job.status === 'failed' ? 'Xoá Job' : 'Huỷ tiến trình'}
                                >
                                  <Trash2 className="w-3 h-3" />
                                </button>
                              </div>
                            </div>

                            {job.status !== 'completed' && (
                              <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--o)' }}>
                                <div
                                  className="h-full transition-all duration-300"
                                  style={{
                                    width: `${job.progress}%`,
                                    background: job.status === 'failed' ? 'var(--do)' : 'var(--la)',
                                  }}
                                />
                              </div>
                            )}

                            {job.error_message && (
                              <div className="text-[11px]" style={{ color: 'var(--do)' }}>
                                {job.error_message}
                              </div>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ==============================================================
                VIEW 5: KHO SẢN PHẨM & LINK BIO
               ============================================================== */}
            {activeTab === 'kho-san-pham' && (
              <div className="space-y-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--chu)' }}>
                      Kho Sản Phẩm & Link Bio (/bio)
                    </h1>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--mo)' }}>
                      Quản lý mã #SP01..#SP99 và theo dõi lượt click thực tế qua trang Storefront Bio miễn phí.
                    </p>
                  </div>
                  <a
                    href="/bio"
                    target="_blank"
                    rel="noreferrer"
                    className="sw-pill-btn-primary px-4 py-2 text-xs flex items-center gap-1.5"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    Mở Trang /bio trực tiếp
                  </a>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                  <div className="lg:col-span-7 space-y-5">
                    <form onSubmit={handleCreateProduct} className="sw-card p-5 space-y-3">
                      <h2 className="text-sm font-bold flex items-center gap-2" style={{ color: 'var(--chu)' }}>
                        <Plus className="w-4 h-4" style={{ color: 'var(--la)' }} />
                        Thêm Sản Phẩm Affiliate Mới
                      </h2>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                        <input
                          value={prodForm.code}
                          onChange={(e) => setProdForm({ ...prodForm, code: e.target.value })}
                          placeholder="Mã SP (vd: SP04)"
                          className="sw-input px-3 py-2 text-xs"
                        />
                        <select
                          value={prodForm.platform_name}
                          onChange={(e) => setProdForm({ ...prodForm, platform_name: e.target.value })}
                          className="sw-input px-3 py-2 text-xs"
                        >
                          <option value="Shopee">Shopee</option>
                          <option value="TikTok Shop">TikTok Shop</option>
                          <option value="Lazada">Lazada</option>
                          <option value="ClickBank">ClickBank / Global</option>
                        </select>
                        <input
                          value={prodForm.price}
                          onChange={(e) => setProdForm({ ...prodForm, price: e.target.value })}
                          placeholder="Giá sale (249.000đ)"
                          className="sw-input px-3 py-2 text-xs"
                        />
                        <input
                          value={prodForm.original_price}
                          onChange={(e) => setProdForm({ ...prodForm, original_price: e.target.value })}
                          placeholder="Giá gốc (499.000đ)"
                          className="sw-input px-3 py-2 text-xs"
                        />
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                        <input
                          value={prodForm.name}
                          onChange={(e) => setProdForm({ ...prodForm, name: e.target.value })}
                          placeholder="Tên sản phẩm hiển thị trên Video & Trang Bio"
                          className="sw-input px-3 py-2 text-xs"
                        />
                        <input
                          value={prodForm.affiliate_url}
                          onChange={(e) => setProdForm({ ...prodForm, affiliate_url: e.target.value })}
                          placeholder="Link Affiliate (https://shope.ee/...)"
                          className="sw-input px-3 py-2 text-xs"
                        />
                      </div>
                      <input
                        value={prodForm.comment_template}
                        onChange={(e) => setProdForm({ ...prodForm, comment_template: e.target.value })}
                        placeholder="Mẫu comment tự động (dùng {affiliate_url} để chèn link)"
                        className="sw-input w-full px-3 py-2 text-xs"
                      />
                      <button type="submit" className="sw-pill-btn-primary px-5 py-2 text-xs">
                        Lưu Sản Phẩm & Đồng Bộ /bio
                      </button>
                    </form>

                    <div className="sw-card p-5 space-y-3">
                      <h3 className="text-sm font-bold" style={{ color: 'var(--chu)' }}>
                        Kho Sản Phẩm Đang Chạy ({products.length})
                      </h3>
                      <div className="space-y-2.5">
                        {products.map((p) => (
                          <div
                            key={p.id}
                            className="p-3 rounded-2xl border flex flex-wrap items-center justify-between gap-3"
                            style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}
                          >
                            <div className="flex items-center gap-3 min-w-0 flex-1">
                              <span
                                className="px-2.5 py-1 rounded-full text-xs font-bold shrink-0"
                                style={{ background: 'var(--cam-bg)', color: 'var(--cam)' }}
                              >
                                #{p.code}
                              </span>
                              <div className="min-w-0">
                                <div className="text-xs font-bold truncate" style={{ color: 'var(--chu)' }}>
                                  {p.name}
                                </div>
                                <div className="text-[11px] truncate" style={{ color: 'var(--mo)' }}>
                                  {p.platform_name} ·{' '}
                                  <span style={{ color: 'var(--la)', fontWeight: 600 }}>{p.price}</span> ·{' '}
                                  {p.clicks_count} clicks
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center gap-1.5">
                              <button
                                onClick={() => api.toggleProductBio(p.id).then(refreshAll)}
                                className="sw-pill-btn px-2.5 py-1 text-[11px] font-semibold"
                                style={{
                                  background: p.bio_active ? 'var(--la-bg)' : 'var(--o)',
                                  color: p.bio_active ? 'var(--la)' : 'var(--mo)',
                                }}
                              >
                                {p.bio_active ? 'Hiện ở Bio' : 'Đang ẩn'}
                              </button>
                              <button
                                onClick={() => copyText(p.affiliate_url, 'Link Affiliate')}
                                className="p-1.5 rounded-full border"
                                style={{ background: 'var(--nen)', borderColor: 'var(--vien-nhe)', color: 'var(--mo)' }}
                                title="Copy link"
                              >
                                <ClipboardCopy className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => api.deleteProduct(p.id).then(refreshAll)}
                                className="p-1.5 rounded-full"
                                style={{ background: 'var(--do-bg)', color: 'var(--do)' }}
                                title="Xoá"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Right: Apple iPhone Bio Storefront Preview */}
                  <div className="lg:col-span-5 flex flex-col items-center">
                    <div
                      className="w-full max-w-[340px] rounded-[42px] border-[7px] p-4 space-y-3"
                      style={{
                        background: 'var(--nen)',
                        borderColor: '#1d1d1f',
                        boxShadow: 'var(--shadow-float)',
                      }}
                    >
                      <div className="w-20 h-1.5 rounded-full mx-auto mb-1" style={{ background: 'var(--vien)' }} />
                      <div className="text-center space-y-1">
                        <div
                          className="w-14 h-14 rounded-full mx-auto flex items-center justify-center text-white font-bold"
                          style={{ background: '#0b0b0d' }}
                        >
                          <SpyWinLogo size={32} />
                        </div>
                        <div className="text-sm font-bold" style={{ color: 'var(--chu)' }}>
                          {bioBrandName || 'Deal Ngon Mỗi Ngày'}
                        </div>
                        <div className="text-[11px]" style={{ color: 'var(--mo)' }}>
                          {bioBrandSub || 'Tìm mã #SP trên video để nhận ưu đãi'}
                        </div>
                      </div>

                      <input
                        value={bioSearch}
                        onChange={(e) => setBioSearch(e.target.value)}
                        placeholder="Tìm mã #SP01..."
                        className="sw-input w-full px-3 py-2 text-xs"
                      />

                      <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1">
                        {filteredBioProducts.map((p) => (
                          <a
                            key={p.id}
                            href={`/bio/go/${p.id}`}
                            target="_blank"
                            rel="noreferrer"
                            className="flex items-center gap-2.5 p-2.5 rounded-2xl border transition hover:opacity-90"
                            style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}
                          >
                            <img
                              src={
                                p.image_url ||
                                'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=200&q=80'
                              }
                              alt={p.name}
                              className="w-12 h-12 rounded-xl object-cover shrink-0"
                            />
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center gap-1.5">
                                <span
                                  className="text-[10px] font-bold px-1.5 py-0.5 rounded-full"
                                  style={{ background: 'var(--xanh)', color: '#fff' }}
                                >
                                  #{p.code}
                                </span>
                                <span className="text-[10px]" style={{ color: 'var(--mo)' }}>
                                  {p.platform_name}
                                </span>
                              </div>
                              <div className="text-xs font-semibold truncate mt-0.5" style={{ color: 'var(--chu)' }}>
                                {p.name}
                              </div>
                              <div className="text-xs font-bold" style={{ color: 'var(--la)' }}>
                                {p.price}
                              </div>
                            </div>
                          </a>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ==============================================================
                VIEW 6: ĐĂNG BÀI & AUTO-COMMENT
               ============================================================== */}
            {activeTab === 'dang-bai' && (
              <div className="space-y-5">
                <div>
                  <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--chu)' }}>
                    Đăng Bài & Auto-Comment Affiliate
                  </h1>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--mo)' }}>
                    Gắn link đúng luật từng nền tảng tránh bóp reach: Comment đầu (Facebook), Link Bio #MãSP (Instagram),
                    Reply Chain (Threads).
                  </p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                  <div className="lg:col-span-6 sw-card p-5 space-y-4">
                    <div>
                      <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                        Chọn Video Clone Đã Render
                      </label>
                      <select
                        value={selectedPubJob?.id || ''}
                        onChange={(e) => setPubJobId(Number(e.target.value))}
                        className="sw-input w-full px-3 py-2 text-xs"
                      >
                        {completedJobs.length === 0 && (
                          <option value="">Chưa có video hoàn tất — hãy clone ở Tab Clone Video</option>
                        )}
                        {completedJobs.map((j) => (
                          <option key={j.id} value={j.id}>
                            Job #{j.id} — {j.product_code ? `#${j.product_code} ${j.product_name}` : `Organic Viral (${j.source_title || j.clone_mode})`}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                          Nền tảng đích
                        </label>
                        <select
                          value={pubPlatform}
                          onChange={(e) => setPubPlatform(e.target.value as typeof pubPlatform)}
                          className="sw-input w-full px-3 py-2 text-xs"
                        >
                          <option value="facebook_reels">Facebook Reels (Comment đầu)</option>
                          <option value="instagram_reels">Instagram Reels (Link Bio #MãSP)</option>
                          <option value="threads">Threads (Chuỗi Reply Link)</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                          Kênh / Fanpage đăng
                        </label>
                        <input
                          value={pubAccount}
                          onChange={(e) => setPubAccount(e.target.value)}
                          className="sw-input w-full px-3 py-2 text-xs"
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-[11px] font-semibold" style={{ color: 'var(--mo)' }}>
                          Caption sạch link (tối ưu reach)
                        </label>
                        <button
                          onClick={() => copyText(pubCaption, 'Caption')}
                          className="text-[11px] font-semibold hover:underline"
                          style={{ color: 'var(--link)' }}
                        >
                          Copy Caption
                        </button>
                      </div>
                      <textarea
                        rows={4}
                        value={pubCaption}
                        onChange={(e) => setPubCaption(e.target.value)}
                        className="sw-input w-full p-3 text-xs"
                      />
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-[11px] font-bold" style={{ color: 'var(--la)' }}>
                          {pubPlatform === 'instagram_reels'
                            ? 'Hướng dẫn tìm #MãSP trên Bio'
                            : pubPlatform === 'threads'
                            ? 'Thread Reply tự động chứa Link Affiliate'
                            : 'Comment đầu tiên tự động chứa Link Affiliate'}
                        </label>
                        <button
                          onClick={() => copyText(pubFirstComment, 'Comment Link')}
                          className="text-[11px] font-semibold hover:underline"
                          style={{ color: 'var(--la)' }}
                        >
                          Copy Comment
                        </button>
                      </div>
                      <textarea
                        rows={2}
                        value={pubFirstComment}
                        onChange={(e) => setPubFirstComment(e.target.value)}
                        className="sw-input w-full p-3 text-xs"
                        style={{ background: 'var(--la-bg)', color: 'var(--la)', borderColor: 'transparent' }}
                      />
                    </div>

                    <button
                      onClick={handlePublish}
                      disabled={!selectedPubJob}
                      className="sw-pill-btn-primary w-full py-3 text-sm flex items-center justify-center gap-2"
                    >
                      <Send className="w-4 h-4" />
                      Đăng Video & Kích hoạt Auto-Link
                    </button>
                  </div>

                  <div className="lg:col-span-6 sw-card p-5 space-y-4">
                    <h2 className="text-sm font-bold" style={{ color: 'var(--chu)' }}>
                      Nhật ký Đăng & Gắn Link ({publishTasks.length})
                    </h2>
                    <div className="space-y-3 max-h-[520px] overflow-y-auto pr-1">
                      {publishTasks.length === 0 ? (
                        <div className="py-12 text-center text-xs" style={{ color: 'var(--mo)' }}>
                          Chưa có bài đăng nào. Chọn video clone hoàn tất bên trái và bấm Đăng Video!
                        </div>
                      ) : (
                        publishTasks.map((t) => (
                          <div
                            key={t.id}
                            className="p-3.5 rounded-2xl border space-y-2 text-xs"
                            style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-bold">
                                {t.target_platform.toUpperCase()} · {t.account_name}
                              </span>
                              <span
                                className="px-2.5 py-0.5 rounded-full text-[10px] font-bold"
                                style={{ background: 'var(--la-bg)', color: 'var(--la)' }}
                              >
                                {t.status}
                              </span>
                            </div>
                            <div className="line-clamp-2" style={{ color: 'var(--mo)' }}>
                              {t.caption}
                            </div>
                            <div className="p-2.5 rounded-xl" style={{ background: 'var(--la-bg)', color: 'var(--la)' }}>
                              <strong>Chiến lược ({t.link_strategy}):</strong> {t.first_comment_text}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ==============================================================
                VIEW 7: CÀI ĐẶT AGENT-REACH, REA-VIDEO & HỆ THỐNG
               ============================================================== */}
            {activeTab === 'cai-dat' && (
              <div className="space-y-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--chu)' }}>
                      Cài đặt Agent-Reach, rea-video &amp; Hệ thống
                    </h1>
                    <p className="text-xs mt-1" style={{ color: 'var(--mo)' }}>
                      Quản lý đăng nhập đa nền tảng qua trình duyệt riêng của Agent-Reach, cấu hình VLM cho rea-video và /bio.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={loadAgentReachStatus}
                    disabled={arLoading}
                    className="sw-pill-btn px-4 py-2 text-xs font-bold border flex items-center gap-1.5"
                    style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)', color: 'var(--chu)' }}
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${arLoading ? 'animate-spin' : ''}`} />
                    {arLoading ? 'Đang kiểm tra Agent-Reach...' : 'Làm mới trạng thái Agent-Reach'}
                  </button>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                  <div className="lg:col-span-6 sw-card p-5 space-y-4">
                    <h2 className="text-sm font-bold flex items-center gap-2">
                      <Activity className="w-4 h-4" style={{ color: 'var(--xanh)' }} />
                      Trạng thái Engine Local (6 Module)
                    </h2>
                    <div className="grid grid-cols-2 gap-3 text-xs">
                      {[
                        {
                          name: 'Agent-Reach CLI',
                          ok: status?.agent_reach_installed,
                          detail: status?.agent_reach_installed
                            ? `v${arStatus?.version || '1.6.1'} · Multi-Social`
                            : 'Chưa cài agent-reach',
                        },
                        {
                          name: 'rea-video Decomposer',
                          ok: status?.rea_video_installed,
                          detail: status?.rea_video_installed ? 'Shot-by-Shot & VLM' : 'Chưa tìm thấy CLI',
                        },
                        { name: 'FFmpeg Video Composer', ok: status?.ffmpeg_installed, detail: '9:16 + CTA Overlay' },
                        { name: 'yt-dlp Downloader', ok: status?.ytdlp_installed, detail: 'YT / Bili / XHS / IG / FB' },
                        { name: 'Playwright Headless', ok: status?.playwright_installed, detail: 'Meta Ads / Browser' },
                        {
                          name: 'Crawl4AI Engine',
                          ok: status?.crawl4ai_installed,
                          detail: status?.crawl4ai_installed ? 'Native' : 'Agent-Reach / PW Fallback',
                        },
                      ].map((item, idx) => (
                        <div
                          key={idx}
                          className="p-3 rounded-2xl border"
                          style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}
                        >
                          <div className="font-bold flex items-center justify-between gap-1">
                            <span className="truncate">{item.name}</span>
                            <span style={{ color: item.ok ? 'var(--la)' : 'var(--cam)' }}>
                              {item.ok ? 'READY' : 'FALLBACK'}
                            </span>
                          </div>
                          <div className="text-[11px] mt-1 truncate" style={{ color: 'var(--mo)' }}>
                            {item.detail}
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="pt-3 border-t space-y-3" style={{ borderColor: 'var(--vien-nhe)' }}>
                      <h3 className="text-sm font-bold">Cấu hình /bio, rea-video VLM &amp; treg.to API</h3>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                          <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                            Tên Shop / Kênh trên Trang /bio
                          </label>
                          <input
                            value={bioBrandName}
                            onChange={(e) => setBioBrandName(e.target.value)}
                            className="sw-input w-full px-3 py-2 text-xs"
                          />
                        </div>
                        <div>
                          <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                            Mô tả ngắn trên Trang /bio
                          </label>
                          <input
                            value={bioBrandSub}
                            onChange={(e) => setBioBrandSub(e.target.value)}
                            className="sw-input w-full px-3 py-2 text-xs"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                          treg.to API Key (Tuỳ chọn — bỏ trống nếu dùng Agent-Reach / Playwright Free)
                        </label>
                        <input
                          type="password"
                          value={tregApiKey}
                          onChange={(e) => setTregApiKey(e.target.value)}
                          placeholder="Bỏ trống để dùng crawler miễn phí trên máy..."
                          className="sw-input w-full px-3 py-2 text-xs"
                        />
                      </div>

                      <div
                        className="p-3.5 rounded-2xl border space-y-3"
                        style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-bold flex items-center gap-1.5">
                            <Scissors className="w-3.5 h-3.5" style={{ color: 'var(--link)' }} />
                            Cấu hình rea-video (Shot-by-Shot &amp; VLM)
                          </span>
                          <label className="flex items-center gap-1.5 text-[11px] font-semibold cursor-pointer">
                            <input
                              type="checkbox"
                              checked={reaVlmEnabled === '1'}
                              onChange={(e) => setReaVlmEnabled(e.target.checked ? '1' : '0')}
                              className="rounded"
                            />
                            Bật VLM (--vlm)
                          </label>
                        </div>

                        <div>
                          <label className="block text-[10px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                            1. VLM Base URL (Endpoint OpenAI-compatible / Gemini / Proxy)
                          </label>
                          <input
                            value={reaVlmBaseUrl}
                            onChange={(e) => setReaVlmBaseUrl(e.target.value)}
                            placeholder="https://api.openai.com/v1 hoặc https://your-proxy.com/v1"
                            className="sw-input w-full px-3 py-1.5 text-xs"
                          />
                        </div>

                        <div>
                          <label className="block text-[10px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                            2. API Key &amp; Tự động Fetch danh sách Model
                          </label>
                          <div className="flex flex-wrap gap-2">
                            <input
                              type="password"
                              value={reaVlmApiKey}
                              onChange={(e) => setReaVlmApiKey(e.target.value)}
                              placeholder="sk-... hoặc AIza... (API Key của endpoint)"
                              className="sw-input flex-1 min-w-[180px] px-3 py-1.5 text-xs"
                            />
                            <button
                              type="button"
                              disabled={vlmFetchingModels}
                              onClick={handleFetchReaVlmModels}
                              className="sw-pill-btn px-3.5 py-1.5 text-xs font-bold flex items-center gap-1.5 shrink-0"
                              style={{ background: 'var(--xanh-bg)', color: 'var(--link)' }}
                            >
                              <RefreshCw className={`w-3.5 h-3.5 ${vlmFetchingModels ? 'animate-spin' : ''}`} />
                              {vlmFetchingModels ? 'Đang Fetch...' : 'Fetch Models'}
                            </button>
                          </div>
                        </div>

                        {vlmFetchedModels.length > 0 && (
                          <div
                            className="p-2.5 rounded-xl border space-y-2"
                            style={{ background: 'var(--nen)', borderColor: 'var(--vien-nhe)' }}
                          >
                            <div className="flex items-center justify-between gap-2 text-[10px]">
                              <span className="font-bold" style={{ color: 'var(--la)' }}>
                                Đã tải {vlmFetchedModels.length} models từ API — Chọn model sử dụng:
                              </span>
                              <span style={{ color: 'var(--mo)' }}>
                                {vlmRecommendedModels.length} Vision/Multimodal
                              </span>
                            </div>
                            <select
                              value={vlmFetchedModels.includes(reaVlmModel) ? reaVlmModel : ''}
                              onChange={(e) => {
                                if (e.target.value) setReaVlmModel(e.target.value);
                              }}
                              className="sw-input w-full px-3 py-1.5 text-xs"
                            >
                              <option value="">-- Chọn nhanh 1 model từ danh sách đã Fetch --</option>
                              {vlmFetchedModels.map((m) => (
                                <option key={m} value={m}>
                                  {vlmRecommendedModels.includes(m) ? `★ ${m} (Vision/Multimodal)` : m}
                                </option>
                              ))}
                            </select>
                            {vlmRecommendedModels.length > 0 && (
                              <div className="flex flex-wrap gap-1">
                                {vlmRecommendedModels.slice(0, 8).map((m) => {
                                  const selected = reaVlmModel
                                    .split(',')
                                    .map((x) => x.trim())
                                    .includes(m);
                                  return (
                                    <button
                                      key={m}
                                      type="button"
                                      onClick={() => setReaVlmModel(m)}
                                      className="px-2 py-0.5 rounded-full text-[10px] font-semibold border transition"
                                      style={{
                                        background: selected ? 'var(--xanh-bg)' : 'var(--xam)',
                                        borderColor: selected ? 'var(--xanh)' : 'var(--vien-nhe)',
                                        color: selected ? 'var(--link)' : 'var(--chu)',
                                      }}
                                    >
                                      {m}
                                    </button>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        )}

                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                          <div className="sm:col-span-2">
                            <label className="block text-[10px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                              3. Model đã chọn (hoặc nhập nhiều model cách dấu phẩy)
                            </label>
                            <input
                              value={reaVlmModel}
                              onChange={(e) => setReaVlmModel(e.target.value)}
                              placeholder="gemini-2.5-pro,gpt-4o"
                              className="sw-input w-full px-3 py-1.5 text-xs"
                            />
                          </div>
                          <div>
                            <label className="block text-[10px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                              Ngôn ngữ Report
                            </label>
                            <select
                              value={reaReportLang}
                              onChange={(e) => setReaReportLang(e.target.value)}
                              className="sw-input w-full px-3 py-1.5 text-xs"
                            >
                              <option value="en">English (en)</option>
                              <option value="zh">中文 (zh)</option>
                            </select>
                          </div>
                        </div>
                      </div>

                      <button
                        onClick={() =>
                          api
                            .updateSettings({
                              treg_api_key: tregApiKey,
                              bio_brand_name: bioBrandName,
                              bio_brand_subtitle: bioBrandSub,
                              rea_vlm_enabled: reaVlmEnabled,
                              rea_vlm_base_url: reaVlmBaseUrl,
                              rea_vlm_api_key: reaVlmApiKey,
                              rea_vlm_model: reaVlmModel,
                              rea_report_lang: reaReportLang,
                            })
                            .then(() => {
                              notify('Đã lưu toàn bộ cấu hình Hệ thống & rea-video!');
                              refreshAll();
                            })
                        }
                        className="sw-pill-btn-primary px-5 py-2 text-xs"
                      >
                        Lưu Cấu Hình
                      </button>
                    </div>
                  </div>

                  <div className="lg:col-span-6 space-y-5">
                    {/* Agent-Reach Browser & Key Config Card */}
                    <div className="sw-card p-5 space-y-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <h2 className="text-sm font-bold flex items-center gap-2">
                          <Globe className="w-4 h-4" style={{ color: 'var(--link)' }} />
                          Trình duyệt &amp; Khoá API cho Agent-Reach
                        </h2>
                        <span
                          className="px-2.5 py-0.5 rounded-full text-[11px] font-bold"
                          style={{
                            background: arStatus?.browser?.running ? 'var(--la-bg)' : 'var(--xam)',
                            color: arStatus?.browser?.running ? 'var(--la)' : 'var(--mo)',
                          }}
                        >
                          {arStatus?.browser?.running ? 'Browser Running' : 'Browser Idle'}
                        </span>
                      </div>

                      <div
                        className="p-3 rounded-2xl border text-[11px] space-y-1"
                        style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)', color: 'var(--mo)' }}
                      >
                        <div>
                          <strong>Profile Dir:</strong>{' '}
                          <span className="font-mono">{arStatus?.browser?.profile_dir || '~/.agent-reach/browser'}</span>
                        </div>
                        <div>
                          <strong>Browser Binary:</strong>{' '}
                          <span className="font-mono">{arStatus?.browser?.chrome || 'Chrome / CloakBrowser'}</span>
                          {arStatus?.browser?.backend ? ` (${arStatus.browser.backend})` : ''}
                        </div>
                        <div>
                          Đăng nhập bằng nút <strong>Đăng nhập Browser</strong> ở bảng kênh bên dưới sẽ mở cửa sổ trình duyệt
                          riêng của Agent-Reach và tự lưu session cookie vào máy — app không giữ mật khẩu của bạn.
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        {[
                          { op: 'status', label: 'Kiểm tra Browser' },
                          { op: 'setup', label: 'Setup Browser' },
                          { op: 'profiles', label: 'Xem Profiles' },
                          { op: 'stop', label: 'Dừng Browser' },
                        ].map((b) => (
                          <button
                            key={b.op}
                            type="button"
                            disabled={arBusyKey === `browser:${b.op}`}
                            onClick={() => handleAgentReachBrowserOp(b.op)}
                            className="sw-pill-btn px-3 py-1.5 text-xs font-semibold border"
                            style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)', color: 'var(--chu)' }}
                          >
                            {arBusyKey === `browser:${b.op}` ? 'Đang chạy...' : b.label}
                          </button>
                        ))}
                      </div>

                      <div className="pt-3 border-t space-y-2" style={{ borderColor: 'var(--vien-nhe)' }}>
                        <div className="text-xs font-bold flex items-center gap-1.5">
                          <KeyRound className="w-3.5 h-3.5" style={{ color: 'var(--cam)' }} />
                          Cấu hình nhanh Key / Proxy (agent-reach configure)
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <select
                            value={arCfgKey}
                            onChange={(e) => setArCfgKey(e.target.value)}
                            className="sw-input px-3 py-1.5 text-xs"
                          >
                            <option value="openai-key">openai-key</option>
                            <option value="groq-key">groq-key (Whisper)</option>
                            <option value="proxy">proxy (http://...)</option>
                            <option value="github-token">github-token</option>
                            <option value="browser-port">browser-port</option>
                          </select>
                          <input
                            type={arCfgKey.includes('key') || arCfgKey.includes('token') ? 'password' : 'text'}
                            value={arCfgVal}
                            onChange={(e) => setArCfgVal(e.target.value)}
                            placeholder={`Nhập giá trị cho ${arCfgKey}...`}
                            className="sw-input flex-1 min-w-[160px] px-3 py-1.5 text-xs"
                          />
                          <button
                            type="button"
                            disabled={arBusyKey === 'configure'}
                            onClick={handleAgentReachConfigure}
                            className="sw-pill-btn-primary px-4 py-1.5 text-xs"
                          >
                            {arBusyKey === 'configure' ? 'Đang lưu...' : 'Áp dụng'}
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* Concise Architecture Overview */}
                    <div className="sw-card p-5 space-y-2.5 text-xs leading-relaxed">
                      <h2 className="text-sm font-bold flex items-center gap-2">
                        <Cpu className="w-4 h-4" style={{ color: 'var(--cam)' }} />
                        Kiến trúc tích hợp: Agent-Reach → yt-dlp → rea-video → FFmpeg
                      </h2>
                      <p style={{ color: 'var(--mo)' }}>
                        Pipeline mới thay thế module crawl đơn nền tảng bằng{' '}
                        <strong style={{ color: 'var(--la)' }}>Agent-Reach v{arStatus?.version || '1.6.1'}</strong> (đa kênh
                        YT, Bilibili, Xiaohongshu, X, IG, FB, Reddit, TikTok/Douyin/Threads) kết hợp{' '}
                        <strong style={{ color: 'var(--link)' }}>rea-video</strong> bóc shot-by-shot trước khi FFmpeg/Muse AI
                        render biến thể 9:16.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Full-width Agent-Reach Channel & Social Account Login Manager */}
                <div className="sw-card p-5 space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <h2 className="text-sm font-bold flex items-center gap-2">
                        <ShieldCheck className="w-4 h-4" style={{ color: 'var(--la)' }} />
                        Quản lý Kênh &amp; Đăng nhập Tài khoản Social (Agent-Reach Channels)
                      </h2>
                      <p className="text-[11px] mt-0.5" style={{ color: 'var(--mo)' }}>
                        Bật kênh cần quét video viral, mở trình duyệt riêng để đăng nhập từng nền tảng hoặc nhập cookie từ Chrome
                        sẵn có trên máy.
                      </p>
                    </div>
                    <span className="text-[11px] font-semibold" style={{ color: 'var(--mo)' }}>
                      {arStatus ? `${arStatus.channels.length} kênh khả dụng` : 'Đang tải danh sách kênh...'}
                    </span>
                  </div>

                  {arStatus && !arStatus.installed && (
                    <div
                      className="p-3 rounded-2xl border text-xs"
                      style={{ background: 'var(--cam-bg)', borderColor: 'var(--cam)', color: 'var(--cam)' }}
                    >
                      {arStatus.error || 'Chưa phát hiện agent-reach CLI trong PATH.'}
                    </div>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                    {(arStatus?.channels || []).map((ch) => {
                      const isReady = ch.status === 'ok' || ch.status === 'ready';
                      const isDisabled = ch.status === 'off' || ch.status === 'disabled' || ch.status === 'not_added';
                      return (
                        <div
                          key={ch.channel}
                          className="p-3.5 rounded-2xl border flex flex-col justify-between gap-3"
                          style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}
                        >
                          <div className="space-y-1.5">
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <div className="text-xs font-bold flex items-center gap-1.5" style={{ color: 'var(--chu)' }}>
                                  <span>{ch.label || ch.channel}</span>
                                  <span className="text-[10px] font-mono" style={{ color: 'var(--mo)' }}>
                                    ({ch.channel})
                                  </span>
                                </div>
                                <div className="text-[10px]" style={{ color: 'var(--mo)' }}>
                                  {ch.category} · {ch.description}
                                </div>
                              </div>
                              <div className="flex flex-col items-end gap-1 shrink-0">
                                <span
                                  className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase"
                                  style={{
                                    background: isReady
                                      ? 'var(--la-bg)'
                                      : isDisabled
                                      ? 'var(--nen)'
                                      : 'var(--cam-bg)',
                                    color: isReady ? 'var(--la)' : isDisabled ? 'var(--mo)' : 'var(--cam)',
                                  }}
                                >
                                  {ch.status}
                                </span>
                                {ch.supports_login && (
                                  <span
                                    className="px-2 py-0.5 rounded-full text-[10px] font-semibold"
                                    style={{
                                      background: ch.logged_in ? 'var(--xanh-bg)' : 'var(--nen)',
                                      color: ch.logged_in ? 'var(--link)' : 'var(--mo)',
                                    }}
                                  >
                                    {ch.logged_in ? 'Đã đăng nhập' : 'Chưa login'}
                                  </span>
                                )}
                              </div>
                            </div>

                            {ch.hint && (
                              <div className="text-[11px]" style={{ color: 'var(--mo)' }}>
                                {ch.hint}
                              </div>
                            )}

                            {ch.problems && ch.problems.length > 0 && (
                              <div className="text-[10px]" style={{ color: 'var(--cam)' }}>
                                {ch.problems.join(' · ')}
                              </div>
                            )}

                            {ch.actions && ch.actions.length > 0 && (
                              <div className="flex flex-wrap gap-1 pt-0.5">
                                {ch.actions.map((act) => (
                                  <span
                                    key={act}
                                    className="px-1.5 py-0.5 rounded text-[9px] font-mono"
                                    style={{ background: 'var(--nen)', color: 'var(--mo)' }}
                                  >
                                    {act}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>

                          <div className="flex flex-wrap gap-1.5 pt-2 border-t" style={{ borderColor: 'var(--vien-nhe)' }}>
                            <button
                              type="button"
                              disabled={arBusyKey === `${ch.channel}:add`}
                              onClick={() => handleAgentReachChannelOp(ch.channel, 'add')}
                              className="sw-pill-btn px-2.5 py-1 text-[10px] font-bold"
                              style={{ background: 'var(--xanh-bg)', color: 'var(--link)' }}
                            >
                              {arBusyKey === `${ch.channel}:add` ? 'Đang bật...' : '+ Bật kênh'}
                            </button>

                            {ch.supports_login && (
                              <>
                                <button
                                  type="button"
                                  disabled={arBusyKey === `${ch.channel}:login`}
                                  onClick={() => handleAgentReachChannelOp(ch.channel, 'login')}
                                  className="sw-pill-btn px-2.5 py-1 text-[10px] font-bold flex items-center gap-1"
                                  style={{ background: 'var(--la-bg)', color: 'var(--la)' }}
                                >
                                  <LogIn className="w-3 h-3" />
                                  {arBusyKey === `${ch.channel}:login` ? 'Đang mở...' : 'Đăng nhập Browser'}
                                </button>
                                <button
                                  type="button"
                                  disabled={arBusyKey === `${ch.channel}:login_import`}
                                  onClick={() => handleAgentReachChannelOp(ch.channel, 'login_import')}
                                  className="sw-pill-btn px-2.5 py-1 text-[10px] font-semibold border"
                                  style={{ background: 'var(--nen)', borderColor: 'var(--vien-nhe)', color: 'var(--chu)' }}
                                >
                                  {arBusyKey === `${ch.channel}:login_import` ? 'Đang lấy...' : 'Đóng Chrome & Lấy Cookie'}
                                </button>
                                <button
                                  type="button"
                                  disabled={arBusyKey === `${ch.channel}:logout`}
                                  onClick={() => handleAgentReachChannelOp(ch.channel, 'logout')}
                                  className="sw-pill-btn px-2.5 py-1 text-[10px] font-semibold border flex items-center gap-1"
                                  style={{ background: 'var(--nen)', borderColor: 'var(--vien-nhe)', color: 'var(--do)' }}
                                >
                                  <LogOut className="w-3 h-3" />
                                  Đăng xuất
                                </button>
                              </>
                            )}

                            <button
                              type="button"
                              disabled={arBusyKey === `${ch.channel}:check`}
                              onClick={() => handleAgentReachChannelOp(ch.channel, 'check')}
                              className="sw-pill-btn px-2.5 py-1 text-[10px] font-semibold border"
                              style={{ background: 'var(--nen)', borderColor: 'var(--vien-nhe)', color: 'var(--chu)' }}
                            >
                              {arBusyKey === `${ch.channel}:check` ? 'Đang check...' : 'Kiểm tra'}
                            </button>

                            <button
                              type="button"
                              disabled={arBusyKey === `${ch.channel}:remove`}
                              onClick={() => handleAgentReachChannelOp(ch.channel, 'remove')}
                              className="sw-pill-btn px-2.5 py-1 text-[10px] font-semibold border"
                              style={{ background: 'var(--nen)', borderColor: 'var(--vien-nhe)', color: 'var(--mo)' }}
                            >
                              Gỡ kênh
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {arActionOutput && (
                    <div className="space-y-1.5 pt-2">
                      <div className="text-[11px] font-bold flex items-center gap-1.5" style={{ color: 'var(--mo)' }}>
                        <Terminal className="w-3.5 h-3.5" />
                        Log phản hồi Agent-Reach gần nhất
                      </div>
                      <pre
                        className="p-3 rounded-2xl border text-[11px] font-mono overflow-x-auto max-h-48"
                        style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)', color: 'var(--chu)' }}
                      >
                        {arActionOutput}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </main>
      </div>

      {/* ====================================================================
          RIGHT-SIDE SLIDE-OVER ANALYSIS DRAWER (KHUNG PHÂN TÍCH SPYWINADS)
         ==================================================================== */}
      {drawerVideo && (
        <div
          className="fixed inset-0 z-50 flex justify-end"
          style={{ background: 'rgba(0, 0, 0, 0.35)', backdropFilter: 'blur(3px)' }}
          onClick={() => setDrawerVideoId(null)}
        >
          <div
            className="w-full max-w-[470px] h-full overflow-y-auto p-5 flex flex-col justify-between gap-4 border-l"
            style={{
              background: 'var(--nen)',
              borderColor: 'var(--vien-nhe)',
              boxShadow: 'var(--shadow-float)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="space-y-4">
              {/* Drawer Header */}
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className="px-2.5 py-0.5 rounded-full text-[11px] font-bold"
                      style={{
                        background:
                          (PLATFORM_META[drawerVideo.raw.platform] || PLATFORM_META.facebook).pillBg,
                        color:
                          (PLATFORM_META[drawerVideo.raw.platform] || PLATFORM_META.facebook).pillColor,
                      }}
                    >
                      {(PLATFORM_META[drawerVideo.raw.platform] || PLATFORM_META.facebook).label}
                    </span>
                    <span
                      className="px-2.5 py-0.5 rounded-full text-[11px] font-bold"
                      style={{ background: 'var(--la-bg)', color: 'var(--la)' }}
                    >
                      {drawerVideo.categoryLabel}
                    </span>
                  </div>
                  <h2 className="text-base font-bold leading-snug" style={{ color: 'var(--chu)' }}>
                    {drawerVideo.raw.title}
                  </h2>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--mo)' }}>
                    {drawerVideo.raw.author} · {drawerVideo.priceLabel} · {formatCompact(drawerVideo.raw.views)} views
                  </p>
                </div>
                <button
                  onClick={() => setDrawerVideoId(null)}
                  className="p-2 rounded-full border shrink-0"
                  style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)', color: 'var(--mo)' }}
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* LIVE VIDEO PLAYER IN DRAWER (MP4 Stream / Local MP4 / Social Embed) */}
              <div
                className="p-3 rounded-2xl border space-y-2.5"
                style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}
              >
                <div className="flex items-center justify-between gap-2 text-xs">
                  <span className="font-bold flex items-center gap-1.5" style={{ color: 'var(--chu)' }}>
                    <Play className="w-3.5 h-3.5" style={{ color: 'var(--la)' }} />
                    Trình phát Video Sản Phẩm Thực Tế
                  </span>
                  <div className="flex items-center gap-1.5">
                    {!drawerVideo.localMediaUrl && (
                      <button
                        type="button"
                        disabled={ensuringVideoId === drawerVideo.raw.id}
                        onClick={() => handleEnsureVideoMp4(drawerVideo.raw.id)}
                        className="sw-pill-btn px-2.5 py-1 text-[11px] font-semibold flex items-center gap-1"
                        style={{ background: 'var(--xanh-bg)', color: 'var(--link)' }}
                      >
                        <Download className="w-3 h-3" />
                        {ensuringVideoId === drawerVideo.raw.id ? 'Đang nạp MP4...' : 'Nạp & Phát MP4 Gốc'}
                      </button>
                    )}
                    <a
                      href={drawerVideo.raw.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="sw-pill-btn px-2.5 py-1 text-[11px] font-medium border flex items-center gap-1"
                      style={{ background: 'var(--nen)', borderColor: 'var(--vien-nhe)', color: 'var(--mo)' }}
                    >
                      <ExternalLink className="w-3 h-3" />
                      Link gốc
                    </a>
                  </div>
                </div>

                {drawerVideo.localMediaUrl ? (
                  <video
                    key={drawerVideo.localMediaUrl}
                    src={drawerVideo.localMediaUrl}
                    poster={drawerVideo.raw.thumbnail_url || undefined}
                    controls
                    autoPlay
                    playsInline
                    className="w-full max-h-[360px] rounded-xl bg-black object-contain"
                  />
                ) : resolveEmbedUrl(drawerVideo.raw) ? (
                  <div className="w-full rounded-xl overflow-hidden bg-black aspect-[9/16] max-h-[360px]">
                    <iframe
                      key={resolveEmbedUrl(drawerVideo.raw)}
                      src={resolveEmbedUrl(drawerVideo.raw)}
                      title={drawerVideo.raw.title}
                      className="w-full h-full border-0"
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen"
                      allowFullScreen
                    />
                  </div>
                ) : (
                  <div className="relative rounded-xl overflow-hidden bg-black max-h-[280px] flex items-center justify-center">
                    <img
                      src={
                        drawerVideo.raw.thumbnail_url ||
                        'https://images.unsplash.com/photo-1611162617474-5b21e879e113?auto=format&fit=crop&w=600&q=80'
                      }
                      alt={drawerVideo.raw.title}
                      className="w-full max-h-[280px] object-cover opacity-60"
                    />
                    <button
                      type="button"
                      disabled={ensuringVideoId === drawerVideo.raw.id}
                      onClick={() => handleEnsureVideoMp4(drawerVideo.raw.id)}
                      className="absolute sw-pill-btn-primary px-4 py-2.5 text-xs flex items-center gap-2 shadow-lg"
                    >
                      <Play className="w-4 h-4 fill-white" />
                      {ensuringVideoId === drawerVideo.raw.id
                        ? 'Đang tải luồng MP4 bằng yt-dlp...'
                        : 'Bấm để Tải & Phát Video MP4'}
                    </button>
                  </div>
                )}
              </div>

              {/* Quick State Toggles (SpyWinAds Personal Tabs) */}
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => toggleWatchlist(drawerVideo.raw.id)}
                  className="sw-pill-btn px-3 py-1.5 text-xs font-semibold border flex items-center gap-1.5"
                  style={{
                    background: watchlistIds.includes(drawerVideo.raw.id) ? '#fef3c7' : 'var(--xam)',
                    borderColor: 'var(--vien-nhe)',
                    color: watchlistIds.includes(drawerVideo.raw.id) ? '#b45309' : 'var(--chu)',
                  }}
                >
                  <Star
                    className="w-3.5 h-3.5"
                    fill={watchlistIds.includes(drawerVideo.raw.id) ? '#d97706' : 'none'}
                  />
                  {watchlistIds.includes(drawerVideo.raw.id) ? 'Đang theo dõi đặc biệt' : 'Theo dõi đặc biệt'}
                </button>
                <button
                  onClick={() => toggleTestlist(drawerVideo.raw.id)}
                  className="sw-pill-btn px-3 py-1.5 text-xs font-semibold border flex items-center gap-1.5"
                  style={{
                    background: testlistIds.includes(drawerVideo.raw.id) ? 'var(--xanh-bg)' : 'var(--xam)',
                    borderColor: 'var(--vien-nhe)',
                    color: testlistIds.includes(drawerVideo.raw.id) ? 'var(--link)' : 'var(--chu)',
                  }}
                >
                  <FlaskConical className="w-3.5 h-3.5" />
                  {testlistIds.includes(drawerVideo.raw.id) ? 'Đã ở tab Video test' : 'Đưa vào tab Video test'}
                </button>
                <button
                  onClick={() => hideFromTable(drawerVideo.raw.id)}
                  className="sw-pill-btn px-3 py-1.5 text-xs font-medium border flex items-center gap-1"
                  style={{ background: 'var(--nen)', borderColor: 'var(--vien-nhe)', color: 'var(--do)' }}
                >
                  <EyeOff className="w-3.5 h-3.5" />
                  Bỏ khỏi bảng
                </button>
                <button
                  disabled={reaBusyVideoId === drawerVideo.raw.id}
                  onClick={() => handleReaDecompose(drawerVideo.raw.id)}
                  className="sw-pill-btn px-3 py-1.5 text-xs font-semibold border flex items-center gap-1.5"
                  style={{
                    background: drawerVideo.raw.rea_breakdown ? 'var(--la-bg)' : 'var(--xanh-bg)',
                    borderColor: 'var(--vien-nhe)',
                    color: drawerVideo.raw.rea_breakdown ? 'var(--la)' : 'var(--link)',
                  }}
                >
                  <Scissors className="w-3.5 h-3.5" />
                  {reaBusyVideoId === drawerVideo.raw.id
                    ? 'Đang mổ xẻ (rea-video)...'
                    : drawerVideo.raw.rea_breakdown
                    ? `Phân tích lại (${drawerVideo.raw.rea_breakdown.shots_count} shots)`
                    : 'Mổ xẻ Shot-by-Shot (rea-video)'}
                </button>
                {drawerVideo.raw.rea_report_url && (
                  <a
                    href={drawerVideo.raw.rea_report_url}
                    target="_blank"
                    rel="noreferrer"
                    className="sw-pill-btn px-3 py-1.5 text-xs font-semibold border flex items-center gap-1.5"
                    style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)', color: 'var(--chu)' }}
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    Mở Report HTML
                  </a>
                )}
              </div>

              {/* ====================================================================
                  MULTI-PLATFORM POTENTIAL EVALUATION & COMPETITOR SHOPS SPY PANEL
                 ==================================================================== */}
              <div
                className="p-4 rounded-2xl border space-y-3 text-xs"
                style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="font-bold flex items-center gap-1.5" style={{ color: 'var(--chu)' }}>
                    <ShoppingBag className="w-4 h-4" style={{ color: 'var(--la)' }} />
                    Đánh Giá Tiềm Năng &amp; Các Shop Đang Chạy Thực Tế
                  </div>
                  <span
                    className="px-2.5 py-0.5 rounded-full text-[11px] font-bold"
                    style={{
                      background: drawerVideo.potentialTier === 'S' ? 'var(--la-bg)' : 'var(--xanh-bg)',
                      color: drawerVideo.potentialTier === 'S' ? 'var(--la)' : 'var(--link)',
                    }}
                  >
                    Hạng {drawerVideo.potentialTier} · {drawerVideo.potentialScore}/100đ
                  </span>
                </div>

                {drawerVideo.marketIntel?.verdict && (
                  <div
                    className="p-2.5 rounded-xl border font-semibold leading-snug"
                    style={{ background: 'var(--nen)', borderColor: 'var(--vien-nhe)', color: 'var(--chu)' }}
                  >
                    {drawerVideo.marketIntel.verdict}
                  </div>
                )}

                {drawerVideo.marketIntel?.evaluation_reasons &&
                  drawerVideo.marketIntel.evaluation_reasons.length > 0 && (
                    <ul className="list-disc pl-4 space-y-1 text-[11px]" style={{ color: 'var(--mo)' }}>
                      {drawerVideo.marketIntel.evaluation_reasons.map((rsn, idxR) => (
                        <li key={idxR}>{rsn}</li>
                      ))}
                    </ul>
                  )}

                {/* Product Keyword Search / Override for Live Competitor Spy */}
                <div className="pt-1 space-y-1.5">
                  <label className="block text-[11px] font-semibold" style={{ color: 'var(--mo)' }}>
                    Từ khoá sản phẩm dò Shop &amp; Ads (tự nhận diện hoặc nhập tên SP cụ thể):
                  </label>
                  <div className="flex gap-2">
                    <input
                      value={customSpyQuery}
                      onChange={(e) => setCustomSpyQuery(e.target.value)}
                      placeholder="VD: dây chuyền bạc, christmas lights, ergonomic chair..."
                      className="sw-input flex-1 px-3 py-1.5 text-xs"
                    />
                    <button
                      type="button"
                      disabled={spyingVideoId === drawerVideo.raw.id}
                      onClick={() => handleEvaluateSingleVideo(drawerVideo.raw.id, customSpyQuery)}
                      className="sw-pill-btn-primary px-3.5 py-1.5 text-xs font-semibold flex items-center gap-1.5 shrink-0"
                    >
                      <Search className="w-3.5 h-3.5" />
                      {spyingVideoId === drawerVideo.raw.id ? 'Đang dò Shop...' : 'Dò Shop & Giá'}
                    </button>
                  </div>
                </div>

                {/* Summary Strip: Active Shops | Total Ads | Selling Price */}
                <div className="grid grid-cols-3 gap-2 pt-1">
                  <div className="p-2.5 rounded-xl text-center" style={{ background: 'var(--nen)' }}>
                    <div className="text-[10px]" style={{ color: 'var(--mo)' }}>
                      Shop đang chạy
                    </div>
                    <div className="text-base font-bold mt-0.5" style={{ color: 'var(--chu)' }}>
                      {drawerVideo.shopActive} shop
                    </div>
                  </div>
                  <div className="p-2.5 rounded-xl text-center" style={{ background: 'var(--nen)' }}>
                    <div className="text-[10px]" style={{ color: 'var(--mo)' }}>
                      Số lượng Ads
                    </div>
                    <div className="text-base font-bold mt-0.5" style={{ color: 'var(--xanh)' }}>
                      {drawerVideo.totalAdsSameVideo} QC
                    </div>
                  </div>
                  <div className="p-2.5 rounded-xl text-center" style={{ background: 'var(--nen)' }}>
                    <div className="text-[10px]" style={{ color: 'var(--mo)' }}>
                      Giá đang bán
                    </div>
                    <div className="text-xs font-bold mt-1 truncate" style={{ color: 'var(--la)' }}>
                      {drawerVideo.priceLabel}
                    </div>
                  </div>
                </div>

                {/* Detailed List of Discovered Competitor Shops */}
                {drawerVideo.shops.length > 0 ? (
                  <div className="space-y-2 pt-1">
                    <div className="text-[11px] font-bold" style={{ color: 'var(--chu)' }}>
                      Danh sách các Shop đang bán ({drawerVideo.shops.length} shop):
                    </div>
                    <div className="space-y-2 max-h-[290px] overflow-y-auto pr-1">
                      {drawerVideo.shops.map((sh, sIdx) => (
                        <div
                          key={sIdx}
                          className="p-3 rounded-xl border space-y-1.5"
                          style={{ background: 'var(--nen)', borderColor: 'var(--vien-nhe)' }}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <div className="font-bold text-xs truncate" style={{ color: 'var(--chu)' }}>
                                {sh.shop_name}
                              </div>
                              {sh.product_title && (
                                <div className="text-[11px] truncate" style={{ color: 'var(--mo)' }}>
                                  SP: {sh.product_title}
                                </div>
                              )}
                            </div>
                            <span
                              className="px-2 py-0.5 rounded-full text-[10px] font-semibold shrink-0"
                              style={{ background: 'var(--xam)', color: 'var(--mo)' }}
                            >
                              {sh.source}
                            </span>
                          </div>

                          <div className="flex flex-wrap items-center justify-between gap-2 pt-0.5">
                            <div className="flex items-center gap-2">
                              <span
                                className="font-bold text-xs"
                                style={{ color: sh.selling_price ? 'var(--la)' : 'var(--mo2)' }}
                              >
                                {sh.selling_price || 'Xem giá trên trang'}
                              </span>
                              {sh.original_price && (
                                <span className="text-[11px] line-through" style={{ color: 'var(--mo2)' }}>
                                  {sh.original_price}
                                </span>
                              )}
                              {sh.ads_count > 0 && (
                                <span
                                  className="px-2 py-0.5 rounded-full text-[10px] font-bold"
                                  style={{ background: 'var(--xanh-bg)', color: 'var(--link)' }}
                                >
                                  {sh.ads_count} QC đang chạy
                                </span>
                              )}
                            </div>

                            <div className="flex flex-wrap items-center gap-1.5">
                              {(sh.page_id || sh.shop_name) && (
                                <button
                                  type="button"
                                  onClick={() =>
                                    handleInspectMetaShopProducts({
                                      page_id: sh.page_id || '',
                                      shop_name: sh.shop_name,
                                    })
                                  }
                                  className="px-2 py-1 rounded-lg text-[10px] font-bold border flex items-center gap-1 hover:opacity-90"
                                  style={{ background: 'var(--nen)', borderColor: 'var(--vien)', color: 'var(--chu)' }}
                                  title="Xem tất cả sản phẩm mà Shop này đang chạy Ads bán"
                                >
                                  Kệ SP Shop
                                </button>
                              )}
                              {sh.ad_library_url && (
                                <a
                                  href={sh.ad_library_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="px-2 py-1 rounded-lg text-[10px] font-semibold border flex items-center gap-1 hover:underline"
                                  style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)', color: 'var(--link)' }}
                                >
                                  Xem Ads
                                  <ExternalLink className="w-2.5 h-2.5" />
                                </a>
                              )}
                              {sh.product_url && (
                                <>
                                  <a
                                    href={sh.product_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="px-2.5 py-1 rounded-lg text-[10px] font-bold flex items-center gap-1 hover:opacity-90"
                                    style={{ background: 'var(--xanh-bg)', color: 'var(--link)' }}
                                    title={sh.product_url}
                                  >
                                    <Link2 className="w-3 h-3" />
                                    Link SP
                                    <ExternalLink className="w-2.5 h-2.5" />
                                  </a>
                                  <button
                                    type="button"
                                    onClick={() => {
                                      navigator.clipboard.writeText(sh.product_url || '');
                                      notify('Đã copy Link Sản Phẩm!');
                                    }}
                                    className="p-1 rounded-lg border"
                                    style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)', color: 'var(--mo)' }}
                                    title="Copy link sản phẩm"
                                  >
                                    <ClipboardCopy className="w-3 h-3" />
                                  </button>
                                </>
                              )}
                              {sh.shop_url ? (
                                <>
                                  <a
                                    href={sh.shop_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="px-2.5 py-1 rounded-lg text-[10px] font-bold flex items-center gap-1 hover:opacity-90"
                                    style={{ background: 'var(--la-bg)', color: 'var(--la)' }}
                                    title={sh.shop_url}
                                  >
                                    <ShoppingBag className="w-3 h-3" />
                                    Link Shop
                                    <ExternalLink className="w-2.5 h-2.5" />
                                  </a>
                                  <button
                                    type="button"
                                    onClick={() => {
                                      navigator.clipboard.writeText(sh.shop_url);
                                      notify(`Đã copy link shop: ${sh.domain}`);
                                    }}
                                    className="p-1 rounded-lg border"
                                    style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)', color: 'var(--mo)' }}
                                    title="Copy link shop đang bán"
                                  >
                                    <ClipboardCopy className="w-3 h-3" />
                                  </button>
                                </>
                              ) : sh.page_url ? (
                                <a
                                  href={sh.page_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="px-2.5 py-1 rounded-lg text-[10px] font-semibold border flex items-center gap-1"
                                  style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)', color: 'var(--chu)' }}
                                >
                                  Mở Fanpage
                                  <ExternalLink className="w-2.5 h-2.5" />
                                </a>
                              ) : null}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div
                    className="p-3 rounded-xl border text-[11px] leading-relaxed"
                    style={{ background: 'var(--nen)', borderColor: 'var(--vien-nhe)', color: 'var(--mo)' }}
                  >
                    Chưa có danh sách shop đối thủ cho video này. Bấm nút <strong>&ldquo;Dò Shop &amp; Giá&rdquo;</strong> ở trên để hệ thống tự động tìm các shop đang chạy quảng cáo, bóc tách link trang bán, số lượng QC và giá thực tế.
                  </div>
                )}
              </div>

              {/* 3 Core Velocity & Ad Age Metrics */}
              <div className="grid grid-cols-3 gap-2.5">
                <div className="p-3 rounded-2xl text-center" style={{ background: 'var(--la-bg)' }}>
                  <div className="text-[11px] font-medium" style={{ color: 'var(--la)' }}>
                    Tốc độ View/ngày
                  </div>
                  <div className="text-xl font-bold mt-0.5" style={{ color: 'var(--la)' }}>
                    {formatCompact(drawerVideo.velocityViewsPerDay)}
                  </div>
                </div>
                <div className="p-3 rounded-2xl text-center" style={{ background: 'var(--xanh-bg)' }}>
                  <div className="text-[11px] font-medium" style={{ color: 'var(--link)' }}>
                    Tương tác thực
                  </div>
                  <div className="text-xl font-bold mt-0.5" style={{ color: 'var(--xanh)' }}>
                    {drawerVideo.engagementRate}%
                  </div>
                </div>
                <div className="p-3 rounded-2xl text-center" style={{ background: 'var(--xam)' }}>
                  <div className="text-[11px] font-medium" style={{ color: 'var(--mo)' }}>
                    Tuổi Video
                  </div>
                  <div className="text-xl font-bold mt-0.5" style={{ color: 'var(--chu)' }}>
                    {drawerVideo.videoAgeDays} ngày
                  </div>
                </div>
              </div>

              {/* Tuổi Video vs Tuổi Trang Bán Diagnosis */}
              <div
                className="p-3.5 rounded-2xl border space-y-1.5 text-xs"
                style={{
                  background: drawerVideo.isOldStoreWarning ? 'var(--cam-bg)' : 'var(--xam)',
                  borderColor: 'var(--vien-nhe)',
                }}
              >
                <div className="flex items-center justify-between font-bold">
                  <span>Tuổi file video: {drawerVideo.videoAgeDays} ngày</span>
                  <span style={{ color: drawerVideo.isOldStoreWarning ? 'var(--cam)' : 'var(--la)' }}>
                    Tuổi trang bán: {drawerVideo.storeAgeDays} ngày
                  </span>
                </div>
                <p style={{ color: 'var(--mo)' }}>
                  {drawerVideo.isOldStoreWarning
                    ? 'Cảnh báo: Trang bán đã hoạt động lâu ngày re-upload creative. Nên đổi mạnh Hook 3s đầu khi Clone bằng Muse AI.'
                    : 'Tín hiệu tốt: Cả file video và trang bán đều mới, khả năng cao đây là sản phẩm Win mới lên.'}
                </p>
              </div>

              {/* 14-day Momentum Sparkline */}
              <div className="p-4 rounded-2xl border space-y-2" style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}>
                <div className="flex items-center justify-between text-xs font-semibold">
                  <span>Động lượng quảng cáo 14 ngày qua</span>
                  <span style={{ color: 'var(--link)' }}>
                    {drawerVideo.shopActive}/{drawerVideo.shopTotal} shop · {drawerVideo.fanpageActive}/
                    {drawerVideo.fanpageTotal} page
                  </span>
                </div>
                <Sparkline bars={drawerVideo.sparkline14d} tall />
              </div>

              {/* AI Hook & Script 3-Part Breakdown */}
              <div className="space-y-2.5 text-xs">
                <div className="p-3.5 rounded-2xl border space-y-1.5" style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}>
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-bold flex items-center gap-1.5" style={{ color: 'var(--link)' }}>
                      <Zap className="w-3.5 h-3.5" />
                      Hook 3 giây đầu &amp; Góc đánh tâm lý
                    </div>
                    <button
                      type="button"
                      disabled={analyzingAiVideoId === drawerVideo.raw.id}
                      onClick={() => handleAnalyzeVideoAi(drawerVideo.raw.id)}
                      className="sw-pill-btn px-2.5 py-0.5 text-[10px] font-bold border flex items-center gap-1"
                      style={{ background: 'var(--nen)', borderColor: 'var(--vien-nhe)', color: 'var(--chu)' }}
                    >
                      <Sparkles className="w-3 h-3" style={{ color: 'var(--cam)' }} />
                      {analyzingAiVideoId === drawerVideo.raw.id ? 'AI đang phân tích...' : 'Phân tích sâu bằng AI'}
                    </button>
                  </div>
                  <p className="whitespace-pre-line leading-relaxed" style={{ color: 'var(--chu)' }}>
                    {drawerVideo.raw.hook_text || drawerVideo.raw.caption}
                  </p>
                </div>

                {drawerVideo.raw.script_summary && (
                  <div
                    className="p-3.5 rounded-2xl border space-y-1.5"
                    style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}
                  >
                    <div className="font-bold flex items-center gap-1.5" style={{ color: 'var(--chu)' }}>
                      <MessageSquare className="w-3.5 h-3.5" />
                      Phân tích Kịch bản &amp; USP Thực tế của Video này
                    </div>
                    <p className="whitespace-pre-line leading-relaxed" style={{ color: 'var(--mo)' }}>
                      {drawerVideo.raw.script_summary}
                    </p>
                  </div>
                )}

                <div className="p-3.5 rounded-2xl border space-y-1" style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}>
                  <div className="font-bold text-[11px]" style={{ color: 'var(--mo)' }}>
                    Nội dung bài viết / Quảng cáo gốc:
                  </div>
                  <p className="whitespace-pre-line text-[11px] max-h-36 overflow-y-auto leading-relaxed" style={{ color: 'var(--chu)' }}>
                    {drawerVideo.raw.caption}
                  </p>
                </div>

                <div className="flex flex-wrap gap-1.5">
                  {drawerVideo.raw.sales_signals.map((sig, i) => (
                    <span
                      key={i}
                      className="px-2.5 py-1 rounded-full text-[11px] font-medium"
                      style={{ background: 'var(--la-bg)', color: 'var(--la)' }}
                    >
                      {sig}
                    </span>
                  ))}
                </div>

                {drawerVideo.raw.rea_breakdown && (() => {
                  const bd = drawerVideo.raw.rea_breakdown;
                  const reportHref = drawerVideo.raw.rea_report_url || bd.report_url;
                  return (
                    <div
                      className="p-3.5 rounded-2xl border space-y-3"
                      style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="font-bold flex items-center gap-1.5" style={{ color: 'var(--chu)' }}>
                          <Film className="w-3.5 h-3.5" style={{ color: 'var(--link)' }} />
                          rea-video Shot-by-Shot Forensics
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span
                            className="px-2 py-0.5 rounded-full text-[10px] font-bold"
                            style={{ background: 'var(--xanh-bg)', color: 'var(--link)' }}
                          >
                            {bd.shots_count} shots · {bd.duration.toFixed(1)}s
                          </span>
                          {reportHref && (
                            <a
                              href={reportHref}
                              target="_blank"
                              rel="noreferrer"
                              className="px-2 py-0.5 rounded-full text-[10px] font-bold flex items-center gap-1"
                              style={{ background: 'var(--nen)', color: 'var(--chu)' }}
                            >
                              <ExternalLink className="w-3 h-3" />
                              report.html
                            </a>
                          )}
                        </div>
                      </div>

                      <div className="text-[11px] space-y-1">
                        <div className="font-semibold" style={{ color: 'var(--chu)' }}>
                          Verdict: {bd.verdict || 'Đã tách shot'}
                        </div>
                        <div style={{ color: 'var(--mo)' }}>
                          Avg shot: {bd.avg_shot_s.toFixed(2)}s · Confidence: {(bd.confidence * 100).toFixed(0)}%
                          {bd.vlm_note ? ` · ${bd.vlm_note}` : ''}
                        </div>
                        {bd.source_note && (
                          <div className="text-[10px]" style={{ color: 'var(--mo)' }}>
                            {bd.source_note}
                          </div>
                        )}
                      </div>

                      {bd.production_mix && bd.production_mix.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {bd.production_mix.map((pm, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-0.5 rounded-full text-[10px] font-semibold"
                              style={{ background: 'var(--nen)', color: 'var(--chu)' }}
                            >
                              {pm.label}: {(pm.ratio * 100).toFixed(0)}% ({pm.seconds.toFixed(1)}s)
                            </span>
                          ))}
                        </div>
                      )}

                      {bd.storyboard_url && (
                        <a href={reportHref || bd.storyboard_url} target="_blank" rel="noreferrer" className="block">
                          <img
                            src={bd.storyboard_url}
                            alt="rea-video storyboard"
                            className="w-full rounded-xl border object-cover max-h-48"
                            style={{ borderColor: 'var(--vien-nhe)' }}
                          />
                        </a>
                      )}

                      {bd.shots && bd.shots.length > 0 && (
                        <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1">
                          {bd.shots.map((s) => (
                            <div
                              key={s.index}
                              className="p-2 rounded-xl border flex gap-2.5 items-start"
                              style={{ background: 'var(--nen)', borderColor: 'var(--vien-nhe)' }}
                            >
                              {s.thumb_url && (
                                <img
                                  src={s.thumb_url}
                                  alt={`Shot ${s.index}`}
                                  className="w-14 h-14 rounded-lg object-cover shrink-0 border"
                                  style={{ borderColor: 'var(--vien-nhe)' }}
                                />
                              )}
                              <div className="min-w-0 flex-1 space-y-0.5">
                                <div className="flex flex-wrap items-center justify-between gap-1 text-[10px]">
                                  <span className="font-bold" style={{ color: 'var(--chu)' }}>
                                    #{s.index} · {s.start.toFixed(1)}s–{s.end.toFixed(1)}s ({s.label})
                                  </span>
                                  <span
                                    className="px-1.5 py-0.5 rounded font-semibold"
                                    style={{ background: 'var(--cam-bg)', color: 'var(--cam)' }}
                                  >
                                    {s.remake_route}
                                  </span>
                                </div>
                                <p className="text-[11px] leading-snug line-clamp-2" style={{ color: 'var(--mo)' }}>
                                  {s.prompt || s.verdict || bd.verdict}
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                        {bd.remake_md_excerpt && (
                          <span className="text-[10px] truncate flex-1" style={{ color: 'var(--mo)' }}>
                            {bd.remake_md_excerpt.split('\n')[0]}
                          </span>
                        )}
                        <button
                          type="button"
                          onClick={() => {
                            const shotLines = (bd.shots || [])
                              .slice(0, 5)
                              .map(
                                (s) =>
                                  `[${s.start.toFixed(1)}s-${s.end.toFixed(1)}s ${s.label} · ${s.remake_route}] ${
                                    s.prompt || bd.verdict
                                  }`
                              )
                              .join('\n');
                            setCloneMode('rea_video_remake');
                            handleSelectForClone(drawerVideo.raw);
                            if (shotLines) setPromptScript(shotLines);
                          }}
                          className="sw-pill-btn px-3 py-1.5 text-[11px] font-bold flex items-center gap-1"
                          style={{ background: 'var(--xanh-bg)', color: 'var(--link)' }}
                        >
                          <Scissors className="w-3 h-3" />
                          Clone theo Shot-by-Shot
                        </button>
                      </div>
                    </div>
                  );
                })()}
              </div>
            </div>

            {/* Drawer Footer CTAs */}
            <div className="pt-4 border-t flex items-center gap-2" style={{ borderColor: 'var(--vien-nhe)' }}>
              <button
                onClick={() => handleDownloadVideoSource(drawerVideo.raw)}
                className="sw-pill-btn px-4 py-2.5 text-xs font-semibold border flex items-center gap-1.5"
                style={{ background: 'var(--xam)', borderColor: 'var(--vien)', color: 'var(--chu)' }}
              >
                <Download className="w-3.5 h-3.5" />
                Tải MP4
              </button>
              <a
                href={drawerVideo.raw.source_url}
                target="_blank"
                rel="noreferrer"
                className="sw-pill-btn p-2.5 border"
                style={{ background: 'var(--nen)', borderColor: 'var(--vien)', color: 'var(--mo)' }}
                title="Mở link gốc"
              >
                <ExternalLink className="w-4 h-4" />
              </a>
              <button
                onClick={() => handleSelectForFlowClone(drawerVideo.raw)}
                className="sw-pill-btn py-2.5 px-3.5 text-xs font-semibold border flex items-center justify-center gap-1.5"
                style={{ background: 'var(--la-bg)', borderColor: 'transparent', color: 'var(--la)' }}
              >
                <Film className="w-4 h-4" />
                Clone Google Flow
              </button>
              <button
                onClick={() => handleSelectForClone(drawerVideo.raw)}
                className="sw-pill-btn-primary flex-1 py-2.5 px-4 text-xs flex items-center justify-center gap-1.5"
              >
                <Sparkles className="w-4 h-4" />
                Clone Muse AI
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ====================================================================
          GOOGLE FLOW (flow.google.com) BULK ACCOUNT IMPORT MODAL
         ==================================================================== */}
      {showFlowImportModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0, 0, 0, 0.5)', backdropFilter: 'blur(4px)' }}
          onClick={() => setShowFlowImportModal(false)}
        >
          <div
            className="sw-card max-w-2xl w-full p-5 space-y-4 max-h-[85vh] overflow-y-auto"
            style={{ boxShadow: 'var(--shadow-float)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold flex items-center gap-2">
                <Film className="w-4 h-4" style={{ color: 'var(--la)' }} />
                Nhập Tài Khoản Google Flow (flow.google.com)
              </h3>
              <button
                onClick={() => setShowFlowImportModal(false)}
                className="p-1.5 rounded-full"
                style={{ background: 'var(--xam)', color: 'var(--mo)' }}
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div
              className="p-3 rounded-xl border text-[11px] space-y-1 leading-relaxed"
              style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)', color: 'var(--mo)' }}
            >
              <div className="font-bold" style={{ color: 'var(--chu)' }}>
                Hỗ trợ tự động nhận diện cả 4 định dạng tài khoản Flow:
              </div>
              <div>• <strong>Cookie JSON</strong> xuất từ tiện ích Cookie-Editor / EditThisCookie trên <code>flow.google.com</code></div>
              <div>• <strong>Dòng hàng loạt</strong>: <code>email@gmail.com | SID=...; HSID=...; SAPISID=... | http://proxy:port</code></div>
              <div>• <strong>OAuth Bearer Token</strong>: <code>TenAcc | ya29.a0AfH6SM... | https://flow.google.com/project/...</code></div>
              <div>• <strong>Gemini Veo API Key</strong>: <code>TenAcc | AIzaSy...</code></div>
            </div>

            <div className="space-y-2">
              <textarea
                rows={6}
                value={flowBulkText}
                onChange={(e) => setFlowBulkText(e.target.value)}
                placeholder="Dán mảng JSON Cookie [...], file Netscape cookies.txt, hoặc danh sách Email|Cookie/Token|Proxy vào đây..."
                className="sw-input w-full p-3 text-xs font-mono"
              />
              <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                <div className="flex flex-wrap items-center gap-3">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs" style={{ color: 'var(--mo)' }}>
                      Gói Acc:
                    </span>
                    <select
                      value={flowBulkTier}
                      onChange={(e) => setFlowBulkTier(e.target.value)}
                      className="sw-input px-2.5 py-1 text-xs"
                    >
                      <option value="Flow Free">Flow Free (50 credits/ngày · OmniFlash ≤10s &amp; Veo 3.1 Lite)</option>
                      <option value="Flow Plus">Google AI Plus (Flow · 200 credits/tháng)</option>
                      <option value="Flow Pro">Google AI Pro (Flow · 1,000 credits/tháng)</option>
                      <option value="Flow Ultra">Google AI Ultra (Flow · 25,000 credits/tháng)</option>
                      <option value="Gemini Veo API">Gemini Veo / Omni API Key</option>
                    </select>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs" style={{ color: 'var(--mo)' }}>
                      Giới hạn lượt/tuần:
                    </span>
                    <input
                      type="number"
                      value={flowBulkLimit}
                      onChange={(e) => setFlowBulkLimit(Number(e.target.value) || 50)}
                      className="sw-input w-20 px-2.5 py-1 text-xs"
                    />
                  </div>
                </div>
                <button onClick={handleFlowBulkImport} className="sw-pill-btn-primary px-4 py-2 text-xs font-semibold">
                  Nạp Vào Kho Google Flow
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ====================================================================
          BULK MUSE 1-BILLION-TOKEN MODAL
         ==================================================================== */}
      {showBulkModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0, 0, 0, 0.5)', backdropFilter: 'blur(4px)' }}
          onClick={() => setShowBulkModal(false)}
        >
          <div
            className="sw-card max-w-2xl w-full p-5 space-y-4 max-h-[85vh] overflow-y-auto"
            style={{ boxShadow: 'var(--shadow-float)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold flex items-center gap-2">
                <KeyRound className="w-4 h-4" style={{ color: 'var(--cam)' }} />
                Kho Token Muse AI (Hỗ trợ Pool 1 Tỷ Token & Auto-Rotate)
              </h3>
              <button
                onClick={() => setShowBulkModal(false)}
                className="p-1.5 rounded-full"
                style={{ background: 'var(--xam)', color: 'var(--mo)' }}
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2">
              <label className="block text-xs" style={{ color: 'var(--mo)' }}>
                Dán danh sách token hàng loạt (<code>TenAcc|Token|Proxy</code> hoặc chỉ <code>Token</code>):
              </label>
              <textarea
                rows={4}
                value={bulkTokenText}
                onChange={(e) => setBulkTokenText(e.target.value)}
                className="sw-input w-full p-3 text-xs font-mono"
              />
              <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs" style={{ color: 'var(--mo)' }}>
                    Hạn mức tuần/acc:
                  </span>
                  <input
                    type="number"
                    value={bulkWeeklyLimit}
                    onChange={(e) => setBulkWeeklyLimit(Number(e.target.value) || 50)}
                    className="sw-input w-20 px-2.5 py-1 text-xs"
                  />
                </div>
                <button onClick={handleBulkImport} className="sw-pill-btn-primary px-4 py-2 text-xs">
                  Nạp Hàng Loạt Vào Pool
                </button>
              </div>
            </div>

            {/* Active Token List */}
            <div className="space-y-2 pt-2 border-t" style={{ borderColor: 'var(--vien-nhe)' }}>
              <div className="text-xs font-bold" style={{ color: 'var(--chu)' }}>
                Danh sách tài khoản Muse đang quản lý ({tokens.length})
              </div>
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {tokens.map((t) => (
                  <div
                    key={t.id}
                    className="p-2.5 rounded-2xl border flex items-center justify-between gap-2 text-xs"
                    style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}
                  >
                    <div className="min-w-0">
                      <div className="font-bold truncate">{t.label}</div>
                      <div className="text-[11px] truncate" style={{ color: 'var(--mo)' }}>
                        {t.auth_token_masked} · Còn {formatCompact(t.tokens_remaining)} tokens · {t.weekly_used}/
                        {t.weekly_limit} tuần
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <button
                        onClick={() => api.toggleMuseToken(t.id).then(refreshAll)}
                        className="sw-pill-btn px-2.5 py-1 text-[10px] font-bold"
                        style={{
                          background: t.status === 'active' ? 'var(--la-bg)' : 'var(--o)',
                          color: t.status === 'active' ? 'var(--la)' : 'var(--mo)',
                        }}
                      >
                        {t.status}
                      </button>
                      <button
                        onClick={() => api.deleteMuseToken(t.id).then(refreshAll)}
                        className="p-1.5 rounded-full"
                        style={{ background: 'var(--do-bg)', color: 'var(--do)' }}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
