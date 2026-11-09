import {useEffect, useState} from 'react';
import {ACCENTS, applySettings, profile, save, settings, store, toast, useStore} from '../store.js';
import {Avatar, Topbar} from './Account.jsx';
import {Icon} from './ui.jsx';

const FIELDS = [
  ['name', 'Display name', 'How your name shows on your profile', 60],
  ['handle', 'Username', 'Shown as @username', 30],
  ['location', 'Location', 'Anything you like, e.g. a city', 60],
  ['website', 'Website', 'example.com', 120],
  ['github', 'GitHub username', 'Links your GitHub profile', 39],
];
const ZONES = Intl.supportedValuesOf?.('timeZone') || [];

const Section = ({title, desc, children}) => (
  <section className="card settings-section">
    <div className="settings-head"><h2>{title}</h2>{desc && <p className="meta">{desc}</p>}</div>
    <div className="settings-body">{children}</div>
  </section>
);

function ProfileForm() {
  const [form, setForm] = useState(() => ({name:'', handle:'', location:'', website:'', github:'', bio:'', ...profile()}));
  const set = k => e => setForm({...form, [k]:e.target.value});
  const submit = e => {
    e.preventDefault();
    const clean = Object.fromEntries(Object.entries(form).map(([k, v]) => [k, v.trim()]));
    clean.github = clean.github.replace(/^@|^https?:\/\/github\.com\//i, '').replace(/\/.*/, '');
    clean.handle = clean.handle.replace(/^@/, '');
    setForm(clean);
    save('app:profile', clean).then(() => toast({kind:'note', text:'Profile saved'}));
  };
  return (
    <form onSubmit={submit} className="fields">
      {FIELDS.map(([k, label, hint, max]) => (
        <label key={k} className="field"><span>{label}</span>
          <input value={form[k]} onChange={set(k)} maxLength={max} placeholder={hint} autoComplete="off"/>
        </label>
      ))}
      <label className="field wide"><span>Bio</span>
        <textarea value={form.bio} onChange={set('bio')} maxLength={160} rows={3} placeholder="A line or two about you"/>
        <span className="meta">{form.bio.length}/160</span>
      </label>
      <div className="wide"><button className="btn primary">Save profile</button></div>
    </form>
  );
}

export default function Settings() {
  useStore();
  useEffect(() => { document.title = 'Settings · nagare'; }, []);
  const s = settings();
  const set = data => { save('app:settings', data); applySettings(); };
  const download = () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(store.progress, null, 1)], {type:'application/json'}));
    Object.assign(document.createElement('a'), {href:url, download:'nagare-progress.json'}).click();
    URL.revokeObjectURL(url);
  };

  return (
    <main id="home" className="page settings">
      <Topbar/>
      <h1>Settings</h1>

      <Section title="Profile" desc="What shows on your profile page. Fill in three fields for an achievement.">
        <div className="photo-row">
          <Avatar size={56}/>
          <label className="check"><input type="checkbox" checked={s.photo} onChange={e => set({photo:e.target.checked})} disabled={!store.user?.picture}/>
            Use my Google photo</label>
        </div>
        <ProfileForm/>
      </Section>

      <Section title="Appearance">
        <fieldset className="field">
          <legend>Accent color</legend>
          <div className="swatches">
            {Object.entries(ACCENTS).map(([k, hex]) => (
              <label key={k} className="swatch" style={{'--c':hex}} title={k}>
                <input type="radio" name="accent" checked={s.accent === k} onChange={() => set({accent:k})}/>
                <span className="sr">{k}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <label className="field"><span>Code font size</span>
          <select value={s.codeSize} onChange={e => set({codeSize:+e.target.value})}>
            {[12, 13, 14, 15, 16, 18].map(n => <option key={n} value={n}>{n}px{n === 14 ? ' (default)' : ''}</option>)}
          </select>
        </label>
      </Section>

      <Section title="Notifications">
        <label className="check"><input type="checkbox" checked={s.toasts} onChange={e => set({toasts:e.target.checked})}/>
          Show XP, level-up and achievement pop-ups</label>
      </Section>

      <Section title="Leaderboard" desc="Your name, photo, level and XP. Never your email.">
        <label className="check"><input type="checkbox" checked={s.leaderboard} onChange={e => set({leaderboard:e.target.checked})}/>
          Show me on the leaderboard</label>
      </Section>

      <Section title="Time zone" desc="Decides when your day starts, for streaks and the activity graph.">
        <label className="field"><span>Time zone</span>
          <select value={s.tz || ''} onChange={e => set({tz:e.target.value})}>
            {ZONES.map(z => <option key={z}>{z}</option>)}
          </select>
        </label>
      </Section>

      <Section title="Your data" desc="Everything saved for you: progress, code, profile, settings and XP.">
        <button className="btn" onClick={download}><Icon name="download"/>Download as JSON</button>
      </Section>
    </main>
  );
}
