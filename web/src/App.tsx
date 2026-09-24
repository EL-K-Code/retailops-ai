import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Bell,
  Bot,
  BrainCircuit,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleGauge,
  Clock3,
  Database,
  FileText,
  Gauge,
  Layers3,
  LineChart as LineChartIcon,
  Menu,
  MessageSquareText,
  PackageSearch,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  Store,
  TerminalSquare,
  TrendingUp,
  UserRoundCheck,
  X,
  XCircle,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api } from './api';
import type {
  AgentRunResult,
  ApprovalRequest,
  ForecastResponse,
  KnowledgeDocument,
  OpsStatus,
  Overview,
  SessionAuditEvent,
  Split,
} from './types';

type PageId =
  | 'dashboard'
  | 'forecasts'
  | 'analytics'
  | 'copilot'
  | 'recommendations'
  | 'approvals'
  | 'knowledge'
  | 'models'
  | 'monitoring'
  | 'audit'
  | 'settings';

type NavItem = { id: PageId; label: string; icon: LucideIcon };
type ApprovalState = {
  threadId: string;
  request: ApprovalRequest;
  status: 'pending' | 'approved' | 'rejected';
  createdAt: string;
  finalAnswer?: string;
};
type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  sources?: string[];
  pendingApproval?: boolean;
};

const NAV_GROUPS: Array<{ label: string; items: NavItem[] }> = [
  {
    label: 'Workspace',
    items: [
      { id: 'dashboard', label: 'Overview', icon: CircleGauge },
      { id: 'forecasts', label: 'Forecasts', icon: TrendingUp },
      { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    ],
  },
  {
    label: 'Decide',
    items: [
      { id: 'copilot', label: 'AI Copilot', icon: Sparkles },
      { id: 'recommendations', label: 'Recommendations', icon: BrainCircuit },
      { id: 'approvals', label: 'Approvals', icon: UserRoundCheck },
    ],
  },
  {
    label: 'Operate',
    items: [
      { id: 'models', label: 'Model', icon: Layers3 },
      { id: 'monitoring', label: 'Monitoring', icon: Activity },
      { id: 'audit', label: 'Audit', icon: TerminalSquare },
    ],
  },
  {
    label: 'More',
    items: [
      { id: 'knowledge', label: 'Knowledge', icon: FileText },
      { id: 'settings', label: 'Settings', icon: Settings },
    ],
  },
];

const PAGE_TITLES: Record<PageId, { eyebrow: string; title: string; subtitle: string }> = {
  dashboard: { eyebrow: 'Workspace', title: 'Overview', subtitle: 'Demand, signals and decisions.' },
  forecasts: { eyebrow: 'Forecasts', title: 'Demand outlook', subtitle: '28-day product-store forecast.' },
  analytics: { eyebrow: 'Analytics', title: 'Performance', subtitle: 'Sales, stores and product mix.' },
  copilot: { eyebrow: 'AI Copilot', title: 'Ask RetailOps', subtitle: 'Grounded decision support.' },
  recommendations: { eyebrow: 'Decisions', title: 'Recommendations', subtitle: 'Evidence-backed follow-up.' },
  approvals: { eyebrow: 'Governance', title: 'Approvals', subtitle: 'Human review queue.' },
  knowledge: { eyebrow: 'AI', title: 'Knowledge', subtitle: 'Grounding sources.' },
  models: { eyebrow: 'ML', title: 'Model', subtitle: 'Forecast quality and serving.' },
  monitoring: { eyebrow: 'Operations', title: 'Monitoring', subtitle: 'Service health and latency.' },
  audit: { eyebrow: 'Governance', title: 'Audit', subtitle: 'Traceable operator activity.' },
  settings: { eyebrow: 'Workspace', title: 'Settings', subtitle: 'Runtime controls.' },
};

const currency = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
});
const compact = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 });
const decimal = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 });

function usePersistedState<T>(key: string, initialValue: T): [T, (value: T | ((old: T) => T)) => void] {
  const [value, setValue] = useState<T>(() => {
    try {
      const stored = localStorage.getItem(key);
      return stored ? (JSON.parse(stored) as T) : initialValue;
    } catch {
      return initialValue;
    }
  });

  const update = (next: T | ((old: T) => T)) => {
    setValue((old) => {
      const resolved = typeof next === 'function' ? (next as (current: T) => T)(old) : next;
      localStorage.setItem(key, JSON.stringify(resolved));
      return resolved;
    });
  };

  return [value, update];
}

function classNames(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(' ');
}

function safeNumber(value: unknown): number {
  const number = Number(value ?? 0);
  return Number.isFinite(number) ? number : 0;
}

function getForecastPoints(response: ForecastResponse | null) {
  if (!response) return [];
  const raw = response as any;
  const candidates = [
    raw.predictions,
    raw.forecasts?.[0]?.predictions,
    raw.results?.[0]?.predictions,
    raw.series?.[0]?.predictions,
  ];
  const predictions = candidates.find((candidate) => Array.isArray(candidate)) ?? [];
  return predictions.map((point: any, index: number) => {
    if (typeof point === 'number') {
      return { horizon: index + 1, label: `D+${index + 1}`, value: point };
    }
    const horizon = safeNumber(point.horizon ?? point.h ?? point.step ?? index + 1);
    return {
      horizon,
      label: point.date ?? `D+${horizon || index + 1}`,
      value: safeNumber(point.prediction ?? point.yhat ?? point.value ?? point.forecast),
    };
  });
}

function modelLabel(model: Record<string, unknown> | undefined) {
  if (!model) return 'Unavailable';
  const nested = (model.model as Record<string, unknown> | undefined) ?? model;
  return String(nested.name ?? nested.model_name ?? nested.model ?? 'lightgbm_global');
}

function modelVersion(model: Record<string, unknown> | undefined) {
  if (!model) return '—';
  const nested = (model.model as Record<string, unknown> | undefined) ?? model;
  return String(nested.version ?? nested.model_version ?? 'v1');
}

function Skeleton({ height = 120 }: { height?: number }) {
  return <div className="skeleton" style={{ height }} />;
}

function EmptyState({ icon: Icon, title, text }: { icon: LucideIcon; title: string; text: string }) {
  return (
    <div className="empty-state">
      <div className="empty-icon"><Icon size={22} /></div>
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

function StatusPill({ tone = 'neutral', children }: { tone?: 'good' | 'warn' | 'bad' | 'neutral' | 'info'; children: React.ReactNode }) {
  return <span className={`status-pill ${tone}`}>{children}</span>;
}

function Card({ className, children }: { className?: string; children: React.ReactNode }) {
  return <section className={classNames('card', className)}>{children}</section>;
}

function KpiCard({
  icon: Icon,
  label,
  value,
  helper,
  badge,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  helper: string;
  badge?: string;
}) {
  return (
    <Card className="kpi-card">
      <div className="kpi-top">
        <div className="icon-chip"><Icon size={18} /></div>
        {badge && <span className="kpi-badge">{badge}</span>}
      </div>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      <div className="kpi-helper">{helper}</div>
    </Card>
  );
}

function SectionHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="section-header">
      <div>
        <h2>{title}</h2>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

function App() {
  const [activePage, setActivePage] = useState<PageId>('dashboard');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [split, setSplit] = useState<Split>('test');
  const [overview, setOverview] = useState<Overview | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [overviewError, setOverviewError] = useState<string | null>(null);
  const [knowledge, setKnowledge] = useState<KnowledgeDocument[]>([]);
  const [knowledgeLoading, setKnowledgeLoading] = useState(true);
  const [ops, setOps] = useState<OpsStatus | null>(null);
  const [readyStatus, setReadyStatus] = useState('unknown');
  const [monitorLatency, setMonitorLatency] = useState<number | null>(null);
  const [approvals, setApprovals] = usePersistedState<ApprovalState[]>('retailops-approvals', []);
  const [audit, setAudit] = usePersistedState<SessionAuditEvent[]>('retailops-audit', []);

  const reloadOverview = async (nextSplit = split) => {
    setOverviewLoading(true);
    setOverviewError(null);
    try {
      const data = await api.overview(nextSplit);
      setOverview(data);
    } catch (error) {
      setOverviewError(error instanceof Error ? error.message : 'Unable to load live RetailOps data.');
    } finally {
      setOverviewLoading(false);
    }
  };

  const refreshOps = async () => {
    const started = performance.now();
    try {
      const [status, ready] = await Promise.all([api.opsStatus(), api.ready()]);
      setOps(status);
      setReadyStatus(ready.status);
      setMonitorLatency(performance.now() - started);
    } catch {
      setReadyStatus('unavailable');
      setMonitorLatency(null);
    }
  };

  useEffect(() => {
    void reloadOverview(split);
  }, [split]);

  useEffect(() => {
    void api
      .knowledge()
      .then((result) => setKnowledge(result.documents))
      .finally(() => setKnowledgeLoading(false));
    void refreshOps();
  }, []);

  const addAudit = (event: Omit<SessionAuditEvent, 'id' | 'at'>) => {
    setAudit((current) => [
      { ...event, id: crypto.randomUUID(), at: new Date().toISOString() },
      ...current,
    ].slice(0, 100));
  };

  const rememberApproval = (result: AgentRunResult) => {
    if (!result.approval_request) return;
    setApprovals((current) => {
      if (current.some((approval) => approval.threadId === result.thread_id)) return current;
      return [
        {
          threadId: result.thread_id,
          request: result.approval_request!,
          status: 'pending',
          createdAt: new Date().toISOString(),
        },
        ...current,
      ];
    });
  };

  const page = PAGE_TITLES[activePage];
  const pendingCount = approvals.filter((approval) => approval.status === 'pending').length;

  return (
    <div className="app-shell">
      <aside className={classNames('sidebar', mobileNavOpen && 'open')}>
        <div className="brand-block">
          <div className="brand-mark"><Zap size={20} fill="currentColor" /></div>
          <div>
            <div className="brand-name">RetailOps AI</div>
            <div className="brand-sub">Decision intelligence</div>
          </div>
          <button className="mobile-close" onClick={() => setMobileNavOpen(false)} aria-label="Close navigation">
            <X size={18} />
          </button>
        </div>

        <nav className="nav-stack">
          {NAV_GROUPS.map((group) => (
            <div className="nav-group" key={group.label}>
              <div className="nav-group-label">{group.label}</div>
              {group.items.map((item) => {
                const Icon = item.icon;
                const active = activePage === item.id;
                return (
                  <button
                    key={item.id}
                    className={classNames('nav-item', active && 'active')}
                    onClick={() => {
                      setActivePage(item.id);
                      setMobileNavOpen(false);
                    }}
                  >
                    <Icon size={18} strokeWidth={1.8} />
                    <span>{item.label}</span>
                    {item.id === 'approvals' && pendingCount > 0 && <span className="nav-count">{pendingCount}</span>}
                    {active && <ChevronRight className="nav-chevron" size={15} />}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="system-mini">
            <div className={classNames('pulse-dot', readyStatus === 'ready' && 'online')} />
            <div>
              <strong>{readyStatus === 'ready' ? 'Systems operational' : 'Checking services'}</strong>
              <span>{ops?.release ?? 'Portfolio release'}</span>
            </div>
          </div>
          <div className="operator-card">
            <div className="operator-avatar">OP</div>
            <div className="operator-copy">
              <strong>Retail Operator</strong>
              <span>Full workspace access</span>
            </div>
            <Settings size={16} />
          </div>
        </div>
      </aside>

      {mobileNavOpen && <button className="sidebar-overlay" onClick={() => setMobileNavOpen(false)} aria-label="Close menu" />}

      <main className="main-panel">
        <header className="topbar">
          <button className="menu-button" onClick={() => setMobileNavOpen(true)} aria-label="Open navigation"><Menu size={20} /></button>
          <div className="search-shell">
            <Search size={17} />
            <span>Search products, stores or ask RetailOps AI…</span>
            <kbd>⌘ K</kbd>
          </div>
          <div className="topbar-actions">
            <button className="icon-button" aria-label="Notifications"><Bell size={18} />{pendingCount > 0 && <span className="notification-dot" />}</button>
            <div className="topbar-divider" />
            <div className="topbar-user">
              <div className="operator-avatar small">OP</div>
              <div><strong>Operator</strong><span>Admin access</span></div>
            </div>
          </div>
        </header>

        <div className="page-wrap">
          <div className="page-heading">
            <div>
              <div className="eyebrow">{page.eyebrow}</div>
              <h1>{page.title}</h1>
              <p>{page.subtitle}</p>
            </div>
            <div className="heading-actions">
              <div className="segmented">
                <button className={split === 'validation' ? 'active' : ''} onClick={() => setSplit('validation')}>Validation</button>
                <button className={split === 'test' ? 'active' : ''} onClick={() => setSplit('test')}>Test</button>
              </div>
              <button className="secondary-button" onClick={() => void reloadOverview()}>
                <RefreshCw size={16} className={overviewLoading ? 'spin' : ''} /> Refresh
              </button>
            </div>
          </div>

          {overviewError && (
            <div className="alert-banner error">
              <AlertTriangle size={18} />
              <div><strong>Live data unavailable</strong><span>{overviewError}</span></div>
              <button onClick={() => void reloadOverview()}>Retry</button>
            </div>
          )}

          {activePage === 'dashboard' && (
            <DashboardPage
              overview={overview}
              loading={overviewLoading}
              approvals={approvals}
              onNavigate={setActivePage}
            />
          )}
          {activePage === 'forecasts' && <ForecastPage split={split} addAudit={addAudit} />}
          {activePage === 'analytics' && <AnalyticsPage overview={overview} loading={overviewLoading} />}
          {activePage === 'copilot' && (
            <CopilotPage addAudit={addAudit} rememberApproval={rememberApproval} onNavigate={setActivePage} />
          )}
          {activePage === 'recommendations' && <RecommendationsPage approvals={approvals} onNavigate={setActivePage} />}
          {activePage === 'approvals' && (
            <ApprovalsPage approvals={approvals} setApprovals={setApprovals} addAudit={addAudit} />
          )}
          {activePage === 'knowledge' && <KnowledgePage documents={knowledge} loading={knowledgeLoading} />}
          {activePage === 'models' && <ModelsPage overview={overview} loading={overviewLoading} />}
          {activePage === 'monitoring' && (
            <MonitoringPage ops={ops} readyStatus={readyStatus} latency={monitorLatency} onRefresh={refreshOps} />
          )}
          {activePage === 'audit' && <AuditPage events={audit} />}
          {activePage === 'settings' && <SettingsPage />}
        </div>
      </main>
    </div>
  );
}

function DashboardPage({
  overview,
  loading,
  approvals,
  onNavigate,
}: {
  overview: Overview | null;
  loading: boolean;
  approvals: ApprovalState[];
  onNavigate: (page: PageId) => void;
}) {
  const sales = overview?.sales_summary.rows[0];
  const reference = overview?.reference_sales_summary?.rows[0];
  const daily = overview?.daily_trend.rows ?? [];
  const categories = overview?.category_summary.rows ?? [];
  const stores = overview?.store_summary.rows ?? [];
  const context = overview?.demand_context.rows[0];
  const weekday = overview?.weekday_profile.rows ?? [];
  const pending = approvals.filter((approval) => approval.status === 'pending');

  const totalUnits = safeNumber(sales?.total_units_sold);
  const unitDelta = reference && safeNumber(reference.total_units_sold) > 0
    ? (totalUnits - safeNumber(reference.total_units_sold)) / safeNumber(reference.total_units_sold)
    : null;
  const dailyValues = daily.map((row) => safeNumber(row.total_units_sold));
  const dailyMean = dailyValues.length
    ? dailyValues.reduce((sum, value) => sum + value, 0) / dailyValues.length
    : 0;
  const dailyStd = dailyValues.length > 1
    ? Math.sqrt(dailyValues.reduce((sum, value) => sum + ((value - dailyMean) ** 2), 0) / (dailyValues.length - 1))
    : 0;
  const demandCv = dailyMean > 0 ? dailyStd / dailyMean : 0;
  const topStore = stores[0];
  const topCategory = categories[0];

  if (loading && !overview) {
    return <div className="premium-loading"><Skeleton height={114} /><Skeleton height={360} /><Skeleton height={300} /></div>;
  }

  return (
    <div className="premium-dashboard">
      <div className="workspace-strip">
        <div className="workspace-identity">
          <span className="workspace-live"><i /> Live workspace</span>
          <strong>Demo Retail Operations</strong>
        </div>
        <div className="workspace-meta">
          <span><BrainCircuit size={13} /> {modelLabel(overview?.model)} {modelVersion(overview?.model)}</span>
          <span><Clock3 size={13} /> 28-day horizon</span>
          <span><ShieldCheck size={13} /> Human governed</span>
        </div>
        <button className="workspace-cta" onClick={() => onNavigate('copilot')}>
          <Sparkles size={14} /> Ask Copilot
        </button>
      </div>

      <div className="premium-kpi-grid">
        <div className="premium-kpi">
          <div className="premium-kpi-head"><span>Demand</span><TrendingUp size={15} /></div>
          <strong>{compact.format(totalUnits)}</strong>
          <div className={`premium-kpi-delta ${unitDelta === null ? '' : unitDelta >= 0 ? 'up' : 'down'}`}>
            {unitDelta === null ? `${sales?.observed_days ?? 0} observed days` : `${unitDelta >= 0 ? '+' : ''}${(unitDelta * 100).toFixed(1)}% vs validation`}
          </div>
        </div>
        <div className="premium-kpi">
          <div className="premium-kpi-head"><span>Sales value</span><Gauge size={15} /></div>
          <strong>{currency.format(safeNumber(sales?.estimated_sales_value))}</strong>
          <div className="premium-kpi-delta">{context ? `${(safeNumber(context.price_coverage_rate) * 100).toFixed(1)}% price coverage` : 'Gold mart estimate'}</div>
        </div>
        <div className="premium-kpi">
          <div className="premium-kpi-head"><span>Demand variability</span><Activity size={15} /></div>
          <strong>{(demandCv * 100).toFixed(1)}%</strong>
          <div className="premium-kpi-delta">CV across daily total demand</div>
        </div>
        <div className="premium-kpi action">
          <div className="premium-kpi-head"><span>Human review</span><UserRoundCheck size={15} /></div>
          <strong>{pending.length}</strong>
          <button onClick={() => onNavigate('approvals')}>{pending.length ? 'Review queue' : 'Queue clear'} <ArrowRight size={13} /></button>
        </div>
      </div>

      <div className="premium-grid primary">
        <Card className="premium-panel demand-panel">
          <SectionHeader
            title="Demand pulse"
            subtitle="Daily observed units"
            action={<span className="panel-chip">{overview?.split === 'test' ? 'Test window' : 'Validation window'}</span>}
          />
          <div className="premium-chart">
            {daily.length ? (
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={daily} margin={{ top: 10, right: 4, left: -22, bottom: 0 }}>
                  <defs>
                    <linearGradient id="premiumDemandArea" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0" stopColor="var(--accent)" stopOpacity={0.28} />
                      <stop offset="1" stopColor="var(--accent)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 7" vertical={false} stroke="var(--grid-line)" />
                  <XAxis dataKey="date" tickLine={false} axisLine={false} minTickGap={26} tick={{ fill: 'var(--text-muted)', fontSize: 9 }} tickFormatter={(value) => String(value).slice(5)} />
                  <YAxis tickLine={false} axisLine={false} tick={{ fill: 'var(--text-muted)', fontSize: 9 }} tickFormatter={(value) => compact.format(Number(value))} />
                  <Tooltip contentStyle={{ background: '#11151b', border: '1px solid #2a3038', borderRadius: 10 }} formatter={(value) => [compact.format(Number(value)), 'Units']} />
                  <Area type="monotone" dataKey="total_units_sold" stroke="var(--accent)" fill="url(#premiumDemandArea)" strokeWidth={2.2} dot={false} activeDot={{ r: 4 }} />
                </AreaChart>
              </ResponsiveContainer>
            ) : <EmptyState icon={TrendingUp} title="No trend data" text="Refresh the workspace." />}
          </div>
        </Card>

        <Card className="premium-panel attention-panel">
          <div className="attention-head">
            <div><span>Attention</span><strong>{pending.length ? `${pending.length} decision${pending.length > 1 ? 's' : ''} waiting` : 'No blocked decisions'}</strong></div>
            <div className={`attention-orb ${pending.length ? 'warn' : 'good'}`}><ShieldCheck size={17} /></div>
          </div>

          <div className="signal-stack">
            <div className="signal-row">
              <span>Top category</span>
              <strong>{topCategory?.category ?? '—'}</strong>
              <small>{topCategory ? compact.format(topCategory.total_units_sold) : '—'} units</small>
            </div>
            <div className="signal-row">
              <span>Top store</span>
              <strong>{topStore?.store_id ?? '—'}</strong>
              <small>{topStore ? `${topStore.state} · ${compact.format(topStore.total_units_sold)} units` : '—'}</small>
            </div>
            <div className="signal-row">
              <span>Peak day</span>
              <strong>{compact.format(safeNumber(sales?.peak_daily_units))}</strong>
              <small>units</small>
            </div>
          </div>

          <div className="attention-actions">
            <button onClick={() => onNavigate('forecasts')}><TrendingUp size={14} /> Forecast</button>
            <button onClick={() => onNavigate('analytics')}><BarChart3 size={14} /> Analyze</button>
            <button className="primary" onClick={() => onNavigate('copilot')}><Sparkles size={14} /> Ask AI</button>
          </div>
        </Card>
      </div>

      <div className="context-grid">
        <div className="context-stat"><span>Weekend demand</span><strong>{context ? `${(safeNumber(context.weekend_unit_share) * 100).toFixed(1)}%` : '—'}</strong></div>
        <div className="context-stat"><span>SNAP-active demand</span><strong>{context ? `${(safeNumber(context.snap_active_unit_share) * 100).toFixed(1)}%` : '—'}</strong></div>
        <div className="context-stat"><span>Event-day demand</span><strong>{context ? `${(safeNumber(context.event_unit_share) * 100).toFixed(1)}%` : '—'}</strong></div>
        <div className="context-stat"><span>Average sell price</span><strong>{context ? currency.format(safeNumber(context.average_sell_price)) : '—'}</strong></div>
      </div>

      <div className="premium-grid secondary">
        <Card className="premium-panel">
          <SectionHeader title="Category mix" subtitle="Observed units by category" />
          <div className="premium-chart compact">
            {categories.length ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={categories} layout="vertical" margin={{ left: 8, right: 14, top: 4, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 7" horizontal={false} stroke="var(--grid-line)" />
                  <XAxis type="number" tickLine={false} axisLine={false} tick={{ fill: 'var(--text-muted)', fontSize: 9 }} tickFormatter={(value) => compact.format(Number(value))} />
                  <YAxis dataKey="category" type="category" width={74} tickLine={false} axisLine={false} tick={{ fill: 'var(--text-soft)', fontSize: 9 }} />
                  <Tooltip contentStyle={{ background: '#11151b', border: '1px solid #2a3038', borderRadius: 10 }} formatter={(value) => [compact.format(Number(value)), 'Units']} />
                  <Bar dataKey="total_units_sold" fill="var(--accent-2)" radius={[0, 5, 5, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : <EmptyState icon={BarChart3} title="No category data" text="Refresh the workspace." />}
          </div>
        </Card>

        <Card className="premium-panel">
          <SectionHeader title="Weekly rhythm" subtitle="Average demand by weekday" />
          <div className="premium-chart compact">
            {weekday.length ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={weekday} margin={{ left: -16, right: 4, top: 4, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 7" vertical={false} stroke="var(--grid-line)" />
                  <XAxis dataKey="weekday" tickLine={false} axisLine={false} tick={{ fill: 'var(--text-muted)', fontSize: 9 }} />
                  <YAxis tickLine={false} axisLine={false} tick={{ fill: 'var(--text-muted)', fontSize: 9 }} tickFormatter={(value) => compact.format(Number(value))} />
                  <Tooltip contentStyle={{ background: '#11151b', border: '1px solid #2a3038', borderRadius: 10 }} formatter={(value) => [compact.format(Number(value)), 'Avg units']} />
                  <Bar dataKey="average_daily_units" fill="var(--accent)" radius={[5, 5, 1, 1]} />
                </BarChart>
              </ResponsiveContainer>
            ) : <EmptyState icon={Activity} title="No weekday data" text="Refresh the workspace." />}
          </div>
        </Card>
      </div>

      <Card className="premium-panel store-table-panel">
        <div className="table-panel-head">
          <div><strong>Store performance</strong><span>Top stores by observed demand</span></div>
          <button onClick={() => onNavigate('analytics')}>Full analytics <ArrowRight size={13} /></button>
        </div>
        <div className="premium-store-list">
          {stores.slice(0, 6).map((store, index) => {
            const share = totalUnits > 0 ? safeNumber(store.total_units_sold) / totalUnits : 0;
            return (
              <div className="premium-store-row" key={store.store_id}>
                <span className="store-rank">{String(index + 1).padStart(2, '0')}</span>
                <div className="store-identity"><strong>{store.store_id}</strong><span>{store.state}</span></div>
                <div className="store-metric"><span>Units</span><strong>{compact.format(store.total_units_sold)}</strong></div>
                <div className="store-metric"><span>Sales value</span><strong>{currency.format(store.estimated_sales_value)}</strong></div>
                <div className="store-share"><span style={{ width: `${Math.min(100, share * 100)}%` }} /></div>
                <small>{(share * 100).toFixed(1)}%</small>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}

function ForecastPage({ split, addAudit }: { split: Split; addAudit: (event: Omit<SessionAuditEvent, 'id' | 'at'>) => void }) {
  const [itemId, setItemId] = useState('FOODS_1_001');
  const [storeId, setStoreId] = useState('CA_1');
  const [response, setResponse] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const points = useMemo(() => getForecastPoints(response), [response]);
  const total = points.reduce((sum, point) => sum + point.value, 0);
  const peak = points.reduce((max, point) => Math.max(max, point.value), 0);

  const runForecast = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.forecast(itemId.trim(), storeId.trim(), split);
      setResponse(result);
      addAudit({ kind: 'forecast', title: `${itemId} · ${storeId}`, status: 'completed', tools: ['forecast_api'] });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Forecast failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="workspace-grid">
      <Card className="control-card sticky-card">
        <SectionHeader title="Forecast request" subtitle="Live V4 model serving" />
        <label className="field-label">Item ID<input value={itemId} onChange={(event) => setItemId(event.target.value)} placeholder="FOODS_1_001" /></label>
        <label className="field-label">Store ID<input value={storeId} onChange={(event) => setStoreId(event.target.value)} placeholder="CA_1" /></label>
        <div className="info-box"><Database size={16} /><span>Predictions come from the same private Forecast API used by the agent.</span></div>
        <button className="primary-button full" disabled={loading || !itemId.trim() || !storeId.trim()} onClick={() => void runForecast()}>
          {loading ? <RefreshCw className="spin" size={17} /> : <TrendingUp size={17} />} Run 28-day forecast
        </button>
        {error && <div className="inline-error"><AlertTriangle size={15} />{error}</div>}
      </Card>

      <div className="workspace-main">
        <div className="mini-kpi-grid">
          <KpiCard icon={TrendingUp} label="Forecast total" value={points.length ? decimal.format(total) : '—'} helper="Predicted units across horizon" />
          <KpiCard icon={Gauge} label="Peak demand" value={points.length ? decimal.format(peak) : '—'} helper="Highest predicted daily demand" />
          <KpiCard icon={Clock3} label="Horizon" value={points.length ? `${points.length} days` : '28 days'} helper={String((response as any)?.forecast_origin ?? 'Awaiting request')} />
        </div>
        <Card className="chart-card large-chart">
          <SectionHeader
            title="Demand trajectory"
            subtitle={response ? `${itemId} · ${storeId} · ${split}` : 'Run a forecast to visualize the serving output'}
            action={response && <StatusPill tone="good">Live model</StatusPill>}
          />
          <div className="chart-wrap forecast-chart">
            {loading ? <Skeleton height={360} /> : points.length ? (
              <ResponsiveContainer width="100%" height={360}>
                <AreaChart data={points} margin={{ top: 12, right: 12, left: -10, bottom: 8 }}>
                  <defs><linearGradient id="forecastArea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="var(--accent)" stopOpacity={0.42} /><stop offset="1" stopColor="var(--accent)" stopOpacity={0} /></linearGradient></defs>
                  <CartesianGrid strokeDasharray="4 8" vertical={false} stroke="var(--grid-line)" />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} minTickGap={24} />
                  <YAxis tickLine={false} axisLine={false} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: '#0d1928', border: '1px solid #203348', borderRadius: 12 }} formatter={(value) => [`${decimal.format(Number(value))} units`, 'Forecast']} />
                  <Area type="monotone" dataKey="value" stroke="var(--accent)" fill="url(#forecastArea)" strokeWidth={2.6} activeDot={{ r: 5 }} />
                </AreaChart>
              </ResponsiveContainer>
            ) : <EmptyState icon={LineChartIcon} title="Ready for inference" text="Choose an item and store, then run the validated 28-day recursive forecast." />}
          </div>
        </Card>
      </div>
    </div>
  );
}

function AnalyticsPage({ overview, loading }: { overview: Overview | null; loading: boolean }) {
  const products = overview?.top_products.rows ?? [];
  const stores = overview?.store_summary.rows ?? [];
  const sales = overview?.sales_summary.rows[0];
  return (
    <>
      <div className="kpi-grid three">
        <KpiCard icon={PackageSearch} label="Total units" value={loading ? '…' : compact.format(safeNumber(sales?.total_units_sold))} helper="Observed demand in selected split" badge="sales_summary" />
        <KpiCard icon={Store} label="Stores surfaced" value={String(stores.length)} helper="Ranked by total units sold" badge="store_summary" />
        <KpiCard icon={Database} label="Analytics mode" value="Allowlisted SQL" helper="Parameterized BigQuery templates only" badge="Read-only" />
      </div>
      <div className="content-grid halves">
        <Card className="chart-card">
          <SectionHeader title="Product ranking" subtitle="Units sold by top product" />
          <div className="chart-wrap">
            {loading ? <Skeleton height={300} /> : (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={products} layout="vertical" margin={{ left: 26, right: 16 }}>
                  <CartesianGrid strokeDasharray="4 8" horizontal={false} stroke="var(--grid-line)" />
                  <XAxis type="number" tickLine={false} axisLine={false} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                  <YAxis dataKey="item_id" type="category" tickLine={false} axisLine={false} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} width={95} />
                  <Tooltip contentStyle={{ background: '#0d1928', border: '1px solid #203348', borderRadius: 12 }} />
                  <Bar dataKey="total_units_sold" fill="var(--accent)" radius={[0, 7, 7, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>
        <Card className="chart-card">
          <SectionHeader title="Store sales value" subtitle="Estimated value from price-covered demand" />
          <div className="chart-wrap">
            {loading ? <Skeleton height={300} /> : (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={stores.slice(0, 15)} margin={{ left: -12, right: 10, top: 10 }}>
                  <CartesianGrid strokeDasharray="4 8" vertical={false} stroke="var(--grid-line)" />
                  <XAxis dataKey="store_id" tickLine={false} axisLine={false} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                  <YAxis tickLine={false} axisLine={false} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickFormatter={(value) => compact.format(value)} />
                  <Tooltip contentStyle={{ background: '#0d1928', border: '1px solid #203348', borderRadius: 12 }} formatter={(value) => currency.format(Number(value))} />
                  <Line type="monotone" dataKey="estimated_sales_value" stroke="var(--accent-2)" strokeWidth={2.5} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>
      </div>
      <Card className="data-table-card">
        <SectionHeader title="Store detail" subtitle="Live BigQuery results with operational context" />
        <div className="table-scroll">
          <table>
            <thead><tr><th>Store</th><th>Units sold</th><th>Estimated sales</th><th>Avg. active items</th><th>Price coverage</th></tr></thead>
            <tbody>{stores.map((store) => (
              <tr key={store.store_id}>
                <td><span className="entity-cell"><Store size={14} />{store.store_id}</span></td>
                <td>{compact.format(safeNumber(store.total_units_sold))}</td>
                <td>{currency.format(safeNumber(store.estimated_sales_value))}</td>
                <td>{decimal.format(safeNumber(store.average_active_items))}</td>
                <td>{`${decimal.format(safeNumber(store.average_price_coverage_rate) * 100)}%`}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </Card>
    </>
  );
}

function CopilotPage({
  addAudit,
  rememberApproval,
  onNavigate,
}: {
  addAudit: (event: Omit<SessionAuditEvent, 'id' | 'at'>) => void;
  rememberApproval: (result: AgentRunResult) => void;
  onNavigate: (page: PageId) => void;
}) {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [threadId, setThreadId] = useState<string | undefined>(undefined);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      text: 'I am grounded on the RetailOps forecast service, allowlisted BigQuery analytics, model metadata and the curated knowledge base. Ask me about demand, model quality, store performance or business policy.',
      sources: ['Forecast API', 'BigQuery', 'Knowledge RAG'],
    },
  ]);

  const quickPrompts = [
    'Forecast FOODS_1_001 in CA_1 and explain the result.',
    'For FOODS_1_001 in CA_1, I have 20 units and 10 units arrive in 3 days. Use a safety stock of 6 and assess the next 5 days.',
    'Using the same scenario, what changes if that delivery is delayed by 5 days?',
  ];

  const send = async (prompt = question) => {
    const trimmed = prompt.trim();
    if (!trimmed || loading) return;
    setMessages((current) => [...current, { id: crypto.randomUUID(), role: 'user', text: trimmed }]);
    setQuestion('');
    setLoading(true);
    try {
      const result = await api.agentQuery(trimmed, threadId);
      setThreadId(result.thread_id);
      rememberApproval(result);
      const approval = result.status === 'approval_required';
      const text = approval
        ? result.approval_request?.answer_preview || result.approval_request?.proposal.description || 'A human review is required before follow-up.'
        : result.answer || 'The agent completed the request without a textual answer.';
      setMessages((current) => [...current, {
        id: crypto.randomUUID(),
        role: 'assistant',
        text,
        sources: result.evidence_sources,
        pendingApproval: approval,
      }]);
      addAudit({
        kind: 'agent',
        title: trimmed.slice(0, 90),
        status: result.status,
        threadId: result.thread_id,
        tools: result.tool_trace.map((trace) => trace.tool),
      });
    } catch (error) {
      setMessages((current) => [...current, {
        id: crypto.randomUUID(),
        role: 'assistant',
        text: `I could not complete that request: ${error instanceof Error ? error.message : 'unknown error'}`,
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="copilot-layout">
      <Card className="copilot-card">
        <div className="copilot-head">
          <div className="agent-avatar"><Sparkles size={20} /></div>
          <div><strong>RetailOps Copilot</strong><span><i /> Grounded agent online</span></div>
          <StatusPill tone="info">Gemini + LangGraph</StatusPill>
        </div>
        <div className="chat-scroll">
          {messages.map((message) => (
            <div className={classNames('chat-row', message.role)} key={message.id}>
              <div className="chat-avatar">{message.role === 'assistant' ? <Bot size={18} /> : 'OP'}</div>
              <div className="chat-bubble">
                <p>{message.text}</p>
                {message.sources?.length ? (
                  <div className="source-row">{message.sources.map((source) => <span key={source}><Database size={12} />{source}</span>)}</div>
                ) : null}
                {message.pendingApproval && (
                  <button className="approval-link" onClick={() => onNavigate('approvals')}><ShieldCheck size={14} /> Open approval center <ArrowRight size={13} /></button>
                )}
              </div>
            </div>
          ))}
          {loading && <div className="chat-row assistant"><div className="chat-avatar"><Bot size={18} /></div><div className="typing"><span /><span /><span /></div></div>}
        </div>
        <div className="composer-wrap">
          <textarea value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void send(); }
          }} placeholder="Ask RetailOps AI about demand, sales, model metrics or policy…" />
          <button className="send-button" disabled={!question.trim() || loading} onClick={() => void send()}><ArrowRight size={18} /></button>
        </div>
      </Card>
      <div className="copilot-side">
        <Card>
          <SectionHeader title="Try a grounded query" subtitle="Prompts mapped to real tools" />
          <div className="prompt-list">{quickPrompts.map((prompt) => <button key={prompt} onClick={() => void send(prompt)}><MessageSquareText size={15} /><span>{prompt}</span><ChevronRight size={14} /></button>)}</div>
        </Card>
        <Card className="trust-card">
          <div className="icon-chip"><ShieldCheck size={18} /></div>
          <h3>Trust boundary</h3>
          <p>The agent can analyze and recommend. It cannot place orders, change inventory, modify prices or execute arbitrary SQL.</p>
          <div className="trust-tags"><span>Read-only tools</span><span>Scenario memory</span><span>HITL gates</span><span>Evidence sources</span></div>
        </Card>
      </div>
    </div>
  );
}

function RecommendationsPage({ approvals, onNavigate }: { approvals: ApprovalState[]; onNavigate: (page: PageId) => void }) {
  if (!approvals.length) {
    return <Card><EmptyState icon={BrainCircuit} title="No recommendations yet" text="Ask the AI Copilot for a demand or replenishment review. Evidence-backed proposals will appear here." /><button className="primary-button centered" onClick={() => onNavigate('copilot')}><Sparkles size={16} /> Open Copilot</button></Card>;
  }
  return (
    <div className="recommendation-grid">
      {approvals.map((approval) => (
        <Card className="recommendation-card" key={approval.threadId}>
          <div className="recommendation-top">
            <div className="decision-icon"><BrainCircuit size={18} /></div>
            <StatusPill tone={approval.status === 'pending' ? 'warn' : approval.status === 'approved' ? 'good' : 'bad'}>{approval.status}</StatusPill>
          </div>
          <div className="recommendation-type">{approval.request.proposal.action_type.replaceAll('_', ' ')}</div>
          <p>{approval.request.proposal.description}</p>
          <div className="entity-tags">{approval.request.proposal.entities.map((entity) => <span key={`${entity.item_id}-${entity.store_id}`}>{entity.item_id} · {entity.store_id}</span>)}</div>
          <div className="evidence-line"><Database size={14} />{approval.request.evidence_sources.join(' + ')}</div>
          <button className="text-button" onClick={() => onNavigate('approvals')}>Review decision <ArrowRight size={14} /></button>
        </Card>
      ))}
    </div>
  );
}

function ApprovalsPage({
  approvals,
  setApprovals,
  addAudit,
}: {
  approvals: ApprovalState[];
  setApprovals: (value: ApprovalState[] | ((old: ApprovalState[]) => ApprovalState[])) => void;
  addAudit: (event: Omit<SessionAuditEvent, 'id' | 'at'>) => void;
}) {
  const [busyThread, setBusyThread] = useState<string | null>(null);
  const [noteByThread, setNoteByThread] = useState<Record<string, string>>({});

  const decide = async (approval: ApprovalState, approved: boolean) => {
    setBusyThread(approval.threadId);
    try {
      const result = await api.resume(approval.threadId, approved, noteByThread[approval.threadId] || undefined);
      setApprovals((current) => current.map((item) => item.threadId === approval.threadId ? {
        ...item,
        status: approved ? 'approved' : 'rejected',
        finalAnswer: result.answer ?? undefined,
      } : item));
      addAudit({
        kind: 'approval',
        title: approval.request.proposal.action_type.replaceAll('_', ' '),
        status: approved ? 'approved' : 'rejected',
        threadId: approval.threadId,
        tools: result.tool_trace.map((trace) => trace.tool),
      });
    } finally {
      setBusyThread(null);
    }
  };

  const pending = approvals.filter((approval) => approval.status === 'pending');
  const history = approvals.filter((approval) => approval.status !== 'pending');

  return (
    <>
      <div className="approval-summary">
        <div><span className="summary-dot warn" /><strong>{pending.length}</strong><span>Pending review</span></div>
        <div><span className="summary-dot good" /><strong>{approvals.filter((item) => item.status === 'approved').length}</strong><span>Approved</span></div>
        <div><span className="summary-dot bad" /><strong>{approvals.filter((item) => item.status === 'rejected').length}</strong><span>Rejected</span></div>
      </div>

      {pending.length ? pending.map((approval) => (
        <Card className="approval-card" key={approval.threadId}>
          <div className="approval-title-row">
            <div>
              <div className="eyebrow">Human approval required</div>
              <h2>{approval.request.proposal.action_type.replaceAll('_', ' ')}</h2>
            </div>
            <StatusPill tone="warn"><Clock3 size={13} /> Pending</StatusPill>
          </div>
          <div className="approval-grid">
            <div className="approval-main">
              <div className="approval-block"><span>Agent recommendation</span><p>{approval.request.proposal.description}</p></div>
              <div className="approval-block"><span>Evidence summary</span><p>{approval.request.answer_preview}</p></div>
              <div className="source-row">{approval.request.evidence_sources.map((source) => <span key={source}><Database size={12} />{source}</span>)}</div>
            </div>
            <div className="approval-side">
              <div className="entity-box"><span>Entities</span>{approval.request.proposal.entities.map((entity) => <strong key={`${entity.item_id}-${entity.store_id}`}>{entity.item_id}<small>{entity.store_id}</small></strong>)}</div>
              <label className="field-label">Reviewer note<textarea value={noteByThread[approval.threadId] ?? ''} onChange={(event) => setNoteByThread((current) => ({ ...current, [approval.threadId]: event.target.value }))} placeholder="Optional rationale for the audit trail…" /></label>
              <div className="approval-actions">
                <button className="reject-button" disabled={busyThread === approval.threadId} onClick={() => void decide(approval, false)}><XCircle size={16} /> Reject</button>
                <button className="approve-button" disabled={busyThread === approval.threadId} onClick={() => void decide(approval, true)}>{busyThread === approval.threadId ? <RefreshCw className="spin" size={16} /> : <Check size={16} />} Approve follow-up</button>
              </div>
              <div className="mutate-warning"><ShieldCheck size={15} /> Approval authorizes human follow-up only. No external system is mutated.</div>
            </div>
          </div>
        </Card>
      )) : <Card><EmptyState icon={ShieldCheck} title="Nothing waiting for approval" text="The human-in-the-loop queue is clear." /></Card>}

      {history.length > 0 && (
        <Card className="history-card">
          <SectionHeader title="Approval history" subtitle="Decisions completed in this operator workspace" />
          <div className="history-list">{history.map((approval) => (
            <div className="history-row" key={approval.threadId}>
              <div className={classNames('history-icon', approval.status)}>{approval.status === 'approved' ? <Check size={15} /> : <X size={15} />}</div>
              <div><strong>{approval.request.proposal.action_type.replaceAll('_', ' ')}</strong><span>{approval.threadId}</span></div>
              <StatusPill tone={approval.status === 'approved' ? 'good' : 'bad'}>{approval.status}</StatusPill>
            </div>
          ))}</div>
        </Card>
      )}
    </>
  );
}

function KnowledgePage({ documents, loading }: { documents: KnowledgeDocument[]; loading: boolean }) {
  return (
    <>
      <div className="knowledge-intro">
        <div className="knowledge-hero-icon"><FileText size={24} /></div>
        <div><h2>Curated evidence, not open-web retrieval</h2><p>These documents are the authoritative project context supplied to the RetailOps RAG tool.</p></div>
        <StatusPill tone="info">Lexical RAG</StatusPill>
      </div>
      <div className="knowledge-grid">
        {loading ? [1, 2, 3].map((item) => <Skeleton key={item} height={230} />) : documents.map((document) => (
          <Card className="knowledge-card" key={document.slug}>
            <div className="doc-top"><div className="doc-icon"><FileText size={18} /></div><span>{compact.format(document.characters)} chars</span></div>
            <h3>{document.title}</h3>
            <p>{document.excerpt || 'Curated RetailOps knowledge document.'}</p>
            <div className="doc-footer"><StatusPill tone="good">Indexed</StatusPill><span>{document.slug}.md</span></div>
          </Card>
        ))}
      </div>
    </>
  );
}

function ModelsPage({ overview, loading }: { overview: Overview | null; loading: boolean }) {
  const baselines = overview?.baseline_metrics.rows ?? [];
  const model = overview?.model;
  const metrics = (model?.metrics as Record<string, unknown> | undefined) ?? model ?? {};
  const activeRmsse = safeNumber(metrics.mean_rmsse ?? metrics.rmsse);
  return (
    <>
      <Card className="model-overview">
        <div className="model-overview-head">
          <div className="model-icon large"><BrainCircuit size={28} /></div>
          <div><div className="eyebrow">Active production model</div><h2>{modelLabel(model)}</h2><p>Global LightGBM demand forecasting · Version {modelVersion(model)}</p></div>
          <div className="model-state"><StatusPill tone="good"><CheckCircle2 size={13} /> Validated</StatusPill><span>Private serving API</span></div>
        </div>
        <div className="model-metric-strip">
          <div><span>Mean RMSSE</span><strong>{activeRmsse ? decimal.format(activeRmsse) : '0.771'}</strong></div>
          <div><span>Forecast horizon</span><strong>28</strong><small>days</small></div>
          <div><span>Objective</span><strong>Poisson</strong><small>LightGBM</small></div>
          <div><span>Serving</span><strong>Cloud Run</strong><small>private</small></div>
        </div>
      </Card>
      <div className="content-grid halves">
        <Card className="chart-card">
          <SectionHeader title="Baseline comparison" subtitle="Lower mean RMSSE is better" />
          <div className="chart-wrap">
            {loading ? <Skeleton height={300} /> : baselines.length ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={baselines} margin={{ left: -8, right: 12, top: 10 }}>
                  <CartesianGrid strokeDasharray="4 8" vertical={false} stroke="var(--grid-line)" />
                  <XAxis dataKey="baseline" tickLine={false} axisLine={false} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                  <YAxis tickLine={false} axisLine={false} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: '#0d1928', border: '1px solid #203348', borderRadius: 12 }} />
                  <Bar dataKey="mean_rmsse" radius={[7, 7, 2, 2]}>{baselines.map((_, index) => <Cell key={index} fill={index === 0 ? 'var(--accent)' : 'var(--accent-2)'} opacity={Math.max(0.35, 1 - index * 0.08)} />)}</Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : <EmptyState icon={BarChart3} title="No baseline metrics" text="Baseline metrics will render from retailops_ml when available." />}
          </div>
        </Card>
        <Card className="model-contract-card">
          <SectionHeader title="Serving contract" subtitle="What the model is allowed to claim" />
          <div className="contract-list">
            <div><CheckCircle2 size={16} /><span><strong>Validated</strong> 28-day recursive demand forecast</span></div>
            <div><CheckCircle2 size={16} /><span><strong>Validated</strong> BigQuery-backed real features</span></div>
            <div><ShieldCheck size={16} /><span><strong>Protected</strong> forecasts are not order quantities</span></div>
            <div><AlertTriangle size={16} /><span><strong>Not available</strong> true retailer inventory position</span></div>
          </div>
          <div className="info-box"><Database size={16} /><span>Model artifacts remain external to the UI image and are loaded through the serving contract.</span></div>
        </Card>
      </div>
    </>
  );
}

function MonitoringPage({ ops, readyStatus, latency, onRefresh }: { ops: OpsStatus | null; readyStatus: string; latency: number | null; onRefresh: () => Promise<void> }) {
  const services = [
    { name: 'RetailOps Agent', status: readyStatus === 'ready' ? 'Operational' : 'Unavailable', latency: latency ? `${Math.round(latency)} ms` : '—', icon: Sparkles },
    { name: 'Forecast API', status: 'Connected through agent runtime', latency: 'private service', icon: TrendingUp },
    { name: 'BigQuery Analytics', status: 'Read-only access', latency: 'allowlisted SQL', icon: Database },
    { name: 'LangGraph State', status: ops?.durable_state ? 'Durable' : 'In-memory', latency: ops?.checkpoint_backend ?? 'unknown', icon: ShieldCheck },
  ];
  return (
    <>
      <div className="monitor-hero">
        <div className={classNames('health-orb', readyStatus === 'ready' && 'healthy')}><Activity size={30} /></div>
        <div><div className="eyebrow">Platform status</div><h2>{readyStatus === 'ready' ? 'All core services are reachable' : 'Service health requires attention'}</h2><p>Production readiness from the currently deployed operator runtime.</p></div>
        <button className="secondary-button" onClick={() => void onRefresh()}><RefreshCw size={16} /> Run health check</button>
      </div>
      <div className="service-grid">
        {services.map((service) => {
          const Icon = service.icon;
          return <Card className="service-card" key={service.name}><div className="service-top"><div className="icon-chip"><Icon size={18} /></div><span className="service-dot" /></div><h3>{service.name}</h3><strong>{service.status}</strong><span>{service.latency}</span></Card>;
        })}
      </div>
      <Card className="ops-card">
        <SectionHeader title="Runtime metadata" subtitle="Reported by /v1/ops/status" />
        <div className="ops-grid">
          <div><span>Environment</span><strong>{ops?.environment ?? '—'}</strong></div>
          <div><span>Release</span><strong>{ops?.release ?? '—'}</strong></div>
          <div><span>Checkpoint backend</span><strong>{ops?.checkpoint_backend ?? '—'}</strong></div>
          <div><span>Durable state</span><strong>{ops?.durable_state ? 'Enabled' : 'Not enabled'}</strong></div>
          <div><span>Readiness</span><strong>{readyStatus}</strong></div>
          <div><span>Console probe latency</span><strong>{latency ? `${Math.round(latency)} ms` : '—'}</strong></div>
        </div>
      </Card>
    </>
  );
}

function AuditPage({ events }: { events: SessionAuditEvent[] }) {
  return (
    <Card className="audit-card">
      <SectionHeader title="Operator session trail" subtitle="Local console history backed by real response thread and tool metadata" action={<StatusPill tone="neutral">Last {events.length} events</StatusPill>} />
      {events.length ? (
        <div className="audit-list">{events.map((event) => (
          <div className="audit-row" key={event.id}>
            <div className={classNames('audit-kind', event.kind)}>{event.kind === 'agent' ? <Bot size={15} /> : event.kind === 'approval' ? <ShieldCheck size={15} /> : <TrendingUp size={15} />}</div>
            <div className="audit-main"><strong>{event.title}</strong><span>{new Date(event.at).toLocaleString()}</span></div>
            <div className="audit-tools">{event.tools?.slice(0, 3).map((tool) => <span key={tool}>{tool}</span>)}</div>
            <div className="audit-thread">{event.threadId ?? '—'}</div>
            <StatusPill tone={event.status.includes('approved') || event.status === 'completed' ? 'good' : event.status.includes('required') ? 'warn' : 'bad'}>{event.status}</StatusPill>
          </div>
        ))}</div>
      ) : <EmptyState icon={TerminalSquare} title="No console events yet" text="Forecasts, Copilot calls and approval decisions will create a trace here." />}
    </Card>
  );
}

function SettingsPage() {
  return (
    <div className="settings-grid">
      <Card>
        <SectionHeader title="Access model" subtitle="Current portfolio release" />
        <div className="role-card"><div className="role-icon"><UserRoundCheck size={20} /></div><div><strong>Operator</strong><span>Full workspace access</span></div><StatusPill tone="good">Active</StatusPill></div>
        <div className="settings-copy">One role is enabled for now. Fine-grained RBAC can be introduced later without changing the console information architecture.</div>
      </Card>
      <Card>
        <SectionHeader title="Safety defaults" subtitle="Applied across the agent workspace" />
        <div className="toggle-list">
          <div><div><strong>Human approval gates</strong><span>Business follow-up proposals require explicit review.</span></div><span className="fake-toggle on" /></div>
          <div><div><strong>Read-only analytics</strong><span>No arbitrary SQL or operational writes.</span></div><span className="fake-toggle on" /></div>
          <div><div><strong>Evidence visibility</strong><span>Tool sources are shown in Copilot responses.</span></div><span className="fake-toggle on" /></div>
        </div>
      </Card>
      <Card className="settings-wide">
        <SectionHeader title="Data boundary" subtitle="Important context for operators" />
        <div className="boundary-grid">
          <div className="boundary-card good"><CheckCircle2 size={19} /><div><strong>Available</strong><span>Sales, prices, calendar, forecasts, model metrics</span></div></div>
          <div className="boundary-card warn"><AlertTriangle size={19} /><div><strong>Not available</strong><span>True retailer inventory position, purchase orders and lead times</span></div></div>
          <div className="boundary-card info"><ShieldCheck size={19} /><div><strong>Policy</strong><span>Never convert a demand forecast directly into an order quantity</span></div></div>
        </div>
      </Card>
    </div>
  );
}

export default App;
