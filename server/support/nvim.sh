#!/bin/sh
# Neovim with the LazyVim setup that ships in the image (/opt/nvim/config/nvim, from server/support/nvim).
# Your own ~/.config/nvim wins if you make one.
[ -e "$HOME/.config/nvim" ] || export XDG_CONFIG_HOME=/opt/nvim/config
exec /opt/nvim/bin/nvim "$@"
