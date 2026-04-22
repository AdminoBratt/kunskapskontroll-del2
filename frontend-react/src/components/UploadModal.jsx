import { useState, useRef, useEffect } from 'react';
import { uploadDocument } from '../api/documents';
import styles from './UploadModal.module.css';

export default function UploadModal({ categories, onClose, onSuccess }) {
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [language, setLanguage] = useState('sv');
  const [dragover, setDragover] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  // Close on Escape
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const pickFile = (f) => {
    if (!f || f.type !== 'application/pdf') return;
    setFile(f);
    setTitle(f.name.replace(/\.pdf$/i, '').replace(/[_-]/g, ' '));
    setError(null);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragover(false);
    pickFile(e.dataTransfer.files[0]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const data = await uploadDocument(file, title || file.name, {
        categoryId: categoryId || undefined,
        language,
      });
      onSuccess(data);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  return (
    <div className={styles.backdrop} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className={styles.modal}>
        <div className={styles.modalHeader}>
          <span className={styles.modalTitle}>Upload PDF</span>
          <button className={styles.closeBtn} onClick={onClose} type="button">
            <CloseIcon />
          </button>
        </div>

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
            onChange={(e) => pickFile(e.target.files[0])}
          />
          <UploadIcon />
          {file ? (
            <span className={styles.dropText}>{file.name}</span>
          ) : (
            <span className={styles.dropText}>Drop a PDF or click to browse</span>
          )}
        </div>

        {file && (
          <form className={styles.fields} onSubmit={handleSubmit}>
            <div className={styles.field}>
              <label className={styles.label}>Title</label>
              <input
                className={styles.input}
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Document title"
              />
            </div>

            <div className={styles.row}>
              <div className={styles.field}>
                <label className={styles.label}>Category</label>
                <select
                  className={styles.input}
                  value={categoryId}
                  onChange={(e) => setCategoryId(e.target.value)}
                >
                  <option value="">No category</option>
                  {categories.map((c) => (
                    <option key={c.category_id} value={c.category_id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className={styles.field}>
                <label className={styles.label}>Language</label>
                <select
                  className={styles.input}
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                >
                  <option value="sv">Swedish</option>
                  <option value="en">English</option>
                  <option value="de">German</option>
                </select>
              </div>
            </div>

            {error && <div className={styles.error}>{error}</div>}

            <div className={styles.actions}>
              <button className={styles.submitBtn} type="submit" disabled={loading}>
                {loading ? 'Uploading…' : 'Upload & Process'}
              </button>
              <button className={styles.cancelBtn} type="button" onClick={onClose}>
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 28, height: 28, marginBottom: 8, opacity: 0.4 }}>
      <path d="M12 16V8M9 11l3-3 3 3" />
      <path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <path d="M2 2l10 10M12 2L2 12" />
    </svg>
  );
}
