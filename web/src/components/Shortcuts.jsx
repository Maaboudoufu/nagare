import {useEffect, useRef} from 'react';
import {N_, t} from '../lib/i18n.js';
import {MOD} from '../lib/keys.js';

const ROWS = [
  [[MOD, 'Enter'], N_('Run code, run checks, or submit a sandbox')],
  [[MOD, 'Shift', 'Enter'], N_('Submit code for grading')],
  [['A'], N_('Pick an answer in a quiz (A–H or 1–8)')],
  [['['], N_('Previous lesson')],
  [[']'], N_('Next lesson')],
  [['?'], N_('Show this list (Esc closes it)')],
];

export default function Shortcuts({onClose}) {
  const dlg = useRef();
  useEffect(() => { dlg.current.showModal(); }, []);
  return (
    <dialog className="shortcuts" ref={dlg} aria-label={t('Keyboard shortcuts')} onClose={onClose} onClick={e => e.target === dlg.current && dlg.current.close()}>
      <form method="dialog">
        <h2>{t('Keyboard shortcuts')}</h2>
        <dl>
          {ROWS.map(([keys, what]) => (
            <div key={what}><dt>{keys.map(k => <kbd key={k}>{k}</kbd>)}</dt><dd>{t(what)}</dd></div>
          ))}
        </dl>
        <button className="btn" autoFocus>{t('Close')}</button>
      </form>
    </dialog>
  );
}
