pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons

// One launch-default reader for every monitor, created on first label enable.
// The setter pushes refresh after every atomic save; no polling,
// provider collectors, authentication, or container operations live here.
Singleton {
  id: root
  property string mode: "unknown"
  property bool refreshRequested: false

  function refresh() {
    refreshRequested = true
    Qt.callLater(root.startRead)
  }

  function startRead() {
    if (reader.running || !refreshRequested) return
    refreshRequested = false
    reader.running = true
  }

  function finishRead(exitCode, output) {
    var value = String(output || "").trim()
    mode = exitCode === 0 && (value === "host" || value === "container") ? value : "unknown"
    if (refreshRequested) Qt.callLater(root.startRead)
  }

  Component.onCompleted: refresh()

  Process {
    id: reader
    command: ["timeout", "5", "omarchy-agent-mode"]
    stdout: StdioCollector { id: result; waitForEnd: true }
    onExited: function(exitCode) { root.finishRead(exitCode, result.text) }
  }

  ShellIpc {
    target: "omarchy.agent-execution-default"
    function refresh(): string { root.refresh(); return "ok" }
  }
}
