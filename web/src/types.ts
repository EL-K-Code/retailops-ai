export type Split = 'validation' | 'test';

export type ToolTrace = {
  tool: string;
  status: string;
  signature?: string;
  latency_ms?: number;
};

export type AgentRunResult = {
  status: 'completed' | 'approval_required';
  thread_id: string;
  answer: string | null;
  approval_request: ApprovalRequest | null;
  evidence_sources: string[];
  tool_trace: ToolTrace[];
  active_scenario?: Record<string, unknown> | null;
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

export type ForecastPoint = {
  horizon?: number;
  date?: string;
  prediction?: number;
  yhat?: number;
};

export type ForecastResponse = {
  request_id?: string;
  split?: Split;
  forecast_origin?: string;
  horizon?: number;
  horizon_days?: number;
  generated_at?: string;
  model?: Record<string, unknown>;
  forecasts?: Array<{
    item_id?: string;
    store_id?: string;
    series_id?: string;
    points?: ForecastPoint[];
    predictions?: ForecastPoint[];
  }>;
  predictions?: ForecastPoint[];
  [key: string]: unknown;
};

export type InventoryTrajectoryPoint = {
  date: string | null;
  horizon: number;
  forecast_demand: number;
  projected_inventory: number;
  safety_stock: number;
};

export type CounterfactualOption = {
  kind: string;
  label: string;
  change: Record<string, number>;
  scenario: {
    current_stock: number;
    incoming_units: number;
    lead_time_days: number;
    safety_stock: number;
  };
  result: {
    risk_level: 'low' | 'medium' | 'high';
    projected_end_inventory: number;
    stockout_day: number | null;
    safety_breach_day: number | null;
  };
};

export type ForecastUncertainty = {
  method: string;
  lower_quantile: number;
  upper_quantile: number;
  points: Array<{
    date: string | null;
    horizon: number;
    prediction: number;
    lower: number;
    upper: number;
  }>;
  total_prediction: number;
  total_lower: number;
  total_upper: number;
  notice: string;
};

export type ReorderOptimization = {
  economics: Record<string, number>;
  recommended_additional_units: number;
  best_candidate: {
    additional_units: number;
    total_scenario_cost: number;
    order_cost: number;
    holding_cost: number;
    stockout_penalty: number;
    safety_breach_penalty: number;
    risk_level: 'low' | 'medium' | 'high';
    projected_end_inventory: number;
    stockout_day: number | null;
    safety_breach_day: number | null;
  };
  candidates_evaluated: number;
  notice: string;
};

export type InventoryScenarioResponse = {
  request_id: string;
  split: Split;
  forecast_origin: string;
  horizon_days: number;
  model: Record<string, unknown>;
  entity: {
    series_id: string;
    item_id: string;
    store_id: string;
  };
  scenario: {
    current_stock: number;
    incoming_units: number;
    lead_time_days: number;
    safety_stock: number;
  };
  scenario_mode: boolean;
  scenario_notice: string;
  forecast_total: number;
  available_units: number;
  projected_end_inventory: number;
  shortage_units: number;
  safety_stock_gap: number;
  review_quantity: number;
  stockout_day: number | null;
  safety_breach_day: number | null;
  risk_level: 'low' | 'medium' | 'high';
  recommended_action: 'monitor' | 'review_reorder' | 'review_safety_stock';
  recommendation: string;
  trajectory: InventoryTrajectoryPoint[];
  counterfactuals: {
    baseline_risk: 'low' | 'medium' | 'high';
    decision_horizon_days: number;
    minimum_immediate_units: number | null;
    minimum_po_increase: number | null;
    latest_safe_arrival_day: number | null;
    options: CounterfactualOption[];
    notice: string;
  };
  uncertainty: ForecastUncertainty;
  upper_demand_stress: {
    risk_level: 'low' | 'medium' | 'high';
    projected_end_inventory: number;
    stockout_day: number | null;
    safety_breach_day: number | null;
  };
  reorder_optimization?: ReorderOptimization;
};

export type FeatureAttribution = {
  feature: string;
  mean_abs_contribution: number;
  mean_contribution: number;
  share: number;
  direction: 'up' | 'down';
};

export type ForecastExplanationResponse = {
  request_id: string;
  split: Split;
  forecast_origin: string;
  horizon_days: number;
  generated_at: string;
  model: Record<string, unknown>;
  method: string;
  contribution_space: string;
  notice: string;
  explanations: Array<{
    series_id: string;
    item_id: string;
    store_id: string;
    features: FeatureAttribution[];
  }>;
};

export type DriftReport = {
  metric: string;
  psi: number;
  mean_shift_std: number;
  status: 'stable' | 'watch' | 'shifted';
  reference_observations: number;
  current_observations: number;
  reference_mean: number;
  current_mean: number;
  notice: string;
};

export type MorningBrief = {
  generated_at: string;
  split: Split;
  priorities: Array<{
    severity: 'watch' | 'high' | 'critical';
    type: 'demand_spike' | 'demand_drop';
    item_id: string;
    store_id: string;
    date: string;
    units_sold: number;
    rolling_mean_28: number;
    anomaly_z: number;
  }>;
  top_products: AnalyticsResult<{
    item_id: string;
    total_units_sold: number;
    estimated_sales_value: number;
    average_price_coverage_rate: number;
  }>;
  demand_drift: DriftReport;
  model: Record<string, unknown>;
  limitations: string[];
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
