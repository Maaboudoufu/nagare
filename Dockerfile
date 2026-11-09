# The app and every lesson toolchain; also the image for users' workspaces and sandboxes.
# Every input is pinned (digests, Debian snapshot, lockfiles, checksums): to update one, change its pin.
ARG GOLANG_IMAGE=golang:1.27.3-trixie@sha256:af1bfc2614ebb1dbd31af514b78740fd678850e76498762b425ecee4c5c6ea80
ARG BUN_IMAGE=oven/bun:1.4.4@sha256:1d22548f177f4ff38e0c15baa3c2c46c6c2060ba2d1bc573bb4720b407548f1d
ARG DOCKER_CLI_IMAGE=docker:29.9.2-cli@sha256:5e6baf67325a79f64ed3bed6863954d5e05d0f3d4e57cbdb14809346814bbfdb
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.13.4@sha256:9f130421e930bfbdc563c00740466603f8723158e90297d07957c2294640262b
ARG FLOCI_IMAGE=floci/floci:2.4.0@sha256:5ee85db604c4aa74ac76e07ea5cc83086f37bb472bf3dbb97e34019e48efae9c

FROM ${DOCKER_CLI_IMAGE} AS docker-cli
FROM ${UV_IMAGE} AS uv
FROM ${FLOCI_IMAGE} AS floci

FROM ${BUN_IMAGE} AS web
WORKDIR /web
COPY web/package.json web/bun.lock ./
RUN bun install --frozen-lockfile --ignore-scripts
COPY web/ ./
RUN bun --bun run build

FROM ${GOLANG_IMAGE} AS gateway
ENV GOTOOLCHAIN=local GOFLAGS=-mod=readonly
WORKDIR /gateway
COPY gateway/go.mod gateway/go.sum ./
RUN go mod download && go mod verify
COPY gateway/*.go ./
RUN CGO_ENABLED=0 go build -trimpath -ldflags=-s -o /nagare-gateway .

FROM ${GOLANG_IMAGE}
# The snapshot the base image was built from (its /etc/apt/sources.list.d).
ARG DEBIAN_SNAPSHOT=20261104T212339Z
RUN sed -i -e "s#http://deb.debian.org/debian-security#http://snapshot.debian.org/archive/debian-security/${DEBIAN_SNAPSHOT}#" \
           -e "s#http://deb.debian.org/debian\$#http://snapshot.debian.org/archive/debian/${DEBIAN_SNAPSHOT}#" \
           /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Check-Valid-Until=false update \
    && apt-get install -y --no-install-recommends \
        python3 python3-pytest jq postgresql-client sqlite3 gh unzip zip nodejs npm \
        less nano vim-tiny sudo procps man-db file tree \
    && rm -rf /var/lib/apt/lists/*
# Sandbox user; passwordless sudo for the Learn Linux permissions lessons.
RUN useradd -m -u 1000 -s /bin/bash user && echo 'user ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/user
COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=uv /uv /uvx /usr/local/bin/
COPY --from=web /usr/local/bin/bun /usr/local/bin/bun
# Floci: local AWS emulator for the AWS course.
COPY --from=floci /app/application /usr/local/bin/floci
# Regenerate after editing requirements.in:
#   docker run --rm -v "$PWD/server:/s" nagare uv pip compile /s/requirements.in --python-version 3.13 --generate-hashes --no-header -o /s/requirements.lock
COPY server/requirements.lock /tmp/requirements.lock
RUN uv pip install --system --break-system-packages --no-cache --require-hashes -r /tmp/requirements.lock && rm /tmp/requirements.lock
ARG AWSCLI_VERSION=2.39.4
ARG AWSCLI_SHA256_x86_64=5153610ddd5dff13d43b2965c92d58f16e9f3f54164eea76d3abb29f38787597
ARG AWSCLI_SHA256_aarch64=76e4ac0f82b5b1ec68dfc747705fa3298c05e22648e5503f1869f0d035ad57bb
RUN arch=$(uname -m) && case $arch in x86_64) sum=$AWSCLI_SHA256_x86_64 ;; aarch64) sum=$AWSCLI_SHA256_aarch64 ;; *) exit 1 ;; esac \
    && curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-${arch}-${AWSCLI_VERSION}.zip" -o /tmp/aws.zip \
    && echo "$sum  /tmp/aws.zip" | sha256sum -c - \
    && unzip -q /tmp/aws.zip -d /tmp && /tmp/aws/install && rm -rf /tmp/aws /tmp/aws.zip

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
# New workspace volumes copy /home/user: a warm Go build cache makes the first Go run ~1s instead of ~10s.
USER user
RUN mkdir -p /tmp/warm && cd /tmp/warm && go mod init warm \
    && printf 'package main\nimport ("encoding/json"; "errors"; "fmt"; "math"; "net/http"; "os"; "sort"; "strings"; "sync"; "time")\nvar _ = []any{json.Marshal, http.Get, sort.Ints, new(sync.Mutex)}\nfunc main() { fmt.Println(errors.New("x"), strings.ToUpper("x"), time.Now(), math.Pi, os.Args) }\n' > main.go \
    && printf 'package main\nimport "testing"\nfunc TestX(t *testing.T) {}\n' > main_test.go \
    && GOTOOLCHAIN=local go build -o /dev/null . && GOTOOLCHAIN=local go test -count=1 . >/dev/null && cd / && rm -rf /tmp/warm
USER root
WORKDIR /app
COPY server/support/sandbox.bashrc /etc/sandbox.bashrc
COPY courses courses
COPY media.lock.json ./
COPY tools/fetch_media.py tools/
COPY server server
COPY --from=web /web/dist web/dist
COPY --from=gateway /nagare-gateway /usr/local/bin/nagare-gateway
EXPOSE 8000
CMD ["nagare-gateway"]
