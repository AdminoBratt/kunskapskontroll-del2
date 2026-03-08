import { useState, useEffect } from 'react';
import { getDocuments, getDocumentChunks } from '../api/documents';
import Button from '../components/Button';
import Alert from '../components/Alert';
import styles from './LibraryPage.module.css';

export default function LibraryPage() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [openDoc, setOpenDoc] = useState(null);
  const [chunks, setChunks] = useState({});
  const [chunksLoading, setChunksLoading] = useState({});

  useEffect(() => {
    getDocuments()
      .then(setDocuments)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const toggleDoc = async (doc) => {
    const id = doc.document_id ?? doc.id;
    if (openDoc === id) {
      setOpenDoc(null);
      return;
    }
    setOpenDoc(id);
    if (!chunks[id]) {
      setChunksLoading((p) => ({ ...p, [id]: true }));
      try {
        const data = await getDocumentChunks(id);
        setChunks((p) => ({ ...p, [id]: data }));
      } catch {
        setChunks((p) => ({ ...p, [id]: [] }));
      } finally {
        setChunksLoading((p) => ({ ...p, [id]: false }));
      }
    }
  };

  const refresh = () => {
    setLoading(true);
    setError(null);
    getDocuments()
      .then(setDocuments)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  return (
    <div className={styles.page}>
      <h1 className={styles.heading}>Document Library</h1>
      <p className={styles.sub}>Browse uploaded documents and inspect their extracted chunks.</p>

      <div className={styles.toolbar}>
        <span className={styles.count}>
          {loading ? 'Loading...' : `${documents.length} document${documents.length !== 1 ? 's' : ''}`}
        </span>
        <Button variant="secondary" size="sm" onClick={refresh} loading={loading}>
          Refresh
        </Button>
      </div>

      {error && <Alert type="error">{error}</Alert>}

      {!loading && documents.length === 0 && !error && (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>
            <EmptyIcon />
          </div>
          No documents yet. Upload a PDF to get started.
        </div>
      )}

      <div className={styles.docList}>
        {documents.map((doc) => {
          const id = doc.document_id ?? doc.id;
          const isOpen = openDoc === id;
          return (
            <div key={id} className={styles.docCard}>
              <div className={styles.docHeader} onClick={() => toggleDoc(doc)}>
                <div className={styles.docIcon}>
                  <PdfIcon />
                </div>
                <div className={styles.docInfo}>
                  <div className={styles.docTitle}>{doc.title}</div>
                  <div className={styles.docMeta}>
                    {doc.category && (
                      <span className={styles.tag}>{doc.category}</span>
                    )}
                    {doc.language && (
                      <span className={styles.docMetaItem}>{doc.language}</span>
                    )}
                    {doc.upload_date && (
                      <span className={styles.docMetaItem}>
                        {new Date(doc.upload_date).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>
                <ChevronIcon className={`${styles.chevron}${isOpen ? ' ' + styles.open : ''}`} />
              </div>

              {isOpen && (
                <div className={styles.chunksPanel}>
                  {chunksLoading[id] ? (
                    <div className={styles.chunksLoading}>Loading chunks...</div>
                  ) : (chunks[id] ?? []).length === 0 ? (
                    <div className={styles.chunksLoading}>No chunks found.</div>
                  ) : (
                    (chunks[id] ?? []).map((chunk, ci) => (
                      <div key={ci} className={styles.chunkItem}>
                        <div className={styles.chunkMeta}>
                          Chunk {chunk.chunk_index ?? ci + 1}
                          {chunk.page_number != null && ` · p. ${chunk.page_number}`}
                        </div>
                        <div className={styles.chunkText}>
                          {chunk.chunk_text ?? chunk.text ?? ''}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function PdfIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 2H4a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V6L9 2z"/>
      <path d="M9 2v4h4"/>
    </svg>
  );
}

function ChevronIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 5l4 4 4-4"/>
    </svg>
  );
}

function EmptyIcon() {
  return (
    <svg viewBox="0 0 40 40" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 5H10a2 2 0 0 0-2 2v26a2 2 0 0 0 2 2h20a2 2 0 0 0 2-2V15L22 5z"/>
      <path d="M22 5v10h10"/>
    </svg>
  );
}
