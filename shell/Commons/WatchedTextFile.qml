import QtQuick
import Quickshell.Io

// Keep the watch separate from synchronous reads. FileView.reload() rebuilds
// its watcher after publishing the read, which can lose an intervening change.
QtObject {
  id: root

  property string path: ""

  // Change paths outside text bindings, and install the watch first.
  onPathChanged: {
    root._watcher.path = root.path
    root._reader.path = root.path
  }

  function text() {
    return root._reader.text()
  }

  readonly property FileView _watcher: FileView {
    preload: false
    printErrors: false
    watchChanges: true
    onFileChanged: root._reader.reload()
  }

  readonly property FileView _reader: FileView {
    preload: false
    blockAllReads: true
    printErrors: false
  }
}
