/* Small shared pieces: icons, logos, progress meters, buttons. */
import {useId, useState} from 'react';
import {brandOf} from '../constants.js';
import {isDone, markDone, pct, useStore} from '../store.js';

/* nagare (流れ, "flow"): three loose, wavy strands (the noise) narrow into one straight stream that goes where it's
   pointed. Dim on the left, clear on the right. */
const STRANDS = ['M3 4C6 1 8 7 11 5S16 8 20 8H31', 'M3 12C6 9 8 15 11 12S16 12 20 12H31', 'M3 20C6 17 8 23 11 19S16 16 20 16H31'];

export function BrandMark({className = 'brand-mark'}) {
  const id = 'flow' + useId().replace(/\W/g, '');  // unique per mark on the page, and safe inside url(#...)
  return (
    <svg className={className} viewBox="0 0 34 24" aria-hidden="true">
      <defs>
        <linearGradient id={id} gradientUnits="userSpaceOnUse" x1="3" y1="0" x2="31" y2="0">
          <stop offset="0" stopColor="#74747E" stopOpacity=".55"/>
          <stop offset=".55" stopColor="#A9C2EC"/>
          <stop offset="1" stopColor="#7AA7FF"/>
        </linearGradient>
      </defs>
      <g fill="none" stroke={`url(#${id})`} strokeWidth="2" strokeLinecap="round">
        {STRANDS.map(d => <path key={d} d={d}/>)}
      </g>
    </svg>
  );
}

export const Brand = () => <a className="brand" href="/" aria-label="nagare, home"><BrandMark/><span aria-hidden="true">nagare</span></a>;

export const Icon = ({name, cls = ''}) => <svg className={'icon ' + cls} aria-hidden="true"><use href={`/vendor/icons.svg?v=4#${name}`}/></svg>;

export const Meter = ({n, total, label, hidden}) => (
  <div className="meter" role={hidden ? undefined : 'progressbar'} aria-hidden={hidden ? 'true' : undefined} aria-label={label}
       aria-valuemin="0" aria-valuemax={total} aria-valuenow={n}><div style={{width:`${pct(n, total)}%`}}></div></div>
);

export function Logo({course, size = 'md'}) {
  const [sym, hex, name, lucide, img] = brandOf(course);
  const n = parseInt(hex.slice(1), 16), lum = (0.299 * (n >> 16) + 0.587 * (n >> 8 & 255) + 0.114 * (n & 255)) / 255;
  return (
    <span className={`logo logo-${size}`} style={{background:hex, color:lum > 0.6 ? '#131315' : '#FFFFFF'}} title={name}>
      {img ? <img className="brand-img" src={img} alt="" aria-hidden="true"/>
           : <svg className={lucide ? 'icon' : 'brand'} aria-hidden="true"><use href={`/vendor/${lucide ? 'icons' : 'brands'}.svg?v=4#${sym}`}/></svg>}
      <span className="sr">{name}</span>
    </span>
  );
}

export function DoneButton({lesson}) {
  useStore();
  const done = isDone(lesson.uuid);
  return (
    <button className={'btn' + (done ? ' is-done' : '')} aria-pressed={done} onClick={() => markDone(lesson.uuid)}>
      <Icon name={done ? 'circle-check' : 'check'}/>{done ? 'Completed' : 'Mark complete'}
    </button>
  );
}

export function CopyButton({text}) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <button className={'icon-btn copy' + (copied ? ' copied' : '')} aria-label={copied ? 'Copied' : 'Copy code'} onClick={copy}>
      <Icon name={copied ? 'check' : 'copy'}/>
    </button>
  );
}

export const Chip = ({kind, text, icon}) => <span className={'chip ' + kind}><Icon name={icon} cls={kind === 'busy' ? 'spin' : ''}/>{text}</span>;
