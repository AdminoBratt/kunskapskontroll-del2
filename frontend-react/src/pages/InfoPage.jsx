import { useState, useEffect } from 'react';
import { getInfo, getStats } from '../api/info';
import Button from '../components/Button';
import Alert from '../components/Alert';
import styles from './InfoPage.module.css';

export default function InfoPage() {
  const [info, setInfo] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = () => {
    setLoading(true);
    setError(null);
    Promise.all([getInfo(), getStats()])
      .then(([i, s]) => { setInfo(i); setStats(s); })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  return (
    <div className={styles.page}>
      <h1 className={styles.heading}>System Info</h1>
      <p className={styles.sub}>Status of the backend, models, and knowledge base.</p>

      <Button variant="secondary" size="sm" className={styles.refreshBtn} onClick={load} loading={loading}>
        Refresh
      </Button>

      {error && <Alert type="error">{error}</Alert>}

      {loading && !info && <div className={styles.loading}>Loading...</div>}

      {stats && (
        <div className={styles.grid}>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{stats.documents ?? 0}</div>
            <div className={styles.statLabel}>Documents</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{stats.chunks ?? 0}</div>
            <div className={styles.statLabel}>Chunks</div>
          </div>
        </div>
      )}

      {info && (
        <>
          <div className={styles.section}>
            <div className={styles.sectionTitle}>LLM</div>
            <div className={styles.infoCard}>
              <InfoRow label="Model" value={info.llm?.model ?? '—'} />
              <InfoRow
                label="Status"
                value={
                  <span className={`${styles.pill} ${info.llm?.status?.available ? styles.ok : styles.error}`}>
                    <span className={styles.dot} />
                    {info.llm?.status?.available ? 'available' : 'unavailable'}
                  </span>
                }
              />
              {info.llm?.status?.error && (
                <InfoRow label="Error" value={<span className={styles.mono}>{info.llm.status.error}</span>} />
              )}
              {info.llm?.status?.models && (
                <InfoRow
                  label="Models"
                  value={info.llm.status.models.join(', ')}
                />
              )}
            </div>
          </div>

          <div className={styles.section}>
            <div className={styles.sectionTitle}>Embeddings</div>
            <div className={styles.infoCard}>
              <InfoRow label="Model" value={info.embeddings?.model ?? '—'} />
              <InfoRow
                label="Status"
                value={
                  <span className={`${styles.pill} ${info.embeddings?.status === 'ok' ? styles.ok : styles.error}`}>
                    <span className={styles.dot} />
                    {info.embeddings?.status ?? 'unknown'}
                  </span>
                }
              />
            </div>
          </div>

          {info.reranker && (
            <div className={styles.section}>
              <div className={styles.sectionTitle}>Reranker</div>
              <div className={styles.infoCard}>
                <InfoRow label="Model" value={info.reranker.model ?? '—'} />
                <InfoRow
                  label="Status"
                  value={
                    <span className={`${styles.pill} ${info.reranker.status === 'ok' ? styles.ok : styles.error}`}>
                      <span className={styles.dot} />
                      {info.reranker.status ?? 'unknown'}
                    </span>
                  }
                />
              </div>
            </div>
          )}

          {info.database && (
            <div className={styles.section}>
              <div className={styles.sectionTitle}>Database</div>
              <div className={styles.infoCard}>
                {Object.entries(info.database).map(([k, v]) => (
                  <InfoRow key={k} label={k} value={String(v)} />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function InfoRow({ label, value }) {
  return (
    <div className={styles.infoRow}>
      <span className={styles.infoKey}>{label}</span>
      <span className={styles.infoVal}>{value}</span>
    </div>
  );
}
