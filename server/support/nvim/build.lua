-- Run once by the Dockerfile (NVIM_BUILD=1 nvim --headless -c "luafile build.lua"): puts every plugin at its commit
-- in lazy-lock.json, compiles the parsers, and fails the build if anything is missing.
local ok, err = pcall(function()
  require("lazy").restore({ wait = true, show = false })
  require("lazy").load({ plugins = { "nvim-treesitter" } })
  local TS = require("nvim-treesitter")
  TS.install(vim.g.workspace_parsers, { summary = true }):wait(900000)
  local have = TS.get_installed()
  local missing = vim.tbl_filter(function(lang)
    return not vim.list_contains(have, lang)
  end, vim.g.workspace_parsers)
  assert(#missing == 0, "parsers not installed: " .. table.concat(missing, ", "))
  for name, plugin in pairs(require("lazy.core.config").plugins) do
    assert(plugin._.installed, "plugin not installed: " .. name)
  end
end)
if not ok then
  io.stderr:write(tostring(err) .. "\n")
  vim.cmd("cquit 1")
end
vim.cmd("qa")
