async () => {
  // Template: make_batches.py replaces LESSONS with [{uuid, title, h1, refs: [{ref, alt}]}] (h1 = lowercase alphanumerics).
  // Walks boot.dev's own router through each lesson and saves the Excalidraw diagrams as boot.dev renders them (SVG).
  const LESSONS = __LESSONS__;
  const router = document.querySelector('#__nuxt').__vue_app__.config.globalProperties.$router;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const norm = s => (s || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  const out = [];
  for (const l of LESSONS) {
    await router.push('/lessons/' + l.uuid);
    let svgs = [], ok = false;
    for (let t = 0; t < 60; t++) {  // up to ~15s for this lesson (not the previous one) and its diagrams to render
      await wait(250);
      const content = document.querySelector('.comark-content');
      if (norm(content?.querySelector('h1')?.textContent) !== l.h1) continue;
      const imgs = [...content.querySelectorAll('img')].filter(i => i.src.startsWith('data:image/svg+xml') && i.src.includes('excalidraw'));
      const used = new Set();
      svgs = l.refs.map(r => {
        const img = imgs.find(i => !used.has(i) && i.alt === r.alt);
        if (img) used.add(img);
        return {ref: r.ref, svg: img ? decodeURIComponent(img.src.replace(/^data:image\/svg\+xml(;charset=utf-8)?,/, '')) : null};
      });
      if (svgs.every(s => s.svg)) { ok = true; break; }
    }
    out.push({uuid: l.uuid, title: l.title, ok, svgs});
  }
  return out;
}
