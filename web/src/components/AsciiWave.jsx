/* The wave behind the home page's header, as live ASCII: a hidden <video> is sampled into a grid every frame and each
   cell drawn as a character from a density ramp. Same-origin video (self-hosted), so the pixels are readable.
   Runs only while on screen and the tab is visible; under reduced motion it draws one still frame. */
import {useEffect, useRef} from 'react';
import waveVideo from '../assets/wave.mp4';

const RAMP = ' .:-=+*#%@';
const CELL_W = 7, CELL_H = 12;  // a monospace glyph is ~0.6 as wide as it is tall

export default function AsciiWave({className = ''}) {
  const ref = useRef(null);

  useEffect(() => {
    const canvas = ref.current, ctx = canvas.getContext('2d');
    const sample = document.createElement('canvas').getContext('2d', {willReadFrequently:true});
    const video = Object.assign(document.createElement('video'), {src:waveVideo, muted:true, loop:true, playsInline:true});
    const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const ink = getComputedStyle(canvas).color;
    const mono = getComputedStyle(document.documentElement).getPropertyValue('--mono') || 'monospace';
    let w = 0, h = 0, cols = 0, rows = 0, raf = 0, visible = false, lastFrame = -1;

    const resize = () => {
      const dpr = Math.min(devicePixelRatio || 1, 2);
      ({width:w, height:h} = canvas.getBoundingClientRect());
      canvas.width = Math.max(1, Math.round(w * dpr));
      canvas.height = Math.max(1, Math.round(h * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.font = `${CELL_H * 0.9}px ${mono}`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      cols = Math.max(1, Math.ceil(w / CELL_W));
      rows = Math.max(1, Math.ceil(h / CELL_H));
      sample.canvas.width = cols;
      sample.canvas.height = rows;
      lastFrame = -1;
    };

    const draw = () => {
      const vw = video.videoWidth, vh = video.videoHeight;
      if (!vw) return;
      // Cover: crop the video to the grid's shape, then shrink it to one pixel per cell.
      const want = (cols * CELL_W) / (rows * CELL_H);
      let sw = vw, sh = vh;
      if (vw / vh > want) sw = vh * want; else sh = vw / want;
      sample.drawImage(video, (vw - sw) / 2, (vh - sh) / 2, sw, sh, 0, 0, cols, rows);
      const px = sample.getImageData(0, 0, cols, rows).data;
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = ink;
      for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) {
        const i = (y * cols + x) * 4;
        const lum = Math.min(1, Math.max(0, (px[i] * .2126 + px[i + 1] * .7152 + px[i + 2] * .0722) / 255 - .03) / .75) ** .6;  // lifted: the dark water still shows
        const ch = RAMP[Math.round(lum * (RAMP.length - 1))];
        if (ch === ' ') continue;
        ctx.globalAlpha = .25 + lum * .75;
        ctx.fillText(ch, x * CELL_W + CELL_W / 2, y * CELL_H + CELL_H / 2);
      }
      ctx.globalAlpha = 1;
    };

    // Redraw only when the video has moved on to a new frame.
    const loop = () => {
      if (video.currentTime !== lastFrame) { lastFrame = video.currentTime; draw(); }
      raf = requestAnimationFrame(loop);
    };
    const run = () => {
      cancelAnimationFrame(raf);
      if (reduced || !visible || document.hidden) { video.pause(); return; }
      video.play().catch(() => {});
      raf = requestAnimationFrame(loop);
    };

    resize();
    video.addEventListener('loadeddata', () => { if (reduced) video.currentTime = 1.2; draw(); }, {once:true});
    video.addEventListener('seeked', draw);
    const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; run(); });
    io.observe(canvas);
    const ro = new ResizeObserver(() => { resize(); draw(); });
    ro.observe(canvas);
    document.addEventListener('visibilitychange', run);
    return () => {
      cancelAnimationFrame(raf);
      io.disconnect();
      ro.disconnect();
      document.removeEventListener('visibilitychange', run);
      video.pause();
      video.removeAttribute('src');
      video.load();
    };
  }, []);

  return <canvas ref={ref} aria-hidden="true" className={className}/>;
}
