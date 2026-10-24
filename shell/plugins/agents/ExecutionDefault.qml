import QtQuick
import qs.Commons
import qs.Ui
import "execution" as Execution

// Deliberately independent of Main.qml and Panel.qml: no usage collection,
// provider authentication, account switching, or agent launch path.
BarWidget {
  id: root
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
    x: root.vertical ? 0 : icon.width
    y: root.vertical ? icon.height : 0
    width: implicitWidth
    height: implicitHeight
  }
}
