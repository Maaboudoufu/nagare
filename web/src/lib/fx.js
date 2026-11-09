/* Feedback for results: short synthesized sounds (Web Audio, no files) and brief screen effects.
   Both can be turned off in Settings; effects also stay off with the OS "reduce motion" setting. */
import {settings} from '../store.js';

let ctx, master;
function audio() {
  if (!settings().sound) return false;
  ctx ??= new AudioContext();
  if (ctx.state === 'suspended') ctx.resume();
  if (!master) (master = ctx.createGain()).connect(ctx.destination);
  master.gain.value = settings().volume / 100 * .6;
  return true;
}

// One bell-like note: a sine with a quiet octave above it, fast attack, exponential decay.
function note(freq, at, {dur = .5, gain = .25, type = 'sine', octave = .15, lowpass} = {}) {
  const t = ctx.currentTime + at, env = ctx.createGain();
  env.gain.setValueAtTime(.0001, t);
  env.gain.exponentialRampToValueAtTime(gain, t + .008);
  env.gain.exponentialRampToValueAtTime(.0001, t + dur);
  if (lowpass) {
    const f = ctx.createBiquadFilter();
    f.type = 'lowpass';
    f.frequency.value = lowpass;
    env.connect(f).connect(master);
  } else env.connect(master);
  for (const [mult, amp] of [[1, 1], [2, octave]]) {
    if (!amp) continue;
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = type;
    o.frequency.value = freq * mult;
    g.gain.value = amp;
    o.connect(g).connect(env);
    o.start(t);
    o.stop(t + dur + .05);
  }
}

const SOUNDS = {
  pass: () => { note(659.25, 0, {dur:.4}); note(987.77, .085, {dur:.7}); },           // E5 then B5: a rising fifth
  correct: () => note(880, 0, {dur:.35, gain:.16}),                                   // one soft A5
  fail: () => { note(196, 0, {dur:.2, type:'triangle', gain:.3, octave:0, lowpass:700});  // two low, muted steps down
                note(174.61, .1, {dur:.28, type:'triangle', gain:.26, octave:0, lowpass:600}); },
  level: () => [523.25, 659.25, 783.99, 1046.5].forEach((f, i) => note(f, i * .075, {dur:.9, gain:.15})),  // C major, upward
  achievement: () => [783.99, 1174.66, 1567.98].forEach((f, i) => note(f, i * .1, {dur:1.2, gain:.12, octave:.3})),
};
export function sound(name) {
  try { if (audio()) SOUNDS[name](); } catch { /* no audio device: stay quiet */ }
}

const calm = () => !settings().effects || matchMedia('(prefers-reduced-motion: reduce)').matches;
// Web Animations, not CSS classes: React re-rendering the element can't cut them short.
const MOTION = {
  pop: [[{transform:'scale(.96)'}, {transform:'scale(1.04)', offset:.45}, {transform:'scale(1)'}], {duration:450, easing:'cubic-bezier(.2,.8,.2,1)'}],
  shake: [[{transform:'none'}, {transform:'translateX(-4px)'}, {transform:'translateX(4px)'}, {transform:'translateX(-2px)'},
           {transform:'translateX(2px)'}, {transform:'none'}], {duration:320, easing:'ease-in-out'}],
  glow: [[{opacity:0}, {opacity:1, offset:.15}, {opacity:0}], {duration:1000, easing:'ease-out'}],
};
const animate = (el, name) => el && !calm() && el.animate(...MOTION[name]);
let edge;
function glow(color) {  // a soft glow around the edges of the window
  edge ??= document.body.appendChild(Object.assign(document.createElement('div'), {className:'fx-edge', ariaHidden:'true'}));
  edge.style.setProperty('--fx', color);
  animate(edge, 'glow');
}

export const fx = {
  pass(el) { sound('pass'); animate(el, 'pop'); glow('var(--success)'); },
  correct(el) { sound('correct'); animate(el, 'pop'); },
  fail(el) { sound('fail'); animate(el, 'shake'); },
  level() { setTimeout(() => { sound('level'); glow('var(--accent)'); }, 350); },
  achievement() { setTimeout(() => sound('achievement'), 700); },
};
