import { request } from './client';

export const searchHybrid = (query, opts = {}) =>
  request('/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, k: 5, ...opts }),
  });

export const searchSemantic = (query, opts = {}) =>
  request('/search/semantic', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, k: 5, ...opts }),
  });

export const searchKeyword = (query, opts = {}) =>
  request('/search/keyword', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, k: 5, ...opts }),
  });
