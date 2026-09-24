import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  CheckCircle2,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  TrendingUp,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { api } from './api';
import type { MorningBrief, Split } from './types';

const number = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 });

const STYLES = `
.morning-page{display:grid;gap:18px;color:#eaf2f8}.morning-hero{display:flex;justify-content:space-between;gap:18px;align-items:flex-start;padding:24px;border:1px solid rgba(82,225,195,.15);border-radius:20px;background:linear-gradient(145deg,#0d1c2c,#08131f)}.morning-hero h1{margin:8px 0 6px;font-size:28px}.morning-hero p{margin:0;max-width:760px;color:#8299ad;font-size:11px;line-height:1.65}.morning-kicker{color:#58e1c3;font-size:10px;font-weight:900;letter-spacing:.13em;text-transform:uppercase}.morning-actions{display:flex;gap:8px}.morning-actions button{height:35px;padding:0 11px;border:1px solid #20364b;border-radius:10px;background:#0b1a29;color:#bdd0dd;font:inherit;font-size:9px;font-weight:800;cursor:pointer}.morning-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.morning-kpi,.morning-card{border:1px solid #1b3044;border-radius:16px;background:#0b1928}.morning-kpi{padding:15px}.morning-kpi span{display:block;color:#72899d;font-size:9px}.morning-kpi strong{display:block;margin-top:8px;font-size:21px}.morning-kpi small{display:block;margin-top:4px;color:#5f788d;font-size:8px}.morning-columns{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(300px,.65fr);gap:14px}.morning-card{padding:17px}.morning-card h2{margin:0;font-size:14px}.morning-card>p{margin:4px 0 14px;color:#6f879b;font-size:9px}.priority-list{display:grid;gap:8px}.priority-row{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:10px;align-items:center;padding:10px;border:1px solid #182d40;border-radius:11px;background:#091725}.priority-icon{display:grid;width:32px;height:32px;place-items:center;border-radius:9px;background:rgba(248,113,113,.08);color:#f19797}.priority-row strong{display:block;font-size:10px}.priority-row span{display:block;margin-top:2px;color:#70899d;font-size:8px}.severity{padding:4px 7px;border-radius:999px;font-size:8px;font-weight:900;text-transform:uppercase}.severity.watch{background:rgba(246,190,90,.08);color:#f0bf67}.severity.high,.severity.critical{background:rgba(248,113,113,.09);color:#f28f8f}.drift-box{display:grid;gap:10px}.drift-status{display:flex;align-items:center;justify-content:space-between;padding:11px;border:1px solid #1b3346;border-radius:11px;background:#081522}.drift-status strong{font-size:18px}.drift-status span{font-size:9px;color:#7590a5}.limitation{display:flex;gap:8px;margin-top:10px;padding:10px;border:1px solid rgba(246,190,90,.14);border-radius:10px;background:rgba(246,190,90,.04);color:#a89674;font-size:8px;line-height:1.5}.empty{padding:26px;text-align:center;color:#70889b;font-size:10px}.spin{animation:morning-spin .8s linear infinite}@keyframes morning-spin{to{transform:rotate(360deg)}}@media(max-width:1050px){.morning-grid{grid-template-columns:repeat(2,1fr)}.morning-columns{grid-template-columns:1fr}}@media(max-width:620px){.morning-hero{display:grid}.morning-grid{grid-template-columns:1fr}}
`;

export default function MorningBriefPage() {
  const [split, setSplit] = useState<Split>('test');
  const [brief, setBrief] = useState<MorningBrief | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setBrief(await api.morningBrief(split));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Morning brief failed.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [split]);

  const drift = brief?.demand_drift;

  return (
    <div className="morning-page">
      <style>{STYLES}</style>
      <section className="morning-hero">
        <div>
          <div className="morning-kicker"><Sparkles size={12} /> Operator decision brief</div>
          <h1>What deserves attention first?</h1>
          <p>
            A data-grounded morning view of unusual demand, model context and distribution
            shift. Inventory risk is added only when explicit operational scenario inputs exist.
          </p>
        </div>
        <div className="morning-actions">
          <button onClick={() => setSplit(split === 'test' ? 'validation' : 'test')}>
            {split === 'test' ? 'Test split' : 'Validation split'}
          </button>
          <button disabled={loading} onClick={() => void load()}>
            <RefreshCw size={12} className={loading ? 'spin' : ''} /> Refresh
          </button>
        </div>
      </section>

      {error && <div className="limitation"><AlertTriangle size={14} />{error}</div>}

      <div className="morning-grid">
        <div className="morning-kpi"><span>Demand exceptions</span><strong>{brief?.priorities.length ?? '—'}</strong><small>|z| ≥ 3 vs trailing 28 days</small></div>
        <div className="morning-kpi"><span>Demand drift</span><strong>{drift?.status.toUpperCase() ?? '—'}</strong><small>PSI {drift ? number.format(drift.psi) : '—'}</small></div>
        <div className="morning-kpi"><span>Reference mean</span><strong>{drift ? number.format(drift.reference_mean) : '—'}</strong><small>validation daily units</small></div>
        <div className="morning-kpi"><span>Current mean</span><strong>{drift ? number.format(drift.current_mean) : '—'}</strong><small>test daily units</small></div>
      </div>

      <div className="morning-columns">
        <section className="morning-card">
          <h2>Priority exceptions</h2>
          <p>Observed sales deviations ranked by robust operational attention signal.</p>
          <div className="priority-list">
            {brief?.priorities.length ? brief.priorities.map((priority, index) => (
              <div className="priority-row" key={`${priority.item_id}-${priority.store_id}-${priority.date}-${index}`}>
                <div className="priority-icon"><TrendingUp size={16} /></div>
                <div>
                  <strong>{priority.item_id} · {priority.store_id}</strong>
                  <span>{priority.type.replaceAll('_', ' ')} · {number.format(priority.units_sold)} units · z={number.format(priority.anomaly_z)}</span>
                </div>
                <span className={`severity ${priority.severity}`}>{priority.severity}</span>
              </div>
            )) : <div className="empty"><CheckCircle2 size={22} /><p>No |z| ≥ 3 demand exception in this split.</p></div>}
          </div>
        </section>

        <section className="morning-card">
          <h2>Monitoring context</h2>
          <p>Short-window diagnostic, not an automatic retraining trigger.</p>
          <div className="drift-box">
            <div className="drift-status"><span>Population Stability Index</span><strong>{drift ? number.format(drift.psi) : '—'}</strong></div>
            <div className="drift-status"><span>Mean shift (σ)</span><strong>{drift ? number.format(drift.mean_shift_std) : '—'}</strong></div>
            <div className="drift-status"><span>Observations</span><strong>{drift ? `${drift.reference_observations}/${drift.current_observations}` : '—'}</strong></div>
          </div>
          <div className="limitation"><Activity size={14} />{drift?.notice ?? 'Loading drift diagnostic…'}</div>
          {brief?.limitations.map((limitation) => (
            <div className="limitation" key={limitation}><ShieldCheck size={14} />{limitation}</div>
          ))}
        </section>
      </div>
    </div>
  );
}
