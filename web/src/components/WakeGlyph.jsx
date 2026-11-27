/* WakeGlyph: a full-bleed field of faint monospace characters. The pointer leaves a wake of heat that decays back to
   the static scatter: a fast pass leaves a thin, quick-fading trail, a slow one a fat, lingering blob.
   Ported from a Tailwind/TS component to plain JSX + styles.css (.wake). Reduced motion: one static frame. */
import {useEffect, useRef} from 'react';

const RAMP = ' .:-=+*#%@';

// Seeded PRNG, so the ambient scatter doesn't reshuffle on every resize.
function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export default function WakeGlyph({cellSize = 12, className = ''}) {
  const ref = useRef(null);

  useEffect(() => {
    const canvas = ref.current, ctx = canvas?.getContext('2d');
    if (!ctx) return;
    const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const ink = getComputedStyle(canvas).color;
    const mono = getComputedStyle(document.documentElement).getPropertyValue('--mono') || 'ui-monospace, monospace';
    let w = 0, h = 0, cols = 0, rows = 0, heat, rate, ambient, raf = 0, last = 0, hot = false;
    const pointer = {x:0, y:0, t:0, has:false};

    const resize = () => {
      const dpr = Math.min(devicePixelRatio || 1, 2);
      ({width:w, height:h} = canvas.getBoundingClientRect());
      canvas.width = Math.max(1, Math.round(w * dpr));
      canvas.height = Math.max(1, Math.round(h * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.font = `${cellSize * 0.85}px ${mono}`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      cols = Math.max(1, Math.ceil(w / cellSize));
      rows = Math.max(1, Math.ceil(h / cellSize));
      const n = cols * rows;
      heat = new Float32Array(n);
      rate = new Float32Array(n).fill(1.4);
      ambient = new Float32Array(n);
      const rand = mulberry32(0xa53f9c1 ^ (cols * 71 + rows));
      for (let i = 0; i < n; i++) if (rand() < 0.035) ambient[i] = 0.08 + rand() * 0.14;
    };

    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = ink;
      for (let gy = 0; gy < rows; gy++) for (let gx = 0; gx < cols; gx++) {
        const lum = Math.max(ambient[gy * cols + gx], heat[gy * cols + gx]);
        if (lum <= 0.03) continue;
        const ch = RAMP[Math.min(RAMP.length - 1, Math.floor(lum * (RAMP.length - 1)))];
        if (ch === ' ') continue;
        ctx.globalAlpha = Math.min(1, 0.15 + lum * 0.85);
        ctx.fillText(ch, gx * cellSize + cellSize / 2, gy * cellSize + cellSize / 2);
      }
      ctx.globalAlpha = 1;
    };

    // A soft circular blot of heat around a point, with the decay rate this pass's speed implies.
    const stamp = (px, py, r, decay) => {
      const cx = px / cellSize, cy = py / cellSize;
      for (let gy = Math.max(0, Math.floor(cy - r)); gy <= Math.min(rows - 1, Math.ceil(cy + r)); gy++)
        for (let gx = Math.max(0, Math.floor(cx - r)); gx <= Math.min(cols - 1, Math.ceil(cx + r)); gx++) {
          const d = Math.hypot(gx + 0.5 - cx, gy + 0.5 - cy);
          const i = gy * cols + gx;
          if (d <= r && 1 - d / r > heat[i]) { heat[i] = 1 - d / r; rate[i] = decay; }
        }
      hot = true;
    };

    // On window, not the canvas: the canvas sits behind the page's content and takes no pointer events.
    const onMove = e => {
      const rect = canvas.getBoundingClientRect(), x = e.clientX - rect.left, y = e.clientY - rect.top, now = performance.now();
      if (pointer.has) {
        const dx = x - pointer.x, dy = y - pointer.y, dist = Math.hypot(dx, dy);
        const speed = dist / Math.max(1, now - pointer.t);  // px/ms
        const r = Math.max(0.6, Math.min(2.6, 2.4 / (1 + speed * 1.6)));
        const decay = Math.max(0.8, Math.min(4.5, 1 + speed * 3.2));
        const steps = Math.max(1, Math.ceil(dist / (cellSize * 0.5)));  // no gaps between frames on a fast pass
        for (let s = 1; s <= steps; s++) stamp(pointer.x + dx * s / steps, pointer.y + dy * s / steps, r, decay);
      } else stamp(x, y, 1.4, 1.4);
      Object.assign(pointer, {x, y, t:now, has:true});
    };
    const onLeave = () => { pointer.has = false; };

    // Only redraws while something is still cooling; at rest the frame stays as it is.
    const loop = now => {
      const dt = last ? Math.min(64, now - last) / 1000 : 1 / 60;
      last = now;
      if (hot) {
        hot = false;
        for (let i = 0; i < heat.length; i++) if (heat[i] > 0) { heat[i] = Math.max(0, heat[i] - rate[i] * dt); hot = true; }
        draw();
      }
      raf = requestAnimationFrame(loop);
    };

    resize();
    draw();
    if (!reduced) {
      addEventListener('pointermove', onMove);
      document.documentElement.addEventListener('pointerleave', onLeave);
      raf = requestAnimationFrame(loop);
    }
    let timer;
    const onResize = () => { clearTimeout(timer); timer = setTimeout(() => { resize(); draw(); }, 150); };
    addEventListener('resize', onResize);
    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(timer);
      removeEventListener('resize', onResize);
      removeEventListener('pointermove', onMove);
      document.documentElement.removeEventListener('pointerleave', onLeave);
    };
  }, [cellSize]);

  return <canvas ref={ref} aria-hidden="true" className={`wake ${className}`}/>;
}
