import React, {
  lazy,
  Suspense,
  useEffect,
  useState,
  useCallback,
  useRef,
} from "react";
import { v4 as uuidv4 } from "uuid";
import { Navbar, NavTab } from "./components/Navbar";
import { SearchDashboard } from "./components/SearchDashboard";
import type { SettingsSection } from "./components/SettingsPage";
import { NotificationBanner } from "./components/NotificationBanner";
import { NotificationHistory } from "./components/NotificationHistory";
import {
  OTSConfig,
  DownloadQueueItem,
  AccountItem,
  LogEntry,
  NotificationBannerItem,
  SearchResultItem,
  NotificationContent,
} from "./types";
import { useNotifications } from "./lib/notifications";
import { installDocumentLocalization } from "./lib/localizeDocument";
import {
  fetchOTSConfig,
  fetchDownloadQueue,
  fetchAccounts,
  fetchAccountHealth,
  reconnectAccounts,
  fetchServerLogs,
  searchCatalog,
  searchMedia,
  clearQueueItems,
  triggerRetryFailed,
  performQueueAction,
  updateOTSConfigValue,
  saveOTSConfig,
  resetOTSConfig,
  addAccountService,
  configureYouTubeAuthentication,
  uploadYouTubeCookies,
  removeAccountUUID,
  check_api_version,
  fetchUpdateInfo,
  batchDownloadQueue,
  verifyDownloadQueue,
  fetchDownloadState,
  setDownloadsPaused,
  reorderDownloadQueue,
  fetchDownloadProfiles,
  setActiveDownloadProfile,
  saveDownloadProfile,
  deleteDownloadProfile,
} from "./lib/api";
import type { DownloadProfile, QueueBatchAction } from "./lib/api";
import type { AccountHealth } from "./lib/api";

const DownloadQueue = lazy(() =>
  import("./components/DownloadQueue").then((module) => ({
    default: module.DownloadQueue,
  })),
);
const SettingsPage = lazy(() =>
  import("./components/SettingsPage").then((module) => ({
    default: module.SettingsPage,
  })),
);
const AccountsManager = lazy(() =>
  import("./components/AccountsManager").then((module) => ({
    default: module.AccountsManager,
  })),
);
const DiagnosticsPanel = lazy(() =>
  import("./components/DiagnosticsPanel").then((module) => ({
    default: module.DiagnosticsPanel,
  })),
);
const LogViewer = lazy(() =>
  import("./components/LogViewer").then((module) => ({
    default: module.LogViewer,
  })),
);

const SSEid = uuidv4();

const PageLoading = () => (
  <div className="ots-page flex min-h-[40vh] items-center justify-center text-sm text-[var(--spotify-text-muted)]">
    Loading…
  </div>
);

const initialTabFromLocation = (): NavTab => {
  const tab = new URLSearchParams(window.location.search).get("tab");
  const validTabs: NavTab[] = [
    "dashboard",
    "queue",
    "settings",
    "accounts",
    "diagnostics",
    "logs",
  ];
  return validTabs.includes(tab as NavTab) ? (tab as NavTab) : "dashboard";
};

export default function App() {
  const [activeTab, setActiveTab] = useState<NavTab>(initialTabFromLocation);
  const [searchQuery, setSearchQuery] = useState("");
  const [settingsSection, setSettingsSection] =
    useState<SettingsSection>("general");
  const [config, setConfig] = useState<OTSConfig | null>(null);
  const [queue, setQueue] = useState<DownloadQueueItem[]>([]);
  const [accounts, setAccounts] = useState<AccountItem[]>([]);
  const [accountHealth, setAccountHealth] = useState<AccountHealth | null>(
    null,
  );
  const [logs, setLogs] = useState<LogEntry[]>([]);

  const {
    notifications,
    history,
    dismissNotification,
    clearHistory,
    lastStatusChange,
  } = useNotifications(SSEid);
  const [notificationHistoryOpen, setNotificationHistoryOpen] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);

  const [isDarkMode, setDarkMode] = useState("dark");
  const [hasNewVersion, SetNewVersion] = useState(false);
  const [downloadsPaused, setDownloadsPausedState] = useState(false);
  const [downloadSpeed, setDownloadSpeed] = useState(0);
  const [downloadEta, setDownloadEta] = useState(0);
  const [profiles, setProfiles] = useState<DownloadProfile[]>([]);
  const [activeProfile, setActiveProfile] = useState("");
  const profileMutationRef = useRef(0);

  // Initial load
  const loadData = useCallback(async () => {
    const [
      cfg,
      qData,
      accData,
      healthData,
      logData,
      downloadState,
      profileData,
    ] = await Promise.all([
      fetchOTSConfig(),
      fetchDownloadQueue(),
      fetchAccounts(),
      fetchAccountHealth(),
      fetchServerLogs(),
      fetchDownloadState(),
      fetchDownloadProfiles(),
    ]);
    if (cfg) {
      setWsConnected(true); // Set Connection status
      setConfig(cfg);
    }
    if (qData) setQueue(qData);
    if (accData) setAccounts(accData);
    setAccountHealth(healthData);
    if (logData) setLogs(logData);
    setDownloadsPausedState(downloadState.paused);
    setDownloadSpeed(downloadState.speed);
    setDownloadEta(downloadState.eta_seconds);
    // Do not let a slow initial request overwrite a selection made while the
    // settings page was opening.
    if (profileMutationRef.current === 0) {
      setProfiles(profileData.profiles);
      setActiveProfile(profileData.active);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

//  useEffect(() => {
//    if (isDarkMode === "dark") {
//      document.documentElement.classList.add("dark");
//    } else {
//      document.documentElement.classList.remove("dark");
//    }
//  }, [isDarkMode]);

  useEffect(() => {
    const locale = (config?.language || "en_US").replace("_", "-");
    document.documentElement.lang = locale;
    document.documentElement.dataset.applicationLanguage = locale;
  }, [config?.language]);

  useEffect(
    () => installDocumentLocalization(config?.language || "en_US"),
    [config?.language],
  );

  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        const input = document.getElementById(
          "global-search",
        ) as HTMLInputElement | null;
        input?.focus();
      }
    };
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, []);

  useEffect(() => {
    async function fetchQueueData() {
      const q = await fetchDownloadQueue();
      if (q) setQueue(q);
    }
    fetchQueueData();
  }, [notifications]);

  const toggleDarkMode = async () => {
    return
    //To be reimplemented as previous code broke the native tailwind behaviour
    if (isDarkMode == "dark") {
      //setDarkMode("dark")
      return
    } else {
      //setDarkMode("light")
      return
    }
    
  }

  const checkNewVersion = async () => {
    const status = await fetchUpdateInfo(true);
    if (status) {
      SetNewVersion(Boolean(status.update_available));
      return;
    }
    const latest = await check_api_version();
    SetNewVersion(!latest);
  };

  const handleDismissNotification = (id: string) => {
    dismissNotification(id);
  };

  const handleDownloadItem = async (
    query: string,
    filters?: Record<string, boolean>,
  ): Promise<boolean> => {
    return searchMedia(query, filters);
  };

  const handleClearCompleted = async () => {
    await clearQueueItems("Downloaded");
    const q = await fetchDownloadQueue();
    setQueue(q);
  };

  const handleClearFailed = async () => {
    await clearQueueItems("Failed");
    const q = await fetchDownloadQueue();
    setQueue(q);
  };

  const handleRetryFailed = async () => {
    await triggerRetryFailed();
    const q = await fetchDownloadQueue();
    setQueue(q);
  };

  const handleQueueAction = async (
    local_id: string,
    action: "cancel" | "delete" | "retry",
  ) => {
    const succeeded = await performQueueAction(local_id, action);
    if (succeeded && action === "cancel") {
      // Reflect the terminal state immediately while the worker unwinds its
      // current network/read operation and publishes the same event.
      setQueue((current) =>
        current.map((item) =>
          item.local_id === local_id
            ? {
                ...item,
                item_status: "Cancelled",
                error: "Cancelled by the user.",
              }
            : item,
        ),
      );
    }
    const q = await fetchDownloadQueue();
    setQueue(q);
  };

  const handleBatchAction = async (
    local_ids: string[],
    action: QueueBatchAction,
    options: { priority?: number; profile_id?: string } = {},
  ) => {
    await batchDownloadQueue(local_ids, action, options);
    setQueue(await fetchDownloadQueue());
  };

  const handleVerifyQueue = async () => {
    return;
  };

  const handlePauseToggle = async () => {
    return;
  };

  const handleReorder = async (local_ids: string[]) => {
    await reorderDownloadQueue(local_ids);
    setQueue(await fetchDownloadQueue());
  };

  const handleProfileChange = async (profile_id: string) => {
    if (await setActiveDownloadProfile(profile_id)) {
      setActiveProfile(profile_id);
      setConfig((prev) =>
        prev ? { ...prev, active_download_profile: profile_id } : prev,
      );
    }
  };

  const handleSaveProfile = async (profile: DownloadProfile) => {
    const saved = await saveDownloadProfile(profile);
    if (saved) {
      const fresh = await fetchDownloadProfiles();
      setProfiles(fresh.profiles);
      setActiveProfile(fresh.active);
    }
    return saved;
  };

  const handleDeleteProfile = async (profile_id: string) => {
    const ok = await deleteDownloadProfile(profile_id);
    if (ok) {
      const fresh = await fetchDownloadProfiles();
      setProfiles(fresh.profiles);
      setActiveProfile(fresh.active);
    }
    return ok;
  };

  const handleActivateProfile = async (profile_id: string) => {
    const previousProfile = activeProfile;
    profileMutationRef.current += 1;
    setActiveProfile(profile_id);
    setConfig((prev) =>
      prev ? { ...prev, active_download_profile: profile_id } : prev,
    );

    const ok = await setActiveDownloadProfile(profile_id);
    if (!ok) {
      setActiveProfile(previousProfile);
      setConfig((prev) =>
        prev ? { ...prev, active_download_profile: previousProfile } : prev,
      );
    }
    return ok;
  };

  const handleUpdateConfigValue = async (
    key: string,
    value: any,
  ): Promise<boolean> => {
    const ok = await updateOTSConfigValue(key, value);
    if (ok) {
      setConfig((prev) => (prev ? { ...prev, [key]: value } : null));
    }
    return ok;
  };

  const handleSaveConfig = async (): Promise<boolean> => {
    return await saveOTSConfig();
  };

  const handleResetConfig = async () => {
    const fresh = await resetOTSConfig();
    if (fresh) setConfig(fresh);
  };

  const handleAddAccount = async (
    service: string,
    creds: { username?: string; token?: string },
  ) => {
    const acc = await addAccountService(service, creds);
    if (acc) {
      const fresh = await fetchAccounts();
      setAccounts(fresh);
      setAccountHealth(await fetchAccountHealth());
    }
    return acc;
  };

  const handleRefreshAccounts = useCallback(async () => {
    const [freshAccounts, freshHealth] = await Promise.all([
      fetchAccounts(),
      fetchAccountHealth(),
    ]);
    setAccounts(freshAccounts);
    setAccountHealth(freshHealth);
    return freshAccounts;
  }, []);

  const handleConfigureYouTubeAuthentication = async (authentication: {
    mode: "none" | "browser" | "cookie_file";
    browser?: string;
    cookie_file?: string;
  }) => {
    const ok = await configureYouTubeAuthentication(authentication);
    if (ok) {
      const fresh = await fetchOTSConfig();
      if (fresh) setConfig(fresh);
    }
    return ok;
  };

  const handleUploadYouTubeCookies = async (file: File) => {
    const status = await uploadYouTubeCookies(file);
    if (status) {
      const fresh = await fetchOTSConfig();
      if (fresh) setConfig(fresh);
    }
    return status;
  };

  const handleRemoveAccount = async (uuid: string) => {
    const ok = await removeAccountUUID(uuid);
    if (ok) {
      setAccounts((prev) => prev.filter((a) => a.uuid !== uuid));
      setAccountHealth(await fetchAccountHealth());
    }
    return ok;
  };

  const handleReconnectAccounts = async () => {
    const ok = await reconnectAccounts();
    if (ok) {
      window.setTimeout(async () => {
        setAccounts(await fetchAccounts());
        setAccountHealth(await fetchAccountHealth());
      }, 2500);
    }
    return ok;
  };

  const handleClearLogs = () => {
    setLogs([]);
  };

  const handleRefreshLogs = async () => {
    const fresh = await fetchServerLogs();
    setLogs(fresh);
  };

  const activeDownloadsCount = queue.filter(
    (i) => i.item_status === "Downloading" || i.item_status === "Paused",
  ).length;

  return (
    <div
      className={`${isDarkMode === "dark" ? "dark-theme" : "light-theme"} min-h-screen antialiased`}>
      <Navbar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        queueCount={
          queue.filter(
            (i) =>
              i.item_status === "Waiting" ||
              i.item_status === "Downloading" ||
              i.item_status === "Paused",
          ).length
        }
        activeDownloads={activeDownloadsCount}
        accountCount={accounts.length}
        toggleTheme={() => toggleDarkMode()}
        appVersion={config?.version || "v2.0.0 Alpha 2"}
        notificationHistoryCount={history.length}
        onOpenNotificationHistory={() => setNotificationHistoryOpen(true)}
        language={config?.language || "en_US"}
      />

      <main className="min-h-screen pb-10 md:ml-64">
        <Suspense fallback={<PageLoading />}>
          {activeTab === "dashboard" && (
            <SearchDashboard
              onSearch={searchCatalog}
              onDownload={handleDownloadItem}
              config={config}
              accounts={accounts}
              query={searchQuery}
              onQueryChange={setSearchQuery}
            />
          )}


          {activeTab === "queue" && (
            <DownloadQueue
              queue={queue}
              onClearCompleted={handleClearCompleted}
              onClearFailed={handleClearFailed}
              onRetryFailed={handleRetryFailed}
              onAction={handleQueueAction}
              onPauseToggle={handlePauseToggle}
              downloadsPaused={downloadsPaused}
              downloadSpeed={downloadSpeed}
              downloadEta={downloadEta}
              onReorder={handleReorder}
              profiles={profiles}
              activeProfile={activeProfile}
              onProfileChange={handleProfileChange}
              onBatchAction={handleBatchAction}
              onVerify={handleVerifyQueue}
              config={config}
            />
          )}

          {activeTab === "settings" && (
            <SettingsPage
              initialSection={settingsSection}
              config={config}
              onUpdateValue={handleUpdateConfigValue}
              onSave={handleSaveConfig}
              onReset={handleResetConfig}
              profiles={profiles}
              activeProfile={activeProfile}
              onSaveProfile={handleSaveProfile}
              onDeleteProfile={handleDeleteProfile}
              onActivateProfile={handleActivateProfile}
            />
          )}

          {activeTab === "accounts" && (
            <AccountsManager
              accounts={accounts.length > 0 ? accounts : config?.accounts || []}
              onAddAccount={handleAddAccount}
              onRemoveAccount={handleRemoveAccount}
              onRefreshAccounts={handleRefreshAccounts}
              health={accountHealth}
              onReconnect={handleReconnectAccounts}
              onConfigureYouTubeAuthentication={
                handleConfigureYouTubeAuthentication
              }
              onUploadYouTubeCookies={handleUploadYouTubeCookies}
              youtubeAuthenticationMode={config?.youtube_auth_mode || "none"}
              youtubeBrowser={config?.youtube_cookies_browser || ""}
              youtubeCookieFile={config?.youtube_cookies_file || ""}
            />
          )}

          {activeTab === "diagnostics" && (
            <DiagnosticsPanel
              wsConnected={wsConnected}
              newVersion={hasNewVersion}
              checkVersion={checkNewVersion}
              config={config}
            />
          )}

          {activeTab === "logs" && (
            <LogViewer
              logs={logs}
              onRefresh={handleRefreshLogs}
              onClear={handleClearLogs}
            />
          )}
        </Suspense>
      </main>

      {/* Real-time floating notification banners */}
      <NotificationBanner
        notifications={notifications}
        onDismiss={handleDismissNotification}
        disabled={config?.disable_download_popups}
      />
      <NotificationHistory
        history={history}
        onClear={clearHistory}
        open={notificationHistoryOpen}
        onOpenChange={setNotificationHistoryOpen}
        hideTrigger
      />
    </div>
  );
}