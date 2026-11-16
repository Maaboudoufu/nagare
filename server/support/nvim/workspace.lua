-- The workspace editor: plain Neovim, set up with what it already has. No plugins and nothing downloaded, at build or
-- at run time. The three language servers it starts (tofu-ls, gopls, pylsp) are part of the image. Yours to override:
-- anything in ~/.config/nvim/init.lua runs after this.
local o, map = vim.o, vim.keymap.set
vim.g.mapleader = " "

o.number, o.cursorline, o.signcolumn, o.scrolloff = true, true, "yes", 4
o.expandtab, o.shiftwidth, o.tabstop, o.smartindent = true, 2, 2, true
o.ignorecase, o.smartcase = true, true
o.splitright, o.splitbelow = true, true
o.undofile, o.swapfile, o.mouse, o.updatetime = true, false, "a", 300
o.termguicolors = vim.env.COLORTERM == "truecolor"
o.completeopt = "menuone,noselect,popup,fuzzy"
o.grepprg, o.grepformat = "rg --vimgrep --smart-case", "%f:%l:%c:%m"
vim.g.netrw_banner, vim.g.netrw_liststyle = 0, 3 -- the file list as a tree, without the header

-- Status line: mode, file, what's wrong, where you are. The last line of the screen says how to get help.
local modes = { n = "NORMAL", i = "INSERT", v = "VISUAL", V = "V-LINE", ["\22"] = "V-BLOCK", c = "COMMAND", R = "REPLACE", t = "TERMINAL" }
function _G.WorkspaceStatus()
  local problems = #vim.diagnostic.get(0, { severity = { min = vim.diagnostic.severity.WARN } })
  return table.concat({
    " ", modes[vim.fn.mode()] or vim.fn.mode(), " | %f%m%r",
    problems > 0 and ("  " .. problems .. " problem" .. (problems > 1 and "s" or "")) or "",
    "%=", vim.bo.filetype, " | %l:%c | space ? for keys ",
  })
end
o.statusline = "%!v:lua.WorkspaceStatus()"

-- Keys. Space is the leader.
local keys = {
  { "<leader>w", "<cmd>write<cr>", "Save" },
  { "<leader>q", "<cmd>quit<cr>", "Quit" },
  { "<leader>e", "<cmd>Lexplore 28<cr>", "File tree (again to close)" },
  { "<leader>f", ":find ", "Find a file by name (Tab completes)" },
  { "<leader>/", ":silent grep  | copen<s-left><s-left><left>", "Search in all files" },
  { "<leader>b", "<cmd>buffers<cr>:buffer ", "Switch between open files" },
  { "<leader>d", vim.diagnostic.open_float, "Explain the problem on this line" },
  { "<leader>c", function() vim.lsp.buf.format({ async = false }) end, "Format the file" },
  { "<esc>", "<cmd>nohlsearch<cr>", "Clear search highlights" },
}
for _, k in ipairs(keys) do
  map("n", k[1], k[2], { desc = k[3], silent = type(k[2]) == "function" or k[2]:sub(1, 1) ~= ":" })
end
map("n", "<leader>?", function()
  local lines = { "i  type          Esc  stop typing        :wq  save and quit     :q!  quit without saving",
    "u  undo          Ctrl-r  redo            gcc  comment a line    K  docs for the word under the cursor",
    "gd  go to definition    grn  rename    grr  where it's used    Tab / Shift-Tab  pick a suggestion", "" }
  for _, k in ipairs(keys) do
    lines[#lines + 1] = ("%-10s %s"):format(k[1]:gsub("<leader>", "space "), k[3])
  end
  vim.notify(table.concat(lines, "\n"))
end, { desc = "Show the keys" })
map("i", "<tab>", function() return vim.fn.pumvisible() == 1 and "<c-n>" or "<tab>" end, { expr = true })
map("i", "<s-tab>", function() return vim.fn.pumvisible() == 1 and "<c-p>" or "<s-tab>" end, { expr = true })

-- Find files by name with what the image has (fd), matched loosely, so `:find mntf` gets main.tf.
function _G.WorkspaceFind(arg)
  local files = vim.fn.systemlist("fdfind --type f --hidden --exclude .git --exclude .terraform --exclude node_modules")
  return #arg == 0 and files or vim.fn.matchfuzzy(files, arg)
end
if vim.fn.executable("fdfind") == 1 then
  o.findfunc = "v:lua.WorkspaceFind"
end

local group = vim.api.nvim_create_augroup("workspace", {})
vim.api.nvim_create_autocmd("TextYankPost", { group = group, callback = function() vim.hl.on_yank() end })
-- Languages whose parser ships with Neovim get it; the rest use Neovim's own syntax files.
vim.api.nvim_create_autocmd("FileType", { group = group, callback = function(ev) pcall(vim.treesitter.start, ev.buf) end })
vim.filetype.add({ extension = { tf = "terraform", tfvars = "terraform-vars", tofu = "terraform" } })

-- Language servers: suggestions as you type, problems underlined, docs on K, and formatting on save.
vim.lsp.config("tofu-ls", {
  cmd = { "tofu-ls", "serve" },
  filetypes = { "terraform", "terraform-vars" },
  -- A Terraform module is a folder: the file's own folder is the project, initialized or not.
  root_dir = function(buf, found) found(vim.fs.dirname(vim.api.nvim_buf_get_name(buf))) end,
})
vim.lsp.config("gopls", { cmd = { "gopls" }, filetypes = { "go", "gomod" }, root_markers = { "go.mod", ".git" } })
vim.lsp.config("pylsp", { cmd = { "pylsp" }, filetypes = { "python" }, root_markers = { "pyproject.toml", ".git" } })
for _, server in ipairs({ "tofu-ls", "gopls", "pylsp" }) do
  if vim.fn.executable(vim.lsp.config[server].cmd[1]) == 1 then
    vim.lsp.enable(server)
  end
end
vim.diagnostic.config({ virtual_text = true, severity_sort = true })
vim.api.nvim_create_autocmd("LspAttach", {
  group = group,
  callback = function(ev)
    local client = assert(vim.lsp.get_client_by_id(ev.data.client_id))
    if client:supports_method("textDocument/completion") then
      vim.lsp.completion.enable(true, client.id, ev.buf, { autotrigger = true })
    end
    if client:supports_method("textDocument/formatting") then
      vim.api.nvim_create_autocmd("BufWritePre", {
        group = group,
        buffer = ev.buf,
        callback = function() vim.lsp.buf.format({ bufnr = ev.buf, id = client.id, timeout_ms = 3000 }) end,
      })
    end
  end,
})
