/* Written-answer and interview lessons: a textarea that saves as you type. */
import {marked} from 'marked';
import {useRef} from 'react';
import {t} from '../../lib/i18n.js';
import {save, store} from '../../store.js';
import {DoneButton, Icon} from '../ui.jsx';

export default function TextAnswer({lesson: l}) {
  const interview = l.prompt != null;
  const timer = useRef();
  const onInput = e => {
    clearTimeout(timer.current);
    const v = e.target.value;
    timer.current = setTimeout(() => save(l.uuid, {text:v}), 600);
  };
  return (
    <section id="work" aria-label={t('Workspace')}><div className="pane">
      <h2 className="pane-title"><Icon name={interview ? 'message-square' : 'pen-line'}/>{interview ? t('Interview question') : t('Your answer')}</h2>
      {interview && <div className="callout info"><div className="q-text" dangerouslySetInnerHTML={{__html:marked.parse(l.prompt)}}></div></div>}
      <div className="field">
        <label htmlFor="answer">{interview ? t('Your answer') : t('Answer')}</label>
        <textarea id="answer" aria-describedby="answer-help" defaultValue={store.progress[l.uuid]?.text || ''} onInput={onInput}></textarea>
        <p className="help" id="answer-help">{t('Saved automatically.')}</p>
      </div>
      <div className="actions"><DoneButton lesson={l}/></div>
    </div></section>
  );
}
