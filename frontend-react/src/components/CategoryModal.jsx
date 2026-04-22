import { useState, useEffect, useRef } from 'react';
import { createCategory, deleteCategory } from '../api/documents';
import styles from './CategoryModal.module.css';

const GRADIENTS = [
  ['#4F6EF7', '#7B94FF'],
  ['#7C3AED', '#A78BFA'],
  ['#DB2777', '#F472B6'],
  ['#D97706', '#FBBF24'],
  ['#059669', '#34D399'],
  ['#DC2626', '#F87171'],
  ['#0891B2', '#38BDF8'],
  ['#9333EA', '#C084FC'],
];

export function categoryGradient(categoryId) {
  if (!categoryId) return 'linear-gradient(135deg, #64748B, #94A3B8)';
  const [a, b] = GRADIENTS[categoryId % GRADIENTS.length];
  return `linear-gradient(135deg, ${a}, ${b})`;
}

export default function CategoryModal({ categories, onClose, onChange }) {
  const [cats, setCats]       = useState(categories);
  const [newName, setNewName] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError]     = useState(null);
  const inputRef = useRef(null);

  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  useEffect(() => { inputRef.current?.focus(); }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const cat = await createCategory(newName.trim());
      const updated = [...cats, cat];
      setCats(updated);
      onChange(updated);
      setNewName('');
    } catch {
      setError('Could not create category.');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this category? Documents in it will become uncategorized.')) return;
    try {
      await deleteCategory(id);
      const updated = cats.filter((c) => c.category_id !== id);
      setCats(updated);
      onChange(updated);
    } catch {
      setError('Could not delete category.');
    }
  };

  return (
    <div className={styles.backdrop} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className={styles.modal}>
        <div className={styles.header}>
          <span className={styles.title}>Manage Categories</span>
          <button className={styles.closeBtn} onClick={onClose} type="button"><CloseIcon /></button>
        </div>

        {error && <div className={styles.error}>{error}</div>}

        <div className={styles.list}>
          {cats.length === 0 && (
            <div className={styles.empty}>No categories yet.</div>
          )}
          {cats.map((c) => (
            <div key={c.category_id} className={styles.row}>
              <span
                className={styles.swatch}
                style={{ background: categoryGradient(c.category_id) }}
              />
              <span className={styles.catName}>{c.name}</span>
              <button
                className={styles.deleteBtn}
                onClick={() => handleDelete(c.category_id)}
                type="button"
                title="Delete category"
              >
                <TrashIcon />
              </button>
            </div>
          ))}
        </div>

        <form className={styles.createRow} onSubmit={handleCreate}>
          <input
            ref={inputRef}
            className={styles.input}
            type="text"
            placeholder="New category name…"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
          <button
            className={styles.createBtn}
            type="submit"
            disabled={!newName.trim() || creating}
          >
            {creating ? '…' : 'Add'}
          </button>
        </form>
      </div>
    </div>
  );
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" style={{ width: 12, height: 12 }}>
      <path d="M2 2l8 8M10 2L2 10" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 13, height: 13 }}>
      <path d="M2 4h10M5 4V2h4v2M5.5 7v4M8.5 7v4M3 4l.7 7.3A1 1 0 0 0 4.7 12h4.6a1 1 0 0 0 1-.7L11 4" />
    </svg>
  );
}
