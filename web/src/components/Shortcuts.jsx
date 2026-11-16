import {useEffect, useRef} from 'react';
import {N_, t} from '../lib/i18n.js';
import {MOD} from '../lib/keys.js';

const ROWS = [
  [[MOD, 'Enter'], N_('Run code, run checks, or submit a sandbox')],
  [[MOD, 'Shift', 'Enter'], N_('Submit code for grading')],
  [[MOD, 'Enter'], N_('After passing: go to the next lesson')],
  [['A'], N_('Pick an answer in a quiz (A–H or 1–8)')],
  [['?'], N_('Show this list (Esc closes it)')],
];
const EDITOR = [
  [[MOD, '/'], N_('Comment or uncomment the line')],
  [['Ctrl', 'Space'], N_('Suggest completions (Tab takes one)')],
  [[MOD, 'F'], N_('Find (Enter for the next match)')],
  [[MOD, 'D'], N_('Select the next match of the word, to edit them together')],
  [[MOD, 'Shift', 'D'], N_('Duplicate the line')],
];
const Rows = ({rows}) => (
  <dl>
    {rows.map(([keys, what]) => (
      <div key={what}><dt>{keys.map(k => <kbd key={k}>{k}</kbd>)}</dt><dd>{t(what)}</dd></div>
    ))}
  </dl>
);

export default function Shortcuts({onClose}) {
  const dlg = useRef();
  useEffect(() => { dlg.current.showModal(); }, []);
  return (
    <dialog className="shortcuts" ref={dlg} aria-label={t('Keyboard shortcuts')} onClose={onClose} onClick={e => e.target === dlg.current && dlg.current.close()}>
      <form method="dialog">
        <h2>{t('Keyboard shortcuts')}</h2>
        <Rows rows={ROWS}/>
        <h3>{t('In the code editor')}</h3>
        <Rows rows={EDITOR}/>
        <button className="btn" autoFocus>{t('Close')}</button>
      </form>
    </dialog>
  );
}
