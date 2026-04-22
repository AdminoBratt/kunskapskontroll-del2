import { useState, useEffect, useLayoutEffect, useMemo, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { getDocuments, getCategories, deleteDocument, updateDocument } from '../api/documents';
import { searchSemantic } from '../api/search';
import UploadModal from '../components/UploadModal';
import CategoryModal, { categoryGradient } from '../components/CategoryModal';
import styles from './DashboardPage.module.css';

// ─── Dashboard ────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const navigate = useNavigate();

  const [documents, setDocuments]             = useState([]);
  const [categories, setCategories]           = useState([]);
  const [loading, setLoading]                 = useState(true);
  const [searchQuery, setSearchQuery]         = useState('');
  const [semanticResults, setSemanticResults] = useState(null);
  const [searchLoading, setSearchLoading]     = useState(false);
  const [categoryFilter, setCategoryFilter]   = useState('');
  const [dateFilter, setDateFilter]           = useState('all');
  const [deleting, setDeleting]               = useState({});
  const [showUpload, setShowUpload]           = useState(false);
  const [showCategoryModal, setShowCategoryModal] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([getDocuments(), getCategories()])
      .then(([docs, cats]) => { setDocuments(docs); setCategories(cats); })
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  const handleSearchChange = (e) => {
    setSearchQuery(e.target.value);
    if (semanticResults) setSemanticResults(null);
  };

  const handleSemanticSearch = async () => {
    if (!searchQuery.trim()) { setSemanticResults(null); return; }
    setSearchLoading(true);
    try {
      const data = await searchSemantic(searchQuery, { k: 30 });
      const results = data.results ?? data;
      const map = new Map();
      for (const r of results) {
        const prev = map.get(r.document_id) ?? 0;
        if (r.score > prev) map.set(r.document_id, r.score);
      }
      setSemanticResults(map);
    } catch { /* fall back to title filter */ }
    finally { setSearchLoading(false); }
  };

  const clearSearch = () => { setSearchQuery(''); setSemanticResults(null); };

  const filteredDocs = useMemo(() => {
    let docs;
    if (semanticResults) {
      docs = documents
        .filter((d) => semanticResults.has(d.document_id))
        .sort((a, b) => (semanticResults.get(b.document_id) ?? 0) - (semanticResults.get(a.document_id) ?? 0));
    } else {
      const q = searchQuery.toLowerCase();
      docs = q ? documents.filter((d) => d.title.toLowerCase().includes(q)) : [...documents];
    }
    if (categoryFilter) docs = docs.filter((d) => String(d.category_id) === categoryFilter);
    if (dateFilter !== 'all') {
      const cutoff = new Date();
      cutoff.setDate(cutoff.getDate() - (dateFilter === 'week' ? 7 : 30));
      docs = docs.filter((d) => new Date(d.upload_date) >= cutoff);
    }
    return docs;
  }, [documents, searchQuery, semanticResults, categoryFilter, dateFilter]);

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm('Ta bort dokumentet och alla dess embeddings?')) return;
    setDeleting((p) => ({ ...p, [id]: true }));
    try {
      await deleteDocument(id);
      setDocuments((p) => p.filter((d) => d.document_id !== id));
    } finally {
      setDeleting((p) => ({ ...p, [id]: false }));
    }
  };

  const handleCategoryChange = async (docId, category) => {
    try {
      await updateDocument(docId, { category_id: category?.category_id ?? null });
      setDocuments((prev) =>
        prev.map((d) =>
          d.document_id === docId
            ? { ...d, category_id: category?.category_id ?? null, category: category?.name ?? null }
            : d
        )
      );
    } catch { /* silently ignore */ }
  };

  return (
    <div className={styles.page}>

      {/* ── Top bar ─────────────────────────────────────────────────────── */}
      <div className={styles.topbar}>
        <div className={styles.searchWrap}>
          <SearchIcon className={styles.searchIcon} />
          <input
            className={styles.searchInput}
            type="text"
            placeholder="Search documents…"
            value={searchQuery}
            onChange={handleSearchChange}
            onKeyDown={(e) => e.key === 'Enter' && handleSemanticSearch()}
          />
          {searchQuery && (
            <button className={styles.clearBtn} onClick={clearSearch} type="button">
              <CloseIcon />
            </button>
          )}
          <button
            className={styles.semanticBtn}
            onClick={handleSemanticSearch}
            disabled={!searchQuery.trim() || searchLoading}
            type="button"
            title="Semantic search (Enter)"
          >
            {searchLoading ? <SpinnerIcon /> : 'Search'}
          </button>
        </div>

        <div className={styles.filters}>
          <div className={styles.categoryFilterWrap}>
            <select
              className={styles.select}
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
            >
              <option value="">All categories</option>
              {categories.map((c) => (
                <option key={c.category_id} value={String(c.category_id)}>{c.name}</option>
              ))}
            </select>
            <button
              className={styles.manageBtn}
              onClick={() => setShowCategoryModal(true)}
              type="button"
              title="Manage categories"
            >
              <SettingsIcon />
            </button>
          </div>

          <select
            className={styles.select}
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
          >
            <option value="all">All time</option>
            <option value="month">Last month</option>
            <option value="week">Last week</option>
          </select>
        </div>

        <button className={styles.uploadBtn} onClick={() => setShowUpload(true)} type="button">
          <PlusIcon /> Upload
        </button>
      </div>

      {/* ── Semantic banner ──────────────────────────────────────────────── */}
      {semanticResults && (
        <div className={styles.semanticBanner}>
          <span>Semantic results for &ldquo;{searchQuery}&rdquo; — {filteredDocs.length} document{filteredDocs.length !== 1 ? 's' : ''} found</span>
          <button className={styles.bannerClear} onClick={clearSearch} type="button">Clear</button>
        </div>
      )}

      <div className={styles.meta}>
        {loading ? 'Loading…' : `${filteredDocs.length} of ${documents.length} document${documents.length !== 1 ? 's' : ''}`}
      </div>

      {/* ── Grid ────────────────────────────────────────────────────────── */}
      {!loading && filteredDocs.length === 0 && (
        <div className={styles.empty}>
          {documents.length === 0
            ? 'No documents yet — click Upload to get started.'
            : 'No documents match your search or filters.'}
        </div>
      )}

      <div className={styles.grid}>
        {filteredDocs.map((doc) => (
          <DocCard
            key={doc.document_id}
            doc={doc}
            categories={categories}
            score={semanticResults?.get(doc.document_id) ?? null}
            deleting={!!deleting[doc.document_id]}
            onDelete={(e) => handleDelete(e, doc.document_id)}
            onCategoryChange={(cat) => handleCategoryChange(doc.document_id, cat)}
            onClick={() => navigate(`/library/${doc.document_id}`)}
          />
        ))}
      </div>

      {/* ── Modals ──────────────────────────────────────────────────────── */}
      {showUpload && (
        <UploadModal
          categories={categories}
          onClose={() => setShowUpload(false)}
          onSuccess={() => { setShowUpload(false); load(); }}
        />
      )}

      {showCategoryModal && (
        <CategoryModal
          categories={categories}
          onClose={() => setShowCategoryModal(false)}
          onChange={(updated) => {
            setCategories(updated);
            // Refresh docs so category names/ids are up to date
            getDocuments().then(setDocuments);
          }}
        />
      )}
    </div>
  );
}

// ─── Doc card ─────────────────────────────────────────────────────────────────

function DocCard({ doc, categories, score, deleting, onDelete, onCategoryChange, onClick }) {
  return (
    <div className={styles.card} onClick={onClick}>
      <div className={styles.thumbnail} style={{ background: categoryGradient(doc.category_id) }}>
        <PdfIcon />
        {score != null && (
          <span className={styles.scoreBadge}>{(score * 100).toFixed(0)}%</span>
        )}
        <button
          className={`${styles.deleteBtn}${deleting ? ' ' + styles.deleting : ''}`}
          onClick={onDelete}
          disabled={deleting}
          type="button"
          title="Delete document"
        >
          <TrashIcon />
        </button>
      </div>
      <div className={styles.cardBody}>
        <div className={styles.cardTitle}>{doc.title}</div>
        <div className={styles.cardFooter}>
          <CategoryPicker
            currentCategory={doc.category_id ? { category_id: doc.category_id, name: doc.category } : null}
            categories={categories}
            onSelect={onCategoryChange}
          />
          {doc.upload_date && (
            <span className={styles.cardDate}>
              {new Date(doc.upload_date).toLocaleDateString()}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Category picker ──────────────────────────────────────────────────────────

function CategoryPicker({ currentCategory, categories, onSelect }) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState({ top: 0, left: 0 });
  const triggerRef = useRef(null);
  const dropdownRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (!dropdownRef.current?.contains(e.target) && !triggerRef.current?.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  // After dropdown renders, measure it and clamp within viewport
  useLayoutEffect(() => {
    if (!open || !dropdownRef.current) return;
    const el = dropdownRef.current;
    const elRect = el.getBoundingClientRect();
    const triggerRect = triggerRef.current.getBoundingClientRect();

    let top = triggerRect.bottom + 4;
    let left = triggerRect.left;

    // Flip above if no space below
    if (elRect.bottom > window.innerHeight - 8) {
      top = triggerRect.top - elRect.height - 4;
    }
    // Never go above viewport
    if (top < 8) top = 8;
    // Never go off the right edge
    if (left + elRect.width > window.innerWidth - 8) {
      left = window.innerWidth - elRect.width - 8;
    }

    setPos({ top, left });
  }, [open]);

  const toggle = (e) => {
    e.stopPropagation();
    if (!open) {
      const rect = triggerRef.current.getBoundingClientRect();
      setPos({ top: rect.bottom + 4, left: rect.left }); // initial estimate, corrected by useLayoutEffect
    }
    setOpen((o) => !o);
  };

  const select = (e, cat) => { e.stopPropagation(); onSelect(cat); setOpen(false); };

  return (
    <div className={styles.picker}>
      <button ref={triggerRef} className={styles.pickerTrigger} onClick={toggle} type="button">
        {currentCategory ? (
          <>
            <span className={styles.pickerDot} style={{ background: categoryGradient(currentCategory.category_id) }} />
            <span className={styles.pickerName}>{currentCategory.name}</span>
            <EditIcon />
          </>
        ) : (
          <span className={styles.pickerAdd}><PlusIcon /> Add category</span>
        )}
      </button>

      {open && createPortal(
        <div
          ref={dropdownRef}
          className={styles.pickerDropdown}
          style={{ position: 'fixed', top: pos.top, left: pos.left }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            className={`${styles.pickerOption} ${!currentCategory ? styles.pickerOptionActive : ''}`}
            onClick={(e) => select(e, null)}
            type="button"
          >
            <span className={styles.pickerDot} style={{ background: categoryGradient(null) }} />
            No category
          </button>
          {categories.map((c) => (
            <button
              key={c.category_id}
              className={`${styles.pickerOption} ${currentCategory?.category_id === c.category_id ? styles.pickerOptionActive : ''}`}
              onClick={(e) => select(e, c)}
              type="button"
            >
              <span className={styles.pickerDot} style={{ background: categoryGradient(c.category_id) }} />
              {c.name}
            </button>
          ))}
        </div>,
        document.body
      )}
    </div>
  );
}

// ─── Icons ────────────────────────────────────────────────────────────────────

function SearchIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="7" cy="7" r="4.5" /><path d="M10.5 10.5L14 14" />
    </svg>
  );
}
function CloseIcon() {
  return <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" style={{ width: 12, height: 12 }}><path d="M2 2l8 8M10 2L2 10" /></svg>;
}
function PlusIcon() {
  return <svg viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" style={{ width: 12, height: 12 }}><path d="M7 2v10M2 7h10" /></svg>;
}
function EditIcon() {
  return <svg viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 11, height: 11, flexShrink: 0 }}><path d="M10 2l2 2-7 7H3v-2l7-7z" /></svg>;
}
function SettingsIcon() {
  return <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 14, height: 14 }}><circle cx="8" cy="8" r="2" /><path d="M8 2v1M8 13v1M2 8h1M13 8h1M3.5 3.5l.7.7M11.8 11.8l.7.7M3.5 12.5l.7-.7M11.8 4.2l.7-.7" /></svg>;
}
function PdfIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.7)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 32, height: 32 }}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8L14 2z" /><path d="M14 2v6h6" /></svg>;
}
function TrashIcon() {
  return <svg viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 13, height: 13 }}><path d="M2 4h10M5 4V2h4v2M5.5 7v4M8.5 7v4M3 4l.7 7.3A1 1 0 0 0 4.7 12h4.6a1 1 0 0 0 1-.7L11 4" /></svg>;
}
function SpinnerIcon() {
  return <svg viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" style={{ width: 13, height: 13, animation: 'spin 0.8s linear infinite' }}><circle cx="7" cy="7" r="5" strokeOpacity="0.25" /><path d="M12 7a5 5 0 0 0-5-5" /></svg>;
}
