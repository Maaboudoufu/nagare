# Terminal for CLI lessons: runs in your project folder with every tool from the Docker image.
# This file is part of the image, not of your files: the terminal doesn't read ~/.bashrc or anything else in your home
# folder to start, so deleting or breaking a file there can never leave you without a shell. To load your own settings
# for a session, run:  . ~/.bashrc
PS1='\[\e[1;32m\]courses\[\e[0m\]:\[\e[1;34m\]\w\[\e[0m\]\$ '
alias ls='ls --color=auto' grep='grep --color=auto'
