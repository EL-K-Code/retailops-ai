import { Boxes, ChevronRight, FlaskConical, Layers3, Sunrise, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import App from './App';
import ArchitecturePage from './ArchitecturePage';
import DecisionLabPage from './DecisionLabPage';
import MorningBriefPage from './MorningBriefPage';
import ScenarioPortfolioPage from './ScenarioPortfolioPage';

type PlatformView = 'brief' | 'scenarios' | 'architecture' | 'decision' | null;

const ROOT_STYLES = `
.platform-extension-host{display:contents}.platform-extension{margin-top:0}.platform-mode .nav-group:not(.platform-extension) .nav-item.active{border-color:transparent;background:transparent;color:var(--text-muted)}.platform-mode .nav-group:not(.platform-extension) .nav-item.active .nav-chevron{display:none}.platform-overlay{position:fixed;z-index:29;top:66px;right:0;bottom:0;left:258px;overflow:auto;background:#07111f}.platform-overlay-inner{max-width:1540px;margin:0 auto;padding:28px 30px 56px}.platform-overlay-toolbar{position:sticky;z-index:4;top:0;display:flex;align-items:center;justify-content:space-between;margin:-28px -30px 24px;padding:15px 30px;border-bottom:1px solid rgba(30,49,71,.72);background:rgba(7,17,31,.92);backdrop-filter:blur(18px)}.platform-overlay-title{display:flex;align-items:center;gap:10px}.platform-overlay-title-icon{display:grid;width:34px;height:34px;place-items:center;border:1px solid rgba(82,225,195,.18);border-radius:10px;background:rgba(82,225,195,.08);color:#58e1c3}.platform-overlay-title strong{display:block;color:#eaf2f8;font-size:12px}.platform-overlay-title span{display:block;margin-top:2px;color:#6f879c;font-size:9px}.platform-close{display:flex;align-items:center;gap:7px;height:34px;padding:0 11px;border:1px solid #203449;border-radius:10px;background:#0c1b2a;color:#9fb2c3;font:inherit;font-size:10px;font-weight:700;cursor:pointer}.platform-close:hover{border-color:#31516b;color:#e8f0f7}@media(max-width:1180px){.platform-overlay{left:228px}.platform-overlay-inner{padding-left:22px;padding-right:22px}.platform-overlay-toolbar{margin-left:-22px;margin-right:-22px;padding-left:22px;padding-right:22px}}@media(max-width:820px){.platform-overlay{left:0}.platform-overlay-inner{padding:18px 15px 40px}.platform-overlay-toolbar{margin:-18px -15px 18px;padding:13px 15px}.platform-overlay-title span{display:none}}
`;

export default function ConsoleRoot() {
  const [platformView, setPlatformView] = useState<PlatformView>(null);
  const [navigationMount, setNavigationMount] = useState<HTMLElement | null>(null);

  useEffect(() => {
    const navigation = document.querySelector<HTMLElement>('.nav-stack');
    if (!navigation) return;

    const mount = document.createElement('div');
    mount.className = 'platform-extension-host';
    const adminGroup = navigation.querySelector('.nav-group:last-child');
    navigation.insertBefore(mount, adminGroup ?? null);
    setNavigationMount(mount);

    const closePlatformWhenNavigating = (event: Event) => {
      const target = event.target as HTMLElement | null;
      const navItem = target?.closest('.nav-item');
      if (navItem && !target?.closest('.platform-extension')) {
        setPlatformView(null);
      }
    };
    navigation.addEventListener('click', closePlatformWhenNavigating);

    return () => {
      navigation.removeEventListener('click', closePlatformWhenNavigating);
      mount.remove();
      setNavigationMount(null);
    };
  }, []);

  useEffect(() => {
    const shell = document.querySelector<HTMLElement>('.app-shell');
    shell?.classList.toggle('platform-mode', Boolean(platformView));
    return () => shell?.classList.remove('platform-mode');
  }, [platformView]);

  const overlay = platformView === 'brief'
    ? {
        title: 'Morning Decision Brief',
        subtitle: 'Demand exceptions · drift · operator priorities',
        icon: <Sunrise size={17} />,
        content: <MorningBriefPage />,
      }
    : platformView === 'scenarios'
    ? {
        title: 'Scenario Workspace',
        subtitle: 'Saved scenarios · portfolio scan · decision history',
        icon: <Boxes size={17} />,
        content: <ScenarioPortfolioPage />,
      }
    : platformView === 'architecture'
    ? {
        title: 'Platform Architecture',
        subtitle: 'RetailOps AI · production-style reference architecture',
        icon: <Layers3 size={17} />,
        content: <ArchitecturePage />,
      }
    : platformView === 'decision'
      ? {
          title: 'Decision Lab',
          subtitle: 'Inventory scenarios · TreeSHAP · human-governed decision support',
          icon: <FlaskConical size={17} />,
          content: <DecisionLabPage />,
        }
      : null;

  return (
    <>
      <App />
      <style>{ROOT_STYLES}</style>

      {navigationMount && createPortal(
        <div className="nav-group platform-extension">
          <div className="nav-group-label">Platform</div>
          <button
            className={`nav-item${platformView === 'brief' ? ' active' : ''}`}
            onClick={() => setPlatformView('brief')}
          >
            <Sunrise size={18} strokeWidth={1.8} />
            <span>Morning Brief</span>
            {platformView === 'brief' && <ChevronRight className="nav-chevron" size={15} />}
          </button>
          <button
            className={`nav-item${platformView === 'scenarios' ? ' active' : ''}`}
            onClick={() => setPlatformView('scenarios')}
          >
            <Boxes size={18} strokeWidth={1.8} />
            <span>Scenarios</span>
            {platformView === 'scenarios' && <ChevronRight className="nav-chevron" size={15} />}
          </button>
          <button
            className={`nav-item${platformView === 'decision' ? ' active' : ''}`}
            onClick={() => setPlatformView('decision')}
          >
            <FlaskConical size={18} strokeWidth={1.8} />
            <span>Decision Lab</span>
            {platformView === 'decision' && <ChevronRight className="nav-chevron" size={15} />}
          </button>
          <button
            className={`nav-item${platformView === 'architecture' ? ' active' : ''}`}
            onClick={() => setPlatformView('architecture')}
          >
            <Layers3 size={18} strokeWidth={1.8} />
            <span>Architecture</span>
            {platformView === 'architecture' && <ChevronRight className="nav-chevron" size={15} />}
          </button>
        </div>,
        navigationMount,
      )}

      {overlay && (
        <div className="platform-overlay">
          <div className="platform-overlay-inner">
            <div className="platform-overlay-toolbar">
              <div className="platform-overlay-title">
                <div className="platform-overlay-title-icon">{overlay.icon}</div>
                <div><strong>{overlay.title}</strong><span>{overlay.subtitle}</span></div>
              </div>
              <button className="platform-close" onClick={() => setPlatformView(null)}>
                <X size={14} /> Back to workspace
              </button>
            </div>
            {overlay.content}
          </div>
        </div>
      )}
    </>
  );
}
