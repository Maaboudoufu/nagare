package main

// Google sign-in: OAuth 2.0 authorization code flow with PKCE. Off unless GOOGLE_CLIENT_ID is set.

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"log"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	"golang.org/x/oauth2"
)

const (
	sessionCookie = "session"
	stateCookie   = "oauth_state"
	sessionTTL    = 30 * 24 * time.Hour
	loginTTL      = 10 * time.Minute
	userinfoURL   = "https://openidconnect.googleapis.com/v1/userinfo"
)

type User struct {
	Email   string `json:"email"`
	Name    string `json:"name"`
	Picture string `json:"picture"`
}

type session struct {
	user    User
	expires time.Time
}

type pending struct {
	verifier string
	expires  time.Time
}

// ponytail: sessions live in memory, so restarting the app signs you out. Persist them if that gets annoying.
type auth struct {
	conf     *oauth2.Config // nil = sign-in off, everyone is let in
	allowed  map[string]bool
	userinfo string
	mu       sync.Mutex
	sessions map[string]session
	logins   map[string]pending // OAuth state -> PKCE verifier, while the user is at Google
}

func newAuth(conf *oauth2.Config, allowedEmails string) *auth {
	a := &auth{conf: conf, allowed: map[string]bool{}, userinfo: userinfoURL,
		sessions: map[string]session{}, logins: map[string]pending{}}
	for _, e := range strings.Split(allowedEmails, ",") {
		if e = strings.ToLower(strings.TrimSpace(e)); e != "" {
			a.allowed[e] = true
		}
	}
	return a
}

func (a *auth) enabled() bool { return a.conf != nil }

func randomToken() string {
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		panic(err)
	}
	return base64.RawURLEncoding.EncodeToString(b)
}

var secureCookies bool // set when BASE_URL is https: cookies then never travel over plain HTTP

func setCookie(w http.ResponseWriter, name, value string, maxAge time.Duration) {
	http.SetCookie(w, &http.Cookie{Name: name, Value: value, Path: "/", MaxAge: int(maxAge.Seconds()),
		HttpOnly: true, Secure: secureCookies, SameSite: http.SameSiteLaxMode}) // Lax: sent on Google's redirect back
}

// userID: a short stable id for the signed-in account (names their progress file and containers).
// "local" when sign-in is off. Only call after requireUser.
func (a *auth) userID(r *http.Request) string {
	if !a.enabled() {
		return "local"
	}
	u := a.user(r)
	if u == nil {
		return "anonymous" // not reached: /api requires a user
	}
	sum := sha256.Sum256([]byte(u.Email))
	return hex.EncodeToString(sum[:8])
}

// user is who's signed in, or nil. With sign-in off, everyone counts as signed in (an empty User).
func (a *auth) user(r *http.Request) *User {
	if !a.enabled() {
		return &User{}
	}
	c, err := r.Cookie(sessionCookie)
	if err != nil {
		return nil
	}
	a.mu.Lock()
	defer a.mu.Unlock()
	s, ok := a.sessions[c.Value]
	if !ok || time.Now().After(s.expires) {
		delete(a.sessions, c.Value)
		return nil
	}
	return &s.user
}

func failLogin(w http.ResponseWriter, r *http.Request, reason string) {
	setCookie(w, stateCookie, "", -1)
	http.Redirect(w, r, "/signin?auth_error="+url.QueryEscape(reason), http.StatusFound)
}

// GET /auth/login: send the browser to Google's consent screen.
func (a *auth) login(w http.ResponseWriter, r *http.Request) {
	if !a.enabled() {
		http.Redirect(w, r, "/", http.StatusFound)
		return
	}
	state, verifier := randomToken(), oauth2.GenerateVerifier()
	a.mu.Lock()
	now := time.Now()
	for k, p := range a.logins { // drop abandoned logins
		if now.After(p.expires) {
			delete(a.logins, k)
		}
	}
	a.logins[state] = pending{verifier, now.Add(loginTTL)}
	a.mu.Unlock()
	setCookie(w, stateCookie, state, loginTTL) // ties the callback to this browser (CSRF)
	http.Redirect(w, r, a.conf.AuthCodeURL(state, oauth2.S256ChallengeOption(verifier),
		oauth2.SetAuthURLParam("prompt", "select_account")), http.StatusFound)
}

// GET /auth/callback: Google sends the user back here with ?code&state.
func (a *auth) callback(w http.ResponseWriter, r *http.Request) {
	if !a.enabled() {
		http.Redirect(w, r, "/", http.StatusFound)
		return
	}
	q := r.URL.Query()
	if e := q.Get("error"); e != "" {
		failLogin(w, r, e) // e.g. access_denied when the user cancels
		return
	}
	state := q.Get("state")
	c, err := r.Cookie(stateCookie)
	if err != nil || state == "" || c.Value != state {
		failLogin(w, r, "state_mismatch")
		return
	}
	a.mu.Lock()
	p, ok := a.logins[state]
	delete(a.logins, state)
	a.mu.Unlock()
	if !ok || time.Now().After(p.expires) {
		failLogin(w, r, "login_expired")
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 15*time.Second)
	defer cancel()
	tok, err := a.conf.Exchange(ctx, q.Get("code"), oauth2.VerifierOption(p.verifier))
	if err != nil {
		log.Printf("auth: token exchange: %v", err)
		failLogin(w, r, "exchange_failed")
		return
	}
	resp, err := a.conf.Client(ctx, tok).Get(a.userinfo)
	if err != nil {
		log.Printf("auth: userinfo: %v", err)
		failLogin(w, r, "userinfo_failed")
		return
	}
	defer resp.Body.Close()
	var info struct {
		User
		EmailVerified bool `json:"email_verified"`
	}
	if resp.StatusCode != http.StatusOK || json.NewDecoder(resp.Body).Decode(&info) != nil {
		failLogin(w, r, "userinfo_failed")
		return
	}
	info.Email = strings.ToLower(info.Email)
	if !info.EmailVerified || (len(a.allowed) > 0 && !a.allowed[info.Email]) {
		failLogin(w, r, "not_allowed")
		return
	}

	sid := randomToken()
	a.mu.Lock()
	a.sessions[sid] = session{info.User, time.Now().Add(sessionTTL)}
	a.mu.Unlock()
	setCookie(w, stateCookie, "", -1)
	setCookie(w, sessionCookie, sid, sessionTTL)
	http.Redirect(w, r, "/", http.StatusFound)
}

// GET /auth/me: {"enabled": bool, "user": {...} | null}
func (a *auth) me(w http.ResponseWriter, r *http.Request) {
	var u *User
	if a.enabled() {
		u = a.user(r)
	}
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	json.NewEncoder(w).Encode(map[string]any{"enabled": a.enabled(), "user": u})
}

// POST /auth/logout (POST, so another site can't sign you out with a link).
func (a *auth) logout(w http.ResponseWriter, r *http.Request) {
	if c, err := r.Cookie(sessionCookie); err == nil {
		a.mu.Lock()
		delete(a.sessions, c.Value)
		a.mu.Unlock()
	}
	setCookie(w, sessionCookie, "", -1)
	w.WriteHeader(http.StatusNoContent)
}
