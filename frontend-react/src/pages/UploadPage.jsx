import { useState, useRef } from 'react';
import { uploadDocument } from '../api/documents';
import Button from '../components/Button';
import Alert from '../components/Alert';
import styles from './UploadPage.module.css';

export default function UploadPage() {
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('');
  const [dragover, setDragover] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  const pickFile = (f) => {
    if (!f || f.type !== 'application/pdf') return;
    setFile(f);
    setTitle(f.name.replace(/\.pdf$/i, '').replace(/[_-]/g, ' '));
    setResult(null);
    setError(null);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragover(false);
    const f = e.dataTransfer.files[0];
    pickFile(f);
  };

  const handleChange = (e) => pickFile(e.target.files[0]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await uploadDocument(file, title || file.name, category || undefined);
      setResult(data);
      setFile(null);
      setTitle('');
      setCategory('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setFile(null);
    setTitle('');
    setCategory('');
    setResult(null);
    setError(null);
  };

  return (
    <div className={styles.page}>
      <h1 className={styles.heading}>Upload PDF</h1>
      <p className={styles.sub}>Add documents to the knowledge base for retrieval and Q&A.</p>

      <div
        className={`${styles.dropzone}${dragover ? ' ' + styles.dragover : ''}${file ? ' ' + styles.hasFile : ''}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragover(true); }}
        onDragLeave={() => setDragover(false)}
        onDrop={handleDrop}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className={styles.hiddenInput}
          onChange={handleChange}
        />
        <UploadIcon className={styles.dropIcon} />
        {file ? (
          <>
            <div className={styles.dropText}>File selected</div>
            <div className={styles.fileName}>{file.name}</div>
          </>
        ) : (
          <>
            <div className={styles.dropText}>Drop a PDF here or click to browse</div>
            <div className={styles.dropSub}>Only PDF files are accepted</div>
          </>
        )}
      </div>

      {file && (
        <form className={styles.formFields} onSubmit={handleSubmit}>
          <div>
            <label className={styles.fieldLabel}>Title</label>
            <input
              className={styles.input}
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Document title"
            />
          </div>
          <div>
            <label className={styles.fieldLabel}>Category (optional)</label>
            <input
              className={styles.input}
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="e.g. Finance, Legal, Research"
            />
          </div>
          <div className={styles.actions}>
            <Button type="submit" loading={loading}>
              Upload &amp; Process
            </Button>
            <Button type="button" variant="secondary" onClick={reset}>
              Cancel
            </Button>
          </div>
        </form>
      )}

      {error && (
        <div style={{ marginTop: 16 }}>
          <Alert type="error">{error}</Alert>
        </div>
      )}

      {result && (
        <div className={styles.successCard}>
          <div className={styles.successTitle}>
            Uploaded: {result.title}
          </div>
          <div className={styles.metricsRow}>
            <div className={styles.metric}>
              <span className={styles.metricValue}>
                {result.extraction?.total_pages ?? '—'}
              </span>
              <span className={styles.metricLabel}>Pages</span>
            </div>
            <div className={styles.metric}>
              <span className={styles.metricValue}>
                {result.extraction?.chunks_created ?? '—'}
              </span>
              <span className={styles.metricLabel}>Chunks</span>
            </div>
            <div className={styles.metric}>
              <span className={styles.metricValue}>
                {result.extraction?.total_chars
                  ? result.extraction.total_chars.toLocaleString()
                  : '—'}
              </span>
              <span className={styles.metricLabel}>Characters</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function UploadIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 21V9M10 15l6-6 6 6"/>
      <path d="M6 24v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2"/>
    </svg>
  );
}
