package main

// Admins (ADMIN_EMAILS in .env) manage who may sign in and can sign out or ban members. Everything is checked here,
// on the server: the UI only hides the Admin link. Admin routes answer 404 to everyone else, take JSON only (a
// cross-site form can't send it), and only work with Google sign-in on, since without it there's no identity.

import (
	"bytes"
	"encoding/json"
	"log"
	"net/http"
	"net/mail"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"time"
)

// access is the admin-editable part of who may sign in, saved in data/access.json.
type access struct {
	Mode    string   `json:"mode"` // "open": any verified Google account; "list": only allowed emails
	Allowed []string `json:"allowed"`
	Banned  []string `json:"banned"`
}

// member is someone who has signed in, saved in data/users.json (the worker reads it for the leaderboard).
type member struct {
	Email   string    `json:"email"`
	Name    string    `json:"name"`
	Picture string    `json:"picture"`
	First   time.Time `json:"first"`
	Last    time.Time `json:"last"`
	Banned  bool      `json:"banned,omitempty"`
}

func emailSet(list string) map[string]bool {
	m := map[string]bool{}
	for _, e := range strings.Split(list, ",") {
		if e = strings.ToLower(strings.TrimSpace(e)); e != "" {
			m[e] = true
		}
	}
	return m
}

// cleanEmail: a lowercase bare address, or "" if it isn't one.
func cleanEmail(s string) string {
	s = strings.ToLower(strings.TrimSpace(s))
	if a, err := mail.ParseAddress(s); err != nil || a.Address != s || len(s) > 254 {
		return ""
	}
	return s
}

func writeJSON(path string, v any) error {
	data, err := json.MarshalIndent(v, "", " ")
	if err != nil {
		return err
	}
	os.MkdirAll(filepath.Dir(path), 0o755)
	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, data, 0o600); err != nil {
		return err
	}
	return os.Rename(tmp, path) // never leave a half-written file
}

// load reads access.json and users.json. With no access.json, ALLOWED_EMAILS decides the mode, as before.
func (a *auth) load() {
	a.access = access{Mode: "open"}
	if len(a.allowed) > 0 {
		a.access.Mode = "list"
	}
	if b, err := os.ReadFile(filepath.Join(a.dataDir, "access.json")); err == nil {
		json.Unmarshal(b, &a.access)
	}
	if b, err := os.ReadFile(filepath.Join(a.dataDir, "users.json")); err == nil {
		json.Unmarshal(b, &a.members)
	}
}

// Call with a.mu held.
func (a *auth) saveAccess() {
	if err := writeJSON(filepath.Join(a.dataDir, "access.json"), a.access); err != nil {
		log.Printf("admin: saving access: %v", err)
	}
	for id, m := range a.members {
		m.Banned = slices.Contains(a.access.Banned, m.Email)
		a.members[id] = m
	}
	a.saveMembers()
}

func (a *auth) saveMembers() {
	if err := writeJSON(filepath.Join(a.dataDir, "users.json"), a.members); err != nil {
		log.Printf("auth: saving users: %v", err)
	}
}

// canSignIn: admins always; banned never; otherwise anyone (open) or the listed emails. Call with a.mu held.
func (a *auth) canSignIn(email string) bool {
	switch {
	case a.admins[email]:
		return true
	case slices.Contains(a.access.Banned, email):
		return false
	case a.access.Mode == "open":
		return true
	}
	return a.allowed[email] || slices.Contains(a.access.Allowed, email)
}

func (a *auth) isAdmin(r *http.Request) bool {
	u := a.user(r)
	return a.enabled() && u != nil && a.admins[u.Email]
}

// enforce ends the sessions of everyone who may no longer sign in and returns their ids, whose containers then go.
// Call with a.mu held.
func (a *auth) enforce() []string {
	gone := map[string]bool{}
	for sid, s := range a.sessions {
		if !a.canSignIn(s.user.Email) {
			delete(a.sessions, sid)
			gone[idOf(s.user.Email)] = true
		}
	}
	ids := make([]string, 0, len(gone))
	for id := range gone {
		ids = append(ids, id)
	}
	return ids
}

func (a *auth) signOutEverywhere(email string) {
	for sid, s := range a.sessions {
		if s.user.Email == email {
			delete(a.sessions, sid)
		}
	}
}

var workerClient = &http.Client{Timeout: 10 * time.Second} // the worker is local: no answer means it's stuck

// kick stops a user's workspace and sandboxes, which also closes their terminals. The worker only accepts this
// with the token we gave it at startup, on a path the /api/ proxy never forwards.
func (a *app) kick(ids ...string) {
	for _, id := range ids {
		req, _ := http.NewRequest("POST", "http://"+a.appAddr+"/internal/kick", bytes.NewReader([]byte(`{"user":"`+id+`"}`)))
		req.Header.Set("X-Internal-Token", a.internalToken)
		if resp, err := workerClient.Do(req); err != nil {
			log.Printf("admin: kick %s: %v", id, err)
		} else {
			resp.Body.Close()
		}
	}
}

func (a *app) requireAdmin(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if !a.auth.isAdmin(r) {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Cache-Control", "no-store")
		if r.Method == http.MethodPost && r.Header.Get("Content-Type") != "application/json" {
			http.Error(w, "JSON only", http.StatusUnsupportedMediaType)
			return
		}
		next(w, r)
	}
}

type memberView struct {
	member
	ID      string `json:"id"`
	Admin   bool   `json:"admin"`
	Online  bool   `json:"online"`
	XP      int    `json:"xp"`
	Lessons int    `json:"lessons"`
}

// progressSummary reads XP and finished lessons from the worker's progress file.
func (a *app) progressSummary(id string) (xp, lessons int) {
	b, err := os.ReadFile(filepath.Join(a.auth.dataDir, "progress", id+".json"))
	if err != nil {
		return
	}
	var prog map[string]struct {
		Done bool `json:"done"`
		XP   int  `json:"xp"`
	}
	json.Unmarshal(b, &prog)
	for k, p := range prog {
		if k == "app:stats" {
			xp = p.XP
		} else if p.Done {
			lessons++
		}
	}
	return
}

// GET /admin/api/state
func (a *app) adminState(w http.ResponseWriter, r *http.Request) {
	au := a.auth
	you := au.user(r).Email
	au.mu.Lock()
	online := map[string]bool{}
	for _, s := range au.sessions {
		if time.Now().Before(s.expires) {
			online[s.user.Email] = true
		}
	}
	members := []memberView{}
	for id, m := range au.members {
		members = append(members, memberView{member: m, ID: id, Admin: au.admins[m.Email], Online: online[m.Email]})
	}
	type entry struct {
		Email string `json:"email"`
		Env   bool   `json:"env"` // from .env: can't be removed here
	}
	allowed := []entry{}
	for e := range au.allowed {
		allowed = append(allowed, entry{e, true})
	}
	for _, e := range au.access.Allowed {
		if !au.allowed[e] {
			allowed = append(allowed, entry{e, false})
		}
	}
	admins := []string{}
	for e := range au.admins {
		admins = append(admins, e)
	}
	state := map[string]any{"mode": au.access.Mode, "allowed": allowed, "banned": append([]string{}, au.access.Banned...),
		"admins": admins, "you": you}
	au.mu.Unlock()
	for i := range members {
		members[i].XP, members[i].Lessons = a.progressSummary(members[i].ID)
	}
	slices.SortFunc(members, func(x, y memberView) int { return y.Last.Compare(x.Last) })
	slices.SortFunc(allowed, func(x, y entry) int { return strings.Compare(x.Email, y.Email) })
	state["members"] = members
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(state)
}

// POST /admin/api/action {"action": "...", "email": "...", "mode": "..."}
//
//	mode           sign-in mode: "open" or "list"
//	allow/disallow add or remove an email on the allowed list
//	signout        end someone's sessions and stop their containers
//	ban/unban      block someone from signing in (and sign them out)
func (a *app) adminAction(w http.ResponseWriter, r *http.Request) {
	var req struct{ Action, Email, Mode string }
	if json.NewDecoder(http.MaxBytesReader(w, r.Body, 4096)).Decode(&req) != nil {
		http.Error(w, "Bad request", http.StatusBadRequest)
		return
	}
	au := a.auth
	by := au.user(r).Email
	email := cleanEmail(req.Email)
	needsEmail := req.Action != "mode"
	if needsEmail && email == "" {
		http.Error(w, "That isn't an email address", http.StatusBadRequest)
		return
	}
	if (req.Action == "ban" || req.Action == "signout" || req.Action == "disallow") && au.admins[email] {
		http.Error(w, "Admins are set in .env and can't be signed out, banned or removed here", http.StatusForbidden)
		return
	}

	au.mu.Lock()
	var kicked []string
	switch req.Action {
	case "mode":
		if req.Mode != "open" && req.Mode != "list" {
			au.mu.Unlock()
			http.Error(w, "Bad mode", http.StatusBadRequest)
			return
		}
		au.access.Mode = req.Mode
	case "allow":
		if !au.allowed[email] && !slices.Contains(au.access.Allowed, email) {
			au.access.Allowed = append(au.access.Allowed, email)
		}
	case "disallow":
		if au.allowed[email] {
			au.mu.Unlock()
			http.Error(w, "That email is in ALLOWED_EMAILS in .env; remove it there", http.StatusConflict)
			return
		}
		au.access.Allowed = slices.DeleteFunc(au.access.Allowed, func(e string) bool { return e == email })
	case "ban":
		if !slices.Contains(au.access.Banned, email) {
			au.access.Banned = append(au.access.Banned, email)
		}
	case "unban":
		au.access.Banned = slices.DeleteFunc(au.access.Banned, func(e string) bool { return e == email })
	case "signout":
		au.signOutEverywhere(email)
		kicked = append(kicked, idOf(email))
	default:
		au.mu.Unlock()
		http.Error(w, "Unknown action", http.StatusBadRequest)
		return
	}
	if req.Action != "signout" {
		au.saveAccess()
		kicked = au.enforce()
	}
	au.mu.Unlock()
	log.Printf("admin %s: %s %s%s", by, req.Action, email, req.Mode)
	a.kick(kicked...)
	a.adminState(w, r)
}
