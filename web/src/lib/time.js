// "5 minutes ago", "yesterday"… in the UI language.
import {locale} from './i18n.js';

export function ago(at) {
  const s = (Date.now() - at) / 1000, rtf = new Intl.RelativeTimeFormat(locale(), {numeric:'auto'});
  if (s < 60) return rtf.format(0, 'minute');
  for (const [unit, n] of [['minute', 60], ['hour', 24], ['day', 7], ['week', 4.35], ['month', 12]]) {
    const v = s / {minute:60, hour:3600, day:86400, week:604800, month:2629800}[unit];
    if (v < n) return rtf.format(-Math.floor(v), unit);
  }
  return rtf.format(-Math.floor(s / 31557600), 'year');
}
