/* Code lessons: CodeMirror editor, Run / Submit against the local runners, optional Vim keys. */
import {useEffect, useMemo, useRef, useState} from 'react';
import {MODES} from '../../constants.js';
import CodeMirror from '../../lib/codemirror.js';
import {markDone, post, save, store, useStore} from '../../store.js';
import {Chip, DoneButton, Icon} from '../ui.jsx';

function Output({lesson: l, out, sql}) {
  if (out) return <>
    {out.diff && <><span className="exp">Expected:</span>{'\n' + (l.expected || '') + '\n'}<span className="exp">Got:</span>{'\n'}</>}
    {out.text}
  </>;
  if (l.expected != null) return <><span className="exp">Expected output:</span>{'\n' + l.expected}</>;
  if (sql) return <span className="exp">SQL lessons have no stored solution to grade against. Run to see your results, then mark the lesson complete.</span>;
  return <span className="exp">Run to see test output.</span>;
}

export default function CodeWorkspace({lesson: l}) {
  useStore();
  const files = useMemo(() => l.files.filter(f => !f.isHidden), [l]);
  const sql = l.lang === 'sql', tabs = l.lang === 'go';
  const [active, setActive] = useState(() => (files.find(f => !f.isReadonly) || files[0]).name);
  const [status, setStatus] = useState(null);
  const [out, setOut] = useState(null);  // null: show the intro text
  const [busy, setBusy] = useState(false);
  const [vimMode, setVimMode] = useState('');
  const host = useRef(), ed = useRef(), docs = useRef(), goRef = useRef();
  const vim = !!store.progress['app:settings']?.vim;
  const code = () => Object.fromEntries(files.filter(f => !f.isReadonly).map(f => [f.name, docs.current[f.name].getValue()]));

  const go = async submit => {
    if (busy) return;
    setBusy(true);
    setStatus({kind:'busy', text:submit ? 'Submitting…' : 'Running…', icon:'loader-circle'});
    try {
      const r = await post('/api/run', {uuid:l.uuid, code:code(), submit});
      setOut({text:r.output || r.error || '(no output)', diff:submit && !r.passed && l.type === 'type_code'});
      if (!submit) setStatus(r.ok === false ? {kind:'fail', text:'Errors or failing tests', icon:'circle-x'} : {kind:'info', text:'Finished', icon:'check'});
      else if (r.passed) { setStatus({kind:'pass', text:'Passed', icon:'circle-check'}); markDone(l.uuid); }
      else setStatus({kind:'fail', text:'Failed', icon:'circle-x'});
    } catch {
      setStatus({kind:'fail', text:'Local server not reachable', icon:'circle-x'});
    }
    setBusy(false);
  };
  goRef.current = go;

  useEffect(() => {  // CodeMirror lives outside React: create it once per lesson
    const saved = store.progress[l.uuid]?.code || {};
    docs.current = Object.fromEntries(files.map(f => [f.name, CodeMirror.Doc(saved[f.name] ?? f.content, MODES[l.lang])]));
    const submitKey = () => goRef.current(!sql);
    const cm = ed.current = CodeMirror(host.current, {
      theme:'material-darker', lineNumbers:true, indentUnit:{py:4, go:4, c:4}[l.lang] || 2, tabSize:4, indentWithTabs:tabs,
      matchBrackets:true, keyMap:vim ? 'vim' : 'default', showCursorWhenSelecting:true,
      extraKeys:{Tab:c => c.state.vim && !c.state.vim.insertMode ? CodeMirror.Pass  // Vim normal mode keeps its own Tab
                         : c.execCommand(tabs ? 'insertTab' : 'insertSoftTab'),
                 'Ctrl-Enter':() => goRef.current(false), 'Cmd-Enter':() => goRef.current(false),
                 'Shift-Ctrl-Enter':submitKey, 'Shift-Cmd-Enter':submitKey},
    });
    cm.on('vim-mode-change', e => setVimMode(`-- ${e.mode.toUpperCase()}${e.subMode ? ' ' + e.subMode.toUpperCase() : ''} --`));
    let t;
    cm.on('change', () => { clearTimeout(t); t = setTimeout(() => save(l.uuid, {code:code()}), 600); });
    const el = host.current;
    return () => { clearTimeout(t); el.innerHTML = ''; };
  }, [l.uuid]);

  useEffect(() => {
    const file = files.find(f => f.name === active);
    ed.current.swapDoc(docs.current[active]);
    ed.current.setOption('readOnly', file.isReadonly);
    ed.current.getInputField().setAttribute('aria-label', `Code editor: ${active}`);
  }, [active, l.uuid]);

  useEffect(() => {
    ed.current.setOption('keyMap', vim ? 'vim' : 'default');
    setVimMode(vim ? '-- NORMAL --' : '');
  }, [vim]);

  const onTabKey = (e, i) => {  // arrow keys move between file tabs
    const d = {ArrowRight:1, ArrowLeft:-1}[e.key];
    if (!d) return;
    const j = (i + d + files.length) % files.length;
    setActive(files[j].name);
    e.currentTarget.parentElement.children[j].focus();
  };
  const reset = () => {
    if (!confirm('Reset this lesson to the starter code? Your changes will be lost.')) return;
    files.forEach(f => docs.current[f.name].setValue(f.content));
  };

  return (
    <section id="work" aria-label="Workspace">
      <div className="work-head" role="tablist" aria-label="Files">
        {files.map((f, i) => (
          <button key={f.name} className="tab" role="tab" aria-controls="ed" aria-selected={f.name === active} tabIndex={f.name === active ? 0 : -1}
                  onClick={() => setActive(f.name)} onKeyDown={e => onTabKey(e, i)}>
            <Icon name={f.isReadonly ? 'lock' : 'code-xml'}/>{f.name}{f.isReadonly && <span className="sr"> (read-only)</span>}
          </button>
        ))}
      </div>
      <div id="ed" role="tabpanel" ref={host}></div>
      <div className="toolbar">
        <button className="btn" disabled={busy} title="Run (Ctrl+Enter)" onClick={() => go(false)}><Icon name="play"/>Run</button>
        {sql ? <DoneButton lesson={l}/>
             : <button className="btn primary" disabled={busy} title="Submit (Ctrl+Shift+Enter)" onClick={() => go(true)}><Icon name="send"/>Submit</button>}
        <span className="kbd-hint"><kbd>Ctrl</kbd> <kbd>Enter</kbd> run{!sql && <> · <kbd>Shift</kbd> to submit</>}</span>
        <span className="vim-mode" aria-live="polite">{vimMode}</span>
        <button className="switch" role="switch" aria-checked={vim} title="Vim key bindings"
                onClick={() => { save('app:settings', {vim:!vim}); ed.current.focus(); }}><span className="knob"></span>Vim</button>
        <button className="btn ghost" onClick={reset}><Icon name="rotate-ccw"/>Reset</button>
      </div>
      <section className="output" aria-label="Output">
        <div className="output-head"><span>Output</span><span role="status" aria-live="polite">{status && <Chip {...status}/>}</span></div>
        <pre id="out"><Output lesson={l} out={out} sql={sql}/></pre>
      </section>
    </section>
  );
}
