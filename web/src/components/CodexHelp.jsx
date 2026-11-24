/* Ask Codex about the lesson you're on, on your own linked ChatGPT account (Settings). The server adds the lesson and
   your saved code to each question; Codex has no tools, it only answers. */
import {Marked} from 'marked';
import {useEffect, useId, useLayoutEffect, useRef, useState} from 'react';
import {createPortal} from 'react-dom';
import {N_, t} from '../lib/i18n.js';
import {settings, useFetch, useStore} from '../store.js';
import {CopyButton, DotLoader, Icon} from './ui.jsx';

// The Codex mark (OpenAI), from Lobe Icons 1.106.0 (MIT), in its brand gradient.
const MARK = 'M8.086.457a6.105 6.105 0 013.046-.415c1.333.153 2.521.72 3.564 1.7a.117.117 0 00.107.029c1.408-.346 2.762-.224 4.061.366l.063.03.154.076c1.357.703 2.33 1.77 2.918 3.198.278.679.418 1.388.421 2.126a5.655 5.655 0 01-.18 1.631.167.167 0 00.04.155 5.982 5.982 0 011.578 2.891c.385 1.901-.01 3.615-1.183 5.14l-.182.22a6.063 6.063 0 01-2.934 1.851.162.162 0 00-.108.102c-.255.736-.511 1.364-.987 1.992-1.199 1.582-2.962 2.462-4.948 2.451-1.583-.008-2.986-.587-4.21-1.736a.145.145 0 00-.14-.032c-.518.167-1.04.191-1.604.185a5.924 5.924 0 01-2.595-.622 6.058 6.058 0 01-2.146-1.781c-.203-.269-.404-.522-.551-.821a7.74 7.74 0 01-.495-1.283 6.11 6.11 0 01-.017-3.064.166.166 0 00.008-.074.115.115 0 00-.037-.064 5.958 5.958 0 01-1.38-2.202 5.196 5.196 0 01-.333-1.589 6.915 6.915 0 01.188-2.132c.45-1.484 1.309-2.648 2.577-3.493.282-.188.55-.334.802-.438.286-.12.573-.22.861-.304a.129.129 0 00.087-.087A6.016 6.016 0 015.635 2.31C6.315 1.464 7.132.846 8.086.457zm-.804 7.85a.848.848 0 00-1.473.842l1.694 2.965-1.688 2.848a.849.849 0 001.46.864l1.94-3.272a.849.849 0 00.007-.854l-1.94-3.393zm5.446 6.24a.849.849 0 000 1.695h4.848a.849.849 0 000-1.696h-4.848z';

export function CodexLogo({size = 20, mono = false, tile = false}) {
  const id = 'cx' + useId().replace(/\W/g, '');
  const mark = (
    <svg className="codex-mark" width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      {!mono && <defs><linearGradient id={id} gradientUnits="userSpaceOnUse" x1="12" x2="12" y1="0" y2="24">
        <stop stopColor="#B1A7FF"/><stop offset=".5" stopColor="#7A9DFF"/><stop offset="1" stopColor="#3941FF"/>
      </linearGradient></defs>}
      <path fillRule="evenodd" clipRule="evenodd" fill={mono ? 'currentColor' : `url(#${id})`} d={MARK}/>
    </svg>
  );
  return tile ? <span className="codex-tile" style={{'--s':`${size * 1.8}px`}}>{mark}</span> : mark;
}

const esc = s => s.replace(/[&<>"]/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;'}[c]));
const md = new Marked({renderer:{html:token => esc(typeof token === 'string' ? token : token.text)}});  // raw HTML shows as text
// ---- Dragging: the panel follows the pointer from where it was grabbed, resists past the screen edge, and on release is
// thrown along its momentum to the nearest side (and flush to the top or bottom when it lands close), on a critically
// damped spring that can be grabbed again mid-flight. Which side it's on is remembered in this browser.
const MARGIN = 12, SNAP_Y = 96, RESPONSE = .4;  // px from the edges; px from top/bottom that snaps flush; spring seconds
const rubber = (over, dim) => over * dim * .55 / (dim + .55 * Math.abs(over));
const band = (v, max, dim) => v < MARGIN ? MARGIN - rubber(MARGIN - v, dim) : v > max ? max + rubber(v - max, dim) : v;
const project = v => v / 1000 * .998 / (1 - .998);  // where a flick at v px/s comes to rest, like scrolling
const clamp = (v, lo, hi) => Math.min(Math.max(v, lo), Math.max(lo, hi));
const loadDock = () => { try { return JSON.parse(localStorage.getItem('codex-dock')); } catch { return null; } };
const saveDock = d => { try { localStorage.setItem('codex-dock', JSON.stringify(d)); } catch {} };

function makeDock(el) {
  let x = 0, y = 0, raf = 0;
  const max = () => [innerWidth - el.offsetWidth - MARGIN, innerHeight - el.offsetHeight - MARGIN];
  const side = () => x + el.offsetWidth / 2 < innerWidth / 2 ? 'left' : 'right';
  const place = (nx, ny) => { x = nx; y = ny; el.style.translate = `${x}px ${y}px`; };
  const settle = () => { el.style.transformOrigin = `top ${side()}`; saveDock({side:side(), y}); };
  const springTo = (tx, ty, vx, vy) => {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return place(tx, ty), settle();
    const w = 2 * Math.PI / RESPONSE, x0 = x - tx, y0 = y - ty, t0 = performance.now();
    const step = now => {  // x(t) = (x0 + (v0 + w x0) t) e^(-wt): starts at the release velocity, never overshoots
      const t = (now - t0) / 1000, e = Math.exp(-w * t), dx = (x0 + (vx + w * x0) * t) * e, dy = (y0 + (vy + w * y0) * t) * e;
      if (t > .05 && Math.abs(dx) < .3 && Math.abs(dy) < .3 || t > 2) return place(tx, ty), settle();
      place(tx + dx, ty + dy);
      raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
  };
  const snap = (vx, vy) => {
    const [mx, my] = max(), px = x + project(vx), py = y + project(vy);
    let ty = clamp(py, MARGIN, my);
    if (ty - MARGIN < SNAP_Y) ty = MARGIN;
    else if (my - ty < SNAP_Y) ty = Math.max(MARGIN, my);
    springTo(px + el.offsetWidth / 2 < innerWidth / 2 ? MARGIN : Math.max(MARGIN, mx), ty, vx, vy);
  };
  return {
    openAt(rect) {  // where it was left, or under the button that opens it
      cancelAnimationFrame(raf);
      const [mx, my] = max(), d = loadDock();
      if (d) place(d.side === 'left' ? MARGIN : Math.max(MARGIN, mx), clamp(d.y, MARGIN, my));
      else place(clamp(rect.right - el.offsetWidth, MARGIN, mx), clamp(rect.bottom + 8, MARGIN, my));
      el.style.transformOrigin = `top ${side()}`;
    },
    refit() { const [mx, my] = max(); place(side() === 'left' ? MARGIN : Math.max(MARGIN, mx), clamp(y, MARGIN, my)); },
    down(e) {
      if (e.button !== 0 || e.target.closest('button')) return;
      cancelAnimationFrame(raf);  // caught mid-flight: carry on from where it is now
      const handle = e.currentTarget, gx = e.clientX - x, gy = e.clientY - y, trail = [];
      let moved = false;
      handle.setPointerCapture(e.pointerId);
      const move = ev => {
        if (!moved && Math.hypot(ev.clientX - e.clientX, ev.clientY - e.clientY) < 4) return;  // a click isn't a drag
        moved = true;
        el.classList.add('dragging');
        trail.push([ev.clientX, ev.clientY, ev.timeStamp]);
        if (trail.length > 8) trail.shift();
        const [mx, my] = max();
        place(band(ev.clientX - gx, mx, innerWidth), band(ev.clientY - gy, my, innerHeight));
      };
      const up = ev => {
        handle.removeEventListener('pointermove', move);
        handle.removeEventListener('pointerup', up);
        handle.removeEventListener('pointercancel', up);
        el.classList.remove('dragging');
        if (!moved) return;
        const recent = trail.filter(p => ev.timeStamp - p[2] < 100), a = recent[0], b = recent.at(-1);  // a rest before letting go is no flick
        const dt = a && b !== a ? (b[2] - a[2]) / 1000 : 0;
        snap(dt ? (b[0] - a[0]) / dt : 0, dt ? (b[1] - a[1]) / dt : 0);
      };
      handle.addEventListener('pointermove', move);
      handle.addEventListener('pointerup', up);
      handle.addEventListener('pointercancel', up);
    },
  };
}

// A snake winding around the dot matrix, while Codex works on an answer.
const SNAKE = [[14, 7, 0, 8, 6, 13, 20], [14, 7, 13, 20, 16, 27, 21], [14, 20, 27, 21, 34, 24, 28], [27, 21, 34, 28, 41, 32, 35],
               [34, 28, 41, 35, 48, 40, 42], [34, 28, 41, 35, 48, 42, 46], [34, 28, 41, 35, 48, 42, 38], [34, 28, 41, 35, 48, 30, 21],
               [34, 28, 41, 48, 21, 22, 14], [34, 28, 41, 21, 14, 16, 27], [34, 28, 21, 14, 10, 20, 27], [28, 21, 14, 4, 13, 20, 27],
               [28, 21, 14, 12, 6, 13, 20], [28, 21, 14, 6, 13, 20, 11], [28, 21, 14, 6, 13, 20, 10], [14, 6, 13, 20, 9, 7, 21]];
const SUGGESTIONS = [N_('Give me a hint'), N_('Explain this lesson simply'), N_('Why is my code failing?')];

export default function CodexHelp({lesson}) {
  useStore();
  const status = useFetch('/api/codex');
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);  // stays after the first open, so closing can animate
  const [chat, setChat] = useState([]);  // {role:'user'|'assistant', text, error?}
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState('');
  const trigger = useRef(), input = useRef(), log = useRef(), abort = useRef(), panel = useRef(), dock = useRef();
  useEffect(() => { abort.current?.abort(); setChat([]); }, [lesson.uuid]);  // a new lesson starts a new chat
  useEffect(() => { log.current && (log.current.scrollTop = log.current.scrollHeight); }, [chat]);
  useLayoutEffect(() => {  // place it before it shows, and keep it on screen when the window changes size
    if (!open || !panel.current) return;
    dock.current ??= makeDock(panel.current);
    dock.current.openAt(trigger.current.getBoundingClientRect());
    input.current?.focus();
    const refit = () => dock.current.refit();
    addEventListener('resize', refit);
    return () => removeEventListener('resize', refit);
  }, [open, mounted]);
  if (!status?.linked) return null;

  const show = () => {
    setMounted(true);
    setOpen(true);
  };
  const close = () => { setOpen(false); trigger.current?.focus(); };

  const send = async text => {
    const question = text.trim();
    if (!question || busy) return;
    const history = chat.filter(m => !m.error);
    setQ(''); setBusy(true);
    setChat([...chat, {role:'user', text:question}, {role:'assistant', text:''}]);
    const update = (text, error) => setChat(c => [...c.slice(0, -1), {role:'assistant', text, error}]);
    abort.current = new AbortController();
    let answer = '';
    try {
      const r = await fetch('/api/codex/ask', {method:'POST', signal:abort.current.signal, body:JSON.stringify({uuid:lesson.uuid, question, history})});
      if (!r.ok) update((await r.json().catch(() => ({}))).error || t('Codex is not reachable right now.'), true);
      else {
        const reader = r.body.pipeThrough(new TextDecoderStream()).getReader();
        for (let part; !(part = await reader.read()).done;) update(answer += part.value);
      }
    } catch (err) {
      if (err.name !== 'AbortError') update(t('Codex is not reachable right now.'), true);
      else if (!answer) update(t('Stopped.'), true);
    }
    setBusy(false);
    input.current?.focus();
  };

  const s = settings();
  const last = chat.length - 1;
  return <>
    <button ref={trigger} className="btn ghost codex-trigger" aria-expanded={open} aria-controls="codex-panel"
            onClick={() => open ? close() : show()}><CodexLogo size={16} mono/>{t('Ask Codex')}</button>
    {mounted && createPortal(  // on <body>: the lesson bar's backdrop-filter would pin a fixed panel inside it
      <aside id="codex-panel" className="codex-panel" data-open={open || undefined} ref={panel} aria-label={t('Ask Codex')}
             inert={!open || undefined} onKeyDown={e => e.key === 'Escape' && close()}>
        <header className="codex-head" onPointerDown={e => dock.current?.down(e)} title={t('Drag to move')}>
          <CodexLogo size={18} tile/>
          <div className="codex-title">
            <h2>Codex</h2>
            <span className="meta">{s.codexModel ? [s.codexModel, s.codexEffort && t(EFFORT_NAMES[s.codexEffort] || s.codexEffort)].filter(Boolean).join(' · ') : t('On your ChatGPT account')}</span>
          </div>
          <button className="icon-btn" aria-label={t('New chat')} title={t('New chat')} disabled={!chat.length || busy} onClick={() => setChat([])}><Icon name="rotate-ccw"/></button>
          <button className="icon-btn" aria-label={t('Close')} title={t('Close')} onClick={close}><Icon name="x"/></button>
        </header>

        <div className="codex-log" ref={log}>
          {chat.length === 0 ? (
            <div className="codex-empty">
              <CodexLogo size={28} tile/>
              <h3>{t('Stuck on this lesson?')}</h3>
              <p className="meta">{t('Codex sees this lesson and your saved code. It gives hints first, not the answer.')}</p>
              <div className="codex-suggest">
                {SUGGESTIONS.map(k => <button key={k} className="codex-chip" onClick={() => send(t(k))}>{t(k)}</button>)}
              </div>
            </div>
          ) : chat.map((m, i) => m.role === 'user'
            ? <p key={i} className="codex-q">{m.text}</p>
            : <div key={i} className={'codex-a' + (m.error ? ' error' : '')}>
                <CodexLogo size={14} tile/>
                {m.error ? <p role="alert"><Icon name="triangle-alert"/>{m.text}</p>
                  : m.text ? <div className={'prose' + (busy && i === last ? ' streaming' : '')} dangerouslySetInnerHTML={{__html:md.parse(m.text)}}></div>
                  : <span className="codex-loading" role="status"><DotLoader frames={SNAKE}/>{t('Loading…')}</span>}
                {!m.error && m.text && !(busy && i === last) && <CopyButton text={m.text} label={t('Copy answer')}/>}
              </div>)}
        </div>

        <form className="codex-compose" onSubmit={e => { e.preventDefault(); send(q); }}>
          <textarea ref={input} value={q} rows={1} aria-label={t('Ask about this lesson…')} placeholder={t('Ask about this lesson…')}
                    onChange={e => setQ(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(q); } }}/>
          <div className="codex-compose-foot">
            <span className="kbd-hint">{t('{enter} to send · {shift} for a new line', {enter:<kbd>Enter</kbd>, shift:<kbd>Shift+Enter</kbd>})}</span>
            {busy
              ? <button type="button" className="codex-send stop" aria-label={t('Stop')} title={t('Stop')} onClick={() => abort.current?.abort()}><span className="stop-square"/></button>
              : <button className="codex-send" aria-label={t('Send')} title={t('Send')} disabled={!q.trim()}><Icon name="send"/></button>}
          </div>
        </form>
      </aside>, document.body)}
  </>;
}

export const EFFORT_NAMES = {minimal:N_('Minimal'), low:N_('Low'), medium:N_('Medium'), high:N_('High'), xhigh:N_('Extra high'), max:N_('Max'), ultra:N_('Ultra')};
