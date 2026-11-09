import {t} from '../lib/i18n.js';
import {store, useStore} from '../store.js';
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

export default function Toasts() {
  useStore();
  return (
    <div className="toasts" role="status" aria-live="polite">
      {store.toasts.map(x => (
        <div key={x.id} className={'toast toast-' + x.kind}>
          {x.kind === 'xp' && <><span className="toast-xp">{t('+{n} XP', {n:x.xp})}</span><span className="meta">{x.more ? t('{reason} + bonuses', {reason:reason(x.first)}) : reason(x.first)}</span></>}
          {x.kind === 'note' && <><span className="toast-icon"><Icon name="check"/></span><span>{x.text}</span></>}
          {x.kind === 'level' && <><span className="toast-icon"><Icon name="star"/></span><span><strong>{t('Level {n}', {n:x.level})}</strong><span className="meta">{t('You leveled up.')}</span></span></>}
          {x.kind === 'achievement' && <><Badge a={{...x, unlocked:true}} size={36}/><span><span className="meta">{t('Achievement unlocked')}</span><strong>{t(x.name)}</strong></span></>}
        </div>
      ))}
    </div>
  );
}
