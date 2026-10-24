import QtQuick
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "." as Execution

WidgetButton {
  id: root
  readonly property string mode: Execution.State.mode
  text: mode === "host" ? Commons.I18n.t("agents.defaultHost")
    : mode === "container" ? Commons.I18n.t("agents.defaultContainer")
    : Commons.I18n.t("agents.defaultUnknown")
  tooltipText: mode === "unknown" ? Commons.I18n.t("agents.defaultUnknownHelp") : Commons.I18n.t("agents.defaultExecutionHelp")
  active: mode === "unknown"
  fontSize: Style.font.bodySmall
  textRotation: vertical ? -90 : 0
  implicitWidth: vertical ? barSize : labelWidth + Style.space(16)
  implicitHeight: vertical ? labelWidth + Style.space(16) : barSize
  onPressed: function(buttonCode) {
    if (buttonCode === Qt.LeftButton && bar) bar.run("omarchy-menu summon agents.execution")
  }
}
