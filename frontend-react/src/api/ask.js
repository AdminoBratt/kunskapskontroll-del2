import { request } from './client';

export const askQuestion = (question, k = 5, rerank = true) =>
  request('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, k, rerank }),
  });
