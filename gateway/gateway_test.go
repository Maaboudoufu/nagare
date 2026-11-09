package main

import (
	"compress/gzip"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"testing"

	"golang.org/x/oauth2"
)

var kicks []string // bodies of the worker's /internal/kick calls

// testApp: a fake built UI, course data and Python worker in a temp dir. conf nil = sign-in off.
func testApp(t *testing.T, conf *oauth2.Config, allowed string) (*app, http.Handler) {
	t.Helper()
	dir := t.TempDir()
	write := func(rel, body string) {
		p := filepath.Join(dir, rel)
		os.MkdirAll(filepath.Dir(p), 0o755)
		os.WriteFile(p, []byte(body), 0o644)
	}
	write("web/index.html", "<!doctype html><div id=root></div>")
	write("web/assets/app.js", strings.Repeat("console.log(1);", 100))
	write("courses/index.json", `{"courses":[]}`)
	write("courses/learn-go.json", `{"slug":"learn-go"}`)
	write("courses/shell/abc.json", `{"secret":true}`)
	write("media/host/v.mp4", strings.Repeat("v", 1000))
	worker := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/internal/kick" && r.Header.Get("X-Internal-Token") == "internal" {
			b, _ := io.ReadAll(r.Body)
			kicks = append(kicks, string(b))
			return
		}
		io.WriteString(w, "worker:"+r.URL.Path+" token="+r.Header.Get("X-Internal-Token")+" origin="+r.Header.Get("Origin")+" user="+r.Header.Get("X-User"))
	}))
	t.Cleanup(worker.Close)
	a := &app{auth: newAuth(conf, allowed, "admin@example.com", filepath.Join(dir, "data")), web: filepath.Join(dir, "web"), courses: filepath.Join(dir, "courses"), media: filepath.Join(dir, "media"),
		hosts: map[string]bool{"localhost:8000": true}, origins: map[string]bool{}}
	a.appAddr, a.internalToken = strings.TrimPrefix(worker.URL, "http://"), "internal"
	a.api = apiProxy(a.appAddr, a.auth)
	return a, a.routes()
}

type client struct {
	h       http.Handler
	cookies []*http.Cookie
}

func (c *client) do(method, target string, hdr ...string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, "http://localhost:8000"+target, nil)
	for i := 0; i+1 < len(hdr); i += 2 {
		req.Header.Set(hdr[i], hdr[i+1])
	}
	for _, ck := range c.cookies {
		req.AddCookie(ck)
	}
	rec := httptest.NewRecorder()
	c.h.ServeHTTP(rec, req)
	for _, ck := range rec.Result().Cookies() { // keep cookies like a browser
		kept := c.cookies[:0]
		for _, old := range c.cookies {
			if old.Name != ck.Name {
				kept = append(kept, old)
			}
		}
		c.cookies = kept
		if ck.MaxAge >= 0 {
			c.cookies = append(c.cookies, ck)
		}
	}
	return rec
}

func expect(t *testing.T, rec *httptest.ResponseRecorder, code int, location string) {
	t.Helper()
	if rec.Code != code || (location != "" && !strings.Contains(rec.Header().Get("Location"), location)) {
		t.Fatalf("got %d %q, want %d %q", rec.Code, rec.Header().Get("Location"), code, location)
	}
}

func TestRoutesSignInOff(t *testing.T) {
	_, h := testApp(t, nil, "")
	c := &client{h: h}
	expect(t, c.do("GET", "/"), 200, "")
	expect(t, c.do("GET", "/learn/learn-go/some-lesson"), 200, "")
	expect(t, c.do("GET", "/settings"), 200, "")
	expect(t, c.do("GET", "/settingsx"), 404, "")
	expect(t, c.do("GET", "/admin"), 404, "") // no sign-in, no admins
	expect(t, c.do("GET", "/learn/no-such-course"), 404, "")
	expect(t, c.do("GET", "/learn/..%2fweb"), 404, "")
	expect(t, c.do("GET", "/signin"), 302, "/")            // nothing to sign in to
	expect(t, c.do("GET", "/courses/index.json"), 200, "") // data
	expect(t, c.do("GET", "/courses/shell/abc.json"), 404, "")
	expect(t, c.do("GET", "/courses/../web/index.html"), 307, "/web/index.html") // ServeMux cleans ".." ...
	expect(t, c.do("GET", "/web/index.html"), 404, "")                           // ... to a path that isn't served
	expect(t, c.do("GET", "/nope"), 404, "")
	// Media: served with byte ranges, so videos can seek; never outside media/.
	if rec := c.do("GET", "/media/host/v.mp4", "Range", "bytes=10-19"); rec.Code != 206 || rec.Body.Len() != 10 {
		t.Fatalf("media range: %d %d", rec.Code, rec.Body.Len())
	}
	expect(t, c.do("GET", "/media/../courses/index.json"), 307, "/courses/index.json")
	var me map[string]any
	json.NewDecoder(c.do("GET", "/auth/me").Body).Decode(&me)
	if me["enabled"] != false {
		t.Fatalf("me = %v", me)
	}

	// The worker gets /api calls without the browser's Origin, as user "local", whatever the browser claims.
	rec := c.do("POST", "/api/run", "Origin", "http://localhost:8000", "X-User", "someone-else")
	if body := rec.Body.String(); rec.Code != 200 || body != "worker:/api/run token= origin= user=local" {
		t.Fatalf("proxy: %d %q", rec.Code, body)
	}

	// Other sites and other host names are refused.
	expect(t, c.do("POST", "/api/run", "Origin", "https://evil.example"), 403, "")
	req := httptest.NewRequest("GET", "http://evil.example:8000/", nil)
	rec = httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	expect(t, rec, 403, "")

	// Assets: gzipped, cached forever (hashed names).
	rec = c.do("GET", "/assets/app.js", "Accept-Encoding", "gzip")
	if rec.Header().Get("Content-Encoding") != "gzip" || !strings.Contains(rec.Header().Get("Cache-Control"), "immutable") {
		t.Fatalf("asset headers: %v", rec.Header())
	}
	zr, err := gzip.NewReader(rec.Body)
	if err != nil {
		t.Fatal(err)
	}
	if b, _ := io.ReadAll(zr); !strings.HasPrefix(string(b), "console.log") {
		t.Fatalf("gzip body: %q", b)
	}
}

// The whole sign-in flow against a fake Google, and that pages, data and the API are locked until then.
func TestSignIn(t *testing.T) {
	email := "Me@Example.com"
	google := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		switch r.URL.Path {
		case "/token":
			r.ParseForm()
			if r.Form.Get("code_verifier") == "" {
				http.Error(w, `{"error":"missing PKCE verifier"}`, 400)
				return
			}
			io.WriteString(w, `{"access_token":"tok","token_type":"Bearer","expires_in":3600}`)
		case "/userinfo":
			json.NewEncoder(w).Encode(map[string]any{"email": email, "email_verified": true, "name": "Me"})
		}
	}))
	defer google.Close()
	conf := &oauth2.Config{ClientID: "id", ClientSecret: "secret", RedirectURL: "http://localhost:8000/auth/callback",
		Endpoint: oauth2.Endpoint{AuthURL: google.URL + "/auth", TokenURL: google.URL + "/token"}}
	a, h := testApp(t, conf, "me@example.com")
	a.auth.userinfo = google.URL + "/userinfo"

	c := &client{h: h}
	expect(t, c.do("GET", "/"), 302, "/signin")
	expect(t, c.do("GET", "/learn/learn-go"), 302, "/signin")
	expect(t, c.do("GET", "/profile"), 302, "/signin")
	expect(t, c.do("GET", "/signin"), 200, "")
	expect(t, c.do("GET", "/courses/index.json"), 401, "")
	expect(t, c.do("GET", "/media/host/v.mp4"), 401, "")
	expect(t, c.do("POST", "/api/run"), 401, "")
	expect(t, c.do("GET", "/api/term"), 401, "") // terminals too

	login := func(c *client) string {
		rec := c.do("GET", "/auth/login")
		loc, _ := url.Parse(rec.Header().Get("Location"))
		if rec.Code != 302 || loc.Query().Get("code_challenge") == "" {
			t.Fatalf("login: %d %s", rec.Code, loc)
		}
		return loc.Query().Get("state")
	}

	// A forged state, or a callback in a browser that didn't start the login, is refused.
	state := login(c)
	expect(t, c.do("GET", "/auth/callback?code=c&state=forged"), 302, "/signin?auth_error=state_mismatch")
	state = login(c)
	other := &client{h: h}
	expect(t, other.do("GET", "/auth/callback?code=c&state="+state), 302, "state_mismatch")

	// The real flow signs in; then everything opens up, and the state can't be replayed.
	state = login(c)
	stateCookies := append([]*http.Cookie(nil), c.cookies...)
	expect(t, c.do("GET", "/auth/callback?code=c&state="+state), 302, "/")
	expect(t, c.do("GET", "/"), 200, "")
	expect(t, c.do("GET", "/signin"), 302, "/")
	expect(t, c.do("GET", "/courses/index.json"), 200, "")
	rec := c.do("POST", "/api/run", "X-User", "forged")
	if body := rec.Body.String(); rec.Code != 200 || !regexp.MustCompile(`user=[0-9a-f]{16}$`).MatchString(body) {
		t.Fatalf("signed-in proxy: %d %q", rec.Code, body)
	}
	var me struct{ User *User }
	json.NewDecoder(c.do("GET", "/auth/me").Body).Decode(&me)
	if me.User == nil || me.User.Email != "me@example.com" {
		t.Fatalf("me = %+v", me.User)
	}
	replay := &client{h: h, cookies: stateCookies}
	expect(t, replay.do("GET", "/auth/callback?code=c&state="+state), 302, "login_expired")

	// Logout locks it again.
	expect(t, c.do("POST", "/auth/logout"), 204, "")
	expect(t, c.do("GET", "/"), 302, "/signin")
	expect(t, c.do("POST", "/api/run"), 401, "")

	// An account outside ALLOWED_EMAILS is refused.
	email = "someone@else.com"
	state = login(c)
	expect(t, c.do("GET", "/auth/callback?code=c&state="+state), 302, "not_allowed")
}

// Admin routes: invisible to everyone but ADMIN_EMAILS, JSON-only, and bans/sign-outs take effect at once.
func TestAdmin(t *testing.T) {
	var email string
	google := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		if r.URL.Path == "/token" {
			io.WriteString(w, `{"access_token":"tok","token_type":"Bearer","expires_in":3600}`)
			return
		}
		json.NewEncoder(w).Encode(map[string]any{"email": email, "email_verified": true, "name": email})
	}))
	defer google.Close()
	conf := &oauth2.Config{ClientID: "id", ClientSecret: "secret", RedirectURL: "http://localhost:8000/auth/callback",
		Endpoint: oauth2.Endpoint{AuthURL: google.URL + "/auth", TokenURL: google.URL + "/token"}}
	a, h := testApp(t, conf, "")
	a.auth.userinfo = google.URL + "/userinfo"
	signIn := func(who string) (*client, *httptest.ResponseRecorder) {
		email = who
		c := &client{h: h}
		loc, _ := url.Parse(c.do("GET", "/auth/login").Header().Get("Location"))
		return c, c.do("GET", "/auth/callback?code=c&state="+loc.Query().Get("state"))
	}
	post := func(c *client, body string, hdr ...string) *httptest.ResponseRecorder {
		req := httptest.NewRequest("POST", "http://localhost:8000/admin/api/action", strings.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		for i := 0; i+1 < len(hdr); i += 2 {
			req.Header.Set(hdr[i], hdr[i+1])
		}
		for _, ck := range c.cookies {
			req.AddCookie(ck)
		}
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, req)
		return rec
	}

	anon := &client{h: h}
	member, _ := signIn("member@example.com")
	admin, _ := signIn("Admin@Example.com")

	// Not an admin: every admin route is a 404, whatever the request claims.
	for _, c := range []*client{anon, member} {
		expect(t, c.do("GET", "/admin"), 404, "")
		expect(t, c.do("GET", "/admin/api/state"), 404, "")
		expect(t, post(c, `{"action":"ban","email":"admin@example.com"}`), 404, "")
	}
	expect(t, member.do("GET", "/admin/api/state", "X-User", "admin"), 404, "")
	var me struct{ Admin bool }
	json.NewDecoder(member.do("GET", "/auth/me").Body).Decode(&me)
	if me.Admin {
		t.Fatal("member reported as admin")
	}

	// Admin: the page and state open up; forms from other sites and non-JSON bodies are refused.
	json.NewDecoder(admin.do("GET", "/auth/me").Body).Decode(&me)
	if !me.Admin {
		t.Fatal("admin not reported as admin")
	}
	expect(t, admin.do("GET", "/admin"), 200, "")
	expect(t, admin.do("GET", "/admin/api/state"), 200, "")
	expect(t, post(admin, `{"action":"ban","email":"member@example.com"}`, "Origin", "https://evil.example"), 403, "")
	expect(t, post(admin, `{"action":"ban","email":"member@example.com"}`, "Content-Type", "text/plain"), 415, "")
	expect(t, post(admin, `{"action":"ban","email":"not an email"}`), 400, "")
	expect(t, post(admin, `{"action":"ban","email":"admin@example.com"}`), 403, "") // admins come from .env
	expect(t, post(admin, `{"action":"nuke","email":"member@example.com"}`), 400, "")

	// Ban: the member is signed out at once, their containers are stopped, and they can't sign back in.
	kicks = nil
	expect(t, post(admin, `{"action":"ban","email":"Member@Example.com"}`), 200, "")
	expect(t, member.do("GET", "/"), 302, "/signin")
	if len(kicks) != 1 || !strings.Contains(kicks[0], idOf("member@example.com")) {
		t.Fatalf("kicks = %v", kicks)
	}
	if _, rec := signIn("member@example.com"); !strings.Contains(rec.Header().Get("Location"), "not_allowed") {
		t.Fatal("banned member signed in")
	}
	expect(t, post(admin, `{"action":"unban","email":"member@example.com"}`), 200, "")
	member, _ = signIn("member@example.com")
	expect(t, member.do("GET", "/"), 200, "")

	// Allow-list mode signs out whoever isn't listed; admins stay. Allowing them lets them back in.
	expect(t, post(admin, `{"action":"mode","mode":"list"}`), 200, "")
	expect(t, member.do("GET", "/"), 302, "/signin")
	expect(t, admin.do("GET", "/admin/api/state"), 200, "")
	expect(t, post(admin, `{"action":"allow","email":"member@example.com"}`), 200, "")
	member, _ = signIn("member@example.com")
	expect(t, member.do("GET", "/"), 200, "")

	// The access rules survive a restart.
	if !newAuth(conf, "", "admin@example.com", a.auth.dataDir).canSignIn("member@example.com") {
		t.Fatal("allow list not saved")
	}

	// A browser can't reach the worker's internal routes or pass its token through the proxy.
	rec := member.do("POST", "/api/run", "X-Internal-Token", "internal")
	if strings.Contains(rec.Body.String(), "token=internal") {
		t.Fatal("internal token forwarded")
	}
	expect(t, member.do("POST", "/internal/kick"), 404, "")
}
