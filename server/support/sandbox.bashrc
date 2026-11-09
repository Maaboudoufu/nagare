# Learn Linux sandbox shell. Every command is logged so the lesson checks can see your last one.
export HISTFILE=/tmp/.shell_history HISTSIZE=10000 HISTFILESIZE=10000 HISTCONTROL=
PROMPT_COMMAND='history -a'
PS1='\[\e[1;32m\]user@worldbanc\[\e[0m\]:\[\e[1;34m\]\w\[\e[0m\]\$ '
alias ls='ls --color=auto' grep='grep --color=auto'
if [ -f /tmp/.lesson_init.sh ]; then  # the lesson's setup (e.g. making a script executable)
  bash /tmp/.lesson_init.sh >/dev/null 2>&1
  rm -f /tmp/.lesson_init.sh
fi
