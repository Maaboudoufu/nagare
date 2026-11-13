# Learn Linux sandbox shell.
# One typed line is one history entry. A lesson with one check reads the last line.
# A lesson with several checks sets NAGARE_RECORD_COMMANDS and reads each simple command.
export HISTFILE=/tmp/.shell_history HISTSIZE=10000 HISTFILESIZE=10000 HISTCONTROL=
PROMPT_COMMAND='history -a'
PS1='\[\e[1;32m\]user@worldbanc\[\e[0m\]:\[\e[1;34m\]\w\[\e[0m\]\$ '
alias ls='ls --color=auto' grep='grep --color=auto'
if [ -f /tmp/.lesson_init.sh ]; then  # the lesson's setup (e.g. making a script executable)
  bash /tmp/.lesson_init.sh >/dev/null 2>&1
  rm -f /tmp/.lesson_init.sh
fi
# Multi-check lessons only, and only after setup, so lesson init is not graded.
# The trap is not inherited by functions, subshells, or scripts.
if [ "${NAGARE_RECORD_COMMANDS:-}" = 1 ]; then
  # functrace is left off, so the history -a inside this function is not recorded.
  _nagare_prompt() { history -a; }
  PROMPT_COMMAND=_nagare_prompt
  _nagare_log_command() {
    [ "$1" = _nagare_prompt ] && return
    printf '%s\0' "$1" >> /tmp/.shell_commands
  }
  trap '_nagare_log_command "$BASH_COMMAND"' DEBUG
fi
