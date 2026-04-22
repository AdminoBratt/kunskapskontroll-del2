import { NavLink } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { getStats, getInfo } from '../api/info';
import styles from './Layout.module.css';

const NAV = [
  { to: '/',     label: 'Documents', icon: <LibraryIcon /> },
  { to: '/info', label: 'System',    icon: <InfoIcon /> },
];

export default function Layout({ children }) {
  const [stats, setStats] = useState(null);
  const [apiOk, setApiOk] = useState(null);

  useEffect(() => {
    getStats()
      .then((s) => { setStats(s); setApiOk(true); })
      .catch(() => setApiOk(false));
  }, []);

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.logo}>
          <div className={styles.logoTitle}>PDF RAG</div>
          <div className={styles.logoSub}>Document Intelligence</div>
        </div>

        <nav className={styles.nav}>
          {NAV.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `${styles.navLink}${isActive ? ' ' + styles.active : ''}`
              }
            >
              <span className={styles.navIcon}>{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>

        <div className={styles.sidebarStats}>
          <div className={styles.statRow}>
            <span className={styles.statLabel}>
              <span className={`${styles.statusDot} ${apiOk ? styles.ok : apiOk === false ? styles.error : ''}`} />
              API
            </span>
            <span className={styles.statValue}>
              {apiOk === null ? '—' : apiOk ? 'online' : 'offline'}
            </span>
          </div>
          {stats && (
            <>
              <div className={styles.statRow}>
                <span className={styles.statLabel}>Documents</span>
                <span className={styles.statValue}>{stats.documents ?? 0}</span>
              </div>
              <div className={styles.statRow}>
                <span className={styles.statLabel}>Chunks</span>
                <span className={styles.statValue}>{stats.chunks ?? 0}</span>
              </div>
            </>
          )}
        </div>
      </aside>

      <main className={styles.main}>
        <div className={styles.content}>{children}</div>
      </main>
    </div>
  );
}

function LibraryIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="2" width="4" height="12" rx="1"/>
      <rect x="8" y="2" width="4" height="12" rx="1"/>
      <rect x="14" y="5" width="4" height="9" rx="1" transform="rotate(15 14 5)"/>
    </svg>
  );
}

function InfoIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="8" r="6"/>
      <path d="M8 7.5v4M8 5.5v.5"/>
    </svg>
  );
}
