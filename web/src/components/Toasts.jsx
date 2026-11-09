import {store, useStore} from '../store.js';
import {Badge} from './Achievements.jsx';
import {Icon} from './ui.jsx';

export default function Toasts() {
  useStore();
  return (
    <div className="toasts" role="status" aria-live="polite">
      {store.toasts.map(t => (
        <div key={t.id} className={'toast toast-' + t.kind}>
          {t.kind === 'xp' && <><span className="toast-xp">+{t.xp} XP</span><span className="meta">{t.reason}</span></>}
          {t.kind === 'note' && <><span className="toast-icon"><Icon name="check"/></span><span>{t.text}</span></>}
          {t.kind === 'level' && <><span className="toast-icon"><Icon name="star"/></span><span><strong>Level {t.level}</strong><span className="meta">You leveled up.</span></span></>}
          {t.kind === 'achievement' && <><Badge a={{...t, unlocked:true}} size={36}/><span><span className="meta">Achievement unlocked</span><strong>{t.name}</strong></span></>}
        </div>
      ))}
    </div>
  );
}
