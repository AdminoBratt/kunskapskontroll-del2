import { useState } from 'react';
import { searchSemantic } from '../api/search';
import Button from '../components/Button';
import Alert from '../components/Alert';
import styles from './SearchPage.module.css';

export default function SearchPage() {
  const [query, setQuery] = useState('');
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
      const data = await searchSemantic(query.trim());
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
      <p className={styles.sub}>Find chunks from your documents using semantic search.</p>

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
