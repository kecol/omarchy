import QtQuick
import qs.Commons
import qs.Ui
import "execution" as Execution
import "overview" as Overview

// Independent of the usage panel. Inventory is loaded only on right-click;
// no startup scan, provider authentication, polling, or agent-launch path.
BarWidget {
  id: root
  moduleName: "omarchy.agent-execution"
  property bool overviewCreated: false
  property bool overviewOpened: false
  function close() { overviewOpened = false }
  function closeForPopoutSwitch() { close() }
  readonly property string mode: label.mode
  implicitWidth: vertical ? Math.max(icon.implicitWidth, label.implicitWidth) : icon.implicitWidth + label.implicitWidth
  implicitHeight: vertical ? icon.implicitHeight + label.implicitHeight : Math.max(icon.implicitHeight, label.implicitHeight)

  BarIconButton {
    id: icon
    bar: root.bar
    width: root.vertical ? root.width : implicitWidth
    height: root.vertical ? implicitHeight : root.height
    text: root.mode === "host" ? "\uf108" : root.mode === "container" ? "\uf487" : "\uf071"
    active: root.mode === "unknown"
    tooltipText: label.tooltipText
    onPressed: function(buttonCode) { label.triggerPress(buttonCode) }
  }

  Execution.Button {
    id: label
    bar: root.bar
    hasOverview: true
    onOpeningModeMenu: root.close()
    onOverviewRequested: {
      root.overviewCreated = true
      root.overviewOpened = !root.overviewOpened
    }
    x: root.vertical ? 0 : icon.width
    y: root.vertical ? icon.height : 0
    width: implicitWidth
    height: implicitHeight
  }

  Loader {
    active: root.overviewCreated
    sourceComponent: Component {
      Overview.Popup {
        anchorItem: icon
        bar: root.bar
        opened: root.overviewOpened
        onDismissed: root.close()
      }
    }
  }
}
