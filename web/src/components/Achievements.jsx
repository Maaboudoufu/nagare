import {N_, locale, t} from '../lib/i18n.js';
import {stats} from '../lib/xp.js';
import medals from '../assets/medals.svg?no-inline';  // a sprite: <use> needs a real file
import {useFetch, useStore} from '../store.js';
import {Page} from './Account.jsx';
import {Meter} from './ui.jsx';

export const formatDate = iso => new Date(iso.length === 10 ? iso + 'T12:00' : iso).toLocaleDateString(locale(), {month:'short', day:'numeric', year:'numeric'});

const TIER_XP = {bronze:25, silver:50, gold:100};
const TIERS = {bronze:N_('Bronze'), silver:N_('Silver'), gold:N_('Gold')};

/* A medal: the achievement's own glyph (assets/medals.svg, by id) in a frame whose shape is the tier, so the tier
   doesn't hang on color alone: bronze a circle, silver a hexagon, gold a seal. Locked ones are a dotted outline. */
const RIM = {bronze:<circle cx="24" cy="24" r="22.5"/>, silver:<path d="M24 1.5 43.5 12.8v22.4L24 46.5 4.5 35.2V12.8Z"/>,
             gold:<path d="M24 1.2 30.2 4.8 37.4 5.6 40.3 12.1 45.7 17 44.2 24 45.7 31 40.3 35.9 37.4 42.4 30.2 43.2 24 46.8 17.8 43.2 10.6 42.4 7.7 35.9 2.3 31 3.8 24 2.3 17 7.7 12.1 10.6 5.6 17.8 4.8Z"/>};
const RING = {bronze:<circle cx="24" cy="24" r="18.5"/>, silver:<path d="M24 6 39.6 15v18L24 42 8.4 33V15Z"/>, gold:<circle cx="24" cy="24" r="17"/>};
export const Badge = ({a, size = 40}) => (
  <svg className={`medal tier-${a.tier}` + (a.unlocked ? '' : ' locked')} width={size} height={size} viewBox="0 0 48 48" aria-hidden="true">
    <g className="medal-rim">{RIM[a.tier]}</g>
    {a.unlocked && <g className="medal-ring">{RING[a.tier]}</g>}
    <use className="medal-glyph" href={`${medals}#${a.id}`} x="12" y="12" width="24" height="24"/>
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
