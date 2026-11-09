import {t} from '../lib/i18n.js';
import {useEffect, useRef} from 'react';
import {dismiss, store, useStore} from '../store.js';
import {Badge} from './Achievements.jsx';
import {Icon} from './ui.jsx';

// Why XP was earned, from the server's event key and params.
function reason(e) {
  if (!e) return '';
  if (e.key === 'login') return e.streak > 1 ? t('Daily visit · {n}-day streak', {n:e.streak}) : t('Daily visit');
  if (e.key === 'lesson') return t('Lesson complete');
  if (e.key === 'course') return t('Finished {title}', {title:e.title});
  if (e.key === 'achievement') return t('Achievement: {name}', {name:t(e.name)});
  return '';
}

const calm = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

// One toast: a bar along the bottom drains over its lifetime, then it slides out. Hover or keyboard focus pauses it.
function Toast({x, children}) {
  const el = useRef(), bar = useRef();
  useEffect(() => {
    const timer = bar.current.animate([{transform:'scaleX(1)'}, {transform:'scaleX(0)'}], {duration:x.ms, easing:'linear', fill:'forwards'});
    timer.onfinish = () => {
      if (calm()) return dismiss(x.id);
      el.current.animate([{opacity:1, transform:'none'}, {opacity:0, transform:'translateX(16px)'}],
                         {duration:200, easing:'cubic-bezier(.4,0,1,1)', fill:'forwards'}).onfinish = () => dismiss(x.id);
    };
    const node = el.current, pause = () => timer.pause(), play = () => node.matches(':hover, :focus-within') || timer.play();
    node.addEventListener('pointerenter', pause);
    node.addEventListener('pointerleave', play);
    node.addEventListener('focusin', pause);
    node.addEventListener('focusout', play);
    return () => timer.cancel();
  }, []);
  return (
    <div ref={el} className={'toast toast-' + x.kind + (x.tier ? ' tier-' + x.tier : '')}>
      <span className="toast-bar" ref={bar} aria-hidden="true"/>
      {children}
      <button className="toast-close" aria-label={t('Close')} onClick={() => dismiss(x.id)}><Icon name="x"/></button>
    </div>
  );
}

export default function Toasts() {
  useStore();
  return (
    <div className="toasts" role="status" aria-live="polite">
      {store.toasts.map(x => (
        <Toast key={x.id} x={x}>
          {x.kind === 'xp' && <><span className="toast-xp">{t('+{n} XP', {n:x.xp})}</span><span className="meta">{x.more ? t('{reason} + bonuses', {reason:reason(x.first)}) : reason(x.first)}</span></>}
          {x.kind === 'note' && <><span className="toast-icon"><Icon name={x.icon || 'check'}/></span><span>{x.text}</span></>}
          {x.kind === 'level' && <><span className="toast-icon"><Icon name="star"/></span><span><strong>{t('Level {n}', {n:x.level})}</strong><span className="meta">{t('You leveled up.')}</span></span></>}
          {x.kind === 'achievement' && <><Badge a={{...x, unlocked:true}} size={36}/><span><span className="meta">{t('Achievement unlocked')}</span><strong>{t(x.name)}</strong></span></>}
        </Toast>
      ))}
    </div>
  );
}
