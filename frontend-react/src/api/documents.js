import { BASE_URL, request } from './client';

export const uploadDocument = async (file, title, { categoryId, language = 'sv' } = {}) => {
  const form = new FormData();
  form.append('file', file);
  form.append('title', title);
  if (categoryId) form.append('category_id', categoryId);
  form.append('language', language);

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
export const getDocument = (id) => request(`/documents/${id}`);
export const getDocumentChunks = (id) => request(`/documents/${id}/chunks`);
export const deleteDocument = (id) => request(`/documents/${id}`, { method: 'DELETE' });
export const updateDocument = (id, data) =>
  request(`/documents/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

export const getCategories = () => request('/categories');
export const createCategory = (name) =>
  request('/categories', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
export const deleteCategory = (id) => request(`/categories/${id}`, { method: 'DELETE' });
