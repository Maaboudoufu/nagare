-- Neovim in workspaces: LazyVim, with every plugin and parser already in the image (/opt/nvim, pinned by
-- lazy-lock.json). Nothing is downloaded or built when you open the editor, and none of it lives in your home folder,
-- so deleting files there can't break it. To use your own setup instead, create ~/.config/nvim (/usr/local/bin/nvim).
local base = vim.fs.dirname(vim.fs.dirname(vim.fn.stdpath("config"))) -- /opt/nvim
local building = vim.env.NVIM_BUILD == "1" -- the Dockerfile's one run that installs everything (build.lua)

-- Syntax parsers compiled into the image: LazyVim's own list, plus what the courses use.
vim.g.workspace_parsers = {
  "bash", "c", "css", "diff", "dockerfile", "git_rebase", "gitcommit", "go", "gomod", "hcl", "html", "javascript",
  "jsdoc", "json", "lua", "luadoc", "luap", "make", "markdown", "markdown_inline", "printf", "python", "query", "regex",
  "sql", "terraform", "toml", "tsx", "typescript", "vim", "vimdoc", "xml", "yaml",
}

vim.opt.rtp:prepend(base .. "/lazy/lazy.nvim")

require("lazy").setup({
  spec = {
    { "LazyVim/LazyVim", import = "lazyvim.plugins", opts = { news = { lazyvim = false, neovim = false } } },
    {
      "nvim-treesitter/nvim-treesitter",
      opts = function(_, opts)
        opts.install_dir = base .. "/site"
        opts.ensure_installed = building and {} or vim.g.workspace_parsers -- build.lua installs them, and waits
      end,
    },
    -- Nothing is downloaded on first start: no formatters, no language servers. Install the ones you want with
    -- :Mason; they go in your home folder and are picked up from there.
    {
      "mason-org/mason.nvim",
      opts = function(_, opts)
        opts.ensure_installed = {}
      end,
    },
    { "neovim/nvim-lspconfig", opts = { servers = { lua_ls = { enabled = false } } } },
    -- The pure-Lua matcher: the default one downloads a binary into the plugin's folder.
    { "saghen/blink.cmp", opts = { fuzzy = { implementation = "lua" } } },
  },
  root = base .. "/lazy",
  lockfile = base .. "/config/nvim/lazy-lock.json",
  defaults = { lazy = false, version = false },
  install = { missing = building, colorscheme = { "tokyonight", "habamax" } },
  checker = { enabled = false }, -- updates come with the image
  change_detection = { enabled = false },
  rocks = { enabled = false },
  performance = {
    rtp = { disabled_plugins = { "gzip", "tarPlugin", "tohtml", "tutor", "zipPlugin" } },
  },
})
