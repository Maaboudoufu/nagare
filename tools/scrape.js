async () => {
  // Template: make_batches.py replaces BATCH with course UUIDs. Needs window.__auth (see make_batches.py).
  // Returns each course with every lesson's static data plus your progress on it.
  const BATCH = __BATCH__;
  const H = {headers: {authorization: window.__auth}};
  const get = async (url) => {
    for (let i = 0; i < 5; i++) {
      const r = await fetch(url, H);
      if (r.ok) return r.json();
      if (r.status !== 429 && r.status < 500) return {error: r.status};
      await new Promise(res => setTimeout(res, 2000 * (i + 1)));
    }
    return {error: 'retries'};
  };
  const out = [];
  for (const id of BATCH) {
    const c = await get("https://api.boot.dev/v1/courses/" + id);
    const prog = await get("https://api.boot.dev/v1/course_progress_by_lesson/" + c.firstLessonUUID);
    const chapters = [];
    for (const ch of prog.chapters) {
      const lessons = await Promise.all(ch.lessons.map(async l => {
        const [s, u] = await Promise.all([
          get("https://api.boot.dev/v1/static/lessons/" + l.uuid),
          get("https://api.boot.dev/v1/users/lessons/" + l.uuid),
        ]);
        const lesson = s.lesson || {uuid: l.uuid, title: l.title, error: s.error};
        lesson.user = u;
        lesson.isComplete = l.isComplete;
        return lesson;
      }));
      chapters.push({title: ch.title, lessons});
    }
    out.push({uuid: c.uuid, slug: c.slug, title: c.title, language: c.language,
              description: c.shortDescription, chapters});
  }
  return out;
}
