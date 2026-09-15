import {
  ArrowRight,
  Bot,
  Box,
  BrainCircuit,
  CheckCircle2,
  Cloud,
  Database,
  FileText,
  Gauge,
  GitBranch,
  Layers3,
  Lock,
  Monitor,
  Server,
  ShieldCheck,
  Sparkles,
  Users,
  Workflow,
  type LucideIcon,
} from 'lucide-react';

type Capability = {
  title: string;
  description: string;
  icon: LucideIcon;
  eyebrow: string;
};

type FlowStep = {
  number: string;
  title: string;
  description: string;
  technology: string;
  icon: LucideIcon;
  tone: 'data' | 'ml' | 'serve' | 'agent' | 'human';
};

type StackItem = {
  name: string;
  role: string;
  group: string;
  short: string;
  icon: LucideIcon;
};

const CAPABILITIES: Capability[] = [
  {
    eyebrow: 'Predict',
    title: 'Demand forecasting',
    description: 'A global LightGBM model produces a validated 28-day recursive demand forecast from real RetailOps features.',
    icon: BrainCircuit,
  },
  {
    eyebrow: 'Understand',
    title: 'Retail analytics',
    description: 'Read-only BigQuery marts expose product, store and sales signals through allowlisted analytics operations.',
    icon: Database,
  },
  {
    eyebrow: 'Reason',
    title: 'Grounded AI agent',
    description: 'Gemini + LangGraph orchestrate forecast, analytics, model-information and curated knowledge tools.',
    icon: Bot,
  },
  {
    eyebrow: 'Govern',
    title: 'Human-in-the-loop',
    description: 'Business-sensitive recommendations are interrupted for explicit operator approval instead of being executed automatically.',
    icon: Users,
  },
  {
    eyebrow: 'Persist',
    title: 'Durable workflow state',
    description: 'LangGraph checkpoints are backed by Cloud SQL PostgreSQL so workflow state is no longer tied to one Cloud Run process.',
    icon: Database,
  },
  {
    eyebrow: 'Operate',
    title: 'Decision console',
    description: 'The React workspace unifies live forecasts, analytics, model health, Copilot, approvals and production status.',
    icon: Monitor,
  },
];

const FLOW: FlowStep[] = [
  {
    number: '01',
    title: 'Curated retail data',
    description: 'Gold and ML marts provide the trusted analytical and model-serving foundation.',
    technology: 'BigQuery',
    icon: Database,
    tone: 'data',
  },
  {
    number: '02',
    title: 'Train & evaluate',
    description: 'A containerized Cloud Run Job trains the global LightGBM model and compares quality against the naive baseline.',
    technology: 'Cloud Run Jobs + LightGBM',
    icon: Workflow,
    tone: 'ml',
  },
  {
    number: '03',
    title: 'Store & promote',
    description: 'Model artifacts land in Cloud Storage and quality-gated versions are registered for model governance.',
    technology: 'GCS + Vertex Model Registry',
    icon: Box,
    tone: 'ml',
  },
  {
    number: '04',
    title: 'Serve forecasts',
    description: 'A private FastAPI service loads the production model and exposes real 28-day forecasts.',
    technology: 'Cloud Run + FastAPI',
    icon: Server,
    tone: 'serve',
  },
  {
    number: '05',
    title: 'Orchestrate intelligence',
    description: 'The agent combines Gemini reasoning with forecast, BigQuery, model metadata and curated RAG tools.',
    technology: 'Gemini + LangGraph',
    icon: Sparkles,
    tone: 'agent',
  },
  {
    number: '06',
    title: 'Gate business decisions',
    description: 'Proposals such as replenishment review are interrupted and sent to the operator for approval.',
    technology: 'Human-in-the-loop',
    icon: ShieldCheck,
    tone: 'human',
  },
  {
    number: '07',
    title: 'Persist agent state',
    description: 'Checkpoint state is stored in PostgreSQL with credentials injected securely at runtime.',
    technology: 'Cloud SQL + Secret Manager',
    icon: Lock,
    tone: 'human',
  },
  {
    number: '08',
    title: 'Operate from one console',
    description: 'A premium React workspace surfaces the complete decision flow to a retail operator.',
    technology: 'React + Cloud Run',
    icon: Monitor,
    tone: 'serve',
  },
];

const STACK: StackItem[] = [
  { name: 'React', role: 'Operator console', group: 'Experience', short: 'RE', icon: Monitor },
  { name: 'FastAPI', role: 'Forecast & agent APIs', group: 'Application', short: 'FA', icon: Server },
  { name: 'LightGBM', role: 'Global demand model', group: 'Machine learning', short: 'LG', icon: BrainCircuit },
  { name: 'LangGraph', role: 'Agent orchestration & HITL', group: 'Agentic AI', short: 'LG', icon: Workflow },
  { name: 'Gemini', role: 'LLM reasoning', group: 'Generative AI', short: 'GM', icon: Sparkles },
  { name: 'BigQuery', role: 'Analytics & serving marts', group: 'Data', short: 'BQ', icon: Database },
  { name: 'Cloud Run', role: 'Serverless API & console', group: 'Compute', short: 'CR', icon: Cloud },
  { name: 'Cloud Run Jobs', role: 'Containerized training', group: 'ML platform', short: 'CJ', icon: Workflow },
  { name: 'Cloud Storage', role: 'Model artifacts', group: 'Storage', short: 'CS', icon: Box },
  { name: 'Vertex AI', role: 'Model Registry + Gemini', group: 'AI platform', short: 'VA', icon: Layers3 },
  { name: 'Cloud SQL', role: 'PostgreSQL agent checkpoints', group: 'State', short: 'SQL', icon: Database },
  { name: 'Secret Manager', role: 'Database credential storage', group: 'Security', short: 'SM', icon: Lock },
  { name: 'IAM', role: 'Least-privilege identities', group: 'Security', short: 'IAM', icon: ShieldCheck },
  { name: 'Artifact Registry', role: 'Container images', group: 'DevOps', short: 'AR', icon: Box },
  { name: 'Cloud Build', role: 'Container build pipeline', group: 'DevOps', short: 'CB', icon: GitBranch },
  { name: 'Cloud Logging', role: 'Request observability', group: 'Operations', short: 'CL', icon: FileText },
];

const VALIDATED = [
  'BigQuery-backed analytics and model inputs',
  'Cloud Run Jobs training on 2.74M rows',
  'Quality-gated model promotion',
  'Private FastAPI forecast serving',
  'Gemini + LangGraph tool orchestration',
  'Human approval interrupt and resume',
  'Cross-service request correlation',
  'PostgreSQL checkpoint backend active',
];

const ARCHITECTURE_STYLES = `
.architecture-page{display:flex;flex-direction:column;gap:22px}.architecture-hero{position:relative;overflow:hidden;display:grid;grid-template-columns:minmax(0,1.35fr) minmax(340px,.65fr);gap:22px;padding:30px;border:1px solid rgba(82,225,195,.16);border-radius:24px;background:radial-gradient(circle at 14% 8%,rgba(70,221,191,.14),transparent 30%),radial-gradient(circle at 88% 18%,rgba(91,124,255,.16),transparent 32%),linear-gradient(145deg,#0c1a29 0%,#091421 62%,#07111d 100%);box-shadow:0 22px 70px rgba(0,0,0,.22)}.architecture-hero:after{content:'';position:absolute;right:-75px;bottom:-95px;width:260px;height:260px;border:1px solid rgba(85,226,198,.1);border-radius:50%;box-shadow:0 0 0 36px rgba(85,226,198,.025),0 0 0 76px rgba(85,226,198,.018)}.architecture-kicker{display:inline-flex;align-items:center;gap:8px;color:#58e1c3;font-size:11px;font-weight:800;letter-spacing:.14em;text-transform:uppercase}.architecture-kicker:before{content:'';width:7px;height:7px;border-radius:50%;background:#58e1c3;box-shadow:0 0 0 5px rgba(88,225,195,.1)}.architecture-hero h2{max-width:820px;margin:12px 0 12px;color:#f5f9ff;font-size:34px;line-height:1.08;letter-spacing:-.035em}.architecture-hero-copy>p{max-width:760px;margin:0;color:#8da5bb;font-size:14px;line-height:1.75}.architecture-badges{display:flex;flex-wrap:wrap;gap:8px;margin-top:21px}.architecture-badges span{padding:7px 10px;border:1px solid rgba(108,149,184,.19);border-radius:999px;background:rgba(11,26,42,.58);color:#b8cad9;font-size:11px;font-weight:700}.architecture-summary{position:relative;z-index:1;display:grid;grid-template-columns:1fr 1fr;gap:10px;align-self:stretch}.architecture-summary-card{display:flex;min-height:112px;flex-direction:column;justify-content:space-between;padding:15px;border:1px solid rgba(112,153,187,.14);border-radius:17px;background:rgba(7,18,30,.66);backdrop-filter:blur(8px)}.architecture-summary-card.wide{grid-column:1/-1;min-height:90px}.architecture-summary-card span{color:#6f899f;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em}.architecture-summary-card strong{color:#f2f7fc;font-size:17px;line-height:1.35}.architecture-summary-card small{color:#58e1c3;font-size:11px}.architecture-section{padding:22px;border:1px solid #182a3c;border-radius:21px;background:#0b1827}.architecture-section-head{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;margin-bottom:18px}.architecture-section-head h3{margin:0;color:#f3f7fb;font-size:18px}.architecture-section-head p{max-width:680px;margin:5px 0 0;color:#748da3;font-size:12px;line-height:1.6}.architecture-section-label{color:#58e1c3;font-size:10px;font-weight:800;letter-spacing:.13em;text-transform:uppercase}.architecture-capabilities{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.architecture-capability{padding:17px;border:1px solid #1a3044;border-radius:16px;background:linear-gradient(145deg,rgba(15,31,48,.95),rgba(10,23,37,.95));transition:transform .18s ease,border-color .18s ease}.architecture-capability:hover{transform:translateY(-2px);border-color:rgba(88,225,195,.34)}.architecture-capability-top{display:flex;align-items:center;justify-content:space-between}.architecture-icon{display:grid;width:38px;height:38px;place-items:center;border:1px solid rgba(88,225,195,.2);border-radius:11px;background:rgba(88,225,195,.08);color:#58e1c3}.architecture-capability-top span{color:#607c94;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.11em}.architecture-capability h4{margin:14px 0 7px;color:#eaf2f8;font-size:14px}.architecture-capability p{margin:0;color:#718ba2;font-size:11px;line-height:1.65}.architecture-flow{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.architecture-flow-card{position:relative;min-height:190px;padding:17px;border:1px solid #1b3044;border-radius:17px;background:#0d1d2d}.architecture-flow-card:after{content:'→';position:absolute;right:-12px;top:50%;z-index:3;display:grid;width:24px;height:24px;place-items:center;border:1px solid #1f3a50;border-radius:50%;background:#0b1827;color:#4edfc1;font-size:12px;transform:translateY(-50%)}.architecture-flow-card:nth-child(4):after,.architecture-flow-card:last-child:after{display:none}.architecture-flow-top{display:flex;align-items:center;justify-content:space-between}.architecture-flow-number{color:#49677e;font-size:10px;font-weight:900;letter-spacing:.09em}.architecture-flow-icon{display:grid;width:40px;height:40px;place-items:center;border-radius:12px;color:#dcecff}.architecture-flow-card.data .architecture-flow-icon{background:rgba(58,157,255,.12);color:#70b8ff}.architecture-flow-card.ml .architecture-flow-icon{background:rgba(134,101,255,.12);color:#a38aff}.architecture-flow-card.serve .architecture-flow-icon{background:rgba(72,217,190,.11);color:#57dfc2}.architecture-flow-card.agent .architecture-flow-icon{background:rgba(239,172,75,.1);color:#f1b660}.architecture-flow-card.human .architecture-flow-icon{background:rgba(232,98,142,.1);color:#ea799e}.architecture-flow-card h4{margin:16px 0 7px;color:#eef5fa;font-size:14px}.architecture-flow-card p{margin:0;color:#71899d;font-size:11px;line-height:1.58}.architecture-tech-chip{display:inline-flex;margin-top:13px;padding:6px 8px;border:1px solid #20374a;border-radius:8px;background:#091725;color:#9db2c4;font-size:10px;font-weight:700}.architecture-platform-flow{display:grid;grid-template-columns:auto 1fr auto;gap:14px;align-items:center;margin-bottom:18px;padding:17px;border:1px solid rgba(87,224,194,.15);border-radius:17px;background:linear-gradient(90deg,rgba(69,211,183,.06),rgba(77,120,255,.05))}.architecture-platform-node{display:flex;align-items:center;gap:11px}.architecture-platform-node-icon{display:grid;width:42px;height:42px;place-items:center;border-radius:12px;background:#10283a;color:#58e1c3}.architecture-platform-node strong{display:block;color:#eaf2f8;font-size:12px}.architecture-platform-node span{display:block;margin-top:2px;color:#687f93;font-size:10px}.architecture-platform-line{position:relative;height:1px;background:linear-gradient(90deg,rgba(88,225,195,.15),#4edfc1,rgba(88,225,195,.15))}.architecture-platform-line:before,.architecture-platform-line:after{content:'';position:absolute;top:50%;width:6px;height:6px;border-radius:50%;background:#52dfc2;transform:translateY(-50%)}.architecture-platform-line:before{left:22%}.architecture-platform-line:after{right:22%}.architecture-stack{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.architecture-stack-card{display:flex;align-items:center;gap:11px;padding:13px;border:1px solid #192d40;border-radius:14px;background:#0c1b2a}.architecture-stack-logo{display:grid;flex:0 0 38px;height:38px;place-items:center;border:1px solid rgba(86,222,195,.16);border-radius:11px;background:linear-gradient(145deg,rgba(73,216,187,.1),rgba(78,116,237,.08));color:#56dfc2;font-size:9px;font-weight:900;letter-spacing:-.02em}.architecture-stack-copy{min-width:0}.architecture-stack-copy strong{display:block;overflow:hidden;color:#eaf2f8;font-size:11px;text-overflow:ellipsis;white-space:nowrap}.architecture-stack-copy span{display:block;margin-top:3px;overflow:hidden;color:#668198;font-size:9px;text-overflow:ellipsis;white-space:nowrap}.architecture-stack-group{margin-left:auto;padding:4px 6px;border-radius:7px;background:#102338;color:#6688a4;font-size:8px;font-weight:800;text-transform:uppercase}.architecture-proof-grid{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(300px,.6fr);gap:14px}.architecture-proof-list{display:grid;grid-template-columns:1fr 1fr;gap:9px}.architecture-proof-item{display:flex;gap:9px;align-items:flex-start;padding:11px;border:1px solid #192e40;border-radius:12px;background:#0c1b2a;color:#91a7b9;font-size:10px;line-height:1.45}.architecture-proof-item svg{flex:0 0 auto;color:#53ddbf}.architecture-guardrail{padding:17px;border:1px solid rgba(245,181,87,.18);border-radius:16px;background:linear-gradient(145deg,rgba(41,31,22,.46),rgba(14,25,36,.8))}.architecture-guardrail-head{display:flex;align-items:center;gap:9px;color:#f0bb69;font-size:12px;font-weight:800}.architecture-guardrail p{margin:10px 0 13px;color:#8fa0ad;font-size:10px;line-height:1.65}.architecture-guardrail-status{display:flex;align-items:center;gap:8px;padding:9px;border-radius:10px;background:rgba(8,18,29,.55);color:#b0c0cc;font-size:9px}.architecture-guardrail-status i{width:7px;height:7px;border-radius:50%;background:#f0bb69;box-shadow:0 0 0 4px rgba(240,187,105,.08)}@media(max-width:1250px){.architecture-hero{grid-template-columns:1fr}.architecture-capabilities{grid-template-columns:repeat(2,minmax(0,1fr))}.architecture-flow{grid-template-columns:repeat(2,minmax(0,1fr))}.architecture-flow-card:nth-child(2):after,.architecture-flow-card:nth-child(6):after{display:none}.architecture-flow-card:nth-child(4):after{display:grid}.architecture-stack{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:900px){.architecture-capabilities,.architecture-flow,.architecture-stack,.architecture-proof-grid,.architecture-proof-list{grid-template-columns:1fr}.architecture-flow-card:after{display:none!important}.architecture-platform-flow{grid-template-columns:1fr}.architecture-platform-line{height:26px;width:1px;margin-left:20px;background:linear-gradient(rgba(88,225,195,.15),#4edfc1,rgba(88,225,195,.15))}.architecture-summary{grid-template-columns:1fr}.architecture-hero{padding:20px}.architecture-hero h2{font-size:27px}}
`;

export default function ArchitecturePage() {
  return (
    <div className="architecture-page">
      <style>{ARCHITECTURE_STYLES}</style>

      <section className="architecture-hero">
        <div className="architecture-hero-copy">
          <div className="architecture-kicker">Production-style AI platform</div>
          <h2>From retail data to governed AI-assisted decisions.</h2>
          <p>
            RetailOps AI connects demand forecasting, live analytics, grounded generative AI,
            human approval workflows and persistent agent state in one Google Cloud architecture.
            The LLM orchestrates and explains; trusted services remain the source of numerical truth.
          </p>
          <div className="architecture-badges">
            <span>Demand forecasting</span>
            <span>Agentic AI</span>
            <span>Grounded RAG</span>
            <span>Human-in-the-loop</span>
            <span>Durable state</span>
            <span>Least-privilege IAM</span>
          </div>
        </div>

        <div className="architecture-summary">
          <div className="architecture-summary-card wide">
            <span>Core principle</span>
            <strong>LLM for reasoning. Trusted tools for facts.</strong>
            <small>Forecast API · BigQuery · Model metadata · Curated knowledge</small>
          </div>
          <div className="architecture-summary-card">
            <span>Forecast quality</span>
            <strong>0.771 RMSSE</strong>
            <small>vs. 0.952 naive baseline</small>
          </div>
          <div className="architecture-summary-card">
            <span>Forecast horizon</span>
            <strong>28 days</strong>
            <small>recursive inference</small>
          </div>
        </div>
      </section>

      <section className="architecture-section">
        <div className="architecture-section-head">
          <div>
            <div className="architecture-section-label">Capabilities</div>
            <h3>What the platform actually does</h3>
            <p>Six connected capabilities turn a forecasting model into a usable decision-support system.</p>
          </div>
        </div>
        <div className="architecture-capabilities">
          {CAPABILITIES.map(({ title, description, icon: Icon, eyebrow }) => (
            <article className="architecture-capability" key={title}>
              <div className="architecture-capability-top">
                <div className="architecture-icon"><Icon size={18} /></div>
                <span>{eyebrow}</span>
              </div>
              <h4>{title}</h4>
              <p>{description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="architecture-section">
        <div className="architecture-section-head">
          <div>
            <div className="architecture-section-label">End-to-end flow</div>
            <h3>How a decision moves through RetailOps AI</h3>
            <p>The architecture deliberately separates data, model training, inference, AI orchestration and human governance.</p>
          </div>
        </div>
        <div className="architecture-flow">
          {FLOW.map(({ number, title, description, technology, icon: Icon, tone }) => (
            <article className={`architecture-flow-card ${tone}`} key={number}>
              <div className="architecture-flow-top">
                <span className="architecture-flow-number">STEP {number}</span>
                <div className="architecture-flow-icon"><Icon size={19} /></div>
              </div>
              <h4>{title}</h4>
              <p>{description}</p>
              <span className="architecture-tech-chip">{technology}</span>
            </article>
          ))}
        </div>
      </section>

      <section className="architecture-section">
        <div className="architecture-section-head">
          <div>
            <div className="architecture-section-label">Runtime architecture</div>
            <h3>Private services, secure state and one operator workspace</h3>
            <p>Cloud Run is the application boundary; managed GCP services provide data, AI, storage, security and persistence.</p>
          </div>
        </div>

        <div className="architecture-platform-flow">
          <div className="architecture-platform-node">
            <div className="architecture-platform-node-icon"><Monitor size={19} /></div>
            <div><strong>Retail Operator</strong><span>React decision workspace</span></div>
          </div>
          <div className="architecture-platform-line" />
          <div className="architecture-platform-node">
            <div className="architecture-platform-node-icon"><Cloud size={19} /></div>
            <div><strong>Cloud Run</strong><span>React + FastAPI + Agent runtime</span></div>
          </div>
        </div>

        <div className="architecture-stack">
          {STACK.map(({ name, role, group, short, icon: Icon }) => (
            <div className="architecture-stack-card" key={`${group}-${name}`}>
              <div className="architecture-stack-logo" title={name}><Icon size={16} /></div>
              <div className="architecture-stack-copy"><strong>{name}</strong><span>{role}</span></div>
              <span className="architecture-stack-group">{group}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="architecture-section">
        <div className="architecture-section-head">
          <div>
            <div className="architecture-section-label">Proof, not slides</div>
            <h3>What has already been validated in the cloud</h3>
            <p>These are working pieces of the deployed platform, not target-state architecture boxes.</p>
          </div>
        </div>

        <div className="architecture-proof-grid">
          <div className="architecture-proof-list">
            {VALIDATED.map((item) => (
              <div className="architecture-proof-item" key={item}>
                <CheckCircle2 size={14} />
                <span>{item}</span>
              </div>
            ))}
          </div>
          <aside className="architecture-guardrail">
            <div className="architecture-guardrail-head"><Gauge size={17} /> Production guardrail</div>
            <p>
              PostgreSQL is now the active checkpoint backend. The final cross-revision
              interrupt → restart → resume test is still required before claiming restart-resilient
              HITL as fully validated.
            </p>
            <div className="architecture-guardrail-status"><i /> Backend active · resilience validation pending</div>
          </aside>
        </div>
      </section>
    </div>
  );
}
