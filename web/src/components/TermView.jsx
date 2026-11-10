/* A browser terminal (xterm.js) on the server's /api/term WebSocket. xterm is its own chunk, loaded on first use. */
import {useEffect, useRef} from 'react';
import {t} from '../lib/i18n.js';
import {settings} from '../store.js';

let xtermModules;
const loadXterm = () => xtermModules ??= Promise.all([
  import('@xterm/xterm'), import('@xterm/addon-fit'), import('@xterm/addon-webgl'), import('@xterm/xterm/css/xterm.css'),
  document.fonts.load('14px "JetBrains Mono"'),
]);

// Same muted palette as the code editor (styles.css).
const THEME = {background:'#0B0D11', foreground:'#D4D7DC', cursor:'#E9EBEE', cursorAccent:'#0B0D11', selectionBackground:'#2E3A52',
               black:'#262C36', brightBlack:'#737C89', red:'#E39B9B', brightRed:'#F0B0AA', green:'#8FBF8A', brightGreen:'#A9C99A',
               yellow:'#D9B27C', brightYellow:'#E6C590', blue:'#8FAEE0', brightBlue:'#A9C2EC', magenta:'#C3A9E0', brightMagenta:'#D3BDEB',
               cyan:'#8CC2C2', brightCyan:'#A6D3D3', white:'#D4D4D8', brightWhite:'#ECECEE'};

export default function TermView({url, className = '', label}) {
  const host = useRef();
  useEffect(() => {
    let closed = false, cleanup = () => {};
    loadXterm().then(([{Terminal}, {FitAddon}, {WebglAddon}]) => {
      if (closed) return;
      const term = new Terminal({fontFamily:'"JetBrains Mono", monospace', fontSize:settings().codeSize, lineHeight:1.15, cursorBlink:true, scrollback:5000, theme:THEME});
      const fit = new FitAddon();
      term.loadAddon(fit);
      term.open(host.current);
      try { term.loadAddon(new WebglAddon()); } catch {}  // GPU text rendering when available
      const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}${url}`);
      ws.binaryType = 'arraybuffer';
      const send = (kind, data) => ws.readyState === WebSocket.OPEN && ws.send(kind + data);
      let raf;
      const resize = () => {
        cancelAnimationFrame(raf);
        raf = requestAnimationFrame(() => {
          if (!host.current?.offsetWidth) return;
          fit.fit();
          send('1', JSON.stringify({cols:term.cols, rows:term.rows}));
        });
      };
      ws.onopen = () => { resize(); term.focus(); };
      ws.onmessage = e => term.write(new Uint8Array(e.data));
      ws.onclose = () => term.write('\r\n\x1b[90m' + t('[connection closed]') + '\x1b[0m\r\n');
      term.onData(d => send('0', d));
      const ro = new ResizeObserver(resize);
      ro.observe(host.current);
      fit.fit();
      cleanup = () => { ro.disconnect(); ws.onclose = null; ws.close(); term.dispose(); };
    });
    return () => { closed = true; cleanup(); };
  }, [url]);
  return <div className={'term-host ' + className} ref={host} aria-label={label}></div>;
}
