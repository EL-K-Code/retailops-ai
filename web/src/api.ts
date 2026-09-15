import type {
  AgentRunResult,
  AnalyticsResult,
  ForecastExplanationResponse,
  ForecastResponse,
  InventoryScenarioResponse,
  KnowledgeDocument,
  OpsStatus,
  Overview,
  Split,
} from './types';

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

function requestId(prefix: string): string {
  const random = crypto.randomUUID?.() ?? Math.random().toString(36).slice(2);
  return `${prefix}-${random}`;
}

async function fetchJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has('content-type')) headers.set('content-type', 'application/json');
  if (!headers.has('x-request-id')) headers.set('x-request-id', requestId('console'));

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: 'same-origin',
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // Keep HTTP fallback.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

function normalizeForecastResponse(response: ForecastResponse): ForecastResponse {
  const raw = response as ForecastResponse & {
    horizon_days?: number;
    forecasts?: Array<Record<string, unknown>>;
  };

  const normalizedForecasts = Array.isArray(raw.forecasts)
    ? raw.forecasts.map((forecast) => {
        const points = Array.isArray(forecast.points) ? forecast.points : [];
        const predictions = Array.isArray(forecast.predictions) ? forecast.predictions : points;
        return { ...forecast, predictions };
      })
    : raw.forecasts;

  return {
    ...response,
    horizon: response.horizon ?? raw.horizon_days,
    forecasts: normalizedForecasts as ForecastResponse['forecasts'],
  };
}

export const api = {
  overview(split: Split = 'test') {
    return fetchJson<Overview>(`/v1/console/overview?split=${split}`);
  },

  analytics(payload: {
    operation: 'sales_summary' | 'store_summary' | 'top_products' | 'baseline_metrics';
    split?: Split;
    item_id?: string | null;
    store_id?: string | null;
    top_n?: number;
  }) {
    return fetchJson<AnalyticsResult>('/v1/console/analytics', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async forecast(itemId: string, storeId: string, split: Split = 'test') {
    const response = await fetchJson<ForecastResponse>('/v1/console/forecast', {
      method: 'POST',
      body: JSON.stringify({
        entities: [{ item_id: itemId, store_id: storeId }],
        split,
      }),
    });
    return normalizeForecastResponse(response);
  },

  inventoryScenario(payload: {
    item_id: string;
    store_id: string;
    split: Split;
    current_stock: number;
    incoming_units: number;
    lead_time_days: number;
    safety_stock: number;
  }) {
    return fetchJson<InventoryScenarioResponse>('/v1/console/inventory-scenario', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  explainForecast(itemId: string, storeId: string, split: Split = 'test', topN = 6) {
    return fetchJson<ForecastExplanationResponse>('/v1/console/explain', {
      method: 'POST',
      body: JSON.stringify({
        item_id: itemId,
        store_id: storeId,
        split,
        top_n: topN,
      }),
    });
  },

  model() {
    return fetchJson<Record<string, unknown>>('/v1/console/model');
  },

  knowledge() {
    return fetchJson<{ documents: KnowledgeDocument[] }>('/v1/console/knowledge');
  },

  opsStatus() {
    return fetchJson<OpsStatus>('/v1/ops/status');
  },

  ready() {
    return fetchJson<{ status: string }>('/readyz');
  },

  agentQuery(question: string, threadId?: string) {
    return fetchJson<AgentRunResult>('/v1/agent/query', {
      method: 'POST',
      body: JSON.stringify({
        question,
        user_context: { role: 'operator' },
        thread_id: threadId,
      }),
      headers: { 'x-request-id': threadId ?? requestId('console-agent') },
    });
  },

  resume(threadId: string, approved: boolean, reviewerNote?: string) {
    return fetchJson<AgentRunResult>('/v1/agent/resume', {
      method: 'POST',
      body: JSON.stringify({
        thread_id: threadId,
        approved,
        reviewer_note: reviewerNote || null,
      }),
      headers: { 'x-request-id': `${threadId}-resume` },
    });
  },
};
