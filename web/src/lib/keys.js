/* Keyboard shortcuts. The open lesson registers what each one does (useShortcut); one listener dispatches.
   Mod+Enter works everywhere, even in the editor and terminal; the single keys only when you aren't typing. */
import {useEffect, useRef} from 'react';

export const MOD = /Mac|iPhone|iPad/.test(navigator.platform) ? '⌘' : 'Ctrl';
const actions = {};

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

const typing = el => el.closest?.('input, textarea, select, [contenteditable="true"], .CodeMirror, .xterm');

addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && !e.altKey) {
    const run = e.shiftKey ? actions.submit || actions.run : actions.run || actions.submit;
    if (run) { e.preventDefault(); e.stopPropagation(); run(); }  // capture phase: before CodeMirror or xterm sees it
    return;
  }
  if (e.ctrlKey || e.metaKey || e.altKey || typing(e.target) || e.target.closest?.('dialog')) return;
  const key = e.key.toLowerCase();
  const act = {']':actions.next, '[':actions.prev, '?':actions.help}[e.key]
    || (actions.answer && /^[a-h1-8]$/.test(key) && (() => actions.answer('abcdefgh12345678'.indexOf(key) % 8)));
  if (act) { e.preventDefault(); act(); }
}, true);
