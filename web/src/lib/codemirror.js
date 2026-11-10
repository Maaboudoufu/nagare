/* CodeMirror 5 with the language modes and addons the lessons use. Its CSS is loaded in main.jsx. */
import CodeMirror from 'codemirror';
import 'codemirror/addon/runmode/runmode';
import 'codemirror/addon/edit/matchbrackets';
import 'codemirror/addon/search/searchcursor';
import 'codemirror/addon/dialog/dialog';
import 'codemirror/keymap/vim';
import 'codemirror/mode/go/go';
import 'codemirror/mode/python/python';
import 'codemirror/mode/sql/sql';
import 'codemirror/mode/shell/shell';
import 'codemirror/mode/javascript/javascript';
import 'codemirror/mode/yaml/yaml';
import 'codemirror/mode/clike/clike';

export default CodeMirror;
