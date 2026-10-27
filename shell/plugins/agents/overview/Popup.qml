import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import qs.Commons
import qs.Commons as Commons
import qs.Ui as Ui
import "../execution" as Execution
import "." as Overview

Item {
  id: root
  required property Item anchorItem
  required property QtObject bar
  property bool opened: false
  // A fixture can inject a local view for a scoped preview, without collectors.
  property var inventory: Overview.State
  property bool ready: false
  signal dismissed()

  function close() { dismissed() }
  function inspectSessions() {
    root.close()
    root.bar.run("omarchy-launch-tui --app-id=org.omarchy.agent-sessions omarchy agent sessions")
  }
  Component.onCompleted: { ready = true; if (opened) inventory.refresh() }
  onOpenedChanged: if (ready && opened) inventory.refresh()

  function groupTitle(group) {
    if (group.type === "desktop") return Commons.I18n.t("agents.overview.desktop").arg(group.monitor).arg(group.label)
    if (group.type === "multiple") return Commons.I18n.t("agents.overview.multiple")
    if (group.type === "candidates") return Commons.I18n.t("agents.overview.candidates")
    return Commons.I18n.t("agents.overview.unknownLocation")
  }
  function coverageText() {
    if (!inventory.snapshot) return ""
    return inventory.snapshot.coverage.map(function(c) { return c.name + "=" + c.state }).join(" · ")
  }

  Ui.KeyboardPanel {
    id: panel
    anchorItem: root.anchorItem
    bar: root.bar
    owner: root
    open: root.opened
    contentWidth: fittedContentWidth(Style.space(560))
    contentHeight: fittedContentHeight(loadedContentHeight, Style.space(640))
    focusTarget: loadedContent
    content: Ui.PanelKeyCatcher {
      id: page
      // Preserve normal Tab/Enter focus for real buttons. The semantic panel
      // dispatcher would otherwise consume their activation keys.
      blocked: true
      implicitHeight: content.implicitHeight
      Keys.onEscapePressed: root.close()
      Keys.onPressed: function(event) {
        if (event.key === Qt.Key_R && !root.inventory.loading) {
          root.inventory.refresh(); event.accepted = true
        } else if (event.key === Qt.Key_PageDown || event.key === Qt.Key_PageUp || event.key === Qt.Key_Down || event.key === Qt.Key_Up) {
          var amount = event.key === Qt.Key_PageDown || event.key === Qt.Key_PageUp ? scroll.height * 0.8 : Style.space(40)
          var down = event.key === Qt.Key_PageDown || event.key === Qt.Key_Down
          scroll.contentY = Math.max(0, Math.min(Math.max(0, scroll.contentHeight - scroll.height), scroll.contentY + (down ? amount : -amount)))
          event.accepted = true
        }
      }

      ColumnLayout {
        id: content
        anchors.fill: parent
        spacing: Style.space(12)

        RowLayout {
          Layout.fillWidth: true
          Label { Layout.fillWidth: true; text: Commons.I18n.t("agents.overview.title"); font.pixelSize: Style.font.body; font.bold: true }
          Ui.Button {
            text: root.inventory.loading ? Commons.I18n.t("agents.overview.refreshing") : Commons.I18n.t("agents.overview.refresh")
            enabled: !root.inventory.loading
            focusable: true
            onClicked: root.inventory.refresh()
          }
          Ui.Button { text: Commons.I18n.t("agents.overview.close"); focusable: true; onClicked: root.close() }
        }
        RowLayout {
          Layout.fillWidth: true
          Label {
            Layout.fillWidth: true
            text: Execution.State.mode === "host" ? Commons.I18n.t("agents.defaultHost")
              : Execution.State.mode === "container" ? Commons.I18n.t("agents.defaultContainer") : Commons.I18n.t("agents.defaultUnknown")
          }
          Ui.Button {
            text: Commons.I18n.t("agents.overview.changeDefault")
            focusable: true
            onClicked: { root.close(); root.bar.run("omarchy-menu summon agents.execution") }
          }
        }
        Label {
          Layout.fillWidth: true
          text: root.inventory.snapshot
            ? Commons.I18n.t("agents.overview.snapshot").arg(Qt.formatDateTime(new Date(root.inventory.snapshot.timestamp), "yyyy-MM-dd hh:mm:ss"))
            : Commons.I18n.t("agents.overview.noSnapshot")
        }
        Label {
          Layout.fillWidth: true
          visible: root.inventory.failed
          text: root.inventory.snapshot ? Commons.I18n.t("agents.overview.staleError") : Commons.I18n.t("agents.overview.error")
        }
        Label {
          Layout.fillWidth: true
          visible: !!root.inventory.snapshot
          text: root.inventory.snapshot && root.inventory.snapshot.partial ? Commons.I18n.t("agents.overview.partial") : Commons.I18n.t("agents.overview.scope")
        }

        Flickable {
          id: scroll
          Layout.fillWidth: true
          Layout.fillHeight: true
          Layout.minimumHeight: Style.space(60)
          Layout.preferredHeight: Math.min(list.implicitHeight, Style.space(370))
          contentWidth: width
          contentHeight: list.implicitHeight
          clip: true
          boundsBehavior: Flickable.StopAtBounds
          Controls.ScrollBar.vertical: Controls.ScrollBar {
            policy: scroll.contentHeight > scroll.height ? Controls.ScrollBar.AlwaysOn : Controls.ScrollBar.AlwaysOff
          }

          Column {
            id: list
            width: scroll.width - Style.space(12)
            spacing: Style.space(10)
            Label {
              width: parent.width
              visible: !!root.inventory.snapshot && root.inventory.snapshot.total === 0
              text: Commons.I18n.t("agents.overview.empty")
            }
            Repeater {
              model: root.inventory.snapshot ? root.inventory.snapshot.groups : []
              delegate: Column {
                id: group
                required property var modelData
                width: list.width
                spacing: Style.space(8)
                Label { width: parent.width; text: root.groupTitle(group.modelData); font.bold: true; font.pixelSize: Style.font.body }
                Repeater {
                  model: group.modelData.rows
                  delegate: AgentCard { required property var modelData; width: list.width; record: modelData }
                }
              }
            }
            Label {
              width: parent.width
              visible: !!root.inventory.snapshot && root.inventory.snapshot.omitted > 0
              text: root.inventory.snapshot ? Commons.I18n.t("agents.overview.omitted").arg(root.inventory.snapshot.omitted) : ""
            }
          }
        }

        Label {
          Layout.fillWidth: true
          visible: !!root.inventory.snapshot
          text: root.inventory.snapshot ? Commons.I18n.t("agents.overview.counts").arg(root.inventory.snapshot.counts.host).arg(root.inventory.snapshot.counts.container).arg(root.inventory.snapshot.counts.unknown + root.inventory.snapshot.counts.observer) : ""
        }
        Label {
          Layout.fillWidth: true
          visible: !!root.inventory.snapshot && root.inventory.snapshot.unverified > 0
          text: root.inventory.snapshot ? Commons.I18n.t("agents.overview.unverified").arg(root.inventory.snapshot.unverified) : ""
        }
        RowLayout {
          Layout.fillWidth: true
          spacing: Style.space(8)
          Ui.Button {
            id: coverageButton
            property bool expanded: false
            text: expanded ? Commons.I18n.t("agents.overview.hideCoverage") : Commons.I18n.t("agents.overview.coverage")
            visible: !!root.inventory.snapshot
            focusable: true
            onClicked: expanded = !expanded
          }
          Ui.Button {
            id: inspectSessionsButton
            text: Commons.I18n.t("agents.overview.inspectSessions")
            focusable: true
            onClicked: root.inspectSessions()
          }
          Item { Layout.fillWidth: true }
        }
        Label { Layout.fillWidth: true; visible: coverageButton.expanded; text: root.coverageText() }
        Label { Layout.fillWidth: true; text: Commons.I18n.t("agents.overview.caution") }
      }
    }
  }
}
