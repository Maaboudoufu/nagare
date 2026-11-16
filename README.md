# Nagare

### About
- Hi. This open-sources learning courses for free by self-hosting the already written deterministic content, allowing users to self host it on their own compute.
- I wanted this to be super plug-and-play, straight to the point, and still gamified for anyone with autism, ADHD, or any other mental disabilities. Oh, I also wanted VIM in here because other learning platforms don't have it and its more aura.
- Nothing in this is monetized.

### Layout
| Folder | What's in it |
| --- | --- |
| `gateway/` | The Go front door: pages, sign-in, course files and media, and the proxy to the worker. |
| `server/` | The Python worker: runs code and checks in each learner's own container, keeps progress and XP. |
| `web/` | The React app. |
| `courses/` | The lessons, one JSON file per course, plus `index.json` (the catalogue) and translations. |
| `sandboxes/` | Starter files and checks for the Learn Linux terminal lessons. Never served to browsers. |
| `tools/` | Scripts that build or check content: the Terraform course, the medals, media, translations. |

`docker compose up -d` runs it; `.env.example` lists the settings.
