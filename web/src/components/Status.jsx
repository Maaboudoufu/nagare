/* Status: 90 days of uptime for what learners depend on, from the server's own checks (server/status.py).
   One bar per day per service; the bars swell like a magnifier under the pointer, and a click (or Enter) pins a day
   to show what happened. Adapted from Kokonut UI's Uptime Card (MIT, @dorianbaffier). */
import {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {N_, lang, t} from '../lib/i18n.js';
import {useFetch, useStore} from '../store.js';
import {Page} from './Account.jsx';
import {Icon} from './ui.jsx';

const DAYS = 90;
const MAGNIFY = 5, SPREAD = 2.4, EASE = 18;  // how much wider the bar under the pointer gets; how far that spreads, in bars; easing per second
const LONG = 15;  // minutes: shorter outages show amber, longer red
const NAMES = {App:N_('App'), Workspaces:N_('Workspaces'), Codex:N_('Codex')};
const WHAT = {App:N_('Nagare was offline'), Workspaces:N_('Code runs and terminals could not start'), Codex:N_('Codex could not be reached')};

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const dayStart = i => { const d = new Date(); d.setHours(0, 0, 0, 0); d.setDate(d.getDate() - (DAYS - 1 - i)); return d.getTime(); };
const formatDay = ms => new Date(ms).toLocaleDateString(lang(), {weekday:'short', month:'short', day:'numeric'});
const clock = ms => new Date(ms).toLocaleTimeString(lang(), {hour:'2-digit', minute:'2-digit'});

/** The server's outages (seconds) as days in the reader's time zone: {name, missing, uptime, down, incidents: {day: …}}. */
function toDays(report) {
  const starts = Array.from({length:DAYS + 1}, (_, i) => dayStart(i));  // starts[DAYS]: tomorrow
  const since = report.since * 1000, now = report.now * 1000;
  return report.services.map(({name, outages}) => {
    const incidents = {};
    let lost = 0;
    for (const [s, e, ongoing] of outages) {
      const a = s * 1000, b = e * 1000;
      lost += b - Math.max(a, starts[0]);
      for (let i = 0; i < DAYS; i++) {
        if (b <= starts[i] || a >= starts[i + 1]) continue;
        const inc = incidents[i] ??= {title:t(WHAT[name]), minutes:0, updates:[]};
        inc.minutes += (Math.min(b, starts[i + 1]) - Math.max(a, starts[i])) / 60000;
        if (a >= starts[i]) inc.updates.push({time:clock(a), label:t('Went down')});
        if (b < starts[i + 1]) inc.updates.push({time:clock(b), label:ongoing ? t('Still down') : t('Back up')});
      }
    }
    for (const inc of Object.values(incidents)) {
      inc.minutes = Math.max(1, Math.round(inc.minutes));
      inc.status = inc.minutes >= LONG ? 'down' : 'degraded';
    }
    const tracked = now - Math.max(since, starts[0]);
    return {name, incidents, down:outages.some(o => o[2]), missing:starts.findIndex(ms => ms > since) - 1,
            uptime:tracked > 0 ? 100 * Math.max(0, 1 - Math.max(0, lost) / tracked) : 100};
  });
}

const statusOf = (s, day) => day < s.missing ? 'none' : s.incidents[day]?.status ?? 'up';
const STATUS_TEXT = {up:N_('Operational'), degraded:N_('Brief outage'), down:N_('Outage'), none:N_('No data')};

function swell(focus, out) {  // target widths: a bump around the focus, flat without one
  for (let i = 0; i < out.length; i++) out[i] = focus === null ? 1 : 1 + MAGNIFY * Math.exp(-(((i - focus) / SPREAD) ** 2));
  return out;
}
function barAt(weights, x) {  // the bar under x (0 to 1) at these widths
  let at = x * weights.reduce((a, b) => a + b, 0);
  for (let i = 0; i < weights.length; i++) if ((at -= weights[i]) <= 0) return i;
  return weights.length - 1;
}

function UptimeCard({services}) {
  const [active, setActive] = useState(null);
  const [pinned, setPinned] = useState(null);
  const bars = useRef(), cur = useRef(null);  // cur: the day keys move from, ahead of the next render
  const sim = useRef({weights:new Float64Array(DAYS).fill(1), target:new Float64Array(DAYS).fill(1), raf:0, last:0, still:false});

  const paint = useCallback(() => {  // widths go straight onto the bars, one flex-grow each
    const {weights} = sim.current;
    for (const row of bars.current?.querySelectorAll('[data-row]') ?? [])
      for (let i = 0; i < row.children.length; i++) row.children[i].style.flexGrow = weights[i].toFixed(3);
  }, []);
  const tick = useCallback(now => {
    const s = sim.current;
    s.raf = 0;
    const dt = s.last ? Math.min((now - s.last) / 1000, 1 / 30) : 1 / 60, k = 1 - Math.exp(-EASE * dt);
    s.last = now;
    let moving = false;
    for (let i = 0; i < DAYS; i++) {
      const gap = s.target[i] - s.weights[i];
      if (Math.abs(gap) > .002) { s.weights[i] += gap * k; moving = true; } else s.weights[i] = s.target[i];
    }
    paint();
    if (moving) s.raf = requestAnimationFrame(tick); else s.last = 0;
  }, [paint]);
  const focusOn = useCallback(focus => {
    const s = sim.current;
    swell(focus, s.target);
    if (s.still) { s.weights.set(s.target); paint(); } else if (!s.raf) s.raf = requestAnimationFrame(tick);
  }, [paint, tick]);
  useEffect(() => {
    const s = sim.current;
    s.still = matchMedia('(prefers-reduced-motion: reduce)').matches;
    return () => cancelAnimationFrame(s.raf);
  }, []);

  const dayAt = clientX => {  // the day under the pointer, found against the swollen layout
    const r = bars.current.getBoundingClientRect(), x = clamp((clientX - r.left) / r.width, 0, 1), probe = new Float64Array(DAYS);
    let day = Math.round(x * (DAYS - 1));
    for (let pass = 0; pass < 3; pass++) day = barAt(swell(day, probe), x);
    return day;
  };
  const go = day => { cur.current = day; setActive(day); focusOn(day); };
  const point = e => go(dayAt(e.clientX));
  const leave = () => { cur.current = null; setActive(null); focusOn(pinned); };
  const onKey = e => {
    const from = cur.current ?? pinned ?? DAYS - 1;
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setPinned(p => p === from ? null : from); return; }
    if (e.key === 'Escape') { setPinned(null); leave(); focusOn(null); return; }
    const move = {ArrowLeft:-1, ArrowRight:1, Home:-DAYS, End:DAYS}[e.key];
    if (move === undefined) return;
    e.preventDefault();
    go(clamp(from + move, 0, DAYS - 1));
  };

  const on = day => day === null ? [] : services.flatMap(s => s.incidents[day] ? [{service:s.name, incident:s.incidents[day]}] : []);
  const shown = active ?? pinned, shownList = on(shown), pinnedList = on(pinned);
  const affected = services.filter(s => s.down);
  let summary = t('Point at a day to see what happened');
  if (shown !== null) {
    const first = shownList[0];
    const what = first ? t('{service} down for {n} min', {service:t(NAMES[first.service]), n:first.incident.minutes})
                         + (shownList.length > 1 ? ' ' + t('+{n} more', {n:shownList.length - 1}) : '')
                       : services.every(s => statusOf(s, shown) === 'none') ? t('No data yet') : t('No incidents');
    summary = `${formatDay(dayStart(shown))} · ${what}`;
  }

  return (
    <section className="uptime">
      <div className="uptime-head">
        <h2>{t('Services')}</h2>
        {affected.length
          ? <p className="uptime-state bad"><Icon name="triangle-alert"/>{affected.length === 1 ? t('{name} is down', {name:t(NAMES[affected[0].name])}) : t('{n} services down', {n:affected.length})}</p>
          : <p className="uptime-state good"><Icon name="circle-check"/>{t('All systems operational')}</p>}
      </div>
      <p className="uptime-summary meta" aria-live="polite">{summary}</p>

      <div className="uptime-bars" ref={bars} role="slider" tabIndex={0} aria-valuemin={1} aria-valuemax={DAYS}
           aria-valuenow={(shown ?? DAYS - 1) + 1} aria-valuetext={summary}
           aria-label={t('Daily status for the last {n} days. Arrow keys move between days, Enter opens one.', {n:DAYS})}
           onClick={() => active !== null && setPinned(p => p === active ? null : active)} onKeyDown={onKey}
           onPointerDown={e => { if (e.pointerType === 'mouse' && e.button) return; if (e.pointerType !== 'mouse') e.currentTarget.setPointerCapture(e.pointerId); point(e); }}
           onPointerMove={e => (e.pointerType === 'mouse' || e.currentTarget.hasPointerCapture(e.pointerId)) && point(e)}
           onPointerLeave={e => e.pointerType === 'mouse' && leave()} onLostPointerCapture={leave}>
        {services.map(s => (
          <div className="uptime-row" key={s.name}>
            <div className="uptime-label"><span>{t(NAMES[s.name])}</span><span className="meta">{s.uptime.toFixed(2)}%</span></div>
            <div className="uptime-days" data-row>
              {Array.from({length:DAYS}, (_, day) => (
                <i key={day} className={statusOf(s, day) + (shown !== null && day !== shown ? ' dim' : '')} style={{flexGrow:1}}/>
              ))}
            </div>
          </div>
        ))}
        <div className="uptime-axis meta"><span>{t('{n} days ago', {n:DAYS})}</span><span>{t('Today')}</span></div>
      </div>

      <div className={'uptime-log' + (pinned === null ? '' : ' open')}>
        <div>
          {pinned !== null && (
            <div className="uptime-day">
              <header><strong>{formatDay(dayStart(pinned))}</strong>
                <button className="icon-btn" aria-label={t('Close day')} onClick={() => { setPinned(null); focusOn(null); }}><Icon name="x"/></button></header>
              {pinnedList.length === 0 && <p className="meta">{services.every(s => statusOf(s, pinned) === 'none') ? t('Nagare wasn\'t keeping track yet.') : t('No incidents. Everything was up all day.')}</p>}
              {pinnedList.map(({service, incident}) => (
                <div className="uptime-incident" key={service}>
                  <p><span className={'uptime-pill ' + incident.status}>{t(STATUS_TEXT[incident.status])}</span>
                    <strong>{t(NAMES[service])}</strong><span className="meta">{incident.title} · {t('{n} min', {n:incident.minutes})}</span></p>
                  <ol>{incident.updates.map((u, i) => <li key={i}><span className="meta">{u.time}</span> {u.label}</li>)}</ol>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

export default function Status() {
  useStore();
  const report = useFetch('/api/status');
  const services = useMemo(() => report && toDays(report), [report, lang()]);
  return (
    <Page title={t('Status')} className="narrow">
      <h1>{t('Status')}</h1>
      <p className="meta status-intro">{t('Checked every two minutes by this server. Times are in your time zone.')}</p>
      {report === undefined ? null : services ? <UptimeCard services={services}/> : <p className="meta">{t('Could not load the status.')}</p>}
    </Page>
  );
}
