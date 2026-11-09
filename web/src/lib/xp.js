/* Mirrors server/gamify.py: level n starts at 50·n·(n-1) XP. */
import {store} from '../store.js';

export const levelStart = n => 50 * n * (n - 1);
export function level(xp) {
  let n = 1;
  while (xp >= levelStart(n + 1)) n++;
  return n;
}
export const stats = () => store.progress['app:stats'] || {xp:0, days:{}, streak:0, best:0, achievements:{}};

export const dayKey = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
export function currentStreak(s = stats()) {
  const today = new Date(), yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  return [dayKey(today), dayKey(yesterday)].includes(s.last) ? s.streak : 0;
}
