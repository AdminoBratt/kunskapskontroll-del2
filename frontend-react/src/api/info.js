import { request } from './client';

export const getInfo = () => request('/info');
export const getStats = () => request('/stats');
