/* CLI / shell / GitHub lessons: the steps to run, local grading (CLI), and a terminal in your project folder. */
import {useRef, useState} from 'react';
import {STEP_TITLES} from '../../constants.js';
import {markDone, post, save, store, useStore} from '../../store.js';
import TermView from '../TermView.jsx';
import {CopyButton, DoneButton, Icon} from '../ui.jsx';

function StepResult({res}) {
  if (!res) return <span className="skipped">Skipped: an earlier step failed.</span>;
  const ok = !res.failures.length;
  return <>
    {!ok && <ul className="fail-list">{res.failures.map((f, j) => <li key={j}><Icon name="circle-x"/><span>{f}</span></li>)}</ul>}
    <details open={!ok}><summary>Output</summary><pre>{res.output}</pre></details>
  </>;
}

export default function StepsWorkspace({lesson: l, courseSlug}) {
  useStore();
  const cli = l.type === 'type_cli', key = 'course:' + courseSlug;
  // AWS lessons talk to an AWS emulator in the workspace (started on demand); their checks don't use a project folder.
  const aws = courseSlug === 'learn-aws';
  const [dir, setDir] = useState(store.progress[key]?.dir || '');
  const [base, setBase] = useState(store.progress[l.uuid]?.baseURL ?? (l.baseURL === 'override' ? '' : l.baseURL || ''));
  const [error, setError] = useState('');
  const [results, setResults] = useState(null);
  const [running, setRunning] = useState(false);
  const folder = dir.trim() || '~';  // empty = your home folder
  const [termDir, setTermDir] = useState(cli ? folder : null);  // CLI lessons open a terminal right away
  const [termGen, setTermGen] = useState(0);  // Restart terminal remounts it
  const dirInput = useRef();
  const [ic, title] = STEP_TITLES[l.type];

  const runChecks = async () => {
    setRunning(true);
    setError('');
    setResults(null);
    try {
      const r = await post('/api/cli', {uuid:l.uuid, dir:folder, baseURL:base.trim(), aws});
      if (r.error) { setError(r.error); dirInput.current?.focus(); }
      else { setResults(r.results); if (r.passed) markDone(l.uuid); }
    } catch {
      setError('Local server not reachable.');
    }
    setRunning(false);
  };
  const restartTerminal = () => {  // also moves it to a newly typed folder
    save(key, {dir:dir.trim()});
    setError('');
    setTermDir(folder);
    setTermGen(g => g + 1);
  };

  return (
    <section id="work" aria-label="Workspace"><div className="pane">
      <h2 className="pane-title"><Icon name={ic}/>{title}</h2>
      {cli && <>
        {!aws && <div className="field">
          <label htmlFor="dir">Project folder</label>
          <input id="dir" ref={dirInput} value={dir} placeholder="~ (your home folder)" spellCheck="false" autoComplete="off"
                 aria-describedby="dir-help dir-err" onChange={e => setDir(e.target.value)} onBlur={() => save(key, {dir:dir.trim()})}/>
          <p className="help" id="dir-help">A folder in your own workspace, where the terminal and the checks run. Your files are kept between visits.</p>
          <p className="field-err" id="dir-err" role="alert">{error}</p>
        </div>}
        {aws && error && <p className="field-err" role="alert">{error}</p>}
        {l.baseURL && (
          <div className="field">
            <label htmlFor="base">Server URL</label>
            <input id="base" value={base} placeholder="https://your-app.example.com" spellCheck="false" autoComplete="off" aria-describedby="base-help"
                   onChange={e => setBase(e.target.value)} onBlur={() => save(l.uuid, {baseURL:base.trim()})}/>
            <p className="help" id="base-help">Where the HTTP checks send their requests.</p>
          </div>
        )}
      </>}
      {termDir && <TermView key={termGen} url={`/api/term?kind=project&dir=${encodeURIComponent(termDir)}${aws ? '&aws=1' : ''}`}
                            className="term-panel" label="Terminal in your workspace"/>}
      <ol className="steps">
        {l.steps.map((s, i) => {
          const res = results?.[i], ok = res && !res.failures.length;
          return (
            <li key={i} className={'step' + (res ? (ok ? ' pass' : ' fail') : '')}>
              <div className="step-head">
                <span className="step-mark">{res ? <><Icon name={ok ? 'check' : 'x'}/><span className="sr">{ok ? 'Passed' : 'Failed'}</span></> : i + 1}</span>
                <span className="step-desc">{s.description || `Step ${i + 1}`}</span>
              </div>
              {s.command && <div className="code-block"><pre>{s.command}</pre><CopyButton text={s.command}/></div>}
              {s.expects.length > 0 && <ul className="expects">{s.expects.map((e, j) => <li key={j}>{e}</li>)}</ul>}
              {results != null && <div className="step-result" aria-live="polite"><StepResult res={res}/></div>}
            </li>
          );
        })}
      </ol>
      <div className="actions">
        {cli && <>
          <button className="btn primary" disabled={running} onClick={runChecks}>
            <Icon name={running ? 'loader-circle' : 'play'} cls={running ? 'spin' : ''}/>{running ? 'Running…' : 'Run checks'}
          </button>
          <button className="btn" onClick={restartTerminal}><Icon name="rotate-ccw"/>Restart terminal</button>
        </>}
        <DoneButton lesson={l}/>
      </div>
    </div></section>
  );
}
