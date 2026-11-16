/* CodeMirror 5 with the language modes and addons the lessons use. Its CSS is loaded in main.jsx; the fold gutter and
   the suggestion list are styled in styles.css. */
import CodeMirror from 'codemirror';
import 'codemirror/addon/runmode/runmode';
import 'codemirror/addon/edit/matchbrackets';
import 'codemirror/addon/edit/closebrackets';
import 'codemirror/addon/comment/comment';
import 'codemirror/addon/selection/active-line';
import 'codemirror/addon/search/searchcursor';
import 'codemirror/addon/search/search';  // find and replace, in the dialog below
import 'codemirror/addon/search/jump-to-line';
import 'codemirror/addon/search/match-highlighter';
import 'codemirror/addon/dialog/dialog';
import 'codemirror/addon/fold/foldcode';
import 'codemirror/addon/fold/foldgutter';
import 'codemirror/addon/fold/brace-fold';
import 'codemirror/addon/fold/indent-fold';
import 'codemirror/addon/fold/comment-fold';
import 'codemirror/addon/hint/show-hint';
import 'codemirror/addon/hint/anyword-hint';
import 'codemirror/keymap/sublime';  // multiple cursors, move / duplicate / delete line, and the rest of Sublime's keys
import 'codemirror/keymap/vim';
import 'codemirror/mode/go/go';
import 'codemirror/mode/python/python';
import 'codemirror/mode/sql/sql';
import 'codemirror/mode/shell/shell';
import 'codemirror/mode/javascript/javascript';
import 'codemirror/mode/yaml/yaml';
import 'codemirror/mode/clike/clike';

/* Completions: the words already in the file, then the language's keywords. Python and C list theirs in the mode;
   Go and JavaScript / TypeScript get a list here. */
const words = (mode, list) => CodeMirror.registerHelper('hintWords', mode, list.split(' '));
words('go', 'break case chan const continue default defer else fallthrough for func go goto if import interface map package range return '
  + 'select struct switch type var append cap close copy delete len make new panic print println recover '
  + 'bool byte error float32 float64 int int32 int64 rune string uint uint8 uint32 uint64 true false nil iota');
words('javascript', 'async await break case catch class const continue default delete else export extends finally for function if import '
  + 'instanceof let new return static super switch this throw try typeof var void while yield true false null undefined '
  + 'interface type enum implements readonly private public protected number string boolean console');

function hint(cm) {
  const r = CodeMirror.hint.anyword(cm), prefix = cm.getRange(r.from, r.to);
  const keywords = (cm.getHelper(r.from, 'hintWords') || []).filter(w => w.startsWith(prefix) && !r.list.includes(w));
  return {...r, list:[...r.list, ...keywords].filter(w => w !== prefix)};
}
/* Tab always takes the suggestion. Enter does too in the list you asked for (Ctrl+Space); in the one that opens as you
   type, Enter is still a new line, so a short name at the end of a line never turns into a longer one.
   Esc closes the list and still reaches the keymap, so Vim leaves insert mode on the first press. */
const dismiss = (cm, list) => { list.close(); return CodeMirror.Pass; };
const complete = (cm, typed) => cm.showHint({hint, completeSingle:false, extraKeys:{Esc:dismiss, ...(typed && {Enter:dismiss})}});
CodeMirror.commands.autocomplete = cm => complete(cm);

// The `suggest` option opens the list as you type: from the second letter of a word, and not in comments or strings.
function onType(cm, change) {
  const cur = cm.getCursor();
  if (change.origin === '+input' && !cm.state.completionActive && /[\w$]{2}$/.test(cm.getLine(cur.line).slice(0, cur.ch))
      && !/comment|string/.test(cm.getTokenTypeAt(cur))) complete(cm, true);
}
CodeMirror.defineOption('suggest', false, (cm, on, old) => {
  if (old === true) cm.off('inputRead', onType);
  if (on) cm.on('inputRead', onType);
});

export default CodeMirror;
