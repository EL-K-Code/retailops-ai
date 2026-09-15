import { ChevronRight, Layers3, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import App from './App';
import ArchitecturePage from './ArchitecturePage';

const ROOT_STYLES = `
.architecture-extension-host{display:contents}.architecture-extension{margin-top:0}.architecture-mode .nav-group:not(.architecture-extension) .nav-item.active{border-color:transparent;background:transparent;color:var(--text-muted)}.architecture-mode .nav-group:not(.architecture-extension) .nav-item.active .nav-chevron{display:none}.architecture-overlay{position:fixed;z-index:29;top:66px;right:0;bottom:0;left:258px;overflow:auto;background:#07111f}.architecture-overlay-inner{max-width:1540px;margin:0 auto;padding:28px 30px 56px}.architecture-overlay-toolbar{position:sticky;z-index:4;top:0;display:flex;align-items:center;justify-content:space-between;margin:-28px -30px 24px;padding:15px 30px;border-bottom:1px solid rgba(30,49,71,.72);background:rgba(7,17,31,.92);backdrop-filter:blur(18px)}.architecture-overlay-title{display:flex;align-items:center;gap:10px}.architecture-overlay-title-icon{display:grid;width:34px;height:34px;place-items:center;border:1px solid rgba(82,225,195,.18);border-radius:10px;background:rgba(82,225,195,.08);color:#58e1c3}.architecture-overlay-title strong{display:block;color:#eaf2f8;font-size:12px}.architecture-overlay-title span{display:block;margin-top:2px;color:#6f879c;font-size:9px}.architecture-close{display:flex;align-items:center;gap:7px;height:34px;padding:0 11px;border:1px solid #203449;border-radius:10px;background:#0c1b2a;color:#9fb2c3;font:inherit;font-size:10px;font-weight:700;cursor:pointer}.architecture-close:hover{border-color:#31516b;color:#e8f0f7}@media(max-width:1180px){.architecture-overlay{left:228px}.architecture-overlay-inner{padding-left:22px;padding-right:22px}.architecture-overlay-toolbar{margin-left:-22px;margin-right:-22px;padding-left:22px;padding-right:22px}}@media(max-width:820px){.architecture-overlay{left:0}.architecture-overlay-inner{padding:18px 15px 40px}.architecture-overlay-toolbar{margin:-18px -15px 18px;padding:13px 15px}.architecture-overlay-title span{display:none}}
`;

export default function ConsoleRoot() {
  const [architectureOpen, setArchitectureOpen] = useState(false);
  const [navigationMount, setNavigationMount] = useState<HTMLElement | null>(null);

  useEffect(() => {
    const navigation = document.querySelector<HTMLElement>('.nav-stack');
    if (!navigation) return;

    const mount = document.createElement('div');
    mount.className = 'architecture-extension-host';
    const adminGroup = navigation.querySelector('.nav-group:last-child');
    navigation.insertBefore(mount, adminGroup ?? null);
    setNavigationMount(mount);

    const closeArchitectureWhenNavigating = (event: Event) => {
      const target = event.target as HTMLElement | null;
      const navItem = target?.closest('.nav-item');
      if (navItem && !target?.closest('.architecture-extension')) {
        setArchitectureOpen(false);
      }
    };
    navigation.addEventListener('click', closeArchitectureWhenNavigating);

    return () => {
      navigation.removeEventListener('click', closeArchitectureWhenNavigating);
      mount.remove();
      setNavigationMount(null);
    };
  }, []);

  useEffect(() => {
    const shell = document.querySelector<HTMLElement>('.app-shell');
    shell?.classList.toggle('architecture-mode', architectureOpen);
    return () => shell?.classList.remove('architecture-mode');
  }, [architectureOpen]);

  return (
    <>
      <App />
      <style>{ROOT_STYLES}</style>

      {navigationMount && createPortal(
        <div className="nav-group architecture-extension">
          <div className="nav-group-label">Platform</div>
          <button
            className={`nav-item${architectureOpen ? ' active' : ''}`}
            onClick={() => setArchitectureOpen(true)}
          >
            <Layers3 size={18} strokeWidth={1.8} />
            <span>Architecture</span>
            {architectureOpen && <ChevronRight className="nav-chevron" size={15} />}
          </button>
        </div>,
        navigationMount,
      )}

      {architectureOpen && (
        <div className="architecture-overlay">
          <div className="architecture-overlay-inner">
            <div className="architecture-overlay-toolbar">
              <div className="architecture-overlay-title">
                <div className="architecture-overlay-title-icon"><Layers3 size={17} /></div>
                <div><strong>Platform Architecture</strong><span>RetailOps AI · production-style reference architecture</span></div>
              </div>
              <button className="architecture-close" onClick={() => setArchitectureOpen(false)}>
                <X size={14} /> Back to workspace
              </button>
            </div>
            <ArchitecturePage />
          </div>
        </div>
      )}
    </>
  );
}
