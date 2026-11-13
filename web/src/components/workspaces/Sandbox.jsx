/* Learn Linux shell lessons: a terminal in this lesson's own Docker sandbox.
   One match check grades the last history line. Two or more grade recorded commands, in order. */
import {useRef, useState} from 'react';
import {fx} from '../../lib/fx.js';
import {t} from '../../lib/i18n.js';
import {MOD, useContinue, useShortcut} from '../../lib/keys.js';
import {markDone, post} from '../../store.js';
import TermView from '../TermView.jsx';
import {DoneButton, Icon, NextStep} from '../ui.jsx';

// Course text says "Your last command should contain" on every match step. One check shows that
// string unchanged. Two or more are separate commands, in order.
const LAST_EXPECT = 'Your last command should contain: ';

function InitialExpects({expects}) {
  const commands = expects.filter(e => e.startsWith(LAST_EXPECT)).map(e => e.slice(LAST_EXPECT.length));
  if (commands.length >= 2 && commands.length === expects.length) {
    return <ul className="expects">{commands.map((need, i) => <li key={i}>{i
      ? t('Then a later command should contain: {need}', {need})
      : t('A command should contain: {need}', {need})}</li>)}</ul>;
  }
  return <ul className="expects">{expects.map((c, i) => <li key={i}>{c}</li>)}</ul>;
}

function MatchItem({c}) {
  const need = (c.want || []).join(', ');
  // One check keeps the server sentence. Ordered checks are separate commands; `after` means a miss
  // that searched past an earlier matched step.
  const title = c.scope === 'last' ? c.message : c.want ? t('A command should contain: {need}', {need}) : c.message;
  const detail = c.ok ? null
    : c.scope === 'last' ? t('Your last command: {cmd}', {cmd:<code>{c.last || t('(none yet)')}</code>})
    : c.after ? t('No matching command occurred after the previous matched step.')
    : c.want ? t('No command contained {need}', {need:<code>{need}</code>})
    : null;
  return (
    <li className={c.ok ? 'pass' : 'fail'}>
      <Icon name={c.ok ? 'circle-check' : 'circle-x'}/>
      <span>{title}{detail && <><br/><span className="meta">{detail}</span></>}</span>
    </li>
  );
}

function CheckResults({result}) {
  if (result.error) return <p className="field-err">{result.error}</p>;
  return <>
    <ul className="check-list">
      {result.results.map((c, i) => c.kind === 'match' ? <MatchItem key={i} c={c}/> : (
        <li key={i} className="review">
          <Icon name="info"/>
          <span>{t('Check the result of {cmd} against the assignment.', {cmd:<code>{c.command}</code>})}<pre>{c.output || t('(no output)')}</pre></span>
        </li>
      ))}
    </ul>
    {result.passed ? <p className="feedback pass"><Icon name="circle-check"/>{t('All checks passed')}</p>
      : result.review && <p className="meta">{t('This check has no stored answer to compare with. If the output matches what the assignment asked for, mark the lesson complete.')}</p>}
  </>;
}

export default function Sandbox({lesson: l}) {
  const [generation, setGeneration] = useState(0);  // bumping it reconnects the terminal to a fresh sandbox
  const [result, setResult] = useState(null);
  const [checking, setChecking] = useState(false);
  const resultEl = useRef();
  const [passed, setPassed] = useState(false);
  useContinue(passed);
  const reset = async () => {
    if (!confirm(t('Reset the sandbox? Files you changed in it are lost.'))) return;
    await post('/api/sandbox/reset', {uuid:l.uuid});
    setResult(null);
    setGeneration(g => g + 1);
  };
  const submit = async () => {
    if (checking) return;
    setChecking(true);
    try {
      const r = await post('/api/sandbox/check', {uuid:l.uuid});
      setResult(r);
      if (r.passed) { fx.pass(resultEl.current); markDone(l.uuid); setPassed(true); }
      else if (!r.review) fx.fail(resultEl.current);
    } catch {
      setResult({error:t('Local server not reachable.')});
    }
    setChecking(false);
  };
  useShortcut('submit', submit);
  return (
    <section id="work" aria-label={t('Workspace')}>
      <div className="term-head">
        <h2 className="pane-title"><Icon name="terminal"/>{t('Linux sandbox')}</h2>
        {l.sandbox === 'approximate' && (
          <span className="chip info" title={t('This lesson\'s exact files weren\'t available, so the sandbox has every Learn Linux file instead.')}>
            <Icon name="info"/>{t('Approximate files')}
          </span>
        )}
        <button className="btn ghost" title={t('Throw this sandbox away and start fresh')} onClick={reset}><Icon name="rotate-ccw"/>{t('Reset')}</button>
      </div>
      <TermView key={generation} url={`/api/term?kind=sandbox&uuid=${l.uuid}&g=${generation}`} label={t('Linux sandbox terminal')}/>
      <section className="sandbox-checks" aria-label={t('Lesson checks')}>
        {!result?.results && <InitialExpects expects={l.steps[0]?.expects || []}/>}
        <div aria-live="polite" ref={resultEl}>{result && <CheckResults result={result}/>}</div>
        <div className="actions">
          <button className={passed ? 'btn' : 'btn primary'} disabled={checking} onClick={submit} title={t('Submit ({mod}+Enter)', {mod:MOD})}><Icon name="send"/>{t('Submit')}</button>
          <DoneButton lesson={l}/>
          {passed ? <NextStep show/> : <span className="kbd-hint">{t('{mod} {enter} submit', {mod:<kbd>{MOD}</kbd>, enter:<kbd>Enter</kbd>})}</span>}
        </div>
      </section>
    </section>
  );
}
