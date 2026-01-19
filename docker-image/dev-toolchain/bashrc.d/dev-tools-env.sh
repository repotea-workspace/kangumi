# Homebrew environment
if [ -d /home/linuxbrew/.linuxbrew ]; then
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
fi

# Source dev-tools environment (custom tools like HarmonyOS)
if [ -f /etc/profile.d/99-dev-tools-env.sh ]; then
    source /etc/profile.d/99-dev-tools-env.sh
fi
