import { useState } from 'react';
import { searchHybrid, searchSemantic, searchKeyword } from '../api/search';
import Button from '../components/Button';
import Alert from '../components/Alert';
import styles from './SearchPage.module.css';

const MODES = [
  { key: 'hybrid',   label: 'Hybrid' },
  { key: 'semantic', label: 'Semantic' },
  { key: 'keyword',  label: 'Keyword' },
];

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('hybrid');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [rerank, setRerank] = useState(true);
  const [semWeight, setSemWeight] = useState(0.7);
  const [kwWeight, setKwWeight] = useState(0.3);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [openItems, setOpenItems] = useState({});

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setResults(null);
    setError(null);
    setOpenItems({});
    try {
      const opts = {};
      if (mode === 'hybrid') {
        opts.rerank = rerank;
        opts.semantic_weight = semWeight;
        opts.keyword_weight = kwWeight;
      }
      const fn = mode === 'semantic' ? searchSemantic
                : mode === 'keyword'  ? searchKeyword
                : searchHybrid;
      const data = await fn(query.trim(), opts);
      setResults(data.results ?? data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggle = (i) => setOpenItems((p) => ({ ...p, [i]: !p[i] }));

  return (
    <div className={styles.page}>
      <h1 className={styles.heading}>Search</h1>
      <p className={styles.sub}>Find chunks from your documents using semantic, keyword, or hybrid search.</p>

      <form onSubmit={handleSubmit}>
        <div className={styles.searchBar}>
          <input
            className={styles.input}
            type="text"
            placeholder="Search documents..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />
          <Button type="submit" loading={loading} disabled={!query.trim()}>
            Search
          </Button>
        </div>

        <div className={styles.modeTabs}>
          {MODES.map((m) => (
            <button
              key={m.key}
              type="button"
              className={`${styles.modeTab}${mode === m.key ? ' ' + styles.active : ''}`}
              onClick={() => setMode(m.key)}
            >
              {m.label}
            </button>
          ))}
        </div>

        <button
          type="button"
          className={styles.advancedToggle}
          onClick={() => setShowAdvanced((p) => !p)}
        >
          {showAdvanced ? '▾' : '▸'} Advanced options
        </button>

        {showAdvanced && (
          <div className={styles.advancedPanel}>
            <div className={styles.advRow}>
              <span className={styles.advLabel}>Rerank results</span>
              <label className={styles.toggle}>
                <input
                  type="checkbox"
                  checked={rerank}
                  onChange={(e) => setRerank(e.target.checked)}
                />
                <span className={styles.toggleTrack} />
                <span className={styles.toggleThumb} />
              </label>
            </div>
            {mode === 'hybrid' && (
              <>
                <div className={styles.advRow}>
                  <span className={styles.advLabel}>Semantic weight</span>
                  <input
                    type="range"
                    className={styles.slider}
                    min={0} max={1} step={0.05}
                    value={semWeight}
                    onChange={(e) => setSemWeight(parseFloat(e.target.value))}
                  />
                  <span className={styles.advValue}>{semWeight.toFixed(2)}</span>
                </div>
                <div className={styles.advRow}>
                  <span className={styles.advLabel}>Keyword weight</span>
                  <input
                    type="range"
                    className={styles.slider}
                    min={0} max={1} step={0.05}
                    value={kwWeight}
                    onChange={(e) => setKwWeight(parseFloat(e.target.value))}
                  />
                  <span className={styles.advValue}>{kwWeight.toFixed(2)}</span>
                </div>
              </>
            )}
          </div>
        )}
      </form>

      {error && <Alert type="error">{error}</Alert>}

      {results && (
        <>
          <div className={styles.resultCount}>
            {results.length} result{results.length !== 1 ? 's' : ''}
          </div>
          {results.length === 0 && (
            <Alert type="info">No results found for this query.</Alert>
          )}
          {results.map((r, i) => (
            <div key={i} className={styles.resultItem}>
              <div className={styles.resultHeader} onClick={() => toggle(i)}>
                <span className={styles.resultTitle}>
                  {r.document_title || r.metadata?.document_title || 'Unknown'}
                </span>
                <span className={styles.resultMeta}>
                  {(r.page_number ?? r.metadata?.page_number) != null && (
                    <span>p.&thinsp;{r.page_number ?? r.metadata?.page_number}</span>
                  )}
                  {r.score != null && (
                    <span className={styles.badge}>
                      {typeof r.score === 'number' && r.score <= 1
                        ? (r.score * 100).toFixed(0) + '%'
                        : r.score.toFixed(3)}
                    </span>
                  )}
                </span>
                <ChevronIcon className={`${styles.chevron}${openItems[i] ? ' ' + styles.open : ''}`} />
              </div>
              {openItems[i] && (
                <div className={styles.resultBody}>
                  {r.chunk_text ?? r.page_content ?? ''}
                </div>
              )}
            </div>
          ))}
        </>
      )}
    </div>
  );
}

function ChevronIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 5l4 4 4-4"/>
    </svg>
  );
}
