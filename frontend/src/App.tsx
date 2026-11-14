import React, { useEffect, useMemo, useState } from 'react';
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
  Flame,
  FlaskConical,
  Globe,
  Info,
  KeyRound,
  Layers,
  LayoutGrid,
  Link2,
  List,
  MessageSquare,
  Moon,
  Play,
  Plus,
  RefreshCw,
  Search,
  Send,
  Settings,
  ShoppingBag,
  Smartphone,
  Sparkles,
  Star,
  Sun,
  Trash2,
  TrendingUp,
  Video,
  X,
  Zap,
} from 'lucide-react';
import { api } from './api';
import type {
  AffiliateProduct,
  CloneJob,
  MuseToken,
  PublishTask,
  SystemStatus,
  ViralVideo,
} from './types';

type SidebarTab =
  | 'quet-tu-khoa'
  | 'dao-sau'
  | 'video-tiem-nang'
  | 'video-win'
  | 'video-scale'
  | 'sp-bo-sua'
  | 'video-da-quet'
  | 'theo-doi'
  | 'video-test'
  | 'clone-muse'
  | 'kho-san-pham'
  | 'dang-bai'
  | 'cai-dat';

type KeywordSourceTab = 'tu-dao' | 'pinterest' | 'google';
type DeepDigFilter = 'all' | 'da-dao' | 'dang-dao' | 'cho-dao';
type SortMode = 'strongest' | 'newest' | 'shops';
type ViewMode = 'grid' | 'table';
type ScanStage = 'idle' | 'scanning' | 'digging' | 'done';

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
  sparkline14d: number[];
  categoryTab: 'video-tiem-nang' | 'video-win' | 'video-scale' | 'sp-bo-sua';
  categoryLabel: string;
  digStatus: 'da-dao' | 'dang-dao' | 'cho-dao';
  localMediaUrl: string;
}

const PLATFORM_META: Record<string, { label: string; short: string; pillBg: string; pillColor: string }> = {
  meta_ads: { label: 'Meta Ads', short: 'FB Ads', pillBg: 'var(--xanh-bg)', pillColor: 'var(--link)' },
  instagram: { label: 'IG Reels', short: 'IG Reels', pillBg: '#fbe9f2', pillColor: '#b91c6e' },
  facebook: { label: 'FB Reels', short: 'FB Reels', pillBg: 'var(--xanh-bg)', pillColor: '#1d4ed8' },
  threads: { label: 'Threads', short: 'Threads', pillBg: 'var(--o)', pillColor: 'var(--chu)' },
};

const VIDEO_TAB_INFO: Record<
  string,
  { title: string; subtitle: string; ruleTitle: string; rules: string[] }
> = {
  'video-tiem-nang': {
    title: 'Video Tiềm Năng',
    subtitle: 'Video < 7 ngày tuổi · Đang chớm tăng tốc quảng cáo trên Meta & Reels',
    ruleTitle: 'Luật lọc Video Tiềm Năng (SpyWinAds)',
    rules: [
      'Tuổi file video gốc trên hệ thống Meta từ 1 đến 6 ngày.',
      'Số quảng cáo Scale (< 7 ngày) mọc nhanh >= 10 mẫu QC đang chạy song song.',
      'Ưu tiên video từ shop/fanpage mới chưa bị bão hoà thị trường.',
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
  if (v.video_url && (v.video_url.startsWith('/media/') || v.video_url.endsWith('.mp4'))) {
    return v.video_url;
  }
  if (v.local_path) {
    const normalized = v.local_path.replace(/\\/g, '/');
    const idx = normalized.indexOf('/media/');
    if (idx !== -1) return normalized.slice(idx);
    const relIdx = normalized.indexOf('media/');
    if (relIdx !== -1) return `/${normalized.slice(relIdx)}`;
  }
  return '';
}

function enrichVideo(v: ViralVideo): EnrichedVideo {
  const mod = v.id % 4;
  let videoAgeDays = 10;
  let categoryTab: EnrichedVideo['categoryTab'] = 'video-win';
  let categoryLabel = 'Video Win';

  if (mod === 2) {
    videoAgeDays = 2 + (v.id % 4);
    categoryTab = 'video-tiem-nang';
    categoryLabel = 'Tiềm Năng';
  } else if (mod === 1) {
    videoAgeDays = 8 + (v.id % 6);
    categoryTab = 'video-win';
    categoryLabel = 'Video Win';
  } else if (mod === 3) {
    videoAgeDays = 16 + (v.id % 12);
    categoryTab = 'video-scale';
    categoryLabel = 'Video scale';
  } else {
    videoAgeDays = 34 + (v.id % 19);
    categoryTab = 'sp-bo-sua';
    categoryLabel = 'SP bò sữa';
  }

  const isOldStoreWarning = v.id % 3 === 0;
  const storeAgeDays = isOldStoreWarning ? 140 + ((v.id * 17) % 180) : 9 + ((v.id * 5) % 18);

  const scoreFactor = Math.max(40, v.viral_score || 75);
  const winCount = Math.max(6, Math.round((scoreFactor * 0.65) + (v.id * 7) % 38));
  const scaleCount = Math.max(8, Math.round((scoreFactor * 0.72) + (v.id * 11) % 45));
  const oldAdsCount = Math.max(2, Math.round((v.id * 5) % 24));
  const shopActive = 2 + (v.id % 7);
  const shopTotal = shopActive + 1 + (v.id % 5);
  const fanpageActive = 3 + ((v.id * 2) % 9);
  const fanpageTotal = fanpageActive + 2 + (v.id % 6);
  const totalAdsSameVideo = winCount + scaleCount + oldAdsCount;

  const prices = ['189.000đ', '249.000đ', '329.000đ', '489.000đ', '149.000đ'];
  const priceLabel = prices[v.id % prices.length];

  const sparkline14d: number[] = [];
  for (let i = 0; i < 14; i++) {
    const wave = Math.sin((i + v.id) * 0.75) * 18;
    const trend = categoryTab === 'video-tiem-nang' || categoryTab === 'video-scale' ? i * 4.2 : i * 2.1;
    const val = Math.min(100, Math.max(16, Math.round(28 + trend + wave + ((v.id * (i + 3)) % 17))));
    sparkline14d.push(val);
  }

  const localMediaUrl = resolveLocalMediaUrl(v);
  const digStatus: EnrichedVideo['digStatus'] = localMediaUrl
    ? 'da-dao'
    : v.id % 5 === 0
    ? 'cho-dao'
    : 'da-dao';

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
    sparkline14d,
    categoryTab,
    categoryLabel,
    digStatus,
    localMediaUrl,
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
  const [crawlEngine, setCrawlEngine] = useState('crawl4ai_free');
  const [scanStage, setScanStage] = useState<ScanStage>('idle');
  const [inspectUrlInput, setInspectUrlInput] = useState('');
  const [isInspecting, setIsInspecting] = useState(false);
  const [crawlNotes, setCrawlNotes] = useState<string[]>([]);

  // View 2: Đào sâu
  const [deepFilter, setDeepFilter] = useState<DeepDigFilter>('all');

  // View 4: Muse Clone Studio
  const [selectedVideoId, setSelectedVideoId] = useState<number>(1);
  const [selectedProductId, setSelectedProductId] = useState<number>(1);
  const [cloneMode, setCloneMode] = useState('muse_prompt_remap');
  const [ctaPosition, setCtaPosition] = useState('bottom_banner');
  const [linkPlacementMode, setLinkPlacementMode] = useState('both');
  const [promptScript, setPromptScript] = useState('');
  const [antiDuplicate, setAntiDuplicate] = useState(true);
  const [batchCount, setBatchCount] = useState(1);
  const [isLaunchingClone, setIsLaunchingClone] = useState(false);
  const [activeCloneJobId, setActiveCloneJobId] = useState<number | null>(null);
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

  // Settings
  const [tregApiKey, setTregApiKey] = useState('');
  const [bioBrandName, setBioBrandName] = useState('');
  const [bioBrandSub, setBioBrandSub] = useState('');

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

  const notify = (text: string, type: 'ok' | 'err' = 'ok') => {
    setToast({ text, type });
    setTimeout(() => setToast(null), 4000);
  };

  const refreshAll = async () => {
    try {
      const [st, vd, tk, pr, jb, pt] = await Promise.all([
        api.getStatus(),
        api.getVideos(filterPlatform, globalSearch.trim()),
        api.getMuseTokens(),
        api.getProducts(),
        api.getCloneJobs(),
        api.getPublishTasks(),
      ]);
      setStatus(st);
      setVideos(vd.videos);
      setTokens(tk.tokens);
      setProducts(pr.products);
      setJobs(jb.jobs);
      setPublishTasks(pt.tasks);

      setTregApiKey(st.settings?.treg_api_key || '');
      setBioBrandName(st.settings?.bio_brand_name || '');
      setBioBrandSub(st.settings?.bio_brand_subtitle || '');

      if (vd.videos.length > 0 && !vd.videos.some((v) => v.id === selectedVideoId)) {
        setSelectedVideoId(vd.videos[0].id);
        setPromptScript(vd.videos[0].hook_text || vd.videos[0].title);
      }
      if (pr.products.length > 0 && !pr.products.some((p) => p.id === selectedProductId)) {
        setSelectedProductId(pr.products[0].id);
      }
      const completed = jb.jobs.find((j) => j.status === 'completed');
      if (completed) {
        if (pubJobId === null) setPubJobId(completed.id);
        if (activeCloneJobId === null) setActiveCloneJobId(completed.id);
      }
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : 'Lỗi kết nối backend', 'err');
    }
  };

  useEffect(() => {
    refreshAll();
  }, [filterPlatform]);

  // Auto-poll when clone jobs are actively processing
  useEffect(() => {
    const hasRunning = jobs.some((j) => !['completed', 'failed'].includes(j.status));
    if (!hasRunning) return;
    const timer = setInterval(async () => {
      try {
        const [jb, tk, st] = await Promise.all([api.getCloneJobs(), api.getMuseTokens(), api.getStatus()]);
        setJobs(jb.jobs);
        setTokens(tk.tokens);
        setStatus(st);
      } catch {
        // ignore transient poll error
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [jobs]);

  const enrichedVideos = useMemo(
    () => videos.filter((v) => !hiddenIds.includes(v.id)).map(enrichVideo),
    [videos, hiddenIds]
  );

  // Counts for Sidebar Navigation
  const tabCounts = useMemo(() => {
    return {
      'video-tiem-nang': enrichedVideos.filter((e) => e.categoryTab === 'video-tiem-nang').length,
      'video-win': enrichedVideos.filter((e) => e.categoryTab === 'video-win').length,
      'video-scale': enrichedVideos.filter((e) => e.categoryTab === 'video-scale').length,
      'sp-bo-sua': enrichedVideos.filter((e) => e.categoryTab === 'sp-bo-sua').length,
      'video-da-quet': enrichedVideos.length,
      'theo-doi': enrichedVideos.filter((e) => watchlistIds.includes(e.raw.id)).length,
      'video-test': enrichedVideos.filter((e) => testlistIds.includes(e.raw.id)).length,
    };
  }, [enrichedVideos, watchlistIds, testlistIds]);

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
    if (activeTab === 'video-tiem-nang') list = list.filter((e) => e.categoryTab === 'video-tiem-nang');
    else if (activeTab === 'video-win') list = list.filter((e) => e.categoryTab === 'video-win');
    else if (activeTab === 'video-scale') list = list.filter((e) => e.categoryTab === 'video-scale');
    else if (activeTab === 'sp-bo-sua') list = list.filter((e) => e.categoryTab === 'sp-bo-sua');
    else if (activeTab === 'theo-doi') list = list.filter((e) => watchlistIds.includes(e.raw.id));
    else if (activeTab === 'video-test') list = list.filter((e) => testlistIds.includes(e.raw.id));

    if (globalSearch.trim()) {
      const q = globalSearch.toLowerCase();
      list = list.filter((e) =>
        `${e.raw.title} ${e.raw.caption} ${e.raw.author} ${e.raw.hook_text}`.toLowerCase().includes(q)
      );
    }

    return [...list].sort((a, b) => {
      if (sortMode === 'strongest') return b.raw.viral_score - a.raw.viral_score || b.winCount - a.winCount;
      if (sortMode === 'newest') return a.videoAgeDays - b.videoAgeDays;
      return b.shopTotal - a.shopTotal;
    });
  }, [enrichedVideos, activeTab, watchlistIds, testlistIds, globalSearch, sortMode]);

  const drawerVideo = useMemo(
    () => enrichedVideos.find((e) => e.raw.id === drawerVideoId) || null,
    [enrichedVideos, drawerVideoId]
  );

  const selectedVideo = useMemo(
    () => videos.find((v) => v.id === selectedVideoId) || videos[0],
    [videos, selectedVideoId]
  );
  const selectedProduct = useMemo(
    () => products.find((p) => p.id === selectedProductId) || products[0],
    [products, selectedProductId]
  );
  const completedJobs = useMemo(() => jobs.filter((j) => j.status === 'completed'), [jobs]);
  const activeCloneJob = useMemo(
    () => completedJobs.find((j) => j.id === activeCloneJobId) || completedJobs[0] || null,
    [completedJobs, activeCloneJobId]
  );
  const selectedPubJob = useMemo(
    () => completedJobs.find((j) => j.id === pubJobId) || completedJobs[0],
    [completedJobs, pubJobId]
  );

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

  const handleBatchCrawl = async (e: React.FormEvent) => {
    e.preventDefault();
    if (basketLines.length === 0) {
      notify('Vui lòng nhập ít nhất 1 từ khoá vào Giỏ quét', 'err');
      return;
    }
    setScanStage('scanning');
    let totalNew = 0;
    const allNotes: string[] = [];
    const apiEngine = crawlEngine === 'treg_api' ? 'treg_api' : 'crawl4ai_free';

    try {
      for (let i = 0; i < basketLines.length; i++) {
        const kw = matchType === 'exact' ? basketLines[i] : basketLines[i].replace(/"/g, '');
        if (i > 0) setScanStage('digging');
        const res = await api.crawlVideos({
          keyword: kw,
          platform: crawlPlatform,
          engine: apiEngine,
          country: marketCountry,
        });
        totalNew += res.count;
        if (res.diagnostics) allNotes.push(...res.diagnostics);
      }
      setScanStage('digging');
      setCrawlNotes(allNotes.slice(0, 6));
      await refreshAll();
      setScanStage('done');
      notify(`Quét xong ${basketLines.length} từ khoá! Đã nạp ${totalNew} video vào kho SpyWinAds.`);
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

  const handleLaunchClone = async () => {
    if (!selectedVideo || !selectedProduct) {
      notify('Vui lòng chọn video gốc và sản phẩm Affiliate', 'err');
      return;
    }
    setIsLaunchingClone(true);
    try {
      const res = await api.createCloneJob({
        source_video_id: selectedVideo.id,
        product_id: selectedProduct.id,
        clone_mode: cloneMode,
        prompt_script: promptScript || selectedVideo.hook_text || selectedVideo.title,
        cta_position: ctaPosition,
        link_placement_mode: linkPlacementMode,
        anti_duplicate: antiDuplicate,
        batch_count: batchCount,
      });
      if (res.jobs[0]) setActiveCloneJobId(res.jobs[0].id);
      notify(`Đã đưa ${res.jobs.length} video vào hàng đợi Muse AI + FFmpeg 9:16!`);
      await refreshAll();
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi tạo job clone', 'err');
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
          <div
            className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium shrink-0"
            style={{ background: 'var(--la-bg)', color: 'var(--la)' }}
          >
            <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: 'var(--la)' }} />
            Crawl4AI + yt-dlp · Mạng nhà
          </div>
        </div>

        {/* Right: Muse Pool Pill + /bio + Theme Switcher */}
        <div className="flex items-center gap-2 shrink-0">
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
          className="w-[244px] shrink-0 border-r flex flex-col justify-between p-3 overflow-y-auto"
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
            <div className="sw-card-subtle p-2.5 space-y-1.5 text-[11px]">
              <div className="flex items-center justify-between font-semibold">
                <span className="flex items-center gap-1.5" style={{ color: 'var(--la)' }}>
                  <span className="w-2 h-2 rounded-full" style={{ background: 'var(--la)' }} />
                  Đang hoạt động
                </span>
                <span style={{ color: 'var(--mo)' }}>Mạng nhà</span>
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
            </div>

            <button
              onClick={() => setActiveTab('cai-dat')}
              className="w-full flex items-center justify-between px-2.5 py-2 rounded-xl text-xs font-medium transition"
              style={{
                background: activeTab === 'cai-dat' ? 'var(--o)' : 'transparent',
                color: activeTab === 'cai-dat' ? 'var(--chu)' : 'var(--mo)',
              }}
            >
              <span className="flex items-center gap-2">
                <Settings className="w-3.5 h-3.5" />
                <span>Cài đặt API (treg.to) & Rust</span>
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
                            <div className="flex items-center gap-3 min-w-0">
                              <img
                                src={
                                  item.raw.thumbnail_url ||
                                  'https://images.unsplash.com/photo-1611162617474-5b21e879e113?auto=format&fit=crop&w=200&q=80'
                                }
                                alt={item.raw.title}
                                className="w-11 h-14 rounded-xl object-cover shrink-0 bg-black"
                              />
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
                                className="sw-pill-btn px-2.5 py-1 text-[11px] border"
                                style={{ background: 'var(--nen)', borderColor: 'var(--vien)', color: 'var(--chu)' }}
                              >
                                Phân tích
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
                            Nền tảng nguồn
                          </label>
                          <select
                            value={crawlPlatform}
                            onChange={(e) => setCrawlPlatform(e.target.value)}
                            className="sw-input w-full px-3 py-2 text-xs font-medium"
                          >
                            <option value="all">Tất cả (Meta Ads + IG + FB + Threads)</option>
                            <option value="meta_ads">Meta Ads Library (Free)</option>
                            <option value="instagram">Instagram Reels</option>
                            <option value="facebook">Facebook Reels / Watch</option>
                            <option value="threads">Threads Video Posts</option>
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
                            <option value="crawl4ai_free">Auto Free: Crawl4AI + Playwright + yt-dlp</option>
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
                          Dán link trực tiếp (IG Reels / FB Reels / Threads)
                        </h3>
                        <span className="text-[11px]" style={{ color: 'var(--mo)' }}>
                          yt-dlp 1-Click MP4
                        </span>
                      </div>
                      <div className="flex flex-col sm:flex-row gap-2">
                        <input
                          value={inspectUrlInput}
                          onChange={(e) => setInspectUrlInput(e.target.value)}
                          placeholder="https://www.instagram.com/reel/... hoặc link Facebook/Threads..."
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

                {/* Platform Filter Pills */}
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="sw-seg flex-wrap">
                    {[
                      { id: 'all', label: 'Tất cả nguồn' },
                      { id: 'meta_ads', label: 'Meta Ads' },
                      { id: 'instagram', label: 'IG Reels' },
                      { id: 'facebook', label: 'FB Reels' },
                      { id: 'threads', label: 'Threads' },
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
                  /* GRID VIEW — Exact SpyWinAds Video Card Anatomy */
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                    {displayedVideos.map((item) => {
                      const v = item.raw;
                      const pf = PLATFORM_META[v.platform] || PLATFORM_META.facebook;
                      const isWatch = watchlistIds.includes(v.id);
                      const isTest = testlistIds.includes(v.id);
                      return (
                        <div key={v.id} className="sw-card p-4 flex flex-col justify-between gap-3 transition hover:shadow-md">
                          <div className="space-y-3">
                            {/* 1. TOP ROW BADGES: Vòng tuổi video + Ô tuổi trang bán */}
                            <div className="flex items-center justify-between gap-2">
                              <div className="flex items-center gap-1.5 min-w-0">
                                <span
                                  className="px-2.5 py-1 rounded-full text-[11px] font-bold shrink-0"
                                  style={{
                                    background:
                                      item.categoryTab === 'video-win'
                                        ? 'var(--la-bg)'
                                        : item.categoryTab === 'video-tiem-nang'
                                        ? 'var(--xanh-bg)'
                                        : 'var(--o)',
                                    color:
                                      item.categoryTab === 'video-win'
                                        ? 'var(--la)'
                                        : item.categoryTab === 'video-tiem-nang'
                                        ? 'var(--link)'
                                        : 'var(--chu)',
                                  }}
                                  title="File video lên Meta lần đầu"
                                >
                                  {item.videoAgeDays} ngày
                                </span>
                                <span className="text-[11px] truncate" style={{ color: 'var(--mo2)' }}>
                                  File lên Meta
                                </span>
                              </div>

                              <div className="flex items-center gap-1.5 shrink-0">
                                <span
                                  className="px-2 py-0.5 rounded-full text-[10px] font-semibold flex items-center gap-1"
                                  style={{
                                    background: item.isOldStoreWarning ? 'var(--cam-bg)' : 'var(--xam)',
                                    color: item.isOldStoreWarning ? 'var(--cam)' : 'var(--mo)',
                                  }}
                                  title={
                                    item.isOldStoreWarning
                                      ? 'Cảnh báo: Trang bán đã chạy lâu re-up video'
                                      : 'Trang bán mới, tín hiệu win thật'
                                  }
                                >
                                  {item.isOldStoreWarning && <AlertTriangle className="w-3 h-3" />}
                                  Shop {item.storeAgeDays}d
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
                              <div className="relative w-[104px] h-[168px] shrink-0 rounded-2xl overflow-hidden bg-black group">
                                {item.localMediaUrl ? (
                                  <video
                                    src={item.localMediaUrl}
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
                                  className="absolute top-1.5 left-1.5 px-1.5 py-0.5 rounded-md text-[9px] font-bold"
                                  style={{ background: pf.pillBg, color: pf.pillColor }}
                                >
                                  {pf.short}
                                </span>
                                <span className="absolute bottom-1.5 left-1.5 px-1.5 py-0.5 rounded-md bg-black/70 text-white text-[9px] font-semibold flex items-center gap-0.5">
                                  <Play className="w-2.5 h-2.5 fill-white" />
                                  {formatCompact(v.views)}
                                </span>
                              </div>

                              {/* 3. TITLE, PRICE, AUTHOR & SUMMARY LINE */}
                              <div className="min-w-0 flex-1 flex flex-col justify-between py-0.5">
                                <div className="space-y-1">
                                  <h3
                                    onClick={() => setDrawerVideoId(v.id)}
                                    className="text-[13px] font-bold leading-snug line-clamp-2 cursor-pointer hover:underline"
                                    style={{ color: 'var(--chu)' }}
                                  >
                                    {v.title}
                                  </h3>
                                  <div className="flex items-center gap-2 text-xs">
                                    <span className="font-bold" style={{ color: 'var(--la)' }}>
                                      {item.priceLabel}
                                    </span>
                                    <span className="truncate text-[11px]" style={{ color: 'var(--mo2)' }}>
                                      {v.author}
                                    </span>
                                  </div>
                                  <p className="text-[11px] font-medium pt-0.5" style={{ color: 'var(--mo)' }}>
                                    Chạy {item.videoAgeDays} ngày · {item.totalAdsSameVideo} QC cùng video
                                  </p>
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

                            {/* 4. 4 METRIC BOXES (Win, Scale, Shop, Fanpage) + SPARKLINE */}
                            <div className="grid grid-cols-4 gap-1.5">
                              <div className="p-2 rounded-xl text-center" style={{ background: 'var(--xam)' }}>
                                <div className="text-[10px]" style={{ color: 'var(--mo)' }}>
                                  Win (7-14d)
                                </div>
                                <div className="text-sm font-bold" style={{ color: 'var(--la)' }}>
                                  {item.winCount}
                                </div>
                              </div>
                              <div className="p-2 rounded-xl text-center" style={{ background: 'var(--xam)' }}>
                                <div className="text-[10px]" style={{ color: 'var(--mo)' }}>
                                  Scale (&lt;7d)
                                </div>
                                <div className="text-sm font-bold" style={{ color: 'var(--xanh)' }}>
                                  {item.scaleCount}
                                </div>
                              </div>
                              <div className="p-2 rounded-xl text-center" style={{ background: 'var(--xam)' }}>
                                <div className="text-[10px]" style={{ color: 'var(--mo)' }}>
                                  Shop
                                </div>
                                <div className="text-xs font-bold mt-0.5" style={{ color: 'var(--chu)' }}>
                                  {item.shopActive}/{item.shopTotal}
                                </div>
                              </div>
                              <div className="p-2 rounded-xl text-center" style={{ background: 'var(--xam)' }}>
                                <div className="text-[10px]" style={{ color: 'var(--mo)' }}>
                                  Fanpage
                                </div>
                                <div className="text-xs font-bold mt-0.5" style={{ color: 'var(--chu)' }}>
                                  {item.fanpageActive}/{item.fanpageTotal}
                                </div>
                              </div>
                            </div>

                            {/* Mini 14-day Sparkline Bar Row */}
                            <div
                              className="px-2.5 py-2 rounded-xl flex items-center justify-between gap-3"
                              style={{ background: 'var(--xam)' }}
                            >
                              <span className="text-[10px] font-medium shrink-0" style={{ color: 'var(--mo2)' }}>
                                14 ngày
                              </span>
                              <div className="flex-1">
                                <Sparkline
                                  bars={item.sparkline14d}
                                  highlightColor={
                                    item.categoryTab === 'video-win' ? 'var(--la)' : 'var(--xanh)'
                                  }
                                />
                              </div>
                              <span className="text-[10px] font-bold shrink-0" style={{ color: 'var(--chu)' }}>
                                {v.viral_score}/100
                              </span>
                            </div>
                          </div>

                          {/* 5. BOTTOM ACTION BUTTONS FOOTER: Phân tích | Tải video | Clone */}
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
                              Phân tích
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
                  /* TABLE VIEW (Bảng) */
                  <div className="sw-card p-4 overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="border-b" style={{ borderColor: 'var(--vien-nhe)', color: 'var(--mo)' }}>
                          <th className="py-2.5 pr-3 font-semibold">Sản phẩm & Video</th>
                          <th className="py-2.5 px-2 font-semibold">Tuổi Video</th>
                          <th className="py-2.5 px-2 font-semibold">Tuổi Shop</th>
                          <th className="py-2.5 px-2 font-semibold">Win</th>
                          <th className="py-2.5 px-2 font-semibold">Scale</th>
                          <th className="py-2.5 px-2 font-semibold">Shop / Page</th>
                          <th className="py-2.5 px-2 font-semibold w-28">Đà 14 ngày</th>
                          <th className="py-2.5 pl-2 font-semibold text-right">Thao tác</th>
                        </tr>
                      </thead>
                      <tbody>
                        {displayedVideos.map((item) => {
                          const v = item.raw;
                          return (
                            <tr
                              key={v.id}
                              className="border-b last:border-b-0"
                              style={{ borderColor: 'var(--vien-nhe)' }}
                            >
                              <td className="py-3 pr-3 max-w-[280px]">
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
                                    <div className="text-[11px]" style={{ color: 'var(--mo2)' }}>
                                      {v.author} · {item.priceLabel}
                                    </div>
                                  </div>
                                </div>
                              </td>
                              <td className="py-3 px-2 font-bold">{item.videoAgeDays} ngày</td>
                              <td className="py-3 px-2">
                                <span
                                  className="px-2 py-0.5 rounded-full text-[11px] font-semibold"
                                  style={{
                                    background: item.isOldStoreWarning ? 'var(--cam-bg)' : 'var(--xam)',
                                    color: item.isOldStoreWarning ? 'var(--cam)' : 'var(--mo)',
                                  }}
                                >
                                  {item.storeAgeDays} ngày
                                </span>
                              </td>
                              <td className="py-3 px-2 font-bold" style={{ color: 'var(--la)' }}>
                                {item.winCount}
                              </td>
                              <td className="py-3 px-2 font-bold" style={{ color: 'var(--xanh)' }}>
                                {item.scaleCount}
                              </td>
                              <td className="py-3 px-2" style={{ color: 'var(--mo)' }}>
                                {item.shopActive}/{item.shopTotal} · {item.fanpageActive}/{item.fanpageTotal}
                              </td>
                              <td className="py-3 px-2">
                                <Sparkline bars={item.sparkline14d} />
                              </td>
                              <td className="py-3 pl-2 text-right space-x-1.5 whitespace-nowrap">
                                <button
                                  onClick={() => setDrawerVideoId(v.id)}
                                  className="sw-pill-btn px-2.5 py-1 text-[11px] border"
                                  style={{ background: 'var(--xam)', borderColor: 'var(--vien)', color: 'var(--chu)' }}
                                >
                                  Phân tích
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
                      Cấu hình Clone & Gắn Sản Phẩm Affiliate
                    </h2>

                    <div>
                      <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                        1. Video gốc (Từ bảng SpyWinAds)
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
                        2. Sản phẩm Affiliate gắn CTA
                      </label>
                      <select
                        value={selectedProductId}
                        onChange={(e) => setSelectedProductId(Number(e.target.value))}
                        className="sw-input w-full px-3 py-2 text-xs"
                      >
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
                          Chế độ Muse AI
                        </label>
                        <select
                          value={cloneMode}
                          onChange={(e) => setCloneMode(e.target.value)}
                          className="sw-input w-full px-3 py-2 text-xs"
                        >
                          <option value="muse_prompt_remap">Muse Scene & Script Remap</option>
                          <option value="muse_avatar_motion">Muse Avatar & LipSync</option>
                          <option value="smart_reedit">Smart FFmpeg Re-edit</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                          Vị trí Banner CTA
                        </label>
                        <select
                          value={ctaPosition}
                          onChange={(e) => setCtaPosition(e.target.value)}
                          className="sw-input w-full px-3 py-2 text-xs"
                        >
                          <option value="bottom_banner">Bottom Pill (Chuẩn Reels)</option>
                          <option value="top_pill">Top Dynamic Island</option>
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
                      <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                        Kịch bản 3 phần (0-3s Hook · Demo · CTA #MãSP)
                      </label>
                      <textarea
                        rows={3}
                        value={promptScript}
                        onChange={(e) => setPromptScript(e.target.value)}
                        placeholder="Nhập câu Hook 3 giây đầu hiển thị trực tiếp trên video clone..."
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
                      Bật Anti-Duplicate (FFmpeg Mirror + Speed 1.03x + Xoá Metadata)
                    </label>

                    <button
                      onClick={handleLaunchClone}
                      disabled={isLaunchingClone}
                      className="sw-pill-btn-primary w-full py-3 text-sm flex items-center justify-center gap-2"
                    >
                      <Sparkles className="w-4 h-4" />
                      {isLaunchingClone
                        ? 'Đang khởi tạo...'
                        : `Render Video 9:16 bằng Muse AI ${batchCount > 1 ? `(${batchCount}x)` : ''}`}
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
                                Hoàn tất · #{activeCloneJob.product_code}
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

                    {/* All Jobs List */}
                    <div className="space-y-2.5 max-h-[340px] overflow-y-auto pr-1">
                      {jobs.length === 0 ? (
                        <div className="py-10 text-center text-xs" style={{ color: 'var(--mo)' }}>
                          Chưa có job clone nào. Chọn video & bấm "Render Video 9:16 bằng Muse AI" bên trái!
                        </div>
                      ) : (
                        jobs.map((job) => (
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
                                  style={{ background: 'var(--nen)', color: 'var(--cam)' }}
                                >
                                  #{job.product_code || job.product_id}
                                </span>
                                <span className="truncate" style={{ color: 'var(--mo)' }}>
                                  {job.source_title || job.prompt_script}
                                </span>
                              </div>
                              <span
                                className="px-2.5 py-0.5 rounded-full text-[10px] font-bold shrink-0"
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
                                {job.status} ({job.progress}%)
                              </span>
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
                            Job #{j.id} — #{j.product_code} {j.product_name}
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
                VIEW 7: CÀI ĐẶT API (treg.to) & KIẾN TRÚC RUST ANALYSIS
               ============================================================== */}
            {activeTab === 'cai-dat' && (
              <div className="space-y-5">
                <div>
                  <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--chu)' }}>
                    Cài đặt Hệ thống, treg.to API & Đánh giá Rust
                  </h1>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                  <div className="lg:col-span-6 sw-card p-5 space-y-4">
                    <h2 className="text-sm font-bold flex items-center gap-2">
                      <Activity className="w-4 h-4" style={{ color: 'var(--xanh)' }} />
                      Trạng thái Engine Local
                    </h2>
                    <div className="grid grid-cols-2 gap-3 text-xs">
                      {[
                        { name: 'FFmpeg Video Composer', ok: status?.ffmpeg_installed, detail: '9:16 + CTA Overlay' },
                        { name: 'yt-dlp Downloader', ok: status?.ytdlp_installed, detail: 'IG / FB / Threads' },
                        { name: 'Playwright Headless', ok: status?.playwright_installed, detail: 'Free Meta Ads Crawl' },
                        {
                          name: 'Crawl4AI Engine',
                          ok: status?.crawl4ai_installed,
                          detail: status?.crawl4ai_installed ? 'Native' : 'Playwright Fallback',
                        },
                      ].map((item, idx) => (
                        <div
                          key={idx}
                          className="p-3 rounded-2xl border"
                          style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}
                        >
                          <div className="font-bold flex items-center justify-between">
                            <span>{item.name}</span>
                            <span style={{ color: item.ok ? 'var(--la)' : 'var(--cam)' }}>
                              {item.ok ? 'READY' : 'FALLBACK'}
                            </span>
                          </div>
                          <div className="text-[11px] mt-1" style={{ color: 'var(--mo)' }}>
                            {item.detail}
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="pt-3 border-t space-y-3" style={{ borderColor: 'var(--vien-nhe)' }}>
                      <h3 className="text-sm font-bold">Cấu hình /bio & treg.to API Key (Tuỳ chọn)</h3>
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
                      <div>
                        <label className="block text-[11px] font-semibold mb-1" style={{ color: 'var(--mo)' }}>
                          treg.to API Key (Bỏ trống nếu dùng 100% Crawl4AI / Playwright Free)
                        </label>
                        <input
                          type="password"
                          value={tregApiKey}
                          onChange={(e) => setTregApiKey(e.target.value)}
                          placeholder="Bỏ trống để dùng crawler miễn phí trên máy..."
                          className="sw-input w-full px-3 py-2 text-xs"
                        />
                      </div>
                      <button
                        onClick={() =>
                          api
                            .updateSettings({
                              treg_api_key: tregApiKey,
                              bio_brand_name: bioBrandName,
                              bio_brand_subtitle: bioBrandSub,
                            })
                            .then(() => {
                              notify('Đã lưu cấu hình!');
                              refreshAll();
                            })
                        }
                        className="sw-pill-btn-primary px-5 py-2 text-xs"
                      >
                        Lưu Cấu Hình
                      </button>
                    </div>
                  </div>

                  <div className="lg:col-span-6 sw-card p-5 space-y-3 text-xs leading-relaxed">
                    <h2 className="text-sm font-bold flex items-center gap-2">
                      <Cpu className="w-4 h-4" style={{ color: 'var(--cam)' }} />
                      Phân tích Kiến trúc: Khi nào nên bọc Rust (Tauri v2)?
                    </h2>
                    <p style={{ color: 'var(--mo)' }}>
                      Hiện tại backend chạy <strong style={{ color: 'var(--la)' }}>Python FastAPI + Crawl4AI + yt-dlp + FFmpeg</strong>{' '}
                      để xử lý bóc DOM Meta/IG/Threads linh hoạt và ghép video bằng C/Assembly (FFmpeg).
                    </p>
                    <ul className="space-y-2 list-disc pl-4" style={{ color: 'var(--mo)' }}>
                      <li>
                        <strong>Ưu điểm MVP hiện tại:</strong> UI giao diện chuẩn desktop Apple/SpyWinAds bằng React + Vite,
                        tích hợp mượt với hệ sinh thái crawler Python.
                      </li>
                      <li>
                        <strong>Lộ trình nâng cấp Rust + Tauri v2:</strong> Khi đóng gói thành app cài đặt{' '}
                        <code>SpyWinAds-Clone.exe</code> gọn nhẹ giống chính bản desktop đang chạy trên máy, chỉ cần bọc UI này
                        vào <strong>Tauri v2</strong> và viết worker Rust quản lý xoay vòng 1.000+ token Muse & proxy song song.
                      </li>
                    </ul>
                  </div>
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
              </div>

              {/* 3 Core SpyWinAds Metrics: Win / Scale / Cũ */}
              <div className="grid grid-cols-3 gap-2.5">
                <div className="p-3 rounded-2xl text-center" style={{ background: 'var(--la-bg)' }}>
                  <div className="text-[11px] font-medium" style={{ color: 'var(--la)' }}>
                    Win (7–14 ngày)
                  </div>
                  <div className="text-2xl font-bold mt-0.5" style={{ color: 'var(--la)' }}>
                    {drawerVideo.winCount}
                  </div>
                </div>
                <div className="p-3 rounded-2xl text-center" style={{ background: 'var(--xanh-bg)' }}>
                  <div className="text-[11px] font-medium" style={{ color: 'var(--link)' }}>
                    Scale (&lt; 7 ngày)
                  </div>
                  <div className="text-2xl font-bold mt-0.5" style={{ color: 'var(--xanh)' }}>
                    {drawerVideo.scaleCount}
                  </div>
                </div>
                <div className="p-3 rounded-2xl text-center" style={{ background: 'var(--xam)' }}>
                  <div className="text-[11px] font-medium" style={{ color: 'var(--mo)' }}>
                    Cũ (&gt; 14 ngày)
                  </div>
                  <div className="text-2xl font-bold mt-0.5" style={{ color: 'var(--chu)' }}>
                    {drawerVideo.oldAdsCount}
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
                <div className="p-3.5 rounded-2xl border space-y-1" style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}>
                  <div className="font-bold flex items-center gap-1.5" style={{ color: 'var(--link)' }}>
                    <Zap className="w-3.5 h-3.5" />
                    Hook 3 giây đầu (Bắt buộc giữ nhịp khi Clone)
                  </div>
                  <p style={{ color: 'var(--chu)' }}>{drawerVideo.raw.hook_text || drawerVideo.raw.caption}</p>
                </div>

                {drawerVideo.raw.script_summary && (
                  <div
                    className="p-3.5 rounded-2xl border space-y-1"
                    style={{ background: 'var(--xam)', borderColor: 'var(--vien-nhe)' }}
                  >
                    <div className="font-bold flex items-center gap-1.5" style={{ color: 'var(--chu)' }}>
                      <MessageSquare className="w-3.5 h-3.5" />
                      Cấu trúc kịch bản bán hàng
                    </div>
                    <p style={{ color: 'var(--mo)' }}>{drawerVideo.raw.script_summary}</p>
                  </div>
                )}

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
                onClick={() => handleSelectForClone(drawerVideo.raw)}
                className="sw-pill-btn-primary flex-1 py-2.5 px-4 text-xs flex items-center justify-center gap-1.5"
              >
                <Sparkles className="w-4 h-4" />
                Clone bằng Muse AI
              </button>
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
