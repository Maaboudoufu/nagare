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
        less nano vim python3-pylsp ripgrep fd-find netcat-openbsd sudo procps man-db file tree \
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

# OpenTofu for the Terraform course. The two providers its lessons use are mirrored into the image and checked against
# server/support/tofu/.terraform.lock.hcl, so `tofu init` in a workspace needs no network.
ARG TOFU_VERSION=1.13.9
ARG TOFU_SHA256_x86_64=bc44eb6b06446ba83bd4072114891987f590f66cca712737a7f1147c50c539ce
ARG TOFU_SHA256_aarch64=04f7c93828b859d420269ed30f923ffebf09157b5d7fb95bf8d88a4d208b7fa3
RUN arch=$(uname -m) && case $arch in x86_64) a=amd64 sum=$TOFU_SHA256_x86_64 ;; aarch64) a=arm64 sum=$TOFU_SHA256_aarch64 ;; *) exit 1 ;; esac \
    && curl -fsSL "https://github.com/opentofu/opentofu/releases/download/v${TOFU_VERSION}/tofu_${TOFU_VERSION}_linux_${a}.zip" -o /tmp/tofu.zip \
    && echo "$sum  /tmp/tofu.zip" | sha256sum -c - \
    && unzip -q /tmp/tofu.zip tofu -d /usr/local/bin && rm /tmp/tofu.zip
COPY server/support/tofu /opt/tofu
RUN cd /opt/tofu && tofu providers mirror providers \
    && TF_CLI_CONFIG_FILE=/opt/tofu/tofurc tofu init -lockfile=readonly && rm -rf .terraform
ENV TF_CLI_CONFIG_FILE=/opt/tofu/tofurc

# The terminal's editor: Neovim with no plugins (server/support/nvim), and the language servers it talks to. tofu-ls is
# what formats and completes Terraform; gopls comes from the Go checksum database at this exact version; pylsp is the
# Debian package above. Nothing is fetched when the editor runs.
ARG NVIM_VERSION=0.12.6
ARG NVIM_SHA256_x86_64=474430d53e6264f6d6dd18db42d6dc9df3a1b56ca9e88a325bbf860e1a811d87
ARG NVIM_SHA256_aarch64=8f1f64a0bdb97247034038c3823c6cbad5bdf9ecd5751b85494b71c3ee04c815
ARG TOFU_LS_VERSION=0.5.3
ARG TOFU_LS_SHA256_x86_64=ccf8d85881f493483c9c20ac010d320bf455fdc9dcc39ba0af515206cb488460
ARG TOFU_LS_SHA256_aarch64=d30430f86720100e6fc6d16881fcf16bc9e4cb3c4d221fafc1aa992f01387db0
ARG GOPLS_VERSION=0.24.0
RUN arch=$(uname -m) && case $arch in \
        x86_64) n=x86_64 nsum=$NVIM_SHA256_x86_64 lsum=$TOFU_LS_SHA256_x86_64 ;; \
        aarch64) n=arm64 nsum=$NVIM_SHA256_aarch64 lsum=$TOFU_LS_SHA256_aarch64 ;; \
        *) exit 1 ;; esac \
    && curl -fsSL "https://github.com/neovim/neovim/releases/download/v${NVIM_VERSION}/nvim-linux-${n}.tar.gz" -o /tmp/nvim.tar.gz \
    && echo "$nsum  /tmp/nvim.tar.gz" | sha256sum -c - \
    && mkdir /opt/nvim && tar -xzf /tmp/nvim.tar.gz -C /opt/nvim --strip-components=1 && ln -s /opt/nvim/bin/nvim /usr/local/bin/nvim \
    && curl -fsSL "https://github.com/opentofu/tofu-ls/releases/download/v${TOFU_LS_VERSION}/tofu-ls_Linux_${n}.tar.gz" -o /tmp/tofu-ls.tar.gz \
    && echo "$lsum  /tmp/tofu-ls.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/tofu-ls.tar.gz -C /usr/local/bin tofu-ls \
    && GOBIN=/usr/local/bin GOFLAGS=-mod=mod go install "golang.org/x/tools/gopls@v${GOPLS_VERSION}" \
    && go clean -modcache && rm -rf /tmp/nvim.tar.gz /tmp/tofu-ls.tar.gz /root/.cache/go-build
COPY server/support/nvim /etc/xdg/nvim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
# New workspace volumes copy /home/user: a warm Go build cache makes the first Go run ~1s instead of ~10s.
USER user
RUN mkdir -p /tmp/warm && cd /tmp/warm && go mod init warm \
    && printf 'package main\nimport ("encoding/json"; "errors"; "fmt"; "math"; "net/http"; "os"; "sort"; "strings"; "sync"; "time")\nvar _ = []any{json.Marshal, http.Get, sort.Ints, new(sync.Mutex)}\nfunc main() { fmt.Println(errors.New("x"), strings.ToUpper("x"), time.Now(), math.Pi, os.Args) }\n' > main.go \
    && printf 'package main\nimport "testing"\nfunc TestX(t *testing.T) {}\n' > main_test.go \
    && GOTOOLCHAIN=local go build -o /dev/null . && GOTOOLCHAIN=local go test -count=1 . >/dev/null && cd / && rm -rf /tmp/warm
USER root
# What a learner installs themselves (go install, npm install -g) goes in their home folder, which is their volume:
# it's still there after the container is replaced. npm's own default (/usr/local) isn't theirs to write to.
ENV GOPATH=/home/user/go NPM_CONFIG_PREFIX=/home/user/.npm-global
ENV PATH=/home/user/go/bin:/home/user/.npm-global/bin:$PATH
WORKDIR /app
COPY server/support/sandbox.bashrc /etc/sandbox.bashrc
COPY courses courses
COPY sandboxes sandboxes
COPY media.lock.json ./
COPY tools/fetch_media.py tools/
COPY server server
COPY --from=web /web/dist web/dist
COPY --from=gateway /nagare-gateway /usr/local/bin/nagare-gateway
EXPOSE 8000
CMD ["nagare-gateway"]
