/* Keyboard shortcuts. The open lesson registers what each one does (useShortcut); one listener dispatches.
   Mod+Enter works everywhere, even in the editor and terminal; the single keys only when you aren't typing. */
import {useEffect, useRef} from 'react';
import {store} from '../store.js';

export const MOD = /Mac|iPhone|iPad/.test(navigator.platform) ? '⌘' : 'Ctrl';
const actions = {};
export const runAction = name => actions[name]?.();
export const hasAction = name => !!actions[name];

export function useShortcut(name, fn) {
  const ref = useRef(fn);
  ref.current = fn;
  useEffect(() => {
    if (!fn) return;
    const call = (...a) => ref.current?.(...a);
    actions[name] = call;
    return () => { if (actions[name] === call) delete actions[name]; };
  }, [name, !!fn]);
}

// Lessons call this with whether you just passed; then Mod+Enter (and the Next button) go to the next lesson.
export function useContinue(passed) {
  useShortcut('continue', passed && hasAction('next') ? () => runAction('next') : null);
}

const typing = el => el.closest?.('input, textarea, select, [contenteditable="true"], .CodeMirror, .xterm');

addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && !e.altKey) {
    // After a pass, Mod+Enter moves on: the same keys you just pressed, so it works from the editor or terminal too.
    const run = e.shiftKey ? actions.submit || actions.run : actions.continue || actions.run || actions.submit;
    if (run) { e.preventDefault(); e.stopPropagation(); run(); }  // capture phase: before CodeMirror or xterm sees it
    return;
  }
  const vim = !!store.progress['app:settings']?.vim;
  if (vim && e.ctrlKey && !e.metaKey && !e.altKey && !e.shiftKey && (e.key === 'h' || e.key === 'l')) {
    // Vim mode: Ctrl+H / Ctrl+L jump between the lesson pane and the workspace, even from the editor or terminal.
    const pane = document.getElementById(e.key === 'h' ? 'lesson' : 'work');
    if (!pane) return;
    e.preventDefault(); e.stopPropagation();
    if (e.key === 'l' && actions.focusWork) return actions.focusWork();
    if (!pane.hasAttribute('tabindex')) pane.tabIndex = -1;
    pane.classList.add('pane-active');  // border until focus leaves the pane (styles.css)
    pane.addEventListener('blur', () => pane.classList.remove('pane-active'), {once:true});
    pane.focus();
    return;
  }
  if (e.ctrlKey || e.metaKey || e.altKey || typing(e.target) || e.target.closest?.('dialog')) return;
  if (vim && (e.key === 'j' || e.key === 'k')) {  // scroll the focused pane (the lesson if nothing is focused)
    const pane = e.target.closest?.('#lesson, #work') || document.getElementById('lesson');
    if (pane) { e.preventDefault(); pane.scrollBy({top:e.key === 'j' ? 60 : -60}); }
    return;
  }
  const key = e.key.toLowerCase();
  const act = {'?':actions.help}[e.key]
    || (actions.answer && /^[a-h1-8]$/.test(key) && (() => actions.answer('abcdefgh12345678'.indexOf(key) % 8)));
  if (act) { e.preventDefault(); act(); }
}, true);
