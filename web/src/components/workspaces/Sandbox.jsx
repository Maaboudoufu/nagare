/* Learn Linux shell lessons: a terminal in this lesson's own Docker sandbox, graded from your shell history. */
import {useState} from 'react';
import {markDone, post} from '../../store.js';
import TermView from '../TermView.jsx';
import {DoneButton, Icon} from '../ui.jsx';

function CheckResults({result}) {
  if (result.error) return <p className="field-err">{result.error}</p>;
  return <>
    <ul className="check-list">
      {result.results.map((c, i) => c.kind === 'match' ? (
        <li key={i} className={c.ok ? 'pass' : 'fail'}>
          <Icon name={c.ok ? 'circle-check' : 'circle-x'}/>
          <span>{c.message}{!c.ok && <><br/><span className="meta">Your last command: <code>{c.last || '(none yet)'}</code></span></>}</span>
        </li>
      ) : (
        <li key={i} className="review">
          <Icon name="info"/>
          <span>Check the result of <code>{c.command}</code> against the assignment.<pre>{c.output || '(no output)'}</pre></span>
        </li>
      ))}
    </ul>
    {result.passed ? <p className="feedback pass"><Icon name="circle-check"/>All checks passed</p>
      : result.review && <p className="meta">This check has no stored answer to compare with. If the output matches what the assignment asked for, mark the lesson complete.</p>}
  </>;
}

export default function Sandbox({lesson: l}) {
  const [generation, setGeneration] = useState(0);  // bumping it reconnects the terminal to a fresh sandbox
  const [result, setResult] = useState(null);
  const [checking, setChecking] = useState(false);
  const reset = async () => {
    if (!confirm('Reset the sandbox? Files you changed in it are lost.')) return;
    await post('/api/sandbox/reset', {uuid:l.uuid});
    setResult(null);
    setGeneration(g => g + 1);
  };
  const submit = async () => {
    setChecking(true);
    try {
      const r = await post('/api/sandbox/check', {uuid:l.uuid});
      setResult(r);
      if (r.passed) markDone(l.uuid);
    } catch {
      setResult({error:'Local server not reachable.'});
    }
    setChecking(false);
  };
  return (
    <section id="work" aria-label="Workspace">
      <div className="term-head">
        <h2 className="pane-title"><Icon name="terminal"/>Linux sandbox</h2>
        {l.sandbox === 'approximate' && (
          <span className="chip info" title="This lesson's exact files weren't available, so the sandbox has every Learn Linux file instead.">
            <Icon name="info"/>Approximate files
          </span>
        )}
        <button className="btn ghost" title="Throw this sandbox away and start fresh" onClick={reset}><Icon name="rotate-ccw"/>Reset</button>
      </div>
      <TermView key={generation} url={`/api/term?kind=sandbox&uuid=${l.uuid}&g=${generation}`} label="Linux sandbox terminal"/>
      <section className="sandbox-checks" aria-label="Lesson checks">
        {!result?.results && <ul className="expects">{(l.steps[0]?.expects || []).map((c, i) => <li key={i}>{c}</li>)}</ul>}
        <div aria-live="polite">{result && <CheckResults result={result}/>}</div>
        <div className="actions">
          <button className="btn primary" disabled={checking} onClick={submit}><Icon name="send"/>Submit</button>
          <DoneButton lesson={l}/>
        </div>
      </section>
    </section>
  );
}
