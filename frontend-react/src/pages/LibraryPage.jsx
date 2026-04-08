import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getDocuments, deleteDocument } from '../api/documents';
import Button from '../components/Button';
import Alert from '../components/Alert';
import styles from './LibraryPage.module.css';

export default function LibraryPage() {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deleting, setDeleting] = useState({});

  const load = () => {
    setLoading(true);
    setError(null);
    getDocuments()
      .then(setDocuments)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm('Ta bort dokumentet och alla dess embeddings?')) return;
    setDeleting((p) => ({ ...p, [id]: true }));
    try {
      await deleteDocument(id);
      setDocuments((p) => p.filter((d) => (d.document_id ?? d.id) !== id));
    } catch (err) {
      setError(err.message);
    } finally {
      setDeleting((p) => ({ ...p, [id]: false }));
    }
  };

  return (
    <div className={styles.page}>
      <h1 className={styles.heading}>Document Library</h1>
      <p className={styles.sub}>Click a document to read and chat with it.</p>

      <div className={styles.toolbar}>
        <span className={styles.count}>
          {loading ? 'Loading…' : `${documents.length} document${documents.length !== 1 ? 's' : ''}`}
        </span>
        <Button variant="secondary" size="sm" onClick={load} loading={loading}>
          Refresh
        </Button>
      </div>

      {error && <Alert type="error">{error}</Alert>}

      {!loading && documents.length === 0 && !error && (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}><EmptyIcon /></div>
          No documents yet. Upload a PDF to get started.
        </div>
      )}

      <div className={styles.docList}>
        {documents.map((doc) => {
          const id = doc.document_id ?? doc.id;
          return (
            <div
              key={id}
              className={styles.docCard}
              onClick={() => navigate(`/library/${id}`)}
            >
              <div className={styles.docIcon}><PdfIcon /></div>
              <div className={styles.docInfo}>
                <div className={styles.docTitle}>{doc.title}</div>
                <div className={styles.docMeta}>
                  {doc.category && <span className={styles.tag}>{doc.category}</span>}
                  {doc.language && <span className={styles.docMetaItem}>{doc.language}</span>}
                  {doc.upload_date && (
                    <span className={styles.docMetaItem}>
                      {new Date(doc.upload_date).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
              <Button
                variant="danger"
                size="sm"
                loading={deleting[id]}
                onClick={(e) => handleDelete(e, id)}
              >
                Delete
              </Button>
              <ChevronIcon />
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

function ChevronIcon() {
  return (
    <svg viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 14, height: 14, color: 'var(--text-muted)', flexShrink: 0 }}>
      <path d="M5 3l4 4-4 4"/>
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
