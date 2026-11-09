# Terminal for CLI lessons: runs in your project folder with every tool from the Docker image.
# Your own ~/.bashrc is skipped on purpose: it's written for your machine, not this container.
PS1='\[\e[1;32m\]courses\[\e[0m\]:\[\e[1;34m\]\w\[\e[0m\]\$ '
alias ls='ls --color=auto' grep='grep --color=auto'
