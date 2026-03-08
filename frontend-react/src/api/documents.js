import { BASE_URL, request } from './client';

export const uploadDocument = async (file, title, category) => {
  const form = new FormData();
  form.append('file', file);
  form.append('title', title);
  if (category) form.append('category', category);

  const res = await fetch(`${BASE_URL}/documents/upload`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
};

export const getDocuments = () => request('/documents');
export const getDocumentChunks = (id) => request(`/documents/${id}/chunks`);
