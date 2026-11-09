import {marked} from 'marked';
import {markDone, save, store, useStore} from '../../store.js';
import {Icon} from '../ui.jsx';

export default function Quiz({lesson: l}) {
  useStore();
  const answers = store.progress[l.uuid]?.answers || [];
  const pick = (qi, a) => {
    const next = [...answers];
    next[qi] = a;
    save(l.uuid, {answers:next});
    if (l.questions.every((q, j) => next[j] === q.answer)) markDone(l.uuid);
  };
  return (
    <section id="work" aria-label="Workspace"><div className="pane">
      <h2 className="pane-title"><Icon name="list-checks"/>Quiz</h2>
      {l.questions.map((q, qi) => {
        const chosen = answers[qi], right = chosen === q.answer;
        return (
          <div key={qi} className="q" role="group" aria-labelledby={'q' + qi}>
            <div className="q-text" id={'q' + qi} dangerouslySetInnerHTML={{__html:marked.parse(q.question)}}></div>
            <div className="options">
              {q.answers.map((a, ai) => {
                const mine = chosen === a;
                return (
                  <button key={ai} className={'option' + (mine ? (right ? ' right' : ' wrong') : '')} aria-pressed={mine} onClick={() => pick(qi, a)}>
                    <span className="key" aria-hidden="true">{'ABCDEFGH'[ai]}</span>
                    <span className="opt-text" dangerouslySetInnerHTML={{__html:marked.parseInline(a)}}></span>
                    <span className="opt-icon">{mine && <Icon name={right ? 'circle-check' : 'circle-x'}/>}</span>
                  </button>
                );
              })}
            </div>
            <p className={'feedback' + (chosen == null ? '' : right ? ' pass' : ' fail')} role="status" aria-live="polite">
              {chosen != null && (right ? <><Icon name="circle-check"/>Correct</> : <><Icon name="circle-x"/>Not quite. Try another answer.</>)}
            </p>
          </div>
        );
      })}
    </div></section>
  );
}
