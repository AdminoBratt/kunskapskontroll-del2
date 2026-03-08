import { useState } from 'react';
import { askQuestion } from '../api/ask';
import Button from '../components/Button';
import Alert from '../components/Alert';
import styles from './AskPage.module.css';

export default function AskPage() {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [openSources, setOpenSources] = useState({});

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setResult(null);
    setError(null);
    setOpenSources({});
    try {
      const data = await askQuestion(question.trim());
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleSource = (i) =>
    setOpenSources((prev) => ({ ...prev, [i]: !prev[i] }));

  return (
    <div className={styles.page}>
      <h1 className={styles.heading}>Ask a Question</h1>
      <p className={styles.sub}>Query your documents using retrieval-augmented generation.</p>

      <form className={styles.form} onSubmit={handleSubmit}>
        <input
          className={styles.input}
          type="text"
          placeholder="What would you like to know?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          autoFocus
        />
        <Button type="submit" loading={loading} disabled={!question.trim()}>
          Ask
        </Button>
      </form>

      {error && <Alert type="error">{error}</Alert>}

      {result && (
        <>
          <div className={styles.answerSection}>
            <div className={styles.sectionLabel}>Answer</div>
            <div className={styles.answerBox}>
              {result.answer || 'No answer returned.'}
            </div>
          </div>

          {result.sources && result.sources.length > 0 && (
            <div className={styles.sources}>
              <div className={styles.sectionLabel}>
                Sources &mdash; {result.sources.length} chunk{result.sources.length !== 1 ? 's' : ''}
              </div>
              {result.sources.map((src, i) => (
                <div key={i} className={styles.sourceItem}>
                  <div className={styles.sourceHeader} onClick={() => toggleSource(i)}>
                    <span className={styles.sourceTitle}>
                      {src.document_title || 'Unknown document'}
                    </span>
                    <span className={styles.sourceMeta}>
                      {src.page_number != null && <span>p.&thinsp;{src.page_number}</span>}
                      {src.score != null && (
                        <span className={styles.badge}>
                          {(src.score * 100).toFixed(0)}%
                        </span>
                      )}
                    </span>
                    <ChevronIcon className={`${styles.sourceChevron}${openSources[i] ? ' ' + styles.open : ''}`} />
                  </div>
                  {openSources[i] && (
                    <div className={styles.sourceBody}>{src.chunk_text}</div>
                  )}
                </div>
              ))}
            </div>
          )}
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
