import { request } from './client';

export const askQuestion = (question, k = 5, document_id = null) =>
  request('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, k, ...(document_id != null && { document_id }) }),
  });
