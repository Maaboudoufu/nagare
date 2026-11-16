" Neovim reads this for everyone in the image (/etc/xdg/nvim/sysinit.vim), before your own ~/.config/nvim/init.lua.
lua dofile('/etc/xdg/nvim/workspace.lua')
