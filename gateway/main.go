// The app's front door: serves the built React app, course data and media, handles Google sign-in (auth.go),
// and proxies /api/* to the Python worker (server/serve.py), which it starts on APP_ADDR itself.
// Run from the repo root (the image's WORKDIR /app is). Settings come from the environment, see .env.example.
package main

import (
	"bytes"
	"compress/gzip"
	"context"
	"errors"
	"html"
	"io"
	"log"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"os/exec"
	"os/signal"
	"path"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"sync/atomic"
	"syscall"
	"time"

	"golang.org/x/oauth2"
	"golang.org/x/oauth2/google"
)

type app struct {
	auth    *auth
	web     string // built React app
	courses string // course JSON + diagrams
	media   string // lesson images and videos, downloaded by tools/fetch_media.py
	api     http.Handler
	baseURL string // BASE_URL without a trailing slash, or "" (then the request's host)
	appAddr string // the Python worker
	// internalToken lets only us call the worker's /internal/ routes (kick); passed to it at startup.
	internalToken string
	hosts         map[string]bool // Host headers we answer to (blocks DNS rebinding)
	origins       map[string]bool // Origins allowed to call us (blocks other sites: CSRF)
	gz            sync.Map        // file path -> gzCache
}

type gzCache struct {
	mod  time.Time
	data []byte
}

var courseSlug = regexp.MustCompile(`^[a-z0-9-]+$`)

func (a *app) routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /{$}", a.page)
	for _, p := range []string{"profile", "settings", "achievements", "leaderboard"} {
		mux.HandleFunc("GET /"+p, a.page)
	}
	mux.HandleFunc("GET /u/{id}", a.page) // a member's profile; the worker decides what's visible
	mux.HandleFunc("GET /admin", a.requireAdmin(a.index))
	mux.HandleFunc("GET /admin/api/state", a.requireAdmin(a.adminState))
	mux.HandleFunc("POST /admin/api/action", a.requireAdmin(a.adminAction))
	mux.HandleFunc("GET /learn/{course}", a.coursePage)
	mux.HandleFunc("GET /learn/{course}/{lesson}", a.coursePage)
	mux.HandleFunc("GET /signin", a.signinPage)
	mux.HandleFunc("GET /assets/", a.static(a.web, "public, max-age=31536000, immutable")) // hashed file names
	mux.HandleFunc("GET /vendor/", a.static(a.web, "no-cache"))
	mux.HandleFunc("GET /favicon.svg", a.static(a.web, "public, max-age=86400"))
	mux.HandleFunc("GET /og.png", a.static(a.web, "public, max-age=86400")) // link preview image, public like the favicon
	mux.HandleFunc("GET /courses/", a.requireUser(a.courseData))
	mux.HandleFunc("GET /media/", a.requireUser(a.mediaFile))
	mux.HandleFunc("GET /auth/login", a.auth.login)
	mux.HandleFunc("GET /auth/callback", a.auth.callback)
	mux.HandleFunc("GET /auth/me", a.auth.me)
	mux.HandleFunc("POST /auth/logout", a.auth.logout)
	mux.Handle("/api/", a.requireUser(a.api.ServeHTTP))
	return a.guard(mux)
}

// guard: only this app's own pages, on localhost, may use it.
func (a *app) guard(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !a.hosts[r.Host] {
			http.Error(w, "Forbidden", http.StatusForbidden)
			return
		}
		if o := r.Header.Get("Origin"); o != "" && !a.origins[o] && o != "http://"+r.Host {
			http.Error(w, "Forbidden", http.StatusForbidden)
			return
		}
		h := w.Header()
		h.Set("X-Content-Type-Options", "nosniff")
		h.Set("X-Frame-Options", "DENY")
		h.Set("Referrer-Policy", "same-origin")
		next.ServeHTTP(w, r)
	})
}

func (a *app) requireUser(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if a.auth.user(r) == nil {
			http.Error(w, "Sign in first", http.StatusUnauthorized)
			return
		}
		next(w, r)
	}
}

// index serves the app's page with __BASE_URL__ filled in: link previews need absolute URLs.
func (a *app) index(w http.ResponseWriter, r *http.Request) {
	b, err := os.ReadFile(filepath.Join(a.web, "index.html"))
	if err != nil {
		http.NotFound(w, r)
		return
	}
	base := a.baseURL
	if base == "" {
		base = "http://" + r.Host // guard already limited Host to the ones we answer to
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Header().Set("Cache-Control", "no-cache")
	w.Write(bytes.ReplaceAll(b, []byte("__BASE_URL__"), []byte(html.EscapeString(base))))
}

func (a *app) page(w http.ResponseWriter, r *http.Request) {
	if a.auth.user(r) == nil {
		http.Redirect(w, r, "/signin", http.StatusFound)
		return
	}
	a.index(w, r)
}

func (a *app) coursePage(w http.ResponseWriter, r *http.Request) {
	slug := r.PathValue("course")
	if _, err := os.Stat(filepath.Join(a.courses, slug+".json")); !courseSlug.MatchString(slug) || err != nil {
		http.NotFound(w, r)
		return
	}
	a.page(w, r) // the lesson id is checked by the app, which falls back to the first unfinished lesson
}

func (a *app) signinPage(w http.ResponseWriter, r *http.Request) {
	if !a.auth.enabled() || a.auth.user(r) != nil {
		http.Redirect(w, r, "/", http.StatusFound)
		return
	}
	a.index(w, r)
}

func (a *app) static(root, cacheControl string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", cacheControl)
		a.serveFile(w, r, safeJoin(root, r.URL.Path))
	}
}

func (a *app) courseData(w http.ResponseWriter, r *http.Request) {
	rel := strings.TrimPrefix(path.Clean(r.URL.Path), "/courses/")
	if rel == "shell" || strings.HasPrefix(rel, "shell/") {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Cache-Control", "no-cache")
	a.serveFile(w, r, safeJoin(a.courses, rel))
}

// Media paths never change content (they mirror the original URL), so browsers may keep them for a long time.
func (a *app) mediaFile(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Cache-Control", "private, max-age=604800")
	a.serveFile(w, r, safeJoin(a.media, strings.TrimPrefix(r.URL.Path, "/media/")))
}

// safeJoin keeps the request path inside root ("/../x" cleans to "/x").
func safeJoin(root, p string) string {
	return filepath.Join(root, filepath.FromSlash(path.Clean("/"+p)))
}

var compressible = map[string]bool{".html": true, ".js": true, ".css": true, ".json": true, ".svg": true}

// serveFile sends a file, gzipped (and cached that way) when the browser accepts it; course JSON shrinks ~4x.
// ServeContent sets Content-Type from the name and handles If-Modified-Since and ranges.
func (a *app) serveFile(w http.ResponseWriter, r *http.Request, name string) {
	f, err := os.Open(name)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	defer f.Close()
	st, err := f.Stat()
	if err != nil || st.IsDir() {
		http.NotFound(w, r)
		return
	}
	if !compressible[filepath.Ext(name)] || !strings.Contains(r.Header.Get("Accept-Encoding"), "gzip") {
		http.ServeContent(w, r, name, st.ModTime(), f)
		return
	}
	c, ok := a.gz.Load(name)
	if !ok || !c.(gzCache).mod.Equal(st.ModTime()) {
		var buf bytes.Buffer
		zw := gzip.NewWriter(&buf)
		if _, err := io.Copy(zw, f); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		zw.Close()
		c = gzCache{st.ModTime(), buf.Bytes()}
		a.gz.Store(name, c)
	}
	w.Header().Set("Content-Encoding", "gzip")
	w.Header().Add("Vary", "Accept-Encoding")
	http.ServeContent(w, r, name, st.ModTime(), bytes.NewReader(c.(gzCache).data))
}

func apiProxy(addr string, au *auth) http.Handler {
	target := &url.URL{Scheme: "http", Host: addr}
	return &httputil.ReverseProxy{ // also carries the terminals' WebSocket upgrades
		Rewrite: func(pr *httputil.ProxyRequest) {
			pr.SetURL(target)
			pr.Out.Header.Del("Origin") // checked by guard; the worker only trusts requests from here
			pr.Out.Header.Del("X-Internal-Token")
			// Who this is, for per-user progress and containers. Always set here, so a browser can't pick it.
			pr.Out.Header.Set("X-User", au.userID(pr.In))
		},
		ErrorHandler: func(w http.ResponseWriter, r *http.Request, err error) {
			log.Printf("api: %v", err)
			http.Error(w, "The app worker isn't running", http.StatusBadGateway)
		},
	}
}

func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func main() {
	addr, appAddr := env("ADDR", "127.0.0.1:8000"), env("APP_ADDR", "127.0.0.1:8002")
	_, port, err := net.SplitHostPort(addr)
	if err != nil {
		log.Fatalf("ADDR: %v", err)
	}

	var conf *oauth2.Config
	if id := os.Getenv("GOOGLE_CLIENT_ID"); id != "" {
		conf = &oauth2.Config{
			ClientID: id, ClientSecret: os.Getenv("GOOGLE_CLIENT_SECRET"), Endpoint: google.Endpoint,
			RedirectURL: strings.TrimRight(env("BASE_URL", "http://localhost:"+port), "/") + "/auth/callback",
			Scopes:      []string{"openid", "email", "profile"},
		}
		if conf.ClientSecret == "" {
			log.Fatal("GOOGLE_CLIENT_ID is set but GOOGLE_CLIENT_SECRET isn't")
		}
	}
	a := &app{
		auth: newAuth(conf, os.Getenv("ALLOWED_EMAILS"), os.Getenv("ADMIN_EMAILS"), env("DATA_DIR", "data")), appAddr: appAddr, internalToken: randomToken(), web: env("WEB_DIR", "web/dist"), courses: env("COURSES_DIR", "courses"), media: env("MEDIA_DIR", "media"),
		hosts:   map[string]bool{"localhost:" + port: true, "127.0.0.1:" + port: true},
		origins: map[string]bool{"http://localhost:5173": true}, // the Vite dev server (cd web && bun run dev)
	}
	a.api = apiProxy(appAddr, a.auth)
	if len(a.auth.admins) > 0 && !a.auth.enabled() {
		log.Printf("ADMIN_EMAILS is set but Google sign-in is off: the admin page needs sign-in")
	}
	// Hosted: BASE_URL is the public address (e.g. https://learn.example.com, TLS ended by a reverse proxy).
	if base := os.Getenv("BASE_URL"); base != "" {
		u, err := url.Parse(base)
		if err != nil || u.Host == "" {
			log.Fatalf("BASE_URL: %q isn't a URL", base)
		}
		a.hosts[u.Host] = true
		a.baseURL = strings.TrimRight(base, "/")
		a.origins[u.Scheme+"://"+u.Host] = true
		secureCookies = u.Scheme == "https"
	}
	if _, err := os.Stat(filepath.Join(a.web, "index.html")); err != nil {
		log.Fatalf("no built UI in %s: cd web && bun install && bun run build", a.web)
	}

	// The worker runs code and terminals; it dies with us and we die with it.
	_, appPort, _ := net.SplitHostPort(appAddr)
	worker := exec.Command("python3", "server/serve.py")
	worker.Env = append(os.Environ(), "PORT="+appPort, "INTERNAL_TOKEN="+a.internalToken)
	worker.Stdout, worker.Stderr = os.Stdout, os.Stderr
	if err := worker.Start(); err != nil {
		log.Fatalf("starting the Python worker: %v", err)
	}
	var stopping atomic.Bool
	done := make(chan struct{})
	go func() {
		err := worker.Wait()
		close(done)
		if !stopping.Load() {
			log.Fatalf("the Python worker exited: %v", err)
		}
	}()
	// Open the doors only once the worker listens, so the first page load's API calls don't hit a 502.
	for start := time.Now(); ; time.Sleep(50 * time.Millisecond) {
		if c, err := net.DialTimeout("tcp", appAddr, time.Second); err == nil {
			c.Close()
			break
		}
		if time.Since(start) > 30*time.Second {
			log.Fatalf("the Python worker didn't start listening on %s", appAddr)
		}
	}

	srv := &http.Server{Addr: addr, Handler: a.routes(), ReadHeaderTimeout: 10 * time.Second}
	go func() {
		ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
		defer stop()
		<-ctx.Done()
		stopping.Store(true)
		worker.Process.Signal(syscall.SIGTERM) // it removes the Linux sandboxes on the way out
		select {
		case <-done:
		case <-time.After(15 * time.Second):
			worker.Process.Kill()
		}
		srv.Close()
	}()

	signin := "off"
	if a.auth.enabled() {
		signin = "on, redirect URI " + conf.RedirectURL
	}
	log.Printf("Courses running at http://localhost:%s (Google sign-in %s)", port, signin)
	if err := srv.ListenAndServe(); !errors.Is(err, http.ErrServerClosed) {
		stopping.Store(true)
		worker.Process.Kill()
		log.Fatal(err)
	}
	<-done
}
