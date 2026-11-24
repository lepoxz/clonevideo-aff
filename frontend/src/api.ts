import type {
  AffiliateProduct,
  AgentReachFullStatus,
  CloneJob,
  FlowAccount,
  FlowModelOption,
  FlowSceneUnit,
  MarketIntel,
  MetaShop,
  MetaShopProduct,
  MuseToken,
  PublishTask,
  ReaBreakdown,
  SystemStatus,
  ViralVideo,
} from './types';

async function request<T>(path: string, options?: RequestInit, timeoutMs = 45000): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(path, {
      headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) },
      ...options,
      signal: options?.signal ?? controller.signal,
    });
    if (!res.ok) {
      let msg = `HTTP ${res.status}`;
      try {
        const err = await res.json();
        msg = err.detail || err.message || msg;
      } catch {
        // ignore
      }
      throw new Error(msg);
    }
    return (await res.json()) as T;
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new Error(`Yêu cầu quá thời gian chờ (${Math.round(timeoutMs / 1000)}s) — hệ thống đã tự ngắt để tránh treo.`);
    }
    throw err;
  } finally {
    window.clearTimeout(timer);
  }
}

export const api = {
  getStatus: () => request<SystemStatus>('/api/system/status'),
  updateSettings: (payload: Record<string, string>) =>
    request<{ ok: boolean; settings: Record<string, string> }>('/api/system/settings', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getVideos: (platform = 'all', search = '') => {
    const params = new URLSearchParams();
    if (platform) params.set('platform', platform);
    if (search) params.set('search', search);
    return request<{ videos: ViralVideo[] }>(`/api/videos?${params.toString()}`);
  },
  crawlVideos: (payload: { keyword: string; platform: string; engine: string; country: string; match_type?: string }) =>
    request<{ keyword: string; engine_used: string; count: number; diagnostics: string[]; videos: ViralVideo[] }>(
      '/api/videos/crawl',
      { method: 'POST', body: JSON.stringify(payload) },
      95000
    ),
  inspectUrl: (url: string, download = true) =>
    request<{ ok: boolean; downloaded: boolean; warning?: string; video: ViralVideo }>(
      '/api/videos/inspect-url',
      {
        method: 'POST',
        body: JSON.stringify({ url, download }),
      },
      95000
    ),
  decomposeVideoRea: (videoId: number, useVlm?: boolean) =>
    request<{ ok: boolean; video: ViralVideo; breakdown: ReaBreakdown }>(
      `/api/videos/${videoId}/rea-decompose`,
      {
        method: 'POST',
        body: JSON.stringify(useVlm === undefined ? {} : { use_vlm: useVlm }),
      },
      150000
    ),
  fetchReaVlmModels: (base_url: string, api_key: string) =>
    request<{
      ok: boolean;
      base_url: string;
      count: number;
      models: string[];
      recommended: string[];
      error?: string;
    }>('/api/rea-video/fetch-models', {
      method: 'POST',
      body: JSON.stringify({ base_url, api_key }),
    }),
  ensureVideoMp4: (videoId: number) =>
    request<{ ok: boolean; play_url: string; video: ViralVideo }>(
      `/api/videos/${videoId}/ensure-mp4`,
      { method: 'POST' },
      95000
    ),
  analyzeVideoAi: (videoId: number) =>
    request<{ ok: boolean; video: ViralVideo }>(
      `/api/videos/${videoId}/analyze-ai`,
      { method: 'POST' },
      60000
    ),
  evaluateVideoPotential: (
    videoId: number,
    payload?: { custom_query?: string; country?: string; deep_spy?: boolean }
  ) =>
    request<{ ok: boolean; video: ViralVideo; market_intel: MarketIntel }>(
      `/api/videos/${videoId}/evaluate-potential`,
      {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      },
      95000
    ),
  evaluateVideosPotentialBatch: (payload?: { video_ids?: number[]; limit?: number; country?: string }) =>
    request<{ ok: boolean; evaluated_count: number; deep_spied_count: number; videos: ViralVideo[] }>(
      '/api/videos/evaluate-potential-batch',
      {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      },
      180000
    ),

  getMetaShops: (params?: { search?: string; country?: string; platform?: string }) => {
    const qs = new URLSearchParams();
    if (params?.search) qs.set('search', params.search);
    if (params?.country) qs.set('country', params.country);
    if (params?.platform) qs.set('platform', params.platform);
    const tail = qs.toString() ? `?${qs.toString()}` : '';
    return request<{ shops: MetaShop[] }>(`/api/meta-shops${tail}`);
  },
  getMetaShopDetail: (shopId: number) =>
    request<{ ok: boolean; shop: MetaShop; products: MetaShopProduct[] }>(`/api/meta-shops/${shopId}`),
  searchMetaShops: (payload: { query: string; country?: string; platform?: string; limit?: number }) =>
    request<{
      ok: boolean;
      query: string;
      country: string;
      platform: string;
      total_market_ads: number;
      count: number;
      shops: MetaShop[];
    }>(
      '/api/meta-shops/search',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      120000
    ),
  scanMetaShopProducts: (payload: {
    page_id?: string;
    shop_query?: string;
    shop_id?: number;
    country?: string;
    limit?: number;
  }) =>
    request<{ ok: boolean; shop: MetaShop; products: MetaShopProduct[] }>(
      '/api/meta-shops/products',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      120000
    ),
  importMetaShopProductVideo: (shopProductId: number) =>
    request<{ ok: boolean; video: ViralVideo }>(
      `/api/meta-shops/products/${shopProductId}/import-video`,
      { method: 'POST' },
      95000
    ),

  getAgentReachStatus: () => request<AgentReachFullStatus>('/api/agent-reach/status'),
  agentReachChannelAction: (channel: string, operation: string) =>
    request<{ ok: boolean; status?: string; message?: string; error?: { code?: string; message?: string } }>(
      '/api/agent-reach/channel-action',
      { method: 'POST', body: JSON.stringify({ channel, operation }) },
      60000
    ),
  agentReachBrowserAction: (operation: string, param = '') =>
    request<{ ok: boolean; result?: unknown; error?: { code?: string; message?: string } }>(
      '/api/agent-reach/browser-action',
      { method: 'POST', body: JSON.stringify({ operation, param }) }
    ),
  agentReachConfigure: (key: string, value: string) =>
    request<{ ok: boolean; error?: { code?: string; message?: string } }>('/api/agent-reach/configure', {
      method: 'POST',
      body: JSON.stringify({ key, value }),
    }),
  agentReachExecute: (payload: {
    channel: string;
    action: string;
    query?: string;
    limit?: number;
    save_to_videos?: boolean;
    country?: string;
  }) =>
    request<{
      ok: boolean;
      channel: string;
      action: string;
      command: string;
      diagnostic?: string | null;
      saved_count: number;
      videos: ViralVideo[];
      raw_response: unknown;
    }>(
      '/api/agent-reach/execute',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      95000
    ),

  getMuseTokens: () =>
    request<{ tokens: MuseToken[]; summary: SystemStatus['muse_pool'] }>('/api/muse-tokens'),
  bulkImportTokens: (raw_tokens: string, weekly_limit = 50) =>
    request<{ ok: boolean; imported: number; tokens: MuseToken[] }>('/api/muse-tokens/bulk', {
      method: 'POST',
      body: JSON.stringify({ raw_tokens, weekly_limit }),
    }),
  toggleMuseToken: (id: number) =>
    request<{ ok: boolean; token: MuseToken }>(`/api/muse-tokens/${id}/toggle`, { method: 'PATCH' }),
  deleteMuseToken: (id: number) =>
    request<{ ok: boolean }>(`/api/muse-tokens/${id}`, { method: 'DELETE' }),

  getFlowAccounts: () =>
    request<{
      accounts: FlowAccount[];
      models: FlowModelOption[];
      summary: NonNullable<SystemStatus['flow_pool']>;
    }>('/api/flow-accounts'),
  loginFlowBrowser: (payload?: { account_id?: number; label?: string; proxy?: string; tier?: string }) =>
    request<{ ok: boolean; account_id: number; message: string; account: FlowAccount }>(
      '/api/flow-accounts/login-browser',
      {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }
    ),
  openFlowBrowser: (accountId: number) =>
    request<{ ok: boolean; message: string }>(`/api/flow-accounts/${accountId}/open-browser`, {
      method: 'POST',
    }),
  verifyFlowAccount: (accountId: number) =>
    request<{ ok: boolean; status: string; message: string; account: FlowAccount }>(
      `/api/flow-accounts/${accountId}/verify`,
      { method: 'POST' },
      60000
    ),
  bulkImportFlowAccounts: (raw_accounts: string, weekly_limit = 50, tier = 'Flow Pro') =>
    request<{
      ok: boolean;
      imported: number;
      accounts: FlowAccount[];
      summary: NonNullable<SystemStatus['flow_pool']>;
    }>('/api/flow-accounts/bulk', {
      method: 'POST',
      body: JSON.stringify({ raw_accounts, weekly_limit, tier }),
    }),
  toggleFlowAccount: (accountId: number) =>
    request<{ ok: boolean; account: FlowAccount }>(`/api/flow-accounts/${accountId}/toggle`, {
      method: 'PATCH',
    }),
  deleteFlowAccount: (accountId: number) =>
    request<{ ok: boolean }>(`/api/flow-accounts/${accountId}`, {
      method: 'DELETE',
    }),
  syncFlowModels: () =>
    request<{
      ok: boolean;
      count: number;
      new_discovered: number;
      models: FlowModelOption[];
    }>('/api/flow/sync-models', { method: 'POST' }, 45000),
  generateFlowPrompt: (payload: {
    video_id: number;
    clone_mode: string;
    custom_hint?: string;
    flow_model?: string;
  }) =>
    request<{
      ok: boolean;
      video_id: number;
      product_en?: string;
      veo_prompt: string;
      scene_units?: FlowSceneUnit[];
      reference_frame_url: string;
    }>(
      '/api/flow/generate-prompt',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      95000
    ),

  getProducts: () => request<{ products: AffiliateProduct[] }>('/api/products'),
  createProduct: (payload: Partial<AffiliateProduct>) =>
    request<{ ok: boolean; product: AffiliateProduct }>('/api/products', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  toggleProductBio: (id: number) =>
    request<{ ok: boolean; product: AffiliateProduct }>(`/api/products/${id}/toggle-bio`, { method: 'PATCH' }),
  deleteProduct: (id: number) =>
    request<{ ok: boolean }>(`/api/products/${id}`, { method: 'DELETE' }),

  getCloneJobs: () => request<{ jobs: CloneJob[] }>('/api/clone-jobs'),
  createCloneJob: (payload: {
    source_video_id: number;
    product_id: number;
    clone_mode: string;
    prompt_script: string;
    cta_position: string;
    link_placement_mode: string;
    anti_duplicate: boolean;
    batch_count: number;
    flow_account_id?: number | null;
    flow_model?: string;
    veo_prompt?: string;
    scene_plan?: FlowSceneUnit[];
  }) =>
    request<{ ok: boolean; jobs: CloneJob[] }>('/api/clone-jobs', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  retryCloneJob: (jobId: number, refreshPlan = true) =>
    request<{ ok: boolean; job: CloneJob }>(`/api/clone-jobs/${jobId}/retry?refresh_plan=${refreshPlan ? 'true' : 'false'}`, {
      method: 'POST',
    }),
  deleteCloneJob: (jobId: number) =>
    request<{ ok: boolean }>(`/api/clone-jobs/${jobId}`, {
      method: 'DELETE',
    }),

  getPublishTasks: () => request<{ tasks: PublishTask[] }>('/api/publish-tasks'),
  previewPublishCopy: (productId: number, targetPlatform: string, customHook = '') => {
    const params = new URLSearchParams({
      product_id: String(productId),
      target_platform: targetPlatform,
      custom_hook: customHook,
    });
    return request<{ caption: string; first_comment: string; link_strategy: string }>(
      `/api/publish-tasks/preview?${params.toString()}`,
      { method: 'POST' }
    );
  },
  createPublishTask: (payload: {
    clone_job_id: number;
    product_id: number;
    target_platform: string;
    account_name: string;
    caption: string;
    first_comment_text: string;
  }) =>
    request<{ ok: boolean; task: PublishTask }>('/api/publish-tasks', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};
