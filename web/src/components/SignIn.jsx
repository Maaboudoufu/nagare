/* Sign-in screen: Google only.
   The button is a plain link: /auth/login redirects to Google, which redirects back to /auth/callback. */
import {N_, t} from '../lib/i18n.js';
import {useStore} from '../store.js';
import {LangMenu} from './Account.jsx';
import {BrandMark, Icon} from './ui.jsx';

const ERRORS = {
  access_denied:N_('Sign-in was cancelled.'),
  not_allowed:N_('That Google account isn\'t allowed to use this app.'),
  state_mismatch:N_('Sign-in expired. Please try again.'),
  login_expired:N_('Sign-in expired. Please try again.'),
};

// Google's "G" mark, as its sign-in branding guidelines require.
const GoogleG = () => (
  <svg className="google-g" viewBox="0 0 48 48" aria-hidden="true">
    <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
    <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
    <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
    <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
  </svg>
);

export default function SignIn() {
  useStore();  // re-render when the language changes
  const code = new URLSearchParams(location.search).get('auth_error');
  const error = code && (ERRORS[code] ? t(ERRORS[code]) : t('Sign-in failed. Please try again.'));
  return (
    <main className="center">
      <LangMenu/>
      <BrandMark className="center-mark"/>
      <h1>{t('Sign in to {app}', {app:t('nagare')})}</h1>
      <p className="meta">{t('Continue with your Google account to pick up where you left off.')}</p>
      {error && <p className="signin-err" role="alert"><Icon name="circle-x"/>{error}</p>}
      <a className="btn google" href="/auth/login"><GoogleG/>{t('Continue with Google')}</a>
    </main>
  );
}
