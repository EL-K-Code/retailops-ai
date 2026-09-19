import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BrainCircuit,
  CheckCircle2,
  Database,
  Gauge,
  PackageCheck,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  TrendingUp,
} from 'lucide-react';
import { useMemo, useState } from 'react';
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api } from './api';
import type {
  FeatureAttribution,
  ForecastExplanationResponse,
  InventoryScenarioResponse,
  Split,
} from './types';

const number = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 });
const percent = new Intl.NumberFormat('en-US', { style: 'percent', maximumFractionDigits: 1 });

const STYLES = `
.decision-lab{display:grid;gap:18px;color:#eaf2f8}.decision-hero{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;padding:4px 2px 8px}.decision-hero-copy{max-width:760px}.decision-eyebrow{display:flex;align-items:center;gap:7px;color:#59e1c3;font-size:10px;font-weight:800;letter-spacing:.13em;text-transform:uppercase}.decision-hero h1{margin:8px 0 7px;font-size:28px;line-height:1.05}.decision-hero p{margin:0;color:#8da2b5;font-size:12px;line-height:1.65}.decision-stack{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:7px;max-width:430px}.decision-chip{display:inline-flex;align-items:center;gap:6px;padding:7px 9px;border:1px solid #20364b;border-radius:999px;background:#0b1928;color:#9fb4c7;font-size:9px;font-weight:700}.decision-chip strong{color:#e7f1f7}.decision-grid{display:grid;grid-template-columns:330px minmax(0,1fr);gap:16px}.decision-card{border:1px solid #1c3044;border-radius:17px;background:linear-gradient(180deg,rgba(13,28,43,.98),rgba(8,19,31,.98));box-shadow:0 18px 45px rgba(0,0,0,.18)}.decision-controls{align-self:start;padding:18px;position:sticky;top:88px}.decision-section-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:15px}.decision-section-head h2{margin:0;font-size:14px}.decision-section-head p{margin:4px 0 0;color:#758ba0;font-size:10px;line-height:1.5}.scenario-badge{display:inline-flex;align-items:center;gap:5px;padding:5px 7px;border:1px solid rgba(246,190,90,.25);border-radius:8px;background:rgba(246,190,90,.08);color:#f6c46e;font-size:8px;font-weight:800;white-space:nowrap}.decision-field{display:grid;gap:6px;margin:11px 0;color:#8fa5b7;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.07em}.decision-field input,.decision-field select{width:100%;box-sizing:border-box;height:39px;padding:0 11px;border:1px solid #20364b;border-radius:10px;outline:none;background:#081522;color:#eaf2f8;font:inherit;font-size:11px;text-transform:none;letter-spacing:0}.decision-field input:focus,.decision-field select:focus{border-color:#3f8f86;box-shadow:0 0 0 3px rgba(82,225,195,.06)}.decision-fields-two{display:grid;grid-template-columns:1fr 1fr;gap:9px}.decision-notice{display:flex;gap:8px;margin:14px 0;padding:10px;border:1px solid rgba(246,190,90,.18);border-radius:11px;background:rgba(246,190,90,.05);color:#b5a47f;font-size:9px;line-height:1.5}.decision-run{display:flex;width:100%;height:42px;align-items:center;justify-content:center;gap:8px;border:0;border-radius:11px;background:linear-gradient(135deg,#52e1c3,#5ea6ff);color:#04131b;font:inherit;font-size:10px;font-weight:900;cursor:pointer}.decision-run:disabled{cursor:not-allowed;opacity:.55}.decision-error{display:flex;gap:7px;margin-top:10px;padding:9px 10px;border:1px solid rgba(248,113,113,.2);border-radius:10px;background:rgba(248,113,113,.06);color:#f3a1a1;font-size:9px}.decision-main{display:grid;gap:16px}.decision-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.decision-kpi{padding:15px}.decision-kpi-top{display:flex;align-items:center;justify-content:space-between;color:#6f879b}.decision-kpi-icon{display:grid;width:30px;height:30px;place-items:center;border:1px solid #1f3a4d;border-radius:9px;background:#0a1b2a;color:#58ddc1}.decision-kpi-label{margin-top:14px;color:#7d92a5;font-size:9px}.decision-kpi-value{margin-top:4px;color:#f1f7fa;font-size:22px;font-weight:800;letter-spacing:-.03em}.decision-kpi-helper{margin-top:4px;color:#5f768a;font-size:8px;line-height:1.4}.risk-pill{padding:5px 7px;border-radius:999px;font-size:8px;font-weight:900;text-transform:uppercase}.risk-pill.low{background:rgba(82,225,195,.09);color:#5be3c5}.risk-pill.medium{background:rgba(246,190,90,.1);color:#f6c46e}.risk-pill.high{background:rgba(248,113,113,.1);color:#f58e8e}.decision-chart-card,.decision-explain-card,.decision-reco-card{padding:17px}.decision-chart{height:330px}.decision-placeholder{display:grid;height:280px;place-items:center;text-align:center;color:#60788d}.decision-placeholder div{max-width:360px}.decision-placeholder strong{display:block;margin:8px 0 5px;color:#b9c9d6;font-size:12px}.decision-placeholder span{font-size:9px;line-height:1.5}.decision-two{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(300px,.8fr);gap:16px}.explain-meta{display:flex;align-items:center;gap:7px;color:#71899c;font-size:8px}.explain-bars{height:280px}.feature-list{display:grid;gap:7px;margin-top:8px}.feature-row{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:9px;align-items:center;padding:8px 9px;border:1px solid #172b3e;border-radius:9px;background:#091725}.feature-row strong{overflow:hidden;color:#cddbe5;font-size:9px;text-overflow:ellipsis}.feature-share{color:#8198aa;font-size:9px;font-variant-numeric:tabular-nums}.feature-direction{display:inline-flex;align-items:center;gap:3px;font-size:8px;font-weight:800}.feature-direction.up{color:#5ee1c4}.feature-direction.down{color:#f39b8c}.decision-reco{display:grid;gap:10px}.decision-reco-top{display:flex;align-items:center;gap:10px}.decision-reco-icon{display:grid;width:38px;height:38px;place-items:center;border:1px solid rgba(94,166,255,.18);border-radius:11px;background:rgba(94,166,255,.07);color:#6eafff}.decision-reco h3{margin:0;font-size:12px}.decision-reco p{margin:3px 0 0;color:#7f95a8;font-size:9px}.decision-reco-text{padding:12px;border:1px solid #1a3145;border-radius:11px;background:#081623;color:#c5d5df;font-size:10px;line-height:1.6}.decision-trust{display:flex;gap:8px;padding:10px;border:1px solid rgba(82,225,195,.14);border-radius:10px;background:rgba(82,225,195,.04);color:#83a699;font-size:8px;line-height:1.5}.decision-actions-card{padding:17px}.counter-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}.counter-option{padding:12px;border:1px solid #1a3145;border-radius:11px;background:#081623}.counter-option strong{display:block;font-size:10px}.counter-option span{display:block;margin-top:5px;color:#7891a5;font-size:8px;line-height:1.5}.decision-econ-label{margin-top:15px;color:#59e1c3;font-size:8px;font-weight:900;letter-spacing:.09em;text-transform:uppercase}.stress-strip{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.stress-strip div{padding:10px;border:1px solid #1a3145;border-radius:10px;background:#081623}.stress-strip span{display:block;color:#6f879b;font-size:8px}.stress-strip strong{display:block;margin-top:4px;font-size:11px}.spin{animation:decision-spin .8s linear infinite}@keyframes decision-spin{to{transform:rotate(360deg)}}@media(max-width:1120px){.decision-grid{grid-template-columns:1fr}.decision-controls{position:static}.decision-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.decision-two{grid-template-columns:1fr}}@media(max-width:620px){.decision-hero{display:grid}.decision-stack{justify-content:flex-start}.decision-fields-two,.decision-kpis{grid-template-columns:1fr}.decision-chart{height:280px}}
`;

function Kpi({ icon: Icon, label, value, helper, risk }: {
  icon: typeof TrendingUp;
  label: string;
  value: string;
  helper: string;
  risk?: 'low' | 'medium' | 'high';
}) {
  return (
    <div className="decision-card decision-kpi">
      <div className="decision-kpi-top">
        <div className="decision-kpi-icon"><Icon size={16} /></div>
        {risk && <span className={`risk-pill ${risk}`}>{risk}</span>}
      </div>
      <div className="decision-kpi-label">{label}</div>
      <div className="decision-kpi-value">{value}</div>
      <div className="decision-kpi-helper">{helper}</div>
    </div>
  );
}

function FeatureRows({ features }: { features: FeatureAttribution[] }) {
  return (
    <div className="feature-list">
      {features.map((feature) => (
        <div className="feature-row" key={feature.feature}>
          <strong>{feature.feature.replaceAll('_', ' ')}</strong>
          <span className="feature-share">{percent.format(feature.share)}</span>
          <span className={`feature-direction ${feature.direction}`}>
            {feature.direction === 'up' ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
            {feature.direction}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function DecisionLabPage() {
  const [itemId, setItemId] = useState('FOODS_1_001');
  const [storeId, setStoreId] = useState('CA_1');
  const [split, setSplit] = useState<Split>('test');
  const [currentStock, setCurrentStock] = useState(20);
  const [incomingUnits, setIncomingUnits] = useState(5);
  const [leadTimeDays, setLeadTimeDays] = useState(5);
  const [safetyStock, setSafetyStock] = useState(6);
  const [unitOrderCost, setUnitOrderCost] = useState(1);
  const [holdingCost, setHoldingCost] = useState(0.05);
  const [stockoutPenalty, setStockoutPenalty] = useState(5);
  const [safetyPenalty, setSafetyPenalty] = useState(1);
  const [minOrderQuantity, setMinOrderQuantity] = useState(1);
  const [orderIncrement, setOrderIncrement] = useState(1);
  const [maxAdditionalUnits, setMaxAdditionalUnits] = useState(60);
  const [scenario, setScenario] = useState<InventoryScenarioResponse | null>(null);
  const [explanation, setExplanation] = useState<ForecastExplanationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const features = explanation?.explanations?.[0]?.features ?? [];
  const featureChart = useMemo(
    () => features.map((feature) => ({
      feature: feature.feature.replaceAll('_', ' '),
      share: feature.share * 100,
    })),
    [features],
  );
  const chartData = useMemo(() => {
    const band = new Map(
      (scenario?.uncertainty?.points ?? []).map((point) => [point.horizon, point]),
    );
    return (scenario?.trajectory ?? []).map((point) => ({
      ...point,
      forecast_lower: band.get(point.horizon)?.lower,
      forecast_upper: band.get(point.horizon)?.upper,
    }));
  }, [scenario]);
  const counterfactuals = scenario?.counterfactuals?.options ?? [];

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const [scenarioResult, explainResult] = await Promise.all([
        api.inventoryScenario({
          item_id: itemId.trim(),
          store_id: storeId.trim(),
          split,
          current_stock: Number(currentStock),
          incoming_units: Number(incomingUnits),
          lead_time_days: Number(leadTimeDays),
          safety_stock: Number(safetyStock),
          economics: {
            unit_order_cost: Number(unitOrderCost),
            holding_cost_per_unit: Number(holdingCost),
            stockout_penalty_per_unit: Number(stockoutPenalty),
            safety_breach_penalty_per_unit: Number(safetyPenalty),
            min_order_quantity: Number(minOrderQuantity),
            order_increment: Number(orderIncrement),
            max_additional_units: Number(maxAdditionalUnits),
          },
        }),
        api.explainForecast(itemId.trim(), storeId.trim(), split, 6),
      ]);
      setScenario(scenarioResult);
      setExplanation(explainResult);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Decision Lab request failed.');
    } finally {
      setLoading(false);
    }
  };

  const risk = scenario?.risk_level;

  return (
    <div className="decision-lab">
      <style>{STYLES}</style>
      <div className="decision-hero">
        <div className="decision-hero-copy">
          <div className="decision-eyebrow"><Sparkles size={13} /> Decision intelligence lab</div>
          <h1>Forecast → risk → explain → human decision</h1>
          <p>
            Combine the live 28-day LightGBM forecast with explicit inventory assumptions,
            deterministic stock-risk logic and local TreeSHAP evidence. No inventory value is
            inferred from M5 and no operational action is executed automatically.
          </p>
        </div>
        <div className="decision-stack">
          <span className="decision-chip"><Database size={12} /><strong>Live</strong> forecast</span>
          <span className="decision-chip"><Gauge size={12} /><strong>Deterministic</strong> rules</span>
          <span className="decision-chip"><BrainCircuit size={12} /><strong>TreeSHAP</strong> evidence</span>
          <span className="decision-chip"><ShieldCheck size={12} /><strong>Human</strong> control</span>
        </div>
      </div>

      <div className="decision-grid">
        <aside className="decision-card decision-controls">
          <div className="decision-section-head">
            <div><h2>Inventory scenario</h2><p>Editable simulation inputs</p></div>
            <span className="scenario-badge">Scenario mode</span>
          </div>

          <label className="decision-field">Item ID
            <input value={itemId} onChange={(event) => setItemId(event.target.value)} />
          </label>
          <label className="decision-field">Store ID
            <input value={storeId} onChange={(event) => setStoreId(event.target.value)} />
          </label>
          <label className="decision-field">Evaluation split
            <select value={split} onChange={(event) => setSplit(event.target.value as Split)}>
              <option value="test">Test</option>
              <option value="validation">Validation</option>
            </select>
          </label>

          <div className="decision-fields-two">
            <label className="decision-field">Current stock
              <input type="number" min="0" step="1" value={currentStock} onChange={(event) => setCurrentStock(Number(event.target.value))} />
            </label>
            <label className="decision-field">Incoming PO
              <input type="number" min="0" step="1" value={incomingUnits} onChange={(event) => setIncomingUnits(Number(event.target.value))} />
            </label>
            <label className="decision-field">Lead time (days)
              <input type="number" min="0" max="28" step="1" value={leadTimeDays} onChange={(event) => setLeadTimeDays(Number(event.target.value))} />
            </label>
            <label className="decision-field">Safety stock
              <input type="number" min="0" step="1" value={safetyStock} onChange={(event) => setSafetyStock(Number(event.target.value))} />
            </label>
          </div>

          <div className="decision-econ-label">Economic assumptions · scenario only</div>
          <div className="decision-fields-two">
            <label className="decision-field">Unit order cost
              <input type="number" min="0" step="0.1" value={unitOrderCost} onChange={(event) => setUnitOrderCost(Number(event.target.value))} />
            </label>
            <label className="decision-field">Holding cost / unit
              <input type="number" min="0" step="0.01" value={holdingCost} onChange={(event) => setHoldingCost(Number(event.target.value))} />
            </label>
            <label className="decision-field">Stockout penalty / unit
              <input type="number" min="0" step="0.1" value={stockoutPenalty} onChange={(event) => setStockoutPenalty(Number(event.target.value))} />
            </label>
            <label className="decision-field">Safety breach penalty
              <input type="number" min="0" step="0.1" value={safetyPenalty} onChange={(event) => setSafetyPenalty(Number(event.target.value))} />
            </label>
            <label className="decision-field">MOQ
              <input type="number" min="0" step="1" value={minOrderQuantity} onChange={(event) => setMinOrderQuantity(Number(event.target.value))} />
            </label>
            <label className="decision-field">Order increment
              <input type="number" min="1" step="1" value={orderIncrement} onChange={(event) => setOrderIncrement(Number(event.target.value))} />
            </label>
            <label className="decision-field">Max extra units
              <input type="number" min="0" step="1" value={maxAdditionalUnits} onChange={(event) => setMaxAdditionalUnits(Number(event.target.value))} />
            </label>
          </div>

          <div className="decision-notice">
            <AlertTriangle size={15} />
            <span>Stock, incoming PO, lead time and safety stock are scenario inputs — not facts contained in the M5 dataset.</span>
          </div>
          <button className="decision-run" disabled={loading || !itemId.trim() || !storeId.trim()} onClick={() => void run()}>
            {loading ? <RefreshCw className="spin" size={16} /> : <Sparkles size={16} />}
            {loading ? 'Running live decision stack…' : 'Run decision scenario'}
          </button>
          {error && <div className="decision-error"><AlertTriangle size={14} />{error}</div>}
        </aside>

        <main className="decision-main">
          <div className="decision-kpis">
            <Kpi icon={TrendingUp} label="28-day demand" value={scenario ? number.format(scenario.forecast_total) : '—'} helper="Live model forecast units" />
            <Kpi icon={PackageCheck} label="Available units" value={scenario ? number.format(scenario.available_units) : '—'} helper="Current stock + incoming scenario PO" />
            <Kpi icon={Gauge} label="End inventory" value={scenario ? number.format(scenario.projected_end_inventory) : '—'} helper={scenario?.stockout_day ? `Stockout around D+${scenario.stockout_day}` : 'Projected horizon balance'} />
            <Kpi icon={ShieldCheck} label="Decision risk" value={risk ? risk.toUpperCase() : '—'} helper={scenario ? `${number.format(scenario.review_quantity)} units flagged for review` : 'Awaiting scenario'} risk={risk} />
          </div>

          <section className="decision-card decision-chart-card">
            <div className="decision-section-head">
              <div><h2>Projected inventory coverage</h2><p>Forecast demand consumed against the scenario inventory position</p></div>
              {scenario && <span className={`risk-pill ${scenario.risk_level}`}>{scenario.risk_level} risk</span>}
            </div>
            <div className="decision-chart">
              {scenario ? (
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData} margin={{ top: 12, right: 14, left: -10, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="4 8" vertical={false} stroke="rgba(124,151,173,.14)" />
                    <XAxis dataKey="horizon" tickFormatter={(value) => `D+${value}`} tickLine={false} axisLine={false} tick={{ fill: '#6f879b', fontSize: 9 }} />
                    <YAxis tickLine={false} axisLine={false} tick={{ fill: '#6f879b', fontSize: 9 }} />
                    <Tooltip contentStyle={{ background: '#081522', border: '1px solid #20364b', borderRadius: 11, fontSize: 10 }} formatter={(value, name) => [`${number.format(Number(value))} units`, String(name)]} />
                    <ReferenceLine y={0} stroke="#e97979" strokeDasharray="4 4" />
                    <ReferenceLine y={scenario.scenario.safety_stock} stroke="#e6b95f" strokeDasharray="5 5" label={{ value: 'Safety stock', fill: '#b39762', fontSize: 8, position: 'insideTopRight' }} />
                    <Area type="monotone" dataKey="projected_inventory" name="Projected inventory" stroke="#55dec1" fill="rgba(82,225,195,.13)" strokeWidth={2.5} />
                    <Line type="monotone" dataKey="forecast_upper" name="Upper demand stress" stroke="#f0b96b" strokeWidth={1.1} strokeDasharray="5 5" dot={false} />
                    <Line type="monotone" dataKey="forecast_demand" name="Daily forecast" stroke="#68a9ff" strokeWidth={1.8} dot={false} />
                    <Line type="monotone" dataKey="forecast_lower" name="Lower demand stress" stroke="#6f879b" strokeWidth={1} strokeDasharray="4 6" dot={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              ) : (
                <div className="decision-placeholder"><div><Gauge size={28} /><strong>Ready for scenario simulation</strong><span>Run the decision stack to combine the live forecast with explicit inventory assumptions.</span></div></div>
              )}
            </div>
          </section>

          <div className="decision-two">
            <section className="decision-card decision-explain-card">
              <div className="decision-section-head">
                <div><h2>Why this forecast?</h2><p>Top local drivers across the recursive 28-day horizon</p></div>
                {explanation && <div className="explain-meta"><BrainCircuit size={12} />{explanation.method}</div>}
              </div>
              {features.length ? (
                <>
                  <div className="explain-bars">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={featureChart} layout="vertical" margin={{ left: 12, right: 16, top: 4, bottom: 4 }}>
                        <CartesianGrid strokeDasharray="4 8" horizontal={false} stroke="rgba(124,151,173,.12)" />
                        <XAxis type="number" tickFormatter={(value) => `${number.format(Number(value))}%`} tickLine={false} axisLine={false} tick={{ fill: '#6f879b', fontSize: 8 }} />
                        <YAxis dataKey="feature" type="category" width={118} tickLine={false} axisLine={false} tick={{ fill: '#93a8b9', fontSize: 8 }} />
                        <Tooltip contentStyle={{ background: '#081522', border: '1px solid #20364b', borderRadius: 11, fontSize: 10 }} formatter={(value) => [`${number.format(Number(value))}%`, 'Influence share']} />
                        <Bar dataKey="share" fill="#65a9ff" radius={[0, 6, 6, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <FeatureRows features={features} />
                  <div className="decision-trust"><ShieldCheck size={14} /><span>{explanation?.notice}</span></div>
                </>
              ) : (
                <div className="decision-placeholder"><div><BrainCircuit size={28} /><strong>Explainability waits for inference</strong><span>TreeSHAP evidence is computed from the same LightGBM model and recursive feature state used for forecasting.</span></div></div>
              )}
            </section>

            <section className="decision-card decision-reco-card">
              <div className="decision-reco">
                <div className="decision-reco-top">
                  <div className="decision-reco-icon">{risk === 'low' ? <CheckCircle2 size={20} /> : <AlertTriangle size={20} />}</div>
                  <div><h3>Deterministic recommendation</h3><p>{scenario ? scenario.recommended_action.replaceAll('_', ' ') : 'Awaiting scenario evidence'}</p></div>
                </div>
                <div className="decision-reco-text">
                  {scenario?.recommendation ?? 'The decision engine will surface stockout or safety-stock risk after the scenario runs.'}
                </div>
                {scenario && (
                  <div className="feature-list">
                    <div className="feature-row"><strong>Potential shortage</strong><span className="feature-share">{number.format(scenario.shortage_units)}</span><span>units</span></div>
                    <div className="feature-row"><strong>Safety-stock gap</strong><span className="feature-share">{number.format(scenario.safety_stock_gap)}</span><span>units</span></div>
                    <div className="feature-row"><strong>First safety breach</strong><span className="feature-share">{scenario.safety_breach_day ? `D+${scenario.safety_breach_day}` : 'None'}</span><span>signal</span></div>
                  </div>
                )}
                <div className="decision-trust">
                  <ShieldCheck size={14} />
                  <span>Forecast = ML evidence. Risk = deterministic business logic. Inventory = scenario input. Final action = human responsibility.</span>
                </div>
              </div>
            </section>
          </div>

          <section className="decision-card decision-actions-card">
            <div className="decision-section-head">
              <div><h2>What would need to change?</h2><p>Deterministic counterfactuals that remove inventory risk</p></div>
              {scenario && <span className={`risk-pill ${scenario.upper_demand_stress.risk_level}`}>stress {scenario.upper_demand_stress.risk_level}</span>}
            </div>
            {scenario && (
              <div className="stress-strip">
                <div><span>Base forecast</span><strong>{number.format(scenario.uncertainty.total_prediction)} units</strong></div>
                <div><span>Upper demand stress</span><strong>{number.format(scenario.uncertainty.total_upper)} units</strong></div>
                <div><span>Stress end inventory</span><strong>{number.format(scenario.upper_demand_stress.projected_end_inventory)}</strong></div>
              </div>
            )}
            <div className="counter-grid" style={{ marginTop: 10 }}>
              {counterfactuals.length ? counterfactuals.map((option) => (
                <div className="counter-option" key={option.kind}>
                  <strong>{option.label}</strong>
                  <span>{Object.entries(option.change).map(([key, value]) => `${key.replaceAll('_', ' ')}: ${number.format(value)}`).join(' · ')}</span>
                  <span>Result: {option.result.risk_level.toUpperCase()} · end inventory {number.format(option.result.projected_end_inventory)}</span>
                </div>
              )) : <div className="counter-option"><strong>No change required</strong><span>The baseline scenario is already low risk or no feasible counterfactual was found.</span></div>}
            </div>
            {scenario && <div className="decision-trust" style={{ marginTop: 10 }}><ShieldCheck size={14} /><span>{scenario.uncertainty.notice}</span></div>}
          </section>

          <section className="decision-card decision-actions-card">
            <div className="decision-section-head">
              <div><h2>Cost-aware scenario optimization</h2><p>Advisory quantity under the economic assumptions entered on the left</p></div>
            </div>
            {scenario?.reorder_optimization ? (
              <>
                <div className="stress-strip">
                  <div><span>Suggested extra units</span><strong>{number.format(scenario.reorder_optimization.recommended_additional_units)}</strong></div>
                  <div><span>Scenario cost</span><strong>{number.format(scenario.reorder_optimization.best_candidate.total_scenario_cost)}</strong></div>
                  <div><span>Resulting risk</span><strong>{scenario.reorder_optimization.best_candidate.risk_level.toUpperCase()}</strong></div>
                </div>
                <div className="decision-trust" style={{ marginTop: 10 }}><ShieldCheck size={14} /><span>{scenario.reorder_optimization.notice}</span></div>
              </>
            ) : <div className="decision-placeholder"><div><Gauge size={28} /><strong>Run the scenario</strong><span>Optimization uses only the editable economic assumptions supplied in this lab.</span></div></div>}
          </section>
        </main>
      </div>
    </div>
  );
}
