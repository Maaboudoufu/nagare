/* Written-answer and interview lessons: a textarea that saves as you type. */
import {marked} from 'marked';
import {useRef} from 'react';
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
    <section id="work" aria-label="Workspace"><div className="pane">
      <h2 className="pane-title"><Icon name={interview ? 'message-square' : 'pen-line'}/>{interview ? 'Interview question' : 'Your answer'}</h2>
      {interview && <div className="callout info"><div className="q-text" dangerouslySetInnerHTML={{__html:marked.parse(l.prompt)}}></div></div>}
      <div className="field">
        <label htmlFor="answer">{interview ? 'Your answer' : 'Answer'}</label>
        <textarea id="answer" aria-describedby="answer-help" defaultValue={store.progress[l.uuid]?.text || ''} onInput={onInput}></textarea>
        <p className="help" id="answer-help">Saved automatically.</p>
      </div>
      <div className="actions"><DoneButton lesson={l}/></div>
    </div></section>
  );
}
