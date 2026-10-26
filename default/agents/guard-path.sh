# Shell-only PATH handling. No processes, mode reads, or tool execution.
# Keep the opt-in guard directory ahead of mise's prompt-time PATH changes.
omarchy_agent_guard_path() {
  local directory="${XDG_DATA_HOME:-$HOME/.local/share}/omarchy/agents/command-guards/bin"
  [[ -d $directory ]] || return 0
  omarchy_agent_guard_unpath
  export PATH="$directory:$PATH"
}

omarchy_agent_guard_init() {
  omarchy_agent_guard_path
  [[ $- == *i* ]] || return 0
  # Run after mise's prompt hook, without a process or a mode-file poll.
  if [[ -v PROMPT_COMMAND && ${PROMPT_COMMAND@a} == *a* ]]; then
    [[ " ${PROMPT_COMMAND[*]} " == *" omarchy_agent_guard_path "* ]] || PROMPT_COMMAND+=(omarchy_agent_guard_path)
  elif [[ ${PROMPT_COMMAND:-} != *omarchy_agent_guard_path* ]]; then
    PROMPT_COMMAND="${PROMPT_COMMAND:+$PROMPT_COMMAND;}omarchy_agent_guard_path"
  fi
}

# Deliberate Omarchy Host/maintenance launches bypass guards only in their
# child process. Never change the saved execution default or installed tools.
omarchy_agent_guard_unpath() {
  local directory="${XDG_DATA_HOME:-$HOME/.local/share}/omarchy/agents/command-guards/bin"
  local entry remaining=${PATH:-} result= separator=
  while :; do
    entry=${remaining%%:*}
    if [[ $entry != "$directory" ]]; then
      result+="$separator$entry"
      separator=:
    fi
    [[ $remaining == *:* ]] || break
    remaining=${remaining#*:}
  done
  export PATH=$result
}
