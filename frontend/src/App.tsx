import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  CheckCircle2,
  ClipboardCopy,
  Cpu,
  Download,
  ExternalLink,
  Flame,
  KeyRound,
  Layers,
  Link2,
  MessageSquarePlus,
  Play,
  Plus,
  RefreshCw,
  Search,
  Send,
  ShoppingBag,
  Smartphone,
  Sparkles,
  Trash2,
  UploadCloud,
  Video,
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

type TabKey = 'research' | 'muse' | 'products' | 'publish' | 'system';

const PLATFORM_LABELS: Record<string, { label: string; color: string }> = {
  meta_ads: { label: 'Meta Ads Library', color: 'bg-blue-500/20 text-blue-300 border-blue-500/40' },
  instagram: { label: 'Instagram Reels', color: 'bg-pink-500/20 text-pink-300 border-pink-500/40' },
  facebook: { label: 'Facebook Reels', color: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40' },
  threads: { label: 'Threads', color: 'bg-slate-500/25 text-slate-200 border-slate-400/40' },
};

function formatCompact(n: number): string {
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(2)}B`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export default function App() {
  const [activeTab, setActiveTab] = useState<TabKey>('research');
  const [toast, setToast] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);

  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [videos, setVideos] = useState<ViralVideo[]>([]);
  const [tokens, setTokens] = useState<MuseToken[]>([]);
  const [products, setProducts] = useState<AffiliateProduct[]>([]);
  const [jobs, setJobs] = useState<CloneJob[]>([]);
  const [publishTasks, setPublishTasks] = useState<PublishTask[]>([]);

  // Research state
  const [crawlKeyword, setCrawlKeyword] = useState('máy ép chậm mini');
  const [crawlPlatform, setCrawlPlatform] = useState('all');
  const [crawlEngine, setCrawlEngine] = useState('crawl4ai_free');
  const [filterPlatform, setFilterPlatform] = useState('all');
  const [inspectUrlInput, setInspectUrlInput] = useState('');
  const [isCrawling, setIsCrawling] = useState(false);
  const [isInspecting, setIsInspecting] = useState(false);
  const [crawlNotes, setCrawlNotes] = useState<string[]>([]);

  // Muse Clone Workbench state
  const [selectedVideoId, setSelectedVideoId] = useState<number>(1);
  const [selectedProductId, setSelectedProductId] = useState<number>(1);
  const [cloneMode, setCloneMode] = useState('muse_prompt_remap');
  const [ctaPosition, setCtaPosition] = useState('bottom_banner');
  const [linkPlacementMode, setLinkPlacementMode] = useState('both');
  const [promptScript, setPromptScript] = useState('');
  const [antiDuplicate, setAntiDuplicate] = useState(true);
  const [batchCount, setBatchCount] = useState(1);
  const [isLaunchingClone, setIsLaunchingClone] = useState(false);

  // Bulk Token Modal
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [bulkTokenText, setBulkTokenText] = useState(
    'Muse_VN_04|muse_sess_demo_token_vn04_1b_xyz|http://103.1.1.10:8080\nMuse_VN_05|muse_sess_demo_token_vn05_1b_abc|'
  );
  const [bulkWeeklyLimit, setBulkWeeklyLimit] = useState(50);

  // Product Form state
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

  // Publish tab state
  const [pubJobId, setPubJobId] = useState<number | null>(null);
  const [pubPlatform, setPubPlatform] = useState<'facebook_reels' | 'instagram_reels' | 'threads'>('facebook_reels');
  const [pubAccount, setPubAccount] = useState('@deal.ngon.aff');
  const [pubCaption, setPubCaption] = useState('');
  const [pubFirstComment, setPubFirstComment] = useState('');

  // Settings tab state
  const [tregApiKey, setTregApiKey] = useState('');
  const [bioBrandName, setBioBrandName] = useState('');
  const [bioBrandSub, setBioBrandSub] = useState('');

  const notify = (text: string, type: 'ok' | 'err' = 'ok') => {
    setToast({ text, type });
    setTimeout(() => setToast(null), 4000);
  };

  const refreshAll = async () => {
    try {
      const [st, vd, tk, pr, jb, pt] = await Promise.all([
        api.getStatus(),
        api.getVideos(filterPlatform),
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
      if (completed && pubJobId === null) {
        setPubJobId(completed.id);
      }
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : 'Lỗi kết nối backend', 'err');
    }
  };

  useEffect(() => {
    refreshAll();
  }, [filterPlatform]);

  // Auto-poll while clone jobs are in flight
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

  const selectedVideo = useMemo(
    () => videos.find((v) => v.id === selectedVideoId) || videos[0],
    [videos, selectedVideoId]
  );
  const selectedProduct = useMemo(
    () => products.find((p) => p.id === selectedProductId) || products[0],
    [products, selectedProductId]
  );
  const completedJobs = useMemo(() => jobs.filter((j) => j.status === 'completed'), [jobs]);
  const selectedPubJob = useMemo(
    () => completedJobs.find((j) => j.id === pubJobId) || completedJobs[0],
    [completedJobs, pubJobId]
  );

  // Sync publish copy preview when selected job or target platform changes
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

  const handleCrawl = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsCrawling(true);
    try {
      const res = await api.crawlVideos({
        keyword: crawlKeyword,
        platform: crawlPlatform,
        engine: crawlEngine,
        country: 'VN',
      });
      setCrawlNotes(res.diagnostics || []);
      notify(`Đã crawl thêm ${res.count} video viral cho "${res.keyword}" (${res.engine_used})`);
      await refreshAll();
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Lỗi crawl', 'err');
    } finally {
      setIsCrawling(false);
    }
  };

  const handleInspectUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inspectUrlInput.trim()) return;
    setIsInspecting(true);
    try {
      const res = await api.inspectUrl(inspectUrlInput, true);
      notify(res.warning ? res.warning : 'Đã tải & phân tích video thành công bằng yt-dlp!');
      setInspectUrlInput('');
      await refreshAll();
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : 'Không thể kiểm tra URL', 'err');
    } finally {
      setIsInspecting(false);
    }
  };

  const handleSelectForClone = (v: ViralVideo) => {
    setSelectedVideoId(v.id);
    setPromptScript(v.hook_text || v.title);
    setActiveTab('muse');
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
      notify(`Đã đưa ${res.jobs.length} video vào hàng đợi Muse + FFmpeg!`);
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
      notify(`Đã thêm sản phẩm #${prodForm.code.toUpperCase()} và đồng bộ lên Link Bio!`);
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
      notify('Đã tạo tác vụ Đăng bài & Thả Comment / Đồng bộ Link Bio!');
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

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Toast Notification */}
      {toast && (
        <div
          className={`fixed bottom-5 right-5 z-50 px-4 py-3 rounded-xl shadow-2xl border text-sm font-medium flex items-center gap-2 ${
            toast.type === 'ok'
              ? 'bg-emerald-950/95 border-emerald-500/50 text-emerald-200'
              : 'bg-rose-950/95 border-rose-500/50 text-rose-200'
          }`}
        >
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{toast.text}</span>
        </div>
      )}

      {/* Top Navigation */}
      <header className="sticky top-0 z-30 border-b border-slate-800/80 bg-slate-950/85 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 via-pink-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-orange-500/20">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-bold tracking-tight text-white flex items-center gap-2">
                CloneVideo-Aff Studio
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                  MVP v0.1
                </span>
              </h1>
              <p className="text-xs text-slate-400">
                Crawl Viral (IG / FB / Threads / Meta Ads) • Muse 1B Token Pool • Affiliate Comment & Bio Link
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs">
            <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800">
              <KeyRound className="w-3.5 h-3.5 text-amber-400" />
              <span className="text-slate-400">Muse Pool:</span>
              <span className="font-bold text-amber-300">
                {status ? formatCompact(status.muse_pool.total_tokens_remaining) : '...'} Tokens
              </span>
              <span className="text-slate-500">
                ({status?.muse_pool.active_accounts ?? 0} acc active)
              </span>
            </div>
            <a
              href="/bio"
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 rounded-lg bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-500/30 text-indigo-300 font-medium flex items-center gap-1.5"
            >
              <Smartphone className="w-3.5 h-3.5" />
              Mở Trang Bio
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>

        {/* Tab Bar */}
        <div className="max-w-7xl mx-auto px-4 flex gap-1 overflow-x-auto pb-2">
          {[
            { id: 'research', label: '1. Research & Crawl Viral', icon: Flame },
            { id: 'muse', label: '2. Muse Studio & Kho Token', icon: Sparkles },
            { id: 'products', label: '3. Sản Phẩm & Link Bio', icon: ShoppingBag },
            { id: 'publish', label: '4. Đăng Bài & Comment Link', icon: Send },
            { id: 'system', label: '5. Kiến Trúc & Hệ Thống', icon: Cpu },
          ].map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as TabKey)}
                className={`px-3.5 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 whitespace-nowrap transition ${
                  active
                    ? 'bg-gradient-to-r from-orange-500/20 to-pink-500/20 text-orange-300 border border-orange-500/40'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-6">
        {/* TAB 1: RESEARCH & CRAWL VIRAL */}
        {activeTab === 'research' && (
          <div className="space-y-6">
            {/* Search & Crawl Bar */}
            <div className="glass-panel rounded-2xl p-5 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <Flame className="w-5 h-5 text-orange-400" />
                    Săn Video Viral & Winning Ads Đa Nền Tảng
                  </h2>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Ưu tiên <strong className="text-emerald-300">Crawl4AI / Playwright + yt-dlp (Miễn phí 100%)</strong> để tìm video đang chạy ads hoặc viral trên Instagram, Facebook, Threads.
                  </p>
                </div>
                <span className="text-[11px] px-2.5 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 font-medium">
                  Zero-Cost Crawler Ready
                </span>
              </div>

              <form onSubmit={handleCrawl} className="grid grid-cols-1 md:grid-cols-12 gap-3">
                <div className="md:col-span-5 relative">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                  <input
                    value={crawlKeyword}
                    onChange={(e) => setCrawlKeyword(e.target.value)}
                    placeholder="Nhập ngách / tên sản phẩm (vd: máy ép chậm, đèn livestream...)"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm focus:border-orange-500 outline-none"
                  />
                </div>
                <div className="md:col-span-3">
                  <select
                    value={crawlPlatform}
                    onChange={(e) => setCrawlPlatform(e.target.value)}
                    className="w-full px-3 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm outline-none"
                  >
                    <option value="all">Tất cả (Meta Ads + IG + FB + Threads)</option>
                    <option value="meta_ads">Meta Ads Library (Free)</option>
                    <option value="instagram">Instagram Reels</option>
                    <option value="facebook">Facebook Reels / Watch</option>
                    <option value="threads">Threads Video Posts</option>
                  </select>
                </div>
                <div className="md:col-span-2">
                  <select
                    value={crawlEngine}
                    onChange={(e) => setCrawlEngine(e.target.value)}
                    className="w-full px-3 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm outline-none"
                  >
                    <option value="crawl4ai_free">Crawl4AI (Free)</option>
                    <option value="treg_api">treg.to API (Optional)</option>
                  </select>
                </div>
                <div className="md:col-span-2">
                  <button
                    type="submit"
                    disabled={isCrawling}
                    className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-orange-500 to-pink-600 hover:from-orange-400 hover:to-pink-500 font-semibold text-sm text-white flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    {isCrawling ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                    {isCrawling ? 'Đang Crawl...' : 'Quét Viral'}
                  </button>
                </div>
              </form>

              {/* Direct URL Inspector */}
              <form onSubmit={handleInspectUrl} className="flex flex-col sm:flex-row gap-2 pt-2 border-t border-slate-800/70">
                <div className="flex-1 relative">
                  <Link2 className="w-4 h-4 text-sky-400 absolute left-3.5 top-3" />
                  <input
                    value={inspectUrlInput}
                    onChange={(e) => setInspectUrlInput(e.target.value)}
                    placeholder="Hoặc dán trực tiếp link Instagram Reel / Facebook Reel / Threads để tải sạch không logo bằng yt-dlp..."
                    className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-950/80 border border-slate-800 text-xs focus:border-sky-500 outline-none"
                  />
                </div>
                <button
                  type="submit"
                  disabled={isInspecting}
                  className="px-4 py-2 rounded-xl bg-sky-500/20 hover:bg-sky-500/30 border border-sky-500/40 text-sky-300 text-xs font-semibold flex items-center justify-center gap-1.5"
                >
                  <Download className="w-3.5 h-3.5" />
                  {isInspecting ? 'Đang tải...' : 'Import & Tải Video'}
                </button>
              </form>

              {crawlNotes.length > 0 && (
                <div className="text-xs text-slate-400 bg-slate-950/70 border border-slate-800 rounded-xl px-3 py-2 space-y-0.5">
                  {crawlNotes.map((n, i) => (
                    <div key={i}>• {n}</div>
                  ))}
                </div>
              )}
            </div>

            {/* Filter Pills */}
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap gap-2">
                {[
                  { id: 'all', label: 'Tất cả nguồn' },
                  { id: 'meta_ads', label: 'Meta Ads Library' },
                  { id: 'instagram', label: 'Instagram' },
                  { id: 'facebook', label: 'Facebook' },
                  { id: 'threads', label: 'Threads' },
                ].map((f) => (
                  <button
                    key={f.id}
                    onClick={() => setFilterPlatform(f.id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
                      filterPlatform === f.id
                        ? 'bg-slate-800 text-white border-slate-600'
                        : 'bg-slate-900/50 text-slate-400 border-slate-800 hover:text-slate-200'
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
              <span className="text-xs text-slate-400">Hiển thị {videos.length} video viral</span>
            </div>

            {/* Viral Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {videos.map((v) => {
                const pf = PLATFORM_LABELS[v.platform] || PLATFORM_LABELS.facebook;
                return (
                  <div
                    key={v.id}
                    className="glass-panel rounded-2xl overflow-hidden flex flex-col hover:border-orange-500/40 transition group"
                  >
                    <div className="relative h-48 bg-slate-900 overflow-hidden">
                      <img
                        src={
                          v.thumbnail_url ||
                          'https://images.unsplash.com/photo-1611162617474-5b21e879e113?auto=format&fit=crop&w=600&q=80'
                        }
                        alt={v.title}
                        className="w-full h-full object-cover opacity-85 group-hover:scale-105 transition duration-500"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/20 to-transparent" />
                      <div className="absolute top-3 left-3 flex items-center gap-2">
                        <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-full border ${pf.color}`}>
                          {pf.label}
                        </span>
                      </div>
                      <div className="absolute top-3 right-3 px-2.5 py-1 rounded-full bg-slate-950/85 border border-orange-500/40 text-orange-300 text-xs font-bold flex items-center gap-1">
                        <Flame className="w-3.5 h-3.5 text-orange-400" />
                        {v.viral_score}/100
                      </div>
                      <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between text-[11px] text-slate-200">
                        <span className="font-medium truncate">{v.author}</span>
                        <span>
                          {formatCompact(v.views)} views • {formatCompact(v.likes)} likes
                        </span>
                      </div>
                    </div>

                    <div className="p-4 flex-1 flex flex-col justify-between space-y-3">
                      <div className="space-y-2">
                        <h3 className="font-bold text-sm text-white line-clamp-2">{v.title}</h3>
                        <p className="text-xs text-slate-400 line-clamp-2">{v.caption}</p>

                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {v.sales_signals.map((sig, i) => (
                            <span
                              key={i}
                              className="text-[10px] px-2 py-0.5 rounded-md bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                            >
                              {sig}
                            </span>
                          ))}
                        </div>

                        {v.hook_text && (
                          <div className="p-2.5 rounded-xl bg-slate-950/80 border border-slate-800 text-[11px] text-slate-300">
                            <span className="text-sky-400 font-semibold">Hook 3s: </span>
                            {v.hook_text}
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-2 pt-2 border-t border-slate-800/80">
                        <button
                          onClick={() => handleSelectForClone(v)}
                          className="flex-1 py-2 px-3 rounded-xl bg-gradient-to-r from-orange-500 to-pink-600 hover:from-orange-400 hover:to-pink-500 text-white text-xs font-bold flex items-center justify-center gap-1.5"
                        >
                          <Sparkles className="w-3.5 h-3.5" />
                          Clone bằng Muse
                        </button>
                        <a
                          href={v.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300"
                          title="Mở link gốc"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </a>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* TAB 2: MUSE STUDIO & KHO TOKEN */}
        {activeTab === 'muse' && (
          <div className="space-y-6">
            {/* Muse Token Pool Telemetry Banner */}
            <div className="glass-panel rounded-2xl p-4 flex flex-wrap items-center justify-between gap-4">
              <div className="flex flex-wrap items-center gap-6">
                <div>
                  <div className="text-[11px] text-slate-400 uppercase tracking-wider">Kho Token Muse (1B Pool)</div>
                  <div className="text-xl font-extrabold text-amber-300">
                    {status ? formatCompact(status.muse_pool.total_tokens_remaining) : '0'} Tokens
                  </div>
                </div>
                <div className="h-8 w-px bg-slate-800 hidden sm:block" />
                <div>
                  <div className="text-[11px] text-slate-400">Tài khoản Active / Tổng</div>
                  <div className="text-sm font-bold text-white">
                    {status?.muse_pool.active_accounts ?? 0} / {status?.muse_pool.total_accounts ?? 0} accounts
                  </div>
                </div>
                <div>
                  <div className="text-[11px] text-slate-400">Hạn mức tuần đã dùng</div>
                  <div className="text-sm font-bold text-sky-300">
                    {status?.muse_pool.weekly_used ?? 0} / {status?.muse_pool.weekly_capacity ?? 0} lượt render
                  </div>
                </div>
              </div>
              <button
                onClick={() => setShowBulkModal(true)}
                className="px-4 py-2 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-300 text-xs font-bold flex items-center gap-2"
              >
                <KeyRound className="w-4 h-4" />
                Quản lý & Nạp Hàng Loạt Token Muse
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left: Clone Workbench */}
              <div className="lg:col-span-5 glass-panel rounded-2xl p-5 space-y-4">
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <Video className="w-4 h-4 text-pink-400" />
                  Cấu hình Clone Video Affiliate
                </h2>

                <div>
                  <label className="block text-xs text-slate-400 mb-1">1. Chọn Video Viral Gốc</label>
                  <select
                    value={selectedVideoId}
                    onChange={(e) => {
                      const id = Number(e.target.value);
                      setSelectedVideoId(id);
                      const found = videos.find((x) => x.id === id);
                      if (found) setPromptScript(found.hook_text || found.title);
                    }}
                    className="w-full px-3 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs outline-none"
                  >
                    {videos.map((v) => (
                      <option key={v.id} value={v.id}>
                        [{v.platform.toUpperCase()}] {v.title} (Score: {v.viral_score})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs text-slate-400 mb-1">2. Gắn Sản Phẩm Affiliate</label>
                  <select
                    value={selectedProductId}
                    onChange={(e) => setSelectedProductId(Number(e.target.value))}
                    className="w-full px-3 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs outline-none"
                  >
                    {products.map((p) => (
                      <option key={p.id} value={p.id}>
                        #{p.code} — {p.name} ({p.price} • {p.platform_name})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Chế độ Muse Clone</label>
                    <select
                      value={cloneMode}
                      onChange={(e) => setCloneMode(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs outline-none"
                    >
                      <option value="muse_prompt_remap">Muse Scene & Script Remap</option>
                      <option value="muse_avatar_motion">Muse Avatar & LipSync</option>
                      <option value="smart_reedit">Smart FFmpeg Re-edit</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Vị trí Banner CTA</label>
                    <select
                      value={ctaPosition}
                      onChange={(e) => setCtaPosition(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs outline-none"
                    >
                      <option value="bottom_banner">Card Sản Phẩm Dưới (Chuẩn Reels)</option>
                      <option value="top_pill">Card Nổi Phía Trên</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Chiến lược Gắn Link</label>
                    <select
                      value={linkPlacementMode}
                      onChange={(e) => setLinkPlacementMode(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs outline-none"
                    >
                      <option value="both">Comment Đầu + Link Bio</option>
                      <option value="comment_first">Gắn Link ở Comment Đầu</option>
                      <option value="bio_link">Điều hướng Link Bio (#MãSP)</option>
                      <option value="threads_reply">Chuỗi Reply Threads</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Số biến thể nhân bản (Batch)</label>
                    <input
                      type="number"
                      min={1}
                      max={10}
                      value={batchCount}
                      onChange={(e) => setBatchCount(Math.max(1, Math.min(10, Number(e.target.value) || 1)))}
                      className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs text-slate-400 mb-1">
                    Hook / Kịch bản AI (hiển thị trực tiếp trên video clone)
                  </label>
                  <textarea
                    rows={3}
                    value={promptScript}
                    onChange={(e) => setPromptScript(e.target.value)}
                    placeholder="Nhập câu hook 3 giây đầu..."
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs outline-none"
                  />
                </div>

                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={antiDuplicate}
                    onChange={(e) => setAntiDuplicate(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-950"
                  />
                  Bật Anti-Duplicate (Xoá metadata gốc + cân chỉnh màu sắc tránh bóp reach)
                </label>

                <button
                  onClick={handleLaunchClone}
                  disabled={isLaunchingClone}
                  className="w-full py-3 rounded-xl bg-gradient-to-r from-orange-500 via-pink-600 to-indigo-600 hover:brightness-110 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-pink-500/20"
                >
                  <Sparkles className="w-4 h-4" />
                  {isLaunchingClone ? 'Đang khởi tạo...' : `Chạy Clone ${batchCount > 1 ? `${batchCount} Biến Thể ` : ''}qua Muse Pool`}
                </button>
              </div>

              {/* Right: Live Render Queue */}
              <div className="lg:col-span-7 glass-panel rounded-2xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    <Layers className="w-4 h-4 text-sky-400" />
                    Hàng Đợi Render Muse & FFmpeg ({jobs.length})
                  </h2>
                  <button
                    onClick={refreshAll}
                    className="text-xs text-slate-400 hover:text-white flex items-center gap-1"
                  >
                    <RefreshCw className="w-3.5 h-3.5" /> Làm mới
                  </button>
                </div>

                {jobs.length === 0 ? (
                  <div className="py-16 text-center text-slate-500 text-sm border border-dashed border-slate-800 rounded-2xl">
                    Chưa có job clone nào. Chọn video & bấm "Chạy Clone qua Muse Pool" bên trái để render video `.mp4` thật!
                  </div>
                ) : (
                  <div className="space-y-4 max-h-[680px] overflow-y-auto pr-1">
                    {jobs.map((job) => (
                      <div key={job.id} className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-3">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div>
                            <div className="text-xs font-bold text-white flex items-center gap-2">
                              <span>Job #{job.id}</span>
                              <span className="px-2 py-0.5 rounded bg-slate-800 text-amber-300 text-[10px]">
                                #{job.product_code || job.product_id}
                              </span>
                              {job.muse_token_label && (
                                <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 text-[10px]">
                                  {job.muse_token_label}
                                </span>
                              )}
                            </div>
                            <p className="text-[11px] text-slate-400 mt-0.5 line-clamp-1">
                              {job.source_title || job.prompt_script}
                            </p>
                          </div>
                          <span
                            className={`text-[11px] font-bold px-2.5 py-1 rounded-full ${
                              job.status === 'completed'
                                ? 'bg-emerald-500/20 text-emerald-300'
                                : job.status === 'failed'
                                ? 'bg-rose-500/20 text-rose-300'
                                : 'bg-amber-500/20 text-amber-300'
                            }`}
                          >
                            {job.status} ({job.progress}%)
                          </span>
                        </div>

                        <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all duration-300 ${
                              job.status === 'failed'
                                ? 'bg-rose-500'
                                : 'bg-gradient-to-r from-orange-500 to-emerald-400'
                            }`}
                            style={{ width: `${job.progress}%` }}
                          />
                        </div>

                        {job.error_message && (
                          <div className="text-xs text-rose-300 bg-rose-950/40 border border-rose-500/30 rounded-lg p-2">
                            {job.error_message}
                          </div>
                        )}

                        {job.status === 'completed' && job.output_video_url && (
                          <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 pt-2">
                            <div className="sm:col-span-5 bg-black rounded-xl overflow-hidden border border-slate-800 aspect-[9/16] max-h-64 mx-auto w-full">
                              <video
                                src={job.output_video_url}
                                controls
                                playsInline
                                className="w-full h-full object-contain"
                              />
                            </div>
                            <div className="sm:col-span-7 flex flex-col justify-between space-y-2 text-xs">
                              <div className="space-y-2">
                                <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800">
                                  <div className="text-[10px] text-slate-400 uppercase mb-1">Caption Đề Xuất</div>
                                  <p className="text-slate-200 whitespace-pre-line line-clamp-3">
                                    {job.generated_caption}
                                  </p>
                                </div>
                                <div className="p-2.5 rounded-xl bg-emerald-950/30 border border-emerald-500/30">
                                  <div className="text-[10px] text-emerald-400 uppercase mb-1">
                                    Auto First-Comment Link
                                  </div>
                                  <p className="text-emerald-200 line-clamp-2">{job.generated_first_comment}</p>
                                </div>
                              </div>

                              <div className="flex flex-wrap gap-2">
                                <a
                                  href={job.output_video_url}
                                  download={`clone_${job.id}.mp4`}
                                  className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-semibold flex items-center gap-1.5"
                                >
                                  <Download className="w-3.5 h-3.5" /> Tải MP4
                                </a>
                                <button
                                  onClick={() => {
                                    setPubJobId(job.id);
                                    setActiveTab('publish');
                                  }}
                                  className="flex-1 px-3 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold flex items-center justify-center gap-1.5"
                                >
                                  <Send className="w-3.5 h-3.5" /> Đăng & Gắn Link Ngay
                                </button>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: PRODUCTS & LINK-IN-BIO */}
        {activeTab === 'products' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left: Add Product + List */}
            <div className="lg:col-span-7 space-y-5">
              <form onSubmit={handleCreateProduct} className="glass-panel rounded-2xl p-5 space-y-3">
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <Plus className="w-4 h-4 text-emerald-400" />
                  Thêm Sản Phẩm Affiliate Mới
                </h2>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <input
                    value={prodForm.code}
                    onChange={(e) => setProdForm({ ...prodForm, code: e.target.value })}
                    placeholder="Mã SP (vd: SP04)"
                    className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs outline-none"
                  />
                  <select
                    value={prodForm.platform_name}
                    onChange={(e) => setProdForm({ ...prodForm, platform_name: e.target.value })}
                    className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs outline-none"
                  >
                    <option value="Shopee">Shopee</option>
                    <option value="TikTok Shop">TikTok Shop</option>
                    <option value="Lazada">Lazada</option>
                    <option value="Custom">Landing Page</option>
                  </select>
                  <input
                    value={prodForm.price}
                    onChange={(e) => setProdForm({ ...prodForm, price: e.target.value })}
                    placeholder="Giá sale (vd: 249.000đ)"
                    className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs outline-none"
                  />
                  <input
                    value={prodForm.original_price}
                    onChange={(e) => setProdForm({ ...prodForm, original_price: e.target.value })}
                    placeholder="Giá gốc (vd: 499.000đ)"
                    className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs outline-none"
                  />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <input
                    value={prodForm.name}
                    onChange={(e) => setProdForm({ ...prodForm, name: e.target.value })}
                    placeholder="Tên sản phẩm hiển thị trên Video & Trang Bio"
                    className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs outline-none"
                  />
                  <input
                    value={prodForm.affiliate_url}
                    onChange={(e) => setProdForm({ ...prodForm, affiliate_url: e.target.value })}
                    placeholder="Link Affiliate (https://shope.ee/...)"
                    className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs outline-none"
                  />
                </div>
                <input
                  value={prodForm.comment_template}
                  onChange={(e) => setProdForm({ ...prodForm, comment_template: e.target.value })}
                  placeholder="Mẫu comment tự động (dùng {affiliate_url} để chèn link)"
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs outline-none"
                />
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs"
                >
                  Lưu Sản Phẩm & Đồng Bộ Bio
                </button>
              </form>

              <div className="glass-panel rounded-2xl p-5 space-y-3">
                <h3 className="text-sm font-bold text-white">Kho Sản Phẩm Đang Chạy ({products.length})</h3>
                <div className="space-y-3">
                  {products.map((p) => (
                    <div
                      key={p.id}
                      className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 flex flex-wrap items-center justify-between gap-3"
                    >
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        <span className="px-2.5 py-1 rounded-lg bg-orange-500/20 text-orange-300 font-bold text-xs shrink-0">
                          #{p.code}
                        </span>
                        <div className="min-w-0">
                          <div className="text-xs font-bold text-white truncate">{p.name}</div>
                          <div className="text-[11px] text-slate-400 truncate">
                            {p.platform_name} • <span className="text-emerald-400 font-semibold">{p.price}</span> •{' '}
                            {p.clicks_count} clicks
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => api.toggleProductBio(p.id).then(refreshAll)}
                          className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold border ${
                            p.bio_active
                              ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                              : 'bg-slate-800 text-slate-400 border-slate-700'
                          }`}
                        >
                          {p.bio_active ? 'Đang hiện ở Bio' : 'Đang ẩn Bio'}
                        </button>
                        <button
                          onClick={() => copyText(p.affiliate_url, 'Link Affiliate')}
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
                          title="Copy link"
                        >
                          <ClipboardCopy className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => api.deleteProduct(p.id).then(refreshAll)}
                          className="p-1.5 rounded-lg bg-rose-500/15 hover:bg-rose-500/25 text-rose-300"
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

            {/* Right: Live Mobile Link-in-Bio Preview */}
            <div className="lg:col-span-5 flex flex-col items-center">
              <div className="w-full max-w-[340px] rounded-[40px] border-[6px] border-slate-800 bg-gradient-to-b from-slate-900 via-slate-950 to-indigo-950 p-4 shadow-2xl space-y-3">
                <div className="w-20 h-1.5 bg-slate-800 rounded-full mx-auto mb-2" />
                <div className="text-center space-y-1">
                  <div className="w-14 h-14 rounded-full bg-gradient-to-br from-orange-500 to-pink-600 mx-auto flex items-center justify-center text-xl">
                    🔥
                  </div>
                  <div className="text-sm font-bold text-white">{bioBrandName || 'Deal Ngon Mỗi Ngày'}</div>
                  <div className="text-[11px] text-slate-400">{bioBrandSub}</div>
                </div>

                <input
                  value={bioSearch}
                  onChange={(e) => setBioSearch(e.target.value)}
                  placeholder="Tìm mã #SP01..."
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs outline-none"
                />

                <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
                  {filteredBioProducts.map((p) => (
                    <a
                      key={p.id}
                      href={`/bio/go/${p.id}`}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-2.5 p-2.5 rounded-2xl bg-slate-900/90 border border-slate-800 hover:border-orange-500/50 transition"
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
                          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-orange-500 text-white">
                            #{p.code}
                          </span>
                          <span className="text-[10px] text-sky-300">{p.platform_name}</span>
                        </div>
                        <div className="text-xs font-semibold text-white truncate mt-0.5">{p.name}</div>
                        <div className="text-xs font-bold text-emerald-400">{p.price}</div>
                      </div>
                    </a>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: PUBLISH & AUTO FIRST COMMENT */}
        {activeTab === 'publish' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-6 glass-panel rounded-2xl p-5 space-y-4">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <MessageSquarePlus className="w-4 h-4 text-emerald-400" />
                Đăng Video & Gắn Link Đúng Luật Từng Nền Tảng
              </h2>

              <div>
                <label className="block text-xs text-slate-400 mb-1">Chọn Video Clone Đã Render</label>
                <select
                  value={selectedPubJob?.id || ''}
                  onChange={(e) => setPubJobId(Number(e.target.value))}
                  className="w-full px-3 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs outline-none"
                >
                  {completedJobs.length === 0 && <option value="">Chưa có video hoàn tất — hãy clone ở Tab 2</option>}
                  {completedJobs.map((j) => (
                    <option key={j.id} value={j.id}>
                      Job #{j.id} — #{j.product_code} {j.product_name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Nền tảng đích</label>
                  <select
                    value={pubPlatform}
                    onChange={(e) => setPubPlatform(e.target.value as typeof pubPlatform)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs outline-none"
                  >
                    <option value="facebook_reels">Facebook Reels (Thả link Comment đầu)</option>
                    <option value="instagram_reels">Instagram Reels (Điều hướng Link Bio #MãSP)</option>
                    <option value="threads">Threads (Video + Reply kèm Link)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Kênh / Fanpage đăng bài</label>
                  <input
                    value={pubAccount}
                    onChange={(e) => setPubAccount(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs outline-none"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs text-slate-400">Caption Bài Đăng (Sạch link tránh bóp tương tác)</label>
                  <button
                    onClick={() => copyText(pubCaption, 'Caption')}
                    className="text-[11px] text-sky-400 hover:underline"
                  >
                    Copy Caption
                  </button>
                </div>
                <textarea
                  rows={4}
                  value={pubCaption}
                  onChange={(e) => setPubCaption(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs outline-none"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs text-emerald-400 font-semibold">
                    {pubPlatform === 'instagram_reels'
                      ? 'Ghi chú nhắc tìm Mã SP trên Bio'
                      : pubPlatform === 'threads'
                      ? 'Thread Reply Tự Động Chứa Link Affiliate'
                      : 'Comment Đầu Tiên Tự Động Chứa Link Affiliate'}
                  </label>
                  <button
                    onClick={() => copyText(pubFirstComment, 'Comment Link')}
                    className="text-[11px] text-emerald-400 hover:underline"
                  >
                    Copy Comment Link
                  </button>
                </div>
                <textarea
                  rows={2}
                  value={pubFirstComment}
                  onChange={(e) => setPubFirstComment(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-emerald-950/20 border border-emerald-500/40 text-xs text-emerald-200 outline-none"
                />
              </div>

              <button
                onClick={handlePublish}
                disabled={!selectedPubJob}
                className="w-full py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-slate-950 font-bold text-sm flex items-center justify-center gap-2 disabled:opacity-40"
              >
                <UploadCloud className="w-4 h-4" />
                Xuất Bản & Tự Động Thả Comment / Sync Bio
              </button>
            </div>

            <div className="lg:col-span-6 glass-panel rounded-2xl p-5 space-y-4">
              <h2 className="text-base font-bold text-white">Nhật Ký Đăng & Gắn Link ({publishTasks.length})</h2>
              <div className="space-y-3 max-h-[540px] overflow-y-auto pr-1">
                {publishTasks.length === 0 ? (
                  <div className="py-12 text-center text-xs text-slate-500 border border-dashed border-slate-800 rounded-2xl">
                    Chưa có bài đăng nào. Chọn video hoàn tất bên trái và bấm Xuất Bản!
                  </div>
                ) : (
                  publishTasks.map((t) => (
                    <div key={t.id} className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white">
                          {t.target_platform.toUpperCase()} • {t.account_name}
                        </span>
                        <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px] font-bold">
                          {t.status}
                        </span>
                      </div>
                      <div className="text-slate-400 line-clamp-2">{t.caption}</div>
                      <div className="p-2 rounded-lg bg-emerald-950/30 border border-emerald-500/25 text-emerald-300">
                        <strong>Link Strategy ({t.link_strategy}):</strong> {t.first_comment_text}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: SYSTEM & ARCHITECTURE */}
        {activeTab === 'system' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-6 glass-panel rounded-2xl p-5 space-y-4">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Activity className="w-4 h-4 text-sky-400" />
                Trạng Thái Engine Trên Máy
              </h2>
              <div className="grid grid-cols-2 gap-3 text-xs">
                {[
                  { name: 'FFmpeg Video Composer', ok: status?.ffmpeg_installed, detail: '9:16 + CTA Overlay' },
                  { name: 'yt-dlp Downloader', ok: status?.ytdlp_installed, detail: 'IG / FB / Threads' },
                  { name: 'Playwright Headless', ok: status?.playwright_installed, detail: 'Free Meta Ads Crawl' },
                  { name: 'Crawl4AI Engine', ok: status?.crawl4ai_installed, detail: status?.crawl4ai_installed ? 'Native' : 'Playwright Fallback' },
                ].map((item, idx) => (
                  <div key={idx} className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                    <div className="font-bold text-white flex items-center justify-between">
                      <span>{item.name}</span>
                      <span className={item.ok ? 'text-emerald-400' : 'text-amber-400'}>
                        {item.ok ? 'READY' : 'FALLBACK'}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400 mt-1">{item.detail}</div>
                  </div>
                ))}
              </div>

              <div className="pt-3 border-t border-slate-800 space-y-3">
                <h3 className="text-sm font-bold text-white">Cấu Hình Trang Bio & API Tuỳ Chọn</h3>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Tên Shop / Kênh trên Trang Bio</label>
                  <input
                    value={bioBrandName}
                    onChange={(e) => setBioBrandName(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Mô tả ngắn trên Trang Bio</label>
                  <input
                    value={bioBrandSub}
                    onChange={(e) => setBioBrandSub(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">
                    treg.to API Key (Không bắt buộc — chỉ dùng nếu bạn muốn gọi endpoint trả phí từ treg.to)
                  </label>
                  <input
                    type="password"
                    value={tregApiKey}
                    onChange={(e) => setTregApiKey(e.target.value)}
                    placeholder="Bỏ trống để dùng 100% Crawl4AI / Playwright Free"
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs outline-none"
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
                  className="px-4 py-2 rounded-xl bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-xs"
                >
                  Lưu Cấu Hình
                </button>
              </div>
            </div>

            <div className="lg:col-span-6 glass-panel rounded-2xl p-5 space-y-3 text-xs leading-relaxed text-slate-300">
              <h2 className="text-base font-bold text-white">🦀 Phân Tích: Có Nên Viết Tool Này Bằng Rust Không?</h2>
              <p>
                <strong className="text-amber-300">Kết luận cho MVP:</strong> Không nên viết thuần Rust ngay từ đầu. Kiến trúc{' '}
                <strong className="text-emerald-300">Python FastAPI + React/Tailwind + FFmpeg</strong> nhanh hơn gấp 3–5 lần về tốc độ ra sản phẩm mà hiệu năng xử lý video vẫn đạt tối đa.
              </p>
              <ul className="space-y-2 list-disc pl-4">
                <li>
                  <strong>Crawl & Anti-Bot:</strong> <code className="text-sky-300">Crawl4AI</code>,{' '}
                  <code className="text-sky-300">Playwright</code>, và <code className="text-sky-300">yt-dlp</code> đều là hệ sinh thái Python. Nếu dùng Rust bạn vẫn phải gọi subprocess ra ngoài hoặc tự code lại parser khi Meta/IG đổi DOM hàng tuần.
                </li>
                <li>
                  <strong>Xử lý Video nặng:</strong> Rust không tự encode MP4 nhanh hơn nếu cuối cùng vẫn gọi <code className="text-sky-300">FFmpeg</code> (vốn đã viết bằng C/Assembly tối ưu nhất).
                </li>
                <li>
                  <strong>Khi nào nâng cấp lên Rust?</strong> Khi bạn thương mại hoá thành 1 file <code className="text-orange-300">.exe</code> đóng gói (dùng <strong>Tauri v2</strong> bọc UI React này + Rust quản lý proxy/license/hàng đợi 1000+ token Muse song song).
                </li>
              </ul>
            </div>
          </div>
        )}
      </main>

      {/* Bulk Muse Token Modal */}
      {showBulkModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel rounded-2xl max-w-2xl w-full p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <KeyRound className="w-4 h-4 text-amber-400" />
                Kho Token Muse (Hỗ trợ tài khoản 1 Tỷ Token & Auto-Rotate)
              </h3>
              <button onClick={() => setShowBulkModal(false)} className="text-slate-400 hover:text-white text-xs">
                Đóng ✕
              </button>
            </div>

            <div className="space-y-2">
              <label className="block text-xs text-slate-300">
                Dán danh sách token/cookie hàng loạt (mỗi dòng 1 tài khoản: <code className="text-amber-300">TenAcc|Token|Proxy</code> hoặc chỉ <code className="text-amber-300">Token</code>):
              </label>
              <textarea
                rows={4}
                value={bulkTokenText}
                onChange={(e) => setBulkTokenText(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono outline-none"
              />
              <div className="flex items-center gap-3">
                <label className="text-xs text-slate-400">Giới hạn tuần/acc:</label>
                <input
                  type="number"
                  value={bulkWeeklyLimit}
                  onChange={(e) => setBulkWeeklyLimit(Number(e.target.value) || 50)}
                  className="w-24 px-2.5 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs"
                />
                <button
                  onClick={handleBulkImport}
                  className="ml-auto px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs"
                >
                  Nạp Vào Kho Token
                </button>
              </div>
            </div>

            <div className="border-t border-slate-800 pt-3 max-h-60 overflow-y-auto space-y-2">
              {tokens.map((t) => (
                <div
                  key={t.id}
                  className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between gap-2 text-xs"
                >
                  <div className="min-w-0">
                    <div className="font-bold text-white truncate">{t.label}</div>
                    <div className="text-[11px] text-slate-400">
                      Còn {formatCompact(t.tokens_remaining)} • Tuần: {t.weekly_used}/{t.weekly_limit} •{' '}
                      <span className="font-mono">{t.auth_token_masked}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => api.toggleMuseToken(t.id).then(refreshAll)}
                      className={`px-2 py-1 rounded-lg text-[10px] font-bold ${
                        t.status === 'active'
                          ? 'bg-emerald-500/20 text-emerald-300'
                          : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {t.status}
                    </button>
                    <button
                      onClick={() => api.deleteMuseToken(t.id).then(refreshAll)}
                      className="p-1 rounded-lg bg-rose-500/15 text-rose-300"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
