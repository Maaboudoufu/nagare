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
		io.WriteString(w, "worker:"+r.URL.Path+" origin="+r.Header.Get("Origin")+" user="+r.Header.Get("X-User"))
	}))
	t.Cleanup(worker.Close)
	a := &app{auth: newAuth(conf, allowed), web: filepath.Join(dir, "web"), courses: filepath.Join(dir, "courses"), media: filepath.Join(dir, "media"),
		hosts: map[string]bool{"localhost:8000": true}, origins: map[string]bool{}}
	a.api = apiProxy(strings.TrimPrefix(worker.URL, "http://"), a.auth)
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
	if body := rec.Body.String(); rec.Code != 200 || body != "worker:/api/run origin= user=local" {
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
