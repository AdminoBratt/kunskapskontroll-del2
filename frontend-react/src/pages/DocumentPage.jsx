import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getDocument } from '../api/documents';
import { askQuestion } from '../api/ask';
import { BASE_URL } from '../api/client';
import styles from './DocumentPage.module.css';

export default function DocumentPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const docId = parseInt(id);

  const [doc, setDoc] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    getDocument(docId)
      .then(setDoc)
      .catch(() => navigate('/library'));
  }, [docId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    const question = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', text: question }]);
    setLoading(true);
    try {
      const data = await askQuestion(question, 5, docId);
      setMessages((prev) => [...prev, {
        role: 'assistant',
        text: data.answer,
        sources: data.sources,
      }]);
    } catch (err) {
      setMessages((prev) => [...prev, {
        role: 'assistant',
        text: `Error: ${err.message}`,
        error: true,
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <button className={styles.back} onClick={() => navigate('/library')}>
          <BackIcon /> Library
        </button>
        <span className={styles.docTitle}>{doc?.title ?? '…'}</span>
      </div>

      <div className={styles.body}>
        <div className={styles.pdfPane}>
          <iframe
            className={styles.pdfFrame}
            src={`${BASE_URL}/documents/${docId}/pdf`}
            title={doc?.title}
          />
        </div>

        <div className={styles.chatPane}>
          <div className={styles.messages}>
            {messages.length === 0 && (
              <div className={styles.emptyChat}>
                Ask anything about this document.
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`${styles.message} ${styles[msg.role]}`}>
                <div className={styles.bubble}>{msg.text}</div>
                {msg.sources?.length > 0 && <Sources sources={msg.sources} />}
              </div>
            ))}
            {loading && (
              <div className={`${styles.message} ${styles.assistant}`}>
                <div className={`${styles.bubble} ${styles.thinking}`}>Thinking…</div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form className={styles.inputRow} onSubmit={handleSubmit}>
            <input
              className={styles.input}
              type="text"
              placeholder="Ask about this document…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
              autoFocus
            />
            <button
              className={styles.sendBtn}
              type="submit"
              disabled={!input.trim() || loading}
            >
              <SendIcon />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

function Sources({ sources }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={styles.sourcesWrap}>
      <button className={styles.sourcesToggle} onClick={() => setOpen((o) => !o)} type="button">
        {sources.length} source{sources.length !== 1 ? 's' : ''}
        <ChevronIcon className={open ? styles.chevronOpen : ''} />
      </button>
      {open && (
        <div className={styles.sourcesList}>
          {sources.map((s, i) => (
            <div key={i} className={styles.sourceItem}>
              <span className={styles.sourceMeta}>
                p.&thinsp;{s.page_number} &middot; {(s.score * 100).toFixed(0)}%
              </span>
              <span className={styles.sourceText}>{s.chunk_text}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function BackIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 3L5 8l5 5" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2L2 7l5 3 2 5 5-13z" />
    </svg>
  );
}

function ChevronIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 5l4 4 4-4" />
    </svg>
  );
}
