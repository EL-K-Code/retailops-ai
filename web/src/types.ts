export type Split = 'validation' | 'test';

export type ToolTrace = {
  tool: string;
  status: string;
  signature?: string;
};

export type AgentRunResult = {
  status: 'completed' | 'approval_required';
  thread_id: string;
  answer: string | null;
  approval_request: ApprovalRequest | null;
  evidence_sources: string[];
  tool_trace: ToolTrace[];
};

export type ApprovalRequest = {
  type: string;
  question: string;
  proposal: {
    action_type: 'review_reorder' | 'review_safety_stock' | 'investigate_anomaly' | 'escalate_to_planner';
    description: string;
    entities: Array<{ item_id: string; store_id: string }>;
  };
  answer_preview: string;
  evidence_sources: string[];
  notice: string;
};

export type AnalyticsResult<T = Record<string, unknown>> = {
  operation: string;
  split: Split;
  rows: T[];
  bytes_processed: number;
  maximum_bytes_billed: number;
};

export type Overview = {
  split: Split;
  sales_summary: AnalyticsResult<{
    start_date: string | null;
    end_date: string | null;
    observed_days: number;
    total_units_sold: number;
    average_daily_units: number;
    peak_daily_units: number;
    estimated_sales_value: number;
  }>;
  store_summary: AnalyticsResult<{
    store_id: string;
    start_date: string;
    end_date: string;
    total_units_sold: number;
    average_active_items: number;
    estimated_sales_value: number;
    average_price_coverage_rate: number;
  }>;
  top_products: AnalyticsResult<{
    item_id: string;
    total_units_sold: number;
    estimated_sales_value: number;
    average_price_coverage_rate: number;
  }>;
  baseline_metrics: AnalyticsResult<{
    baseline: string;
    mae: number;
    rmse: number;
    mean_rmsse: number;
  }>;
  model: Record<string, unknown>;
};

export type ForecastResponse = {
  request_id?: string;
  split?: Split;
  forecast_origin?: string;
  horizon?: number;
  model?: Record<string, unknown>;
  forecasts?: Array<{
    item_id?: string;
    store_id?: string;
    series_id?: string;
    predictions?: Array<{ horizon?: number; date?: string; prediction?: number; yhat?: number }>;
  }>;
  predictions?: Array<{ horizon?: number; date?: string; prediction?: number; yhat?: number }>;
  [key: string]: unknown;
};

export type OpsStatus = {
  service: string;
  environment: string;
  release: string;
  checkpoint_backend: string;
  durable_state: boolean;
  ready: boolean;
};

export type KnowledgeDocument = {
  slug: string;
  title: string;
  excerpt: string;
  characters: number;
};

export type SessionAuditEvent = {
  id: string;
  at: string;
  kind: 'agent' | 'forecast' | 'approval';
  title: string;
  status: string;
  threadId?: string;
  tools?: string[];
};
