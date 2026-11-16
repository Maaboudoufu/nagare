import {N_, locale, t} from '../lib/i18n.js';
import {stats} from '../lib/xp.js';
import medals from '../assets/medals.svg?no-inline';  // a sprite: <use> needs a real file
import {useFetch, useStore} from '../store.js';
import {Page} from './Account.jsx';
import {Meter} from './ui.jsx';

export const formatDate = iso => new Date(iso.length === 10 ? iso + 'T12:00' : iso).toLocaleDateString(locale(), {month:'short', day:'numeric', year:'numeric'});

const TIER_XP = {bronze:25, silver:50, gold:100};
const TIERS = {bronze:N_('Bronze'), silver:N_('Silver'), gold:N_('Gold')};

/* A medal: the achievement's pixel-art scene (assets/medals.svg, drawn by tools/make_medals.py) in a frame of the tier's
   metal, with one to three studs on its bottom edge so the tier doesn't hang on color alone. A scene is 24 pixels
   across: keep sizes to multiples of 24, so every pixel lands whole. Locked ones are greyed out. */
export const Badge = ({a, size = 48}) => (
  <svg className={`medal tier-${a.tier}` + (a.unlocked ? '' : ' locked')} width={size} height={size} aria-hidden="true">
    <use href={`${medals}#${a.id}`}/>
  </svg>
);

export function AchievementRow({a}) {
  return (
    <li className={'ach' + (a.unlocked ? '' : ' locked')}>
      <Badge a={a}/>
      <div className="ach-text">
        <span className="ach-name">{t(a.name)}</span>
        <span className="meta">{t(a.description)}</span>
        <span className="ach-tier"><span className={`tier-dot tier-${a.tier}`} aria-hidden="true"/>{t('{tier} · {xp} XP', {tier:t(TIERS[a.tier]), xp:TIER_XP[a.tier]})}</span>
      </div>
      <div className="ach-side">
        {a.unlocked ? <span className="meta">{formatDate(a.unlocked)}</span> : a.goal > 1 && <>
          <span className="meta">{t('{n} / {total}', {n:a.value, total:a.goal})}</span>
          <Meter n={a.value} total={a.goal} label={t('{name} progress', {name:t(a.name)})}/>
        </>}
      </div>
    </li>
  );
}

export default function Achievements() {
  useStore();
  const list = useFetch('/api/achievements', stats().xp);  // each with your progress toward it; again whenever you earn XP
  const got = (list || []).filter(a => a.unlocked).sort((a, b) => b.unlocked.localeCompare(a.unlocked));
  const left = (list || []).filter(a => !a.unlocked).sort((a, b) => b.value / b.goal - a.value / a.goal);  // closest first
  const group = (title, items) => items.length > 0 && (
    <section className="section">
      <div className="section-head"><h2>{title}</h2><span className="meta">{items.length}</span></div>
      <ul className="ach-list">{items.map(a => <AchievementRow key={a.id} a={a}/>)}</ul>
    </section>
  );
  return (
    <Page title={t('Achievements')} className="narrow">
      <h1>{t('Achievements')}</h1>
      <p className="lede">{list ? t('{n} of {total} unlocked. Each one is worth bonus XP: bronze 25, silver 50, gold 100.', {n:got.length, total:list.length}) : t('Loading…')}</p>
      {group(t('Unlocked'), got)}
      {group(t('Locked'), left)}
    </Page>
  );
}
