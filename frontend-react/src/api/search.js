import { request } from './client';

export const searchSemantic = (query, opts = {}) =>
  request('/search/semantic', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, k: 5, ...opts }),
  });
