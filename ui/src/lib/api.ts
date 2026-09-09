import {
  OTSConfig,
  SearchResultItem,
  DownloadQueueItem,
  LogEntry,
  AccountItem,
} from "../types";
import { AppSettings } from "./settings";

const config = {
  // Production UI is served by FastAPI, so use the current browser origin.
  // This also works behind Unraid's host/IP and reverse proxies.
  api_url: import.meta.env.VITE_API_URL || window.location.origin,
};
const STORAGE_KEY = "OTS_FASTAPI_URL";
const DEFAULT_URL = config.api_url;

export function getTargetBackendUrl(): string {
  if (typeof window === "undefined") return DEFAULT_URL;
  return localStorage.getItem(STORAGE_KEY) || DEFAULT_URL;
}

export function setTargetBackendUrl(url: string): void {
  if (typeof window === "undefined") return;
  const cleaned = url.trim().replace(/\/$/, "");
  if (!cleaned) {
    localStorage.removeItem(STORAGE_KEY);
  } else {
    localStorage.setItem(STORAGE_KEY, cleaned);
  }
}

function getEndpoint(path: string): string {
  const base = getTargetBackendUrl().replace(/\/$/, "");
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return `${base}${cleanPath}`;
}

async function request(
  path: string,
  options: RequestInit = {},
): Promise<Response> {
  const url = getEndpoint(path);
  const headers = new Headers(options.headers || {});
  if (
    !headers.has("Content-Type") &&
    options.body &&
    !(typeof FormData !== "undefined" && options.body instanceof FormData)
  ) {
    headers.set("Content-Type", "application/json");
  }
  return fetch(url, { ...options, headers });
}

export async function checkServerHealth(): Promise<{
  status: "online" | "offline";
  version?: string;
  target: string;
}> {
  const target = getTargetBackendUrl();
  try {
    const res = await request("/config/get");
    if (!res.ok) throw new Error("Status check failed");
    const config = await res.json();
    return {
      status: "online",
      version: config.version || "FastAPI Engine",
      target,
    };
  } catch (err) {
    return { status: "offline", target };
  }
}

export async function searchMedia(
  query: string,
  filters?: Record<string, boolean>,
): Promise<boolean> {
  try {
    const qParam = query ? `?q=${encodeURIComponent(query)}` : "";
    const res = await request(`/query/url${qParam}`, {
      method: "POST",
      body: JSON.stringify(filters || {}),
    });
    if (!res.ok) throw new Error("Search request failed");
    return res.ok;
  } catch (err) {
    console.error("Search API connection failed:", err);
    throw err;
  }
}

export async function searchCatalog(
  query: string,
  filters?: Record<string, boolean>,
  services?: string[],
): Promise<SearchResultItem[]> {
  const qParam = query ? `?q=${encodeURIComponent(query)}` : "";
  const res = await request(`/search${qParam}`, {
    method: "POST",
    body: JSON.stringify({
      ...(filters || {}),
      ...(services ? { services } : {}),
    }),
  });
  if (!res.ok) throw new Error("Catalogue search failed");
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

export async function fetchDownloadQueue(): Promise<DownloadQueueItem[]> {
  try {
    const res = await request("/queue/downloads");
    if (!res.ok) throw new Error("Failed to fetch queue");
    const data = await res.json();
    return Array.isArray(data)
      ? data
      : typeof data === "object" && data !== null
        ? Object.values(data)
        : [];
  } catch (err) {
    console.error("Fetch download queue failed:", err);
    return [];
  }
}

export async function fetchDownloadState(): Promise<{
  paused: boolean;
  active: number;
  speed: number;
  eta_seconds: number;
}> {
  try {
    const res = await request("/queue/downloads/state");
    if (!res.ok) throw new Error("Failed to fetch download state");
    return await res.json();
  } catch (err) {
    console.error("Fetch download state failed:", err);
    return { paused: false, active: 0, speed: 0, eta_seconds: 0 };
  }
}

export async function setDownloadsPaused(paused: boolean): Promise<boolean> {
  try {
    const res = await request(
      `/queue/downloads/pause?paused=${paused ? "true" : "false"}`,
      { method: "POST" },
    );
    if (!res.ok) return false;
    const body = await res.json().catch(() => null);
    return body?.success ?? body === true;
  } catch (err) {
    console.error("Set download pause failed:", err);
    return false;
  }
}

export async function reorderDownloadQueue(
  local_ids: string[],
): Promise<boolean> {
  try {
    const res = await request("/queue/downloads/reorder", {
      method: "POST",
      body: JSON.stringify({ local_ids }),
    });
    return res.ok;
  } catch (err) {
    console.error("Reorder download queue failed:", err);
    return false;
  }
}

export type QueueBatchAction =
  | "pause"
  | "resume"
  | "retry"
  | "cancel"
  | "delete"
  | "priority"
  | "profile";

export async function batchDownloadQueue(
  local_ids: string[],
  action: QueueBatchAction,
  options: { priority?: number; profile_id?: string } = {},
): Promise<boolean> {
  try {
    const res = await request("/queue/downloads/batch", {
      method: "POST",
      body: JSON.stringify({ local_ids, action, ...options }),
    });
    return res.ok;
  } catch (err) {
    console.error(`Batch queue action (${action}) failed:`, err);
    throw new Error("Failed to fetch queue");
  }
}

export async function fetchPendingQueue(): Promise<SearchResultItem[]> {
  try {
    const res = await request("/queue/pending");
    if (!res.ok) throw new Error("Failed to fetch queue");
    const data = await res.json();
    return data;
  } catch (err) {
    console.error("Fetch download queue failed:", err);
    return [];
  }
}

export async function performPendingAction(
  local_id: string,
  action: "cancel",
): Promise<boolean> {
  try {
    const res = await request(
      `/queue/pending/action?lid=${encodeURIComponent(local_id)}&action=${encodeURIComponent(action)}`,
      {
        method: "POST",
      },
    );
    return res.ok;
  } catch (err) {
    console.error(`Perform queue action (${action}) failed:`, err);
    return false;
  }
}

export async function verifyDownloadQueue(
  local_ids: string[] = [],
  retry = true,
): Promise<{
  checked: number;
  healthy: number;
  corrupt: number;
  retried: number;
}> {
  try {
    const res = await request("/queue/downloads/verify", {
      method: "POST",
      body: JSON.stringify({ local_ids, retry }),
    });
    if (!res.ok) throw new Error("Queue verification failed");
    return await res.json();
  } catch (err) {
    console.error("Verify download queue failed:", err);
    return { checked: 0, healthy: 0, corrupt: 0, retried: 0 };
  }
}

export interface DownloadProfile {
  id: string;
  name: string;
  format: string;
  bitrate: string;
  download_path: string;
}

export async function fetchDownloadProfiles(): Promise<{
  active: string;
  profiles: DownloadProfile[];
}> {
  try {
    const res = await request("/profiles");
    if (!res.ok) throw new Error("Failed to fetch download profiles");
    return await res.json();
  } catch (err) {
    console.error("Fetch download profiles failed:", err);
    return { active: "", profiles: [] };
  }
}

export async function setActiveDownloadProfile(
  profile_id: string,
): Promise<boolean> {
  try {
    const res = await request("/profiles/active", {
      method: "POST",
      body: JSON.stringify({ profile_id }),
    });
    if (!res.ok) return false;
    const data = await res.json().catch(() => ({}));
    return data.success !== false;
  } catch (err) {
    console.error("Set active download profile failed:", err);
    return false;
  }
}

export async function saveDownloadProfile(
  profile: DownloadProfile,
): Promise<DownloadProfile | null> {
  try {
    const res = await request("/profiles", {
      method: "POST",
      body: JSON.stringify(profile),
    });
    if (!res.ok) throw new Error("Save profile failed");
    const data = await res.json();
    return data?.success === false ? null : data;
  } catch (err) {
    console.error("Save download profile failed:", err);
    return null;
  }
}

export async function deleteDownloadProfile(
  profile_id: string,
): Promise<boolean> {
  try {
    const res = await request(`/profiles/${encodeURIComponent(profile_id)}`, {
      method: "DELETE",
    });
    if (!res.ok) return false;
    const data = await res.json().catch(() => ({}));
    return data.success !== false;
  } catch (err) {
    console.error("Delete download profile failed:", err);
    return false;
  }
}

export interface LibraryItem {
  id: string;
  path: string;
  relative_path: string;
  filename: string;
  format: string;
  size: number;
  modified_at: number;
  title: string;
  artist: string;
  album_artist?: string;
  album: string;
  genre: string;
  year: string;
  release_date?: string;
  lyrics?: string;
  has_artwork?: boolean;
  metadata_complete?: boolean;
  metadata_error?: string;
  track_number?: number | null;
  disc_number?: number | null;
  duration_seconds?: number | null;
  bitrate?: number | null;
  sample_rate?: number | null;
  channels?: number | null;
  duplicate_count?: number;
  is_duplicate?: boolean;
  source_url?: string;
  source_service?: string;
  source_type?: string;
  source_id?: string;
  playlist_name?: string;
  playlist_by?: string;
}

export interface LibraryResponse {
  items: LibraryItem[];
  count: number;
  duplicate_count: number;
  roots: string[];
  storage_used?: number;
  scanned_at: number;
}

export interface LibraryFilters {
  missingArtwork?: boolean;
  failedMetadata?: boolean;
  format?: string;
  artist?: string;
  genre?: string;
  dateFrom?: string;
  dateTo?: string;
}

const dateToTimestamp = (value?: string, endOfDay = false) => {
  if (!value) return "";
  const date = new Date(`${value}T${endOfDay ? "23:59:59" : "00:00:00"}`);
  return Number.isNaN(date.getTime())
    ? ""
    : String(Math.floor(date.getTime() / 1000));
};

const libraryParams = (
  query: string,
  sort: string,
  sortDescending: boolean,
  duplicatesOnly: boolean,
  filters: LibraryFilters,
) => {
  const params = new URLSearchParams({
    q: query,
    sort,
    sort_descending: String(sortDescending),
    duplicates_only: String(duplicatesOnly),
  });
  if (filters.missingArtwork) params.set("missing_artwork", "true");
  if (filters.failedMetadata) params.set("failed_metadata", "true");
  if (filters.format) params.set("file_format", filters.format);
  if (filters.artist) params.set("artist", filters.artist);
  if (filters.genre) params.set("genre", filters.genre);
  const from = dateToTimestamp(filters.dateFrom);
  const to = dateToTimestamp(filters.dateTo, true);
  if (from) params.set("date_from", from);
  if (to) params.set("date_to", to);
  return params;
};

export function getLibraryCoverUrl(path: string, cacheKey?: number): string {
  const params = new URLSearchParams({ path });
  if (cacheKey) params.set("v", String(cacheKey));
  return `${getTargetBackendUrl()}/library/cover?${params.toString()}`;
}

export async function fetchLibrary(
  query = "",
  sort = "artist",
  sortDescending = false,
  duplicatesOnly = false,
  filters: LibraryFilters = {},
): Promise<LibraryResponse> {
  try {
    const params = libraryParams(
      query,
      sort,
      sortDescending,
      duplicatesOnly,
      filters,
    );
    const res = await request(`/library?${params.toString()}`);
    if (!res.ok) throw new Error("Failed to fetch local library");
    return await res.json();
  } catch (err) {
    console.error("Fetch local library failed:", err);
    return {
      items: [],
      count: 0,
      duplicate_count: 0,
      roots: [],
      storage_used: 0,
      scanned_at: 0,
    };
  }
}

export async function scanLibrary(
  query = "",
  sort = "artist",
  sortDescending = false,
  duplicatesOnly = false,
  filters: LibraryFilters = {},
): Promise<LibraryResponse> {
  try {
    const params = libraryParams(
      query,
      sort,
      sortDescending,
      duplicatesOnly,
      filters,
    );
    const res = await request(`/library/scan?${params.toString()}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to scan local library");
    return await res.json();
  } catch (err) {
    console.error("Scan local library failed:", err);
    return {
      items: [],
      count: 0,
      duplicate_count: 0,
      roots: [],
      storage_used: 0,
      scanned_at: 0,
    };
  }
}

export async function verifyLibraryFiles(
  paths: string[] = [],
): Promise<{ checked: number; healthy: number; corrupt: number }> {
  try {
    const res = await request("/library/verify", {
      method: "POST",
      body: JSON.stringify({ paths }),
    });
    if (!res.ok) throw new Error("Library verification failed");
    return await res.json();
  } catch (err) {
    console.error("Verify library files failed:", err);
    return { checked: 0, healthy: 0, corrupt: 0 };
  }
}

export async function fetchMissingLibraryItems(
  query = "",
): Promise<LibraryItem[]> {
  try {
    const params = new URLSearchParams({ q: query });
    const res = await request(`/library/missing?${params.toString()}`);
    if (!res.ok) throw new Error("Failed to fetch missing library items");
    const data = await res.json();
    return Array.isArray(data?.items) ? data.items : [];
  } catch (err) {
    console.error("Fetch missing library items failed:", err);
    return [];
  }
}

export async function openLibraryItem(
  path: string,
  action: "play" | "folder" = "folder",
): Promise<boolean> {
  try {
    const res = await request("/library/open", {
      method: "POST",
      body: JSON.stringify({ path, action }),
    });
    return res.ok;
  } catch (err) {
    console.error("Open library item failed:", err);
    return false;
  }
}

export async function renameLibraryItem(
  path: string,
  new_name: string,
): Promise<LibraryItem | null> {
  try {
    const res = await request("/library/rename", {
      method: "POST",
      body: JSON.stringify({ path, new_name }),
    });
    if (!res.ok) {
      let detail = "Could not rename that file.";
      try {
        const payload = await res.json();
        if (typeof payload?.detail === "string") detail = payload.detail;
      } catch {
        // Keep the useful fallback when the server did not return JSON.
      }
      throw new Error(detail);
    }
    const data = await res.json();
    return data.item || null;
  } catch (err) {
    console.error("Rename library item failed:", err);
    throw err;
  }
}

export async function updateLibraryMetadata(
  path: string,
  changes: Partial<
    Pick<
      LibraryItem,
      | "title"
      | "artist"
      | "album"
      | "genre"
      | "year"
      | "release_date"
      | "lyrics"
    >
  > & {
    album_artist?: string;
    track_number?: string | number;
    disc_number?: string | number;
  },
): Promise<LibraryItem | null> {
  try {
    const res = await request("/library/metadata", {
      method: "POST",
      body: JSON.stringify({ path, ...changes }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.item || null;
  } catch (err) {
    console.error("Update library metadata failed:", err);
    return null;
  }
}

export async function uploadLibraryCover(
  path: string,
  file: File,
): Promise<LibraryItem | null> {
  try {
    const form = new FormData();
    form.append("path", path);
    form.append("cover", file);
    const res = await request("/library/cover", { method: "POST", body: form });
    if (!res.ok) return null;
    const data = await res.json();
    return data.item || null;
  } catch (err) {
    console.error("Update library cover failed:", err);
    return null;
  }
}

export async function createLibraryM3U(
  name: string,
  paths: string[],
): Promise<string | null> {
  try {
    const res = await request("/library/m3u", {
      method: "POST",
      body: JSON.stringify({ name, paths }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.path || null;
  } catch (err) {
    console.error("Create library playlist failed:", err);
    return null;
  }
}

export async function requeueMissingLibraryItem(
  path: string,
): Promise<boolean> {
  try {
    const res = await request("/library/requeue", {
      method: "POST",
      body: JSON.stringify({ path }),
    });
    return res.ok;
  } catch (err) {
    console.error("Requeue missing library item failed:", err);
    return false;
  }
}

export async function removeMissingLibraryItems(
  paths: string[] = [],
): Promise<number> {
  try {
    const res = await request("/library/missing", {
      method: "DELETE",
      body: JSON.stringify({ paths }),
    });
    if (!res.ok) throw new Error("Failed to remove missing library entries");
    const data = await res.json();
    return Number(data?.removed || 0);
  } catch (err) {
    console.error("Remove missing library items failed:", err);
    return 0;
  }
}

export async function clearQueueItems(
  status: "Downloaded" | "Failed" | "all",
): Promise<boolean> {
  try {
    const statusParam = status === "all" ? "All" : status;
    const res = await request(
      `/queue/downloads/clear?status=${encodeURIComponent(statusParam)}`,
    );
    return res.ok;
  } catch (err) {
    console.error("Clear queue failed:", err);
    return false;
  }
}

export async function triggerRetryFailed(): Promise<{ success: boolean }> {
  try {
    const res = await request("/queue/downloads/retryfailed");
    if (!res.ok) return { success: false };
    return await res.json().catch(() => ({ success: true }));
  } catch (err) {
    console.error("Retry failed API error:", err);
    return { success: false };
  }
}

export async function performQueueAction(
  local_id: string,
  action: "cancel" | "delete" | "retry",
): Promise<boolean> {
  try {
    const res = await request(
      `/queue/downloads/action?lid=${encodeURIComponent(local_id)}&action=${encodeURIComponent(action)}`,
      {
        method: "POST",
      },
    );
    if (!res.ok) return false;
    const body = await res.json().catch(() => null);
    return body?.success ?? body === true;
  } catch (err) {
    console.error(`Perform queue action (${action}) failed:`, err);
    return false;
  }
}

export async function fetchOTSConfig(): Promise<OTSConfig | null> {
  try {
    const res = await request("/config/get");
    if (!res.ok) throw new Error("Failed to fetch configuration");
    return await res.json();
  } catch (err) {
    console.error("Fetch OTS config failed:", err);
    return null;
  }
}

export async function updateOTSConfigValue<K extends keyof AppSettings>(
  key: K,
  value: AppSettings[K]
): Promise<boolean> {
  const payload = {
    [key]: value,
  };

  const response = await request(`/config/set`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json();
    console.error(
      errorData.detail 
        ? (typeof errorData.detail === "string" ? errorData.detail : JSON.stringify(errorData.detail))
        : `Failed to update setting '${String(key)}' (Status ${response.status})`
    );
    return false
  } else {
    return response.ok
  }
}

export async function saveOTSConfig(): Promise<boolean> {
  try {
    const res = await request("/config/save", { method: "POST" });
    return res.ok;
  } catch (err) {
    console.error("Save config failed:", err);
    return false;
  }
}

export async function resetOTSConfig(): Promise<OTSConfig | null> {
  try {
    const res = await request("/config/reset", { method: "POST" });
    if (!res.ok) throw new Error("Reset config failed");
    return await res.json();
  } catch (err) {
    console.error("Reset config failed:", err);
    return null;
  }
}

export async function fetchAccounts(): Promise<AccountItem[]> {
  try {
    const res = await request("/accounts/get");
    if (!res.ok) throw new Error("Failed to fetch accounts");
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch (err) {
    console.error("Fetch accounts failed:", err);
    return [];
  }
}

export interface AccountHealth {
  healthy: boolean;
  spotify: {
    configured: boolean;
    connected: boolean;
    status: string;
    connect_service?: { running: boolean; device_name: string; port: number };
  };
  configured_accounts: number;
  authenticated_accounts: number;
  missing_services: string[];
  checked_at: number;
}

export async function fetchAccountHealth(): Promise<AccountHealth> {
  try {
    const res = await request("/accounts/health");
    if (!res.ok) throw new Error("Failed to fetch account health");
    return await res.json();
  } catch (err) {
    console.error("Fetch account health failed:", err);
    return {
      healthy: false,
      spotify: { configured: false, connected: false, status: "Unavailable" },
      configured_accounts: 0,
      authenticated_accounts: 0,
      missing_services: [],
      checked_at: 0,
    };
  }
}

export async function reconnectAccounts(): Promise<boolean> {
  try {
    const res = await request("/accounts/reconnect", { method: "POST" });
    return res.ok;
  } catch (err) {
    console.error("Reconnect accounts failed:", err);
    return false;
  }
}

export interface SystemDiagnostics {
  backend: { status: string; version: string };
  workers: Record<string, boolean>;
  queue: {
    pending: number;
    parsing: number;
    downloads: number;
    statuses: Record<string, number>;
    paused: boolean;
  };
  ffmpeg: { path: string; available: boolean };
  disk: { total: number; free: number; used: number };
  rate_limit: {
    active: boolean;
    host: string;
    seconds_remaining: number;
    count: number;
  };
  spotify_api: {
    configured: boolean;
    connected: boolean;
    status: string;
    rate_limited: boolean;
    seconds_remaining: number;
    connect_service?: { running: boolean; device_name: string; port: number };
  };
}

export interface UpdateAsset {
  name: string;
  size: number;
  download_url: string;
  platform: string;
}

export interface UpdateInfo {
  repository: string;
  current_version: string;
  latest_version: string;
  update_available: boolean;
  release_name: string;
  release_url: string;
  release_notes: string;
  published_at: string | null;
  prerelease: boolean;
  assets: UpdateAsset[];
  recommended_asset: UpdateAsset | null;
  install_supported: boolean;
  checked_at: number;
  error: string;
}

export async function fetchUpdateInfo(
  force = false,
): Promise<UpdateInfo | null> {
  try {
    const suffix = force ? "?force=true" : "";
    const res = await request(`/updates/check${suffix}`);
    if (!res.ok) throw new Error("Failed to check for updates");
    return await res.json();
  } catch (err) {
    console.error("Fetch update information failed:", err);
    return null;
  }
}

export async function fetchSystemDiagnostics(): Promise<SystemDiagnostics | null> {
  try {
    const res = await request("/system/diagnostics");
    if (!res.ok) throw new Error("Failed to fetch diagnostics");
    return await res.json();
  } catch (err) {
    console.error("Fetch system diagnostics failed:", err);
    return null;
  }
}

export interface DownloadStatistics {
  totals: {
    downloads: number;
    bytes: number;
    success: number;
    failed: number;
    success_rate: number;
  };
  formats: Record<string, number>;
  history: Array<{
    id: string;
    timestamp: number;
    status: string;
    success: boolean;
    bytes: number;
    format: string;
    name: string;
    artist: string;
    error?: string;
  }>;
  storage_used: number;
  library_tracks: number;
  queue_counts: Record<string, number>;
}

export async function fetchDownloadStatistics(): Promise<DownloadStatistics | null> {
  try {
    const res = await request("/statistics");
    if (!res.ok) throw new Error("Failed to fetch download statistics");
    return await res.json();
  } catch (err) {
    console.error("Fetch download statistics failed:", err);
    return null;
  }
}

export async function clearDownloadStatistics(): Promise<boolean> {
  try {
    const res = await request("/statistics/clear", { method: "POST" });
    if (!res.ok) throw new Error("Failed to clear download statistics");
    return true;
  } catch (err) {
    console.error("Clear download statistics failed:", err);
    return false;
  }
}

export async function exportBackup(): Promise<Record<string, unknown> | null> {
  try {
    const res = await request("/backup/export");
    if (!res.ok) throw new Error("Failed to export backup");
    return await res.json();
  } catch (err) {
    console.error("Export backup failed:", err);
    return null;
  }
}

export async function saveBackupFile(
  backup: Record<string, unknown>,
  directory = "",
): Promise<string | null> {
  try {
    const res = await request("/backup/export-file", {
      method: "POST",
      body: JSON.stringify({ backup, directory }),
    });
    if (!res.ok) throw new Error("Failed to save backup file");
    return String((await res.json()).path || "") || null;
  } catch (err) {
    console.error("Save backup file failed:", err);
    return null;
  }
}

export async function fetchExportDirectory(): Promise<string> {
  try {
    const res = await request("/exports/location");
    if (!res.ok) throw new Error("Failed to fetch export location");
    return String((await res.json()).directory || "");
  } catch (err) {
    console.error("Fetch export location failed:", err);
    return "";
  }
}

export async function saveTextExport(
  filename: string,
  content: string,
  directory = "",
): Promise<string | null> {
  try {
    const res = await request("/exports/write", {
      method: "POST",
      body: JSON.stringify({ filename, content, directory }),
    });
    if (!res.ok) throw new Error("Failed to save export file");
    return String((await res.json()).path || "") || null;
  } catch (err) {
    console.error("Save text export failed:", err);
    return null;
  }
}

export async function openExportFolder(
  playlistBackups = false,
): Promise<string | null> {
  try {
    const res = await request("/exports/open-folder", {
      method: "POST",
      body: JSON.stringify({ playlist_backups: playlistBackups }),
    });
    if (!res.ok) throw new Error("Failed to open export folder");
    return String((await res.json()).path || "") || null;
  } catch (err) {
    console.error("Open export folder failed:", err);
    return null;
  }
}

export async function importBackup(
  payload: Record<string, unknown>,
): Promise<boolean> {
  try {
    const res = await request("/backup/import", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return res.ok;
  } catch (err) {
    console.error("Import backup failed:", err);
    return false;
  }
}

export async function exportSettings(): Promise<Record<
  string,
  unknown
> | null> {
  try {
    const res = await request("/config/export");
    if (!res.ok) throw new Error("Failed to export settings");
    return await res.json();
  } catch (err) {
    console.error("Export settings failed:", err);
    return null;
  }
}

export async function importSettings(
  payload: Record<string, unknown>,
): Promise<boolean> {
  try {
    const res = await request("/config/import", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return res.ok;
  } catch (err) {
    console.error("Import settings failed:", err);
    return false;
  }
}

export async function addAccountService(
  service: string,
  credentials: { username?: string; token?: string },
): Promise<AccountItem | null> {
  try {
    const res = await request(
      `/accounts/add?service=${encodeURIComponent(service)}`,
      {
        method: "POST",
        body: JSON.stringify(credentials),
      },
    );
    if (!res.ok) throw new Error("Add account request failed");
    const data = await res.json();
    return data.account || (credentials as AccountItem);
  } catch (err) {
    console.error("Add account failed:", err);
    return null;
  }
}

export async function removeAccountUUID(uuid: string): Promise<boolean> {
  try {
    const res = await request(
      `/accounts/remove?luuid=${encodeURIComponent(uuid)}`,
      {
        method: "POST",
      },
    );
    return res.ok;
  } catch (err) {
    console.error("Remove account failed:", err);
    return false;
  }
}

export async function toggleMirrorSpotify(state: boolean): Promise<boolean> {
  try {
    const res = await request(
      `/spotify/mirror?state=${state ? "true" : "false"}`,
      {
        method: "POST",
      },
    );
    return res.ok;
  } catch (err) {
    console.error("Toggle mirror Spotify failed:", err);
    return false;
  }
}

export async function fetchServerLogs(): Promise<LogEntry[]> {
  try {
    const res = await request("/logs");
    if (!res.ok) throw new Error("Failed to fetch server logs");
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch (err) {
    console.error("Fetch server logs failed:", err);
    return [];
  }
}

export async function check_api_version(): Promise<boolean> {
  try {
    const res = await request("/config/version");
    if (!res.ok) throw new Error("Failed to fetch api version");
    return Boolean(await res.json());
  } catch (err) {
    console.error("Fetch version failed:", err);
    return false;
  }
}

export interface SpotifyCompanionPairing {
  pairing_token: string;
  expires_at: number;
  expires_in: number;
  device_name: string;
}

export async function createSpotifyCompanionPairing(): Promise<SpotifyCompanionPairing | null> {
  try {
    const res = await request("/accounts/spotify/companion/pair", {
      method: "POST",
    });
    if (!res.ok) throw new Error("Create Spotify companion pairing failed");
    return await res.json();
  } catch (err) {
    console.error("Create Spotify companion pairing failed:", err);
    return null;
  }
}

export type YouTubeAuthentication = {
  mode: "none" | "browser" | "cookie_file";
  browser?: string;
  cookie_file?: string;
};

export interface YouTubeAuthenticationStatus {
  mode: "none" | "browser" | "cookie_file";
  configured: boolean;
  ready: boolean;
  source: string;
  error: string;
}

export async function configureYouTubeAuthentication(
  authentication: YouTubeAuthentication,
): Promise<boolean> {
  try {
    const res = await request("/accounts/youtube-auth", {
      method: "POST",
      body: JSON.stringify(authentication),
    });
    if (!res.ok) {
      const payload = await res.json().catch(() => ({}));
      throw new Error(
        payload.detail || "The YouTube authentication setup is not usable",
      );
    }
    return true;
  } catch (err) {
    console.error("Configure YouTube authentication failed:", err);
    throw err;
  }
}

export async function fetchYouTubeAuthenticationStatus(): Promise<YouTubeAuthenticationStatus | null> {
  try {
    const res = await request("/accounts/youtube-auth/status");
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error("Fetch YouTube authentication status failed:", err);
    return null;
  }
}

export async function uploadYouTubeCookies(
  file: File,
): Promise<YouTubeAuthenticationStatus | null> {
  try {
    const form = new FormData();
    form.append("cookies", file);
    const res = await request("/accounts/youtube-auth/upload", {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      const payload = await res.json().catch(() => ({}));
      throw new Error(
        payload.detail || "The cookies file could not be uploaded",
      );
    }
    return await res.json();
  } catch (err) {
    console.error("Upload YouTube cookies failed:", err);
    throw err;
  }
}

export interface SpotifyPlaylistSummary {
  id: string;
  name: string;
  owner: string;
  editable: boolean;
  collaborative: boolean;
  public: boolean;
  tracks: number;
  image: string;
}
