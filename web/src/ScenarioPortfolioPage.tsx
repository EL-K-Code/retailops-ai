import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  FileUp,
  History,
  Layers3,
  Play,
  RefreshCw,
  ShieldCheck,
  Trash2,
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { api } from './api';
import type { BatchScenarioResult, DecisionHistoryEvent, SavedScenario, Split } from './types';

const number = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 });

const STYLES = `
.portfolio-page{display:grid;gap:12px;color:#eef3f7}.portfolio-toolbar{display:flex;align-items:center;gap:10px;padding:12px;border:1px solid #232a32;border-radius:11px;background:#111419}.portfolio-toolbar>div:first-child{display:grid;gap:2px;flex:1}.portfolio-toolbar strong{font-size:12px}.portfolio-toolbar span{color:#707c88;font-size:8.5px}.portfolio-button{height:32px;display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:0 10px;border:1px solid #2a3139;border-radius:8px;background:#0e1115;color:#9ba6b1;font:inherit;font-size:8.5px;font-weight:750;cursor:pointer}.portfolio-button.primary{border-color:rgba(103,224,194,.22);background:rgba(103,224,194,.08);color:#dffff6}.portfolio-button.danger{color:#e89aa1}.portfolio-button:disabled{opacity:.45;cursor:not-allowed}.portfolio-grid{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(300px,.75fr);gap:12px}.portfolio-card{border:1px solid #232a32;border-radius:11px;background:#111419;overflow:hidden}.portfolio-card-head{min-height:50px;display:flex;align-items:center;gap:10px;padding:0 13px;border-bottom:1px solid #20262d}.portfolio-card-head>div{display:grid;gap:2px;flex:1}.portfolio-card-head strong{font-size:10.5px}.portfolio-card-head span{color:#66727e;font-size:8px}.scenario-list{display:grid}.scenario-row{display:grid;grid-template-columns:minmax(140px,1.2fr) minmax(120px,.9fr) 72px 80px auto;gap:10px;align-items:center;min-height:62px;padding:8px 12px;border-bottom:1px solid #1e242b}.scenario-row:last-child{border-bottom:0}.scenario-name{display:grid;gap:3px}.scenario-name strong{font-size:9.5px}.scenario-name span,.scenario-meta span{color:#66727e;font-size:7.8px}.scenario-meta{display:grid;gap:3px}.scenario-meta strong{font-size:8.5px}.risk{width:max-content;padding:4px 7px;border-radius:999px;font-size:7.5px;font-weight:900;text-transform:uppercase}.risk.low{color:#77dcb8;background:rgba(78,210,154,.08)}.risk.medium{color:#edbc69;background:rgba(246,184,75,.08)}.risk.high{color:#ee9098;background:rgba(239,111,122,.08)}.risk.none{color:#77838f;background:#171c22}.row-actions{display:flex;gap:5px;justify-content:flex-end}.icon-action{width:30px;height:30px;display:grid;place-items:center;border:1px solid #272e36;border-radius:8px;background:#0e1115;color:#8d99a5;cursor:pointer}.icon-action:hover{color:#eef3f7;border-color:#39434e}.portfolio-empty{padding:30px 16px;text-align:center;color:#67737f;font-size:9px}.portfolio-empty svg{display:block;margin:0 auto 8px}.batch-body{padding:13px}.upload-zone{min-height:112px;display:grid;place-items:center;padding:15px;border:1px dashed #323a44;border-radius:10px;background:#0e1115;text-align:center;cursor:pointer}.upload-zone input{display:none}.upload-zone strong{display:block;margin-top:7px;font-size:9.5px}.upload-zone span{display:block;margin-top:4px;color:#687480;font-size:8px}.batch-ready{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:10px;padding:9px 10px;border:1px solid #222a32;border-radius:9px;background:#0f1216}.batch-ready div{display:grid;gap:2px}.batch-ready strong{font-size:9px}.batch-ready span{font-size:7.8px;color:#65717d}.portfolio-error{display:flex;align-items:center;gap:6px;margin-top:9px;color:#ec999f;font-size:8.5px}.portfolio-table{width:100%;border-collapse:collapse}.portfolio-table th{padding:8px 11px;color:#5f6b77;text-align:left;text-transform:uppercase;letter-spacing:.06em;font-size:7px}.portfolio-table td{padding:10px 11px;border-top:1px solid #1e242b;color:#aeb8c2;font-size:8.5px}.portfolio-table td strong{color:#e6ecf1}.portfolio-history{grid-column:1/-1}.history-dot{width:7px;height:7px;border-radius:50%;background:#5d6873}.history-dot.high{background:#e8757f}.history-dot.medium{background:#e2ac53}.history-dot.low{background:#55c99d}@media(max-width:1000px){.portfolio-grid{grid-template-columns:1fr}.portfolio-history{grid-column:auto}}@media(max-width:700px){.scenario-row{grid-template-columns:1fr auto}.scenario-row>.scenario-meta{display:none}.portfolio-toolbar{align-items:flex-start;flex-wrap:wrap}}
`;

type ParsedScenario = {
  name?: string;
  item_id: string;
  store_id: string;
  split: Split;
  current_stock: number;
  incoming_units: number;
  lead_time_days: number;
  safety_stock: number;
};

function parseCsv(text: string): ParsedScenario[] {
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (lines.length < 2) return [];
  const headers = lines[0].split(',').map((value) => value.trim().toLowerCase());
  const index = Object.fromEntries(headers.map((header, position) => [header, position]));
  for (const required of ['item_id', 'store_id', 'current_stock']) {
    if (index[required] === undefined) throw new Error(`Missing required column: ${required}`);
  }

  return lines.slice(1, 26).map((line, rowIndex) => {
    const values = line.split(',').map((value) => value.trim());
    const numeric = (key: string, fallback = 0) => {
      const raw = values[index[key]];
      if (raw === undefined || raw === '') return fallback;
      const parsed = Number(raw);
      if (!Number.isFinite(parsed) || parsed < 0) throw new Error(`Invalid ${key} on row ${rowIndex + 2}`);
      return parsed;
    };
    const splitValue = values[index.split] || 'test';
    if (splitValue !== 'test' && splitValue !== 'validation') {
      throw new Error(`Invalid split on row ${rowIndex + 2}`);
    }
    return {
      name: values[index.name] || undefined,
      item_id: values[index.item_id],
      store_id: values[index.store_id],
      split: splitValue,
      current_stock: numeric('current_stock'),
      incoming_units: numeric('incoming_units'),
      lead_time_days: numeric('lead_time_days'),
      safety_stock: numeric('safety_stock'),
    };
  });
}

function riskRank(risk: string) {
  return risk === 'high' ? 0 : risk === 'medium' ? 1 : 2;
}

export default function ScenarioPortfolioPage() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [scenarios, setScenarios] = useState<SavedScenario[]>([]);
  const [history, setHistory] = useState<DecisionHistoryEvent[]>([]);
  const [storageBackend, setStorageBackend] = useState('—');
  const [batch, setBatch] = useState<ParsedScenario[]>([]);
  const [batchName, setBatchName] = useState('');
  const [results, setResults] = useState<BatchScenarioResult[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [batchBusy, setBatchBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = async () => {
    setError(null);
    try {
      const [saved, events] = await Promise.all([api.savedScenarios(), api.decisionHistory(30)]);
      setScenarios(saved.scenarios);
      setStorageBackend(saved.storage_backend);
      setHistory(events.events);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Workspace load failed.');
    }
  };

  useEffect(() => { void reload(); }, []);

  const sortedResults = useMemo(
    () => [...results].sort((a, b) => riskRank(a.risk_level) - riskRank(b.risk_level)),
    [results],
  );

  const runSaved = async (scenario: SavedScenario) => {
    setBusy(scenario.id);
    setError(null);
    try {
      await api.runSavedScenario(scenario.id);
      await reload();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Scenario run failed.');
    } finally {
      setBusy(null);
    }
  };

  const remove = async (scenario: SavedScenario) => {
    setBusy(scenario.id);
    try {
      await api.deleteScenario(scenario.id);
      await reload();
    } finally {
      setBusy(null);
    }
  };

  const loadCsv = async (file: File) => {
    setError(null);
    try {
      const parsed = parseCsv(await file.text());
      if (!parsed.length) throw new Error('The CSV has no scenario rows.');
      setBatch(parsed);
      setBatchName(file.name);
      setResults([]);
    } catch (caught) {
      setBatch([]);
      setResults([]);
      setError(caught instanceof Error ? caught.message : 'Could not parse CSV.');
    }
  };

  const evaluateBatch = async () => {
    if (!batch.length) return;
    setBatchBusy(true);
    setError(null);
    try {
      const response = await api.batchScenarios(batch);
      setResults(response.results);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Batch evaluation failed.');
    } finally {
      setBatchBusy(false);
    }
  };

  return (
    <div className="portfolio-page">
      <style>{STYLES}</style>
      <div className="portfolio-toolbar">
        <div><strong>Scenario workspace</strong><span>{scenarios.length} saved · {storageBackend} storage</span></div>
        <button className="portfolio-button" onClick={() => void reload()}><RefreshCw size={13} /> Refresh</button>
      </div>

      {error && <div className="portfolio-error"><AlertTriangle size={14} />{error}</div>}

      <div className="portfolio-grid">
        <section className="portfolio-card">
          <div className="portfolio-card-head">
            <Layers3 size={15} />
            <div><strong>Saved scenarios</strong><span>Reusable planning assumptions</span></div>
          </div>
          <div className="scenario-list">
            {scenarios.length ? scenarios.map((scenario) => (
              <div className="scenario-row" key={scenario.id}>
                <div className="scenario-name"><strong>{scenario.name}</strong><span>{scenario.item_id} · {scenario.store_id}</span></div>
                <div className="scenario-meta"><span>Stock / PO / Lead time</span><strong>{number.format(scenario.current_stock)} / {number.format(scenario.incoming_units)} / {scenario.lead_time_days}d</strong></div>
                <span className={`risk ${scenario.latest_risk ?? 'none'}`}>{scenario.latest_risk ?? 'Not run'}</span>
                <div className="scenario-meta"><span>End inventory</span><strong>{scenario.latest_end_inventory == null ? '—' : number.format(scenario.latest_end_inventory)}</strong></div>
                <div className="row-actions">
                  <button className="icon-action" disabled={busy === scenario.id} title="Run scenario" onClick={() => void runSaved(scenario)}>{busy === scenario.id ? <RefreshCw className="spin" size={13} /> : <Play size={13} />}</button>
                  <button className="icon-action" disabled={busy === scenario.id} title="Delete scenario" onClick={() => void remove(scenario)}><Trash2 size={13} /></button>
                </div>
              </div>
            )) : <div className="portfolio-empty"><ShieldCheck size={22} />Save a scenario from Decision Lab to build your planning library.</div>}
          </div>
        </section>

        <section className="portfolio-card">
          <div className="portfolio-card-head">
            <FileUp size={15} />
            <div><strong>Portfolio scan</strong><span>Evaluate up to 25 inventory scenarios</span></div>
          </div>
          <div className="batch-body">
            <label className="upload-zone">
              <input ref={fileRef} type="file" accept=".csv,text/csv" onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void loadCsv(file);
              }} />
              <FileUp size={22} />
              <strong>Drop or choose a scenario CSV</strong>
              <span>item_id, store_id, current_stock + optional PO, lead time, safety stock</span>
            </label>
            {batch.length > 0 && (
              <div className="batch-ready">
                <div><strong>{batch.length} scenarios ready</strong><span>{batchName}</span></div>
                <button className="portfolio-button primary" disabled={batchBusy} onClick={() => void evaluateBatch()}>
                  {batchBusy ? <RefreshCw className="spin" size={13} /> : <ArrowRight size={13} />}
                  Evaluate
                </button>
              </div>
            )}
          </div>
        </section>

        {sortedResults.length > 0 && (
          <section className="portfolio-card portfolio-history">
            <div className="portfolio-card-head">
              <CheckCircle2 size={15} />
              <div><strong>Portfolio risk queue</strong><span>Highest-risk scenarios first</span></div>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table className="portfolio-table">
                <thead><tr><th>Scenario</th><th>Entity</th><th>Risk</th><th>28d demand</th><th>End inventory</th><th>Stockout</th><th>Review qty</th></tr></thead>
                <tbody>{sortedResults.map((result, index) => (
                  <tr key={`${result.item_id}-${result.store_id}-${index}`}>
                    <td><strong>{result.name}</strong></td>
                    <td>{result.item_id} · {result.store_id}</td>
                    <td><span className={`risk ${result.risk_level}`}>{result.risk_level}</span></td>
                    <td>{number.format(result.forecast_total)}</td>
                    <td>{number.format(result.projected_end_inventory)}</td>
                    <td>{result.stockout_day ? `D+${result.stockout_day}` : '—'}</td>
                    <td>{number.format(result.review_quantity)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </section>
        )}

        <section className="portfolio-card portfolio-history">
          <div className="portfolio-card-head">
            <History size={15} />
            <div><strong>Decision history</strong><span>Recent server-side scenario runs</span></div>
          </div>
          {history.length ? (
            <div style={{ overflowX: 'auto' }}>
              <table className="portfolio-table">
                <thead><tr><th></th><th>Scenario</th><th>Entity</th><th>Risk</th><th>End inventory</th><th>Action</th><th>Time</th></tr></thead>
                <tbody>{history.map((event) => (
                  <tr key={event.id}>
                    <td><span className={`history-dot ${event.risk_level ?? ''}`} /></td>
                    <td><strong>{event.scenario_name ?? 'Scenario run'}</strong></td>
                    <td>{event.item_id} · {event.store_id}</td>
                    <td>{event.risk_level ? <span className={`risk ${event.risk_level}`}>{event.risk_level}</span> : '—'}</td>
                    <td>{event.projected_end_inventory == null ? '—' : number.format(event.projected_end_inventory)}</td>
                    <td>{event.recommended_action?.replaceAll('_', ' ') ?? '—'}</td>
                    <td>{new Date(event.created_at).toLocaleString()}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          ) : <div className="portfolio-empty"><History size={22} />Run a saved scenario to build a durable decision trail.</div>}
        </section>
      </div>
    </div>
  );
}
