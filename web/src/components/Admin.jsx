/* Admin: who may sign in, and signing out or banning members. The gateway checks every request (gateway/admin.go);
   this page is only a view of it. */
import {useEffect, useState} from 'react';
import {N_, locale, t} from '../lib/i18n.js';
import {level} from '../lib/xp.js';
import {get, toast} from '../store.js';
import {formatDate} from './Achievements.jsx';
import {Avatar, Page} from './Account.jsx';
import {Icon} from './ui.jsx';

async function call(body) {
  const r = await fetch('/admin/api/action', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export default function Admin() {
  const [state, setState] = useState();
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { get('/admin/api/state').catch(() => null).then(setState); }, []);

  const act = async (body, done) => {
    setBusy(true);
    try {
      setState(await call(body));
      if (done) toast({kind:'note', text:done});
    } catch (e) {
      toast({kind:'note', text:t(e.message.trim())});
    }
    setBusy(false);
  };
  const confirmAct = (msg, body, done) => confirm(msg) && act(body, done);

  if (state === undefined) return <Page><p className="empty">{t('Loading…')}</p></Page>;
  if (state === null) return <Page title={t('Not available')}><h1>{t('Not available')}</h1><p className="lede">{t('This page is for admins.')}</p></Page>;

  const add = e => {
    e.preventDefault();
    act({action:'allow', email}, t('{email} can sign in', {email})).then(() => setEmail(''));
  };
  return (
    <Page title={t('Admin')}>
      <h1>{t('Admin')}</h1>
      <p className="lede">{t('Admins are set with ADMIN_EMAILS in .env: {list}.', {list:state.admins.join(', ')})}</p>

      <section className="section setting">
        <div className="setting-head"><h2>{t('Who can sign in')}</h2><p className="meta">{t('Switching to the list signs out anyone not on it. Admins can always sign in.')}</p></div>
        <div className="setting-body" role="radiogroup" aria-label={t('Who can sign in')}>
          {[['open', N_('Anyone with a verified Google account')], ['list', N_('Only the emails below')]].map(([m, label]) => (
            <label key={m} className="check"><input type="radio" name="mode" checked={state.mode === m} disabled={busy}
              onChange={() => m === 'list' ? confirmAct(t('Sign out everyone who is not on the list?'), {action:'mode', mode:m}) : act({action:'mode', mode:m})}/>{t(label)}</label>
          ))}
          <form className="add-email" onSubmit={add}>
            <input type="email" required value={email} onChange={e => setEmail(e.target.value)} placeholder="name@example.com" aria-label={t('Email to allow')}/>
            <button className="btn" disabled={busy}><Icon name="plus"/>{t('Allow')}</button>
          </form>
          {state.allowed.length ? (
            <ul className="email-list">
              {state.allowed.map(a => (
                <li key={a.email}><span>{a.email}</span>
                  {a.env ? <span className="meta">.env</span>
                    : <button className="btn ghost" disabled={busy} onClick={() => confirmAct(t('Remove {email} from the list?', {email:a.email}), {action:'disallow', email:a.email})}>{t('Remove')}</button>}
                </li>
              ))}
            </ul>
          ) : <p className="meta">{t('No emails on the list yet.')}</p>}
        </div>
      </section>

      <section className="section">
        <div className="section-head"><h2>{t('Members')}</h2><span className="meta">{t('{n} signed in at least once', {n:state.members.length})}</span></div>
        <div className="table-scroll">
          <table className="members">
            <thead><tr><th>{t('Member')}</th><th>{t('Level')}</th><th>{t('Lessons')}</th><th>{t('Last sign-in')}</th><th><span className="sr">{t('Actions')}</span></th></tr></thead>
            <tbody>
              {state.members.map(m => (
                <tr key={m.id}>
                  <td><div className="who">
                    <Avatar picture={m.picture} name={m.name || m.email}/>
                    <span><strong>{m.name || m.email}</strong><span className="meta">{m.email}</span></span>
                    {m.online && <span className="chip pass">{t('Online')}</span>}
                    {m.admin && <span className="chip info">{t('Admin')}</span>}
                    {m.banned && <span className="chip fail">{t('Banned')}</span>}
                  </div></td>
                  <td>{level(m.xp)} <span className="meta">· {t('{n} XP', {n:m.xp.toLocaleString(locale())})}</span></td>
                  <td>{m.lessons}</td>
                  <td className="meta">{formatDate(m.last)}</td>
                  <td className="member-actions">{!m.admin && <>
                    {m.online && <button className="btn ghost" disabled={busy}
                      onClick={() => confirmAct(t('Sign {email} out? Their open terminals close.', {email:m.email}), {action:'signout', email:m.email}, t('Signed out'))}>{t('Sign out')}</button>}
                    {m.banned
                      ? <button className="btn ghost" disabled={busy} onClick={() => act({action:'unban', email:m.email}, t('Unbanned'))}>{t('Unban')}</button>
                      : <button className="btn ghost danger" disabled={busy}
                          onClick={() => confirmAct(t('Ban {email}? They\'re signed out now and can\'t sign back in. Their progress is kept.', {email:m.email}), {action:'ban', email:m.email}, t('Banned'))}><Icon name="ban"/>{t('Ban')}</button>}
                  </>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {state.banned.filter(e => !state.members.some(m => m.email === e)).map(e => (
          <p key={e} className="meta">{t('Banned (never signed in): {email}', {email:e})} <button className="btn ghost" onClick={() => act({action:'unban', email:e})}>{t('Unban')}</button></p>
        ))}
      </section>
    </Page>
  );
}
