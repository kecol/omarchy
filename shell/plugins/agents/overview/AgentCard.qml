import QtQuick
import QtQuick.Layouts
import qs.Commons
import qs.Commons as Commons
import qs.Ui as Ui

Rectangle {
  id: root
  required property var record
  property bool expanded: false
  implicitHeight: body.implicitHeight + Style.space(20)
  radius: Style.cornerRadius
  color: Style.selectedFillFor(Commons.Color.foreground, Commons.Color.accent)

  function boundary() {
    if (record.boundary === "host") return Commons.I18n.t("agents.overview.host")
    if (record.boundary === "container") return Commons.I18n.t("agents.overview.container")
    if (record.boundary === "observer") return Commons.I18n.t("agents.overview.observer")
    return Commons.I18n.t("agents.overview.unknownBoundary")
  }
  function activity() {
    if (!record.reported) return Commons.I18n.t("agents.overview.observed")
    var value = Commons.I18n.t("agents.overview.unknownActivity")
    if (record.activity === "working") value = Commons.I18n.t("agents.overview.working")
    else if (record.activity === "idle") value = Commons.I18n.t("agents.overview.idle")
    else if (["waiting", "attention", "needs_input", "needs-input"].indexOf(record.activity) >= 0) value = Commons.I18n.t("agents.overview.attention")
    else if (record.activity === "exited") value = Commons.I18n.t("agents.overview.exited")
    else if (record.activity === "conflicting-reports") value = Commons.I18n.t("agents.overview.conflicting")
    return Commons.I18n.t("agents.overview.herdrActivity").arg(value)
  }
  function details() {
    var lines = [Commons.I18n.t("agents.overview.pid").arg(record.identity.pid),
      Commons.I18n.t("agents.overview.identity").arg(record.identity.boot || "-").arg(record.identity.start)]
    if (record.cwd) lines.push(Commons.I18n.t("agents.overview.directory").arg(record.cwd))
    if (record.container) lines.push(Commons.I18n.t("agents.overview.containerName").arg(record.container))
    if (record.workspaceId) lines.push(Commons.I18n.t("agents.overview.workspaceId").arg(record.workspaceId))
    record.herdr.slice(0, 8).forEach(function(e) {
      lines.push(Commons.I18n.t("agents.overview.herdrIds").arg(e.session).arg(e.workspace).arg(e.tab).arg(e.pane))
      lines.push(Commons.I18n.t("agents.overview.herdrPath").arg(e.workspaceLabel).arg(e.tabLabel))
    })
    if (record.herdr.length > 8) lines.push(Commons.I18n.t("agents.overview.moreEvidence").arg(record.herdr.length - 8))
    record.windows.slice(0, 12).forEach(function(w) {
      lines.push(Commons.I18n.t("agents.overview.window").arg(w.monitor).arg(w.label).arg(w.workspace).arg(w.pid).arg(w.address))
      lines.push(Commons.I18n.t("agents.overview.source").arg(w.source))
      if (w.hidden) lines.push(Commons.I18n.t("agents.overview.hidden"))
    })
    if (record.windows.length > 12) lines.push(Commons.I18n.t("agents.overview.moreWindows").arg(record.windows.length - 12))
    return lines.join("\n")
  }

  Column {
    id: body
    x: Style.space(10)
    y: Style.space(10)
    width: parent.width - Style.space(20)
    spacing: Style.space(6)

    RowLayout {
      width: parent.width
      spacing: Style.space(12)
      Label {
        Layout.fillWidth: true
        text: root.record.agent === "pi" ? "Pi" : root.record.agent === "codex" ? "Codex" : root.record.agent
        font.pixelSize: Style.font.body
        font.bold: true
      }
      Label { text: root.boundary() }
      Label { text: root.activity(); Layout.maximumWidth: body.width * 0.45 }
    }
    Label {
      width: parent.width
      visible: root.record.herdr.length > 0
      text: visible ? Commons.I18n.t("agents.overview.herdrPath").arg(root.record.herdr[0].workspaceLabel).arg(root.record.herdr[0].tabLabel) : ""
    }
    Label {
      width: parent.width
      visible: root.record.workspace !== "" || root.record.container !== ""
      text: root.record.workspace ? Commons.I18n.t("agents.overview.workspaceName").arg(root.record.workspace)
        : Commons.I18n.t("agents.overview.containerName").arg(root.record.container)
    }
    Label {
      width: parent.width
      visible: root.record.windows.some(function(w) { return w.source === "workspace-editor-profile" })
      text: Commons.I18n.t("agents.overview.editorCaution")
    }
    Label {
      width: parent.width
      visible: root.record.windows.some(function(w) { return w.source === "herdr-session-client" })
      text: Commons.I18n.t("agents.overview.paneCaution")
    }
    Label {
      width: parent.width
      visible: root.record.candidate
      text: Commons.I18n.t("agents.overview.candidateCaution")
    }
    Ui.Button {
      width: Math.min(implicitWidth, parent.width)
      text: root.expanded ? Commons.I18n.t("agents.overview.hideDetails") : Commons.I18n.t("agents.overview.details")
      focusable: true
      fontSize: Style.font.bodySmall
      onClicked: root.expanded = !root.expanded
    }
    Label { width: parent.width; visible: root.expanded; text: visible ? root.details() : "" }
  }
}
