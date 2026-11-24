import {useEffect, useState} from 'react';
import {ACCENTS, applySettings, get, post, profile, save, settings, store, toast, useFetch, useStore} from '../store.js';
import {sound} from '../lib/fx.js';
import {LANGS, N_, contentPct, lang, setLang, t} from '../lib/i18n.js';
import {Avatar, Page} from './Account.jsx';
import {CodexLogo, EFFORT_NAMES} from './CodexHelp.jsx';
import {CopyButton, Icon} from './ui.jsx';

const FIELDS = [
  ['name', N_('Display name'), N_('How your name shows on your profile'), 60],
  ['handle', N_('Username'), N_('Shown as @username'), 30],
  ['location', N_('Location'), N_('Anything you like, e.g. a city'), 60],
  ['website', N_('Website'), 'example.com', 120],
  ['github', N_('GitHub username'), N_('Links your GitHub profile'), 39],
];
const ACCENT_NAMES = {blue:N_('Blue'), violet:N_('Violet'), teal:N_('Teal'), green:N_('Green'), amber:N_('Amber'), rose:N_('Rose')};
const SOUNDS = [['pass', N_('Pass')], ['fail', N_('Miss')], ['level', N_('Level up')], ['achievement', N_('Achievement')]];
const ZONES = Intl.supportedValuesOf?.('timeZone') || [];

const Section = ({title, desc, children}) => (
  <section className="section setting">
    <div className="setting-head"><h2>{title}</h2>{desc && <p className="meta">{desc}</p>}</div>
    <div className="setting-body">{children}</div>
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
    save('app:profile', clean).then(() => toast({kind:'note', text:t('Profile saved')}));
  };
  return (
    <form onSubmit={submit} className="fields">
      {FIELDS.map(([k, label, hint, max]) => (
        <label key={k} className="field"><span>{t(label)}</span>
          <input value={form[k]} onChange={set(k)} maxLength={max} placeholder={t(hint)} autoComplete="off"/>
        </label>
      ))}
      <label className="field wide"><span>{t('Bio')}</span>
        <textarea value={form.bio} onChange={set('bio')} maxLength={160} rows={3} placeholder={t('A line or two about you')}/>
        <span className="meta">{form.bio.length}/160</span>
      </label>
      <div className="wide"><button className="btn primary">{t('Save profile')}</button></div>
    </form>
  );
}

// The account's models (asked of OpenAI by the server), and how hard the chosen one thinks. Saved with the settings.
function CodexModel() {
  useStore();
  const list = useFetch('/api/codex/models');
  if (!Array.isArray(list) || !list.length) return list === undefined ? null : <p className="meta">{list?.error || t('Could not load your models.')}</p>;
  const s = settings();
  const model = list.find(m => m.slug === s.codexModel) || list[0];
  const effort = model.efforts.includes(s.codexEffort) ? s.codexEffort : model.effort;
  return <>
    <label className="field"><span>{t('Model')}</span>
      <select value={model.slug} onChange={e => save('app:settings', {codexModel:e.target.value})}>
        {list.map(m => <option key={m.slug} value={m.slug}>{m.name}</option>)}
      </select>
      {model.description && <span className="meta">{model.description}</span>}
    </label>
    <fieldset className="field">
      <legend>{t('Reasoning effort')}</legend>
      <div className="segmented">
        {model.efforts.map(e => (
          <label key={e}><input type="radio" name="codex-effort" checked={effort === e} onChange={() => save('app:settings', {codexEffort:e})}/>
            <span>{t(EFFORT_NAMES[e] || e)}</span></label>
        ))}
      </div>
      <span className="meta">{t('Higher thinks longer before answering, and uses more of your plan.')}</span>
    </fieldset>
  </>;
}

function CodexLink() {
  const [st, setSt] = useState();
  useEffect(() => { get('/api/codex').then(setSt, () => setSt(null)); }, []);
  useEffect(() => {  // while a code is showing: ask every few seconds whether it's been entered
    if (!st?.code) return;
    const id = setTimeout(() => post('/api/codex/poll', {}).then(s => {
      setSt(s);
      if (s.linked) toast({kind:'note', text:t('Codex account linked')});
    }, () => {}), st.interval * 1000);
    return () => clearTimeout(id);
  }, [st]);
  const call = path => post(path, {}).then(setSt, () => setSt({error:t('Server not reachable')}));
  if (st === undefined) return null;

  if (st?.linked) return <>
    <div className="codex-card">
      <CodexLogo size={22} tile/>
      <div className="codex-card-text"><strong>{t('Linked')}</strong>{st.email && <span className="meta">{st.email}</span>}</div>
      <button className="btn ghost danger" onClick={() => call('/api/codex/unlink')}>{t('Unlink')}</button>
    </div>
    <CodexModel/>
  </>;

  if (st?.code) return (
    <div className="codex-card codex-steps">
      <ol>
        <li><span>{t('Open the sign-in page and sign in to ChatGPT')}</span>
          <a className="btn primary" href={st.url} target="_blank" rel="noopener noreferrer"><Icon name="link"/>{t('Open sign-in page')}</a></li>
        <li><span>{t('Enter this code')}</span>
          <div className="codex-usercode"><code>{st.code}</code><CopyButton text={st.code} label={t('Copy code')}/></div></li>
      </ol>
      <p className="codex-wait meta" role="status"><Icon name="loader-circle" cls="spin"/>{t('Waiting for you to sign in…')}
        <button className="btn ghost" onClick={() => call('/api/codex/unlink')}>{t('Cancel')}</button></p>
    </div>
  );

  return (
    <div className="codex-card">
      <CodexLogo size={22} tile/>
      <div className="codex-card-text">
        <strong>{t('Codex by OpenAI')}</strong>
        <span className="meta">{(st?.error || (st?.expired && t('The code expired. Start again.'))) || t('Uses your own ChatGPT plan. Nagare never sees your password.')}</span>
      </div>
      <button className="btn primary" onClick={() => call('/api/codex/link')}>{t('Link Codex account')}</button>
    </div>
  );
}

export default function Settings() {
  useStore();
  const s = settings();
  const set = data => { save('app:settings', data); applySettings(); };
  const download = () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(store.progress, null, 1)], {type:'application/json'}));
    Object.assign(document.createElement('a'), {href:url, download:'nagare-progress.json'}).click();
    URL.revokeObjectURL(url);
  };

  return (
    <Page title={t('Settings')} className="narrow">
      <h1>{t('Settings')}</h1>

      <Section title={t('Profile')} desc={t('What shows on your profile page. Fill in three fields for an achievement.')}>
        <div className="photo-row">
          <Avatar size={56}/>
          <label className="check"><input type="checkbox" checked={s.photo} onChange={e => set({photo:e.target.checked})} disabled={!store.user?.picture}/>
            {t('Use my Google photo')}</label>
        </div>
        <ProfileForm/>
      </Section>

      <Section title={t('Appearance')}>
        {LANGS.length > 1 && <label className="field"><span>{t('Language')}</span>
          <select value={lang()} onChange={e => setLang(e.target.value)}>
            {LANGS.map(([code, name]) => <option key={code} value={code} lang={code}>{code === 'en' ? name : `${name} (${contentPct(code)}%)`}</option>)}
          </select>
          {lang() !== 'en' && <span className="meta">{t('The interface is fully translated; {pct}% of lessons are so far. The rest show in English.', {pct:contentPct(lang())})}</span>}
        </label>}
        <fieldset className="field">
          <legend>{t('Accent color')}</legend>
          <div className="swatches">
            {Object.entries(ACCENTS).map(([k, hex]) => (
              <label key={k} className="swatch" style={{'--c':hex}} title={t(ACCENT_NAMES[k] || k)}>
                <input type="radio" name="accent" checked={s.accent === k} onChange={() => set({accent:k})}/>
                <span className="sr">{t(ACCENT_NAMES[k] || k)}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <label className="field"><span>{t('Code font size')}</span>
          <select value={s.codeSize} onChange={e => set({codeSize:+e.target.value})}>
            {[12, 13, 14, 15, 16, 18].map(n => <option key={n} value={n}>{n === 14 ? t('{n}px (default)', {n}) : `${n}px`}</option>)}
          </select>
        </label>
        <label className="check"><input type="checkbox" checked={s.suggest} onChange={e => set({suggest:e.target.checked})}/>
          {t('Suggest completions as I type in the code editor')}</label>
      </Section>

      <Section title={t('Sound and effects')} desc={t('Played when you pass or miss a check, level up, or unlock an achievement.')}>
        <label className="check"><input type="checkbox" checked={s.sound} onChange={e => set({sound:e.target.checked})}/>{t('Sound effects')}</label>
        <div className="volume">
          <label className="field"><span>{t('Volume')}</span>
            <input type="range" min="5" max="100" step="5" value={s.volume} disabled={!s.sound}
                   onChange={e => set({volume:+e.target.value})} onPointerUp={() => sound('pass')} onKeyUp={() => sound('correct')}/>
          </label>
          <span className="meta">{s.volume}%</span>
        </div>
        <div className="sound-test">
          {SOUNDS.map(([k, label]) => (
            <button key={k} type="button" className="btn ghost" disabled={!s.sound} onClick={() => sound(k)}><Icon name="play"/>{t(label)}</button>
          ))}
        </div>
        <label className="check"><input type="checkbox" checked={s.effects} onChange={e => set({effects:e.target.checked})}/>
          {t('Screen effects (off anyway when your system asks for reduced motion)')}</label>
      </Section>

      <Section title={t('Notifications')}>
        <label className="check"><input type="checkbox" checked={s.toasts} onChange={e => set({toasts:e.target.checked})}/>
          {t('Show XP, level-up and achievement pop-ups')}</label>
      </Section>

      <Section title={t('Privacy')} desc={t('Other members can see your name, photo, profile, XP, course progress and achievements. Never your email or your code.')}>
        <label className="check"><input type="checkbox" checked={s.leaderboard} onChange={e => set({leaderboard:e.target.checked})}/>
          {t('Show me on the leaderboard')}</label>
        <label className="check"><input type="checkbox" checked={s.publicProfile} onChange={e => set({publicProfile:e.target.checked})}/>
          {t('Let other members see my profile')}</label>
      </Section>

      <Section title={t('Time zone')} desc={t('Decides when your day starts, for streaks and the activity graph.')}>
        <label className="field"><span>{t('Time zone')}</span>
          <select value={s.tz || ''} onChange={e => set({tz:e.target.value})}>
            {ZONES.map(z => <option key={z}>{z}</option>)}
          </select>
        </label>
      </Section>

      <Section title={t('Codex')} desc={t('Link your ChatGPT account to ask Codex for help in lessons. It sees the lesson and your saved code, and can\'t run anything.')}>
        <CodexLink/>
      </Section>

      <Section title={t('Your data')} desc={t('Everything saved for you: progress, code, profile, settings and XP.')}>
        <button className="btn" onClick={download}><Icon name="download"/>{t('Download as JSON')}</button>
      </Section>
    </Page>
  );
}
