import {marked} from 'marked';
import {t} from '../../lib/i18n.js';
import {fx} from '../../lib/fx.js';
import {useContinue, useShortcut} from '../../lib/keys.js';
import {useState} from 'react';
import {markDone, save, store, useStore} from '../../store.js';
import {Icon, NextStep} from '../ui.jsx';

export default function Quiz({lesson: l}) {
  useStore();
  const answers = store.progress[l.uuid]?.answers || [];
  const [passed, setPassed] = useState(false);
  useContinue(passed);
  const pick = (qi, a, el) => {
    const next = [...answers];
    next[qi] = a;
    save(l.uuid, {answers:next});
    const all = l.questions.every((q, j) => next[j] === q.answer);
    if (a !== l.questions[qi].answer) fx.fail(el);
    else if (all) { fx.pass(el); markDone(l.uuid); setPassed(true); }
    else fx.correct(el);
  };
  // A–H / 1–8 answer the first question that isn't right yet.
  useShortcut('answer', ai => {
    const qi = l.questions.findIndex((q, j) => answers[j] !== q.answer);
    const a = l.questions[qi]?.answers[ai];
    if (a != null) pick(qi, a, document.querySelectorAll('#work .q')[qi]?.querySelectorAll('.option')[ai]);
  });
  return (
    <section id="work" aria-label={t('Workspace')}><div className="pane">
      <h2 className="pane-title"><Icon name="list-checks"/>{t('Quiz')}</h2>
      {l.questions.map((q, qi) => {
        const chosen = answers[qi], right = chosen === q.answer;
        return (
          <div key={qi} className="q" role="group" aria-labelledby={'q' + qi}>
            <div className="q-text" id={'q' + qi} dangerouslySetInnerHTML={{__html:marked.parse(q.question)}}></div>
            <div className="options">
              {q.answers.map((a, ai) => {
                const mine = chosen === a;
                return (
                  <button key={ai} className={'option' + (mine ? (right ? ' right' : ' wrong') : '')} aria-pressed={mine} onClick={e => pick(qi, a, e.currentTarget)}>
                    <span className="key" aria-hidden="true">{'ABCDEFGH'[ai]}</span>
                    <span className="opt-text" dangerouslySetInnerHTML={{__html:marked.parseInline(q.labels?.[ai] ?? a)}}></span>
                    <span className="opt-icon">{mine && <Icon name={right ? 'circle-check' : 'circle-x'}/>}</span>
                  </button>
                );
              })}
            </div>
            <p className={'feedback' + (chosen == null ? '' : right ? ' pass' : ' fail')} role="status" aria-live="polite">
              {chosen != null && (right ? <><Icon name="circle-check"/>{t('Correct')}</> : <><Icon name="circle-x"/>{t('Not quite. Try another answer.')}</>)}
            </p>
          </div>
        );
      })}
      <div className="actions"><NextStep show={passed}/></div>
    </div></section>
  );
}
