import type {
  AffiliateProduct,
  CloneJob,
  MuseToken,
  PublishTask,
  SystemStatus,
  ViralVideo,
} from './types';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) },
    ...options,
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
  return res.json() as Promise<T>;
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
  crawlVideos: (payload: { keyword: string; platform: string; engine: string; country: string }) =>
    request<{ keyword: string; engine_used: string; count: number; diagnostics: string[]; videos: ViralVideo[] }>(
      '/api/videos/crawl',
      { method: 'POST', body: JSON.stringify(payload) }
    ),
  inspectUrl: (url: string, download = true) =>
    request<{ ok: boolean; downloaded: boolean; warning?: string; video: ViralVideo }>('/api/videos/inspect-url', {
      method: 'POST',
      body: JSON.stringify({ url, download }),
    }),

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
  }) =>
    request<{ ok: boolean; jobs: CloneJob[] }>('/api/clone-jobs', {
      method: 'POST',
      body: JSON.stringify(payload),
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
