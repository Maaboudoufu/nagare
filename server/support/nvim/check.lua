-- CI, in the built image with no network and as the workspace user:
--   nvim --headless main.tf -c "luafile /opt/nvim/config/nvim/check.lua"
-- Fails unless every plugin is there, the file is highlighted by its parser, and nothing complained on the way.
vim.wait(5000, function()
  return false
end) -- let the lazy-loaded plugins and anything they start in the background settle
local problems = {}
for name, plugin in pairs(require("lazy.core.config").plugins) do
  if not plugin._.installed then
    problems[#problems + 1] = "plugin not installed: " .. name
  end
end
if not vim.treesitter.highlighter.active[vim.api.nvim_get_current_buf()] then
  problems[#problems + 1] = "no syntax parser running for filetype '" .. vim.bo.filetype .. "'"
end
local messages = vim.trim(vim.fn.execute("messages"))
if messages ~= "" then
  problems[#problems + 1] = "messages: " .. messages
end
for _, note in ipairs(Snacks.notifier.get_history()) do
  if note.level == "error" or note.level == "warn" then
    problems[#problems + 1] = "notification: " .. tostring(note.msg)
  end
end
if #problems > 0 then
  io.stderr:write(table.concat(problems, "\n") .. "\n")
  vim.cmd("cquit 1")
end
io.stdout:write(("ok: LazyVim, %d plugins, %s highlighted\n"):format(require("lazy").stats().count, vim.bo.filetype))
vim.cmd("qa!")
