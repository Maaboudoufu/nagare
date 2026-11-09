/* Admin: who may sign in, and signing out or banning members. The gateway checks every request (gateway/admin.go);
   this page is only a view of it. */
import {useEffect, useState} from 'react';
import {formatDate} from './Achievements.jsx';
import {Topbar} from './Account.jsx';
import {level} from '../lib/xp.js';
import {toast} from '../store.js';
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
  useEffect(() => {
    document.title = 'Admin · nagare';
    fetch('/admin/api/state', {cache:'no-store'}).then(r => r.ok ? r.json() : null).then(setState);
  }, []);

  const act = async (body, done) => {
    setBusy(true);
    try {
      setState(await call(body));
      if (done) toast({kind:'note', text:done});
    } catch (e) {
      toast({kind:'note', text:e.message.trim()});
    }
    setBusy(false);
  };
  const confirmAct = (msg, body, done) => confirm(msg) && act(body, done);

  if (state === undefined) return <main id="home" className="page"><Topbar/><p className="empty">Loading…</p></main>;
  if (state === null) return <main id="home" className="page"><Topbar/><h1>Not available</h1><p className="path-desc">This page is for admins.</p></main>;

  const add = e => {
    e.preventDefault();
    act({action:'allow', email}, `${email} can sign in`).then(() => setEmail(''));
  };
  return (
    <main id="home" className="page admin">
      <Topbar/>
      <h1>Admin</h1>
      <p className="path-desc">Admins are set with ADMIN_EMAILS in .env: {state.admins.join(', ')}.</p>

      <section className="card settings-section">
        <div className="settings-head"><h2>Who can sign in</h2><p className="meta">Switching to the list signs out anyone not on it. Admins can always sign in.</p></div>
        <div className="settings-body" role="radiogroup" aria-label="Who can sign in">
          {[['open', 'Anyone with a verified Google account'], ['list', 'Only the emails below']].map(([m, label]) => (
            <label key={m} className="check"><input type="radio" name="mode" checked={state.mode === m} disabled={busy}
              onChange={() => m === 'list' ? confirmAct('Sign out everyone who is not on the list?', {action:'mode', mode:m}) : act({action:'mode', mode:m})}/>{label}</label>
          ))}
          <form className="add-email" onSubmit={add}>
            <input type="email" required value={email} onChange={e => setEmail(e.target.value)} placeholder="name@example.com" aria-label="Email to allow"/>
            <button className="btn" disabled={busy}><Icon name="plus"/>Allow</button>
          </form>
          {state.allowed.length ? (
            <ul className="email-list">
              {state.allowed.map(a => (
                <li key={a.email}><span>{a.email}</span>
                  {a.env ? <span className="meta">.env</span>
                    : <button className="btn ghost" disabled={busy} onClick={() => confirmAct(`Remove ${a.email} from the list?`, {action:'disallow', email:a.email})}>Remove</button>}
                </li>
              ))}
            </ul>
          ) : <p className="meta">No emails on the list yet.</p>}
        </div>
      </section>

      <section className="card">
        <div className="card-head"><h2>Members</h2><span className="meta">{state.members.length} signed in at least once</span></div>
        <div className="table-scroll">
          <table className="members">
            <thead><tr><th>Member</th><th>Level</th><th>Lessons</th><th>Last sign-in</th><th><span className="sr">Actions</span></th></tr></thead>
            <tbody>
              {state.members.map(m => (
                <tr key={m.id}>
                  <td><div className="who">
                    {m.picture ? <img className="avatar" src={m.picture} alt="" referrerPolicy="no-referrer"/> : <span className="avatar" aria-hidden="true">{(m.name || m.email)[0].toUpperCase()}</span>}
                    <span><strong>{m.name || m.email}</strong><span className="meta">{m.email}</span></span>
                    {m.online && <span className="chip pass">Online</span>}
                    {m.admin && <span className="chip info">Admin</span>}
                    {m.banned && <span className="chip fail">Banned</span>}
                  </div></td>
                  <td>{level(m.xp)} <span className="meta">· {m.xp.toLocaleString()} XP</span></td>
                  <td>{m.lessons}</td>
                  <td className="meta">{formatDate(m.last)}</td>
                  <td className="member-actions">{!m.admin && <>
                    {m.online && <button className="btn ghost" disabled={busy}
                      onClick={() => confirmAct(`Sign ${m.email} out? Their open terminals close.`, {action:'signout', email:m.email}, 'Signed out')}>Sign out</button>}
                    {m.banned
                      ? <button className="btn ghost" disabled={busy} onClick={() => act({action:'unban', email:m.email}, 'Unbanned')}>Unban</button>
                      : <button className="btn ghost danger" disabled={busy}
                          onClick={() => confirmAct(`Ban ${m.email}? They're signed out now and can't sign back in. Their progress is kept.`, {action:'ban', email:m.email}, 'Banned')}><Icon name="ban"/>Ban</button>}
                  </>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {state.banned.filter(e => !state.members.some(m => m.email === e)).map(e => (
          <p key={e} className="meta">Banned (never signed in): {e} <button className="btn ghost" onClick={() => act({action:'unban', email:e})}>Unban</button></p>
        ))}
      </section>
    </main>
  );
}
