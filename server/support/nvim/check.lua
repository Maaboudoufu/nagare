-- CI, in the built image with no network and as the workspace user:
--   nvim --headless main.tf -c "luafile /etc/xdg/nvim/check.lua"
-- Opens a badly formatted file and fails unless the language server attaches, saving formats it, and nothing complained.
local function fail(why)
  io.stderr:write(why .. "\nmessages: " .. vim.fn.execute("messages") .. "\n")
  vim.cmd("cquit 1")
end
local attached = vim.wait(20000, function() return #vim.lsp.get_clients({ bufnr = 0 }) > 0 end, 100)
if not attached then
  fail("no language server attached for filetype '" .. vim.bo.filetype .. "'")
end
local before = table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n")
vim.cmd("silent write")
local after = table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n")
if after == before then
  fail("saving did not format the file")
end
local messages = vim.trim(vim.fn.execute("messages"))
if messages ~= "" then
  fail("unexpected messages")
end
io.stdout:write(("ok: %s, formatted on save by %s\n"):format(vim.bo.filetype, vim.lsp.get_clients({ bufnr = 0 })[1].name))
vim.cmd("qa!")
