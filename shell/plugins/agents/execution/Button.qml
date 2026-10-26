import QtQuick
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "." as Execution

WidgetButton {
  id: root
  property bool hasOverview: false
  signal overviewRequested()
  signal openingModeMenu()
  readonly property string mode: Execution.State.mode
  text: mode === "host" ? Commons.I18n.t("agents.defaultHost")
    : mode === "container" ? Commons.I18n.t("agents.defaultContainer")
    : Commons.I18n.t("agents.defaultUnknown")
  tooltipText: (mode === "unknown" ? Commons.I18n.t("agents.defaultUnknownHelp") : Commons.I18n.t("agents.defaultExecutionHelp"))
    + (hasOverview ? "\n" + Commons.I18n.t("agents.overview.openHelp") : "")
  active: mode === "unknown"
  fontSize: Style.font.bodySmall
  textRotation: vertical ? -90 : 0
  implicitWidth: vertical ? barSize : labelWidth + Style.space(16)
  implicitHeight: vertical ? labelWidth + Style.space(16) : barSize
  onPressed: function(buttonCode) {
    if (buttonCode === Qt.LeftButton && bar) {
      openingModeMenu()
      bar.run("omarchy-menu summon agents.execution")
    } else if (buttonCode === Qt.RightButton && hasOverview) overviewRequested()
  }
}
