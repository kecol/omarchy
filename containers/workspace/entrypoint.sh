#!/bin/bash
set -euo pipefail
umask 077
mkdir -p "$HOME/.omarchy-sshd" "$HOME/.codex" /run/omarchy-workspace /run/sshd
if [[ ! -f $HOME/.omarchy-sshd/host_ed25519 ]]; then
  ssh-keygen -q -t ed25519 -N '' -f "$HOME/.omarchy-sshd/host_ed25519"
fi
/usr/sbin/sshd -t -f /etc/omarchy-workspace/sshd_config
exec /usr/sbin/sshd -D -e -f /etc/omarchy-workspace/sshd_config
