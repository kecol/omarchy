pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "Model.js" as Model

// One bounded on-demand read shared by every monitor. No startup/hover reads,
// timers, file cache, usage imports, provider requests, or retry loops.
Singleton {
  id: root
  property var snapshot: null
  property bool loading: false
  property bool scheduled: false
  property bool failed: false
  property string buffer: ""
  property bool overflow: false

  function refresh() {
    if (loading || scheduled) return
    scheduled = true
    Qt.callLater(root.startRead)
  }
  function startRead() {
    if (!scheduled || loading) return
    scheduled = false
    buffer = ""
    overflow = false
    failed = false
    loading = true
    reader.running = true
  }
  function receive(line) {
    if (overflow) return
    if (buffer.length + line.length + 1 > Model.MAX_OUTPUT) {
      overflow = true
      buffer = ""
    } else buffer += line + "\n"
  }
  function finish(code) {
    try {
      if (code !== 0 || overflow) throw new Error("unavailable snapshot")
      snapshot = Model.parse(buffer)
      failed = false
    } catch (error) {
      failed = true
      // Keep the previous valid snapshot and its original timestamp.
    }
    buffer = ""
    loading = false
  }

  Process {
    id: reader
    command: ["timeout", "12", "omarchy-agent-status", "--json"]
    stdout: SplitParser { splitMarker: "\n"; onRead: function(data) { root.receive(data) } }
    // Adapter errors never expose stderr, prompts, or partial JSON in the UI.
    onExited: function(exitCode) { root.finish(exitCode) }
  }
}
