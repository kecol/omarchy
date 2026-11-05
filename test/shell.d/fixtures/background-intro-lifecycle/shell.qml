import QtQuick
import Quickshell
import Quickshell.Io
import "services"
import "Commons" as Commons

ShellRoot {
  id: test
  property bool failed: false
  readonly property bool expectAnimations: Quickshell.env("INTRO_TEST_ANIMATIONS") === "true"
  property var services: ({})
  function firstPartyServiceFor(id) { return services[id] || null }
  function check(ok, message) {
    if (!ok) {
      failed = true
      console.log("RESULT fail " + message)
    }
  }

  QtObject { id: retainedBackground; property bool suspended: false }
  BackgroundIntro { id: intro; host: test }

  Process {
    id: revealVideo
    command: ["touch", Quickshell.env("INTRO_TEST_FRAME_READY"), Quickshell.env("INTRO_TEST_LAUNCHER_DONE")]
  }

  FileView {
    id: coveredStatus
    path: Quickshell.env("INTRO_TEST_COVERED")
    blockLoading: true
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
  }

  // Bound each readiness wait, rather than assuming decoding/presentation or
  // a child process has finished after a fixed number of milliseconds.
  property int step: 0
  property double readinessDeadline: 0
  Timer {
    id: preparation
    interval: 16
    running: true
    repeat: true
    onTriggered: {
      if (!test.readinessDeadline) test.readinessDeadline = Date.now() + 3000
      if (test.step === 0) {
        if (!intro.checked || Commons.Style.reduceMotion !== !test.expectAnimations) {
          if (Date.now() >= test.readinessDeadline) {
            test.check(false, "startup and the explicit animation policy become ready before the deadline")
            stop()
            Qt.quit()
          }
          return
        }
        test.check(intro.checked, "startup runs even when OWE left the background disabled for a video")
        test.check(Commons.Style.duration(420) === (test.expectAnimations ? 420 : 0), "the fixture uses its explicit animation policy")
        test.services = ({ "omarchy.background": retainedBackground })
        intro.prepareTheme(Quickshell.env("INTRO_TEST_COVER"), "theme-one", Qt.btoa('background = "#123456"'), "")
        test.check(intro.themeCoverStatus("theme-one") === "loading", "the cover waits for decoding and presentation")
        test.check(intro.themeStatus("theme-one") === "pending", "app retints wait for the intro reveal")
        test.check(!Qt.colorEqual(Commons.Color.background, "#123456"), "the palette waits for OWE's first frame")
        intro.finishTheme("superseded-theme")
        test.check(intro.themeToken === "theme-one", "an older intro cannot release the pending handoff")
        test.step = 1
        test.readinessDeadline = Date.now() + 3000
        return
      }
      if (test.step === 1) {
        var status = intro.themeCoverStatus("theme-one")
        if (status !== "ready") {
          if (status === "error" || status === "superseded" || Date.now() >= test.readinessDeadline) {
            test.check(false, "the outgoing cover becomes presented before the deadline: " + status)
            stop()
            Qt.quit()
          }
          return
        }
        test.check(intro.cover, "the still stays covered while the launcher waits")
        test.check(intro.themeCoverStatus("theme-one") === "ready", "the outgoing cover is presented before the shell is hidden")
        retainedBackground.suspended = true
        test.step = 2
        test.readinessDeadline = Date.now() + 3000
        return
      }
      if (!String(coveredStatus.text() || "").trim()) {
        if (Date.now() >= test.readinessDeadline) {
          test.check(false, "the transitioning renderer is polled before the deadline")
          stop()
          Qt.quit()
        }
        return
      }
      stop()
      test.check(intro.themeToken === "theme-one", "a leftover renderer still stays covered until video is revealed")
      revealVideo.running = true
      test.handoffDeadline = Date.now() + 3000
      handoff.start()
    }
  }
  property double handoffDeadline: 0
  property bool openingFadeObserved: false
  Connections {
    target: intro
    function onThemeTokenChanged() {
      if (handoff.running && intro.themeToken === "") {
        Qt.callLater(function() {
          if (test.expectAnimations) {
            test.check(intro.themeStatus("theme-one") === "pending", "app retints also wait through the opening crossfade")
          } else {
            test.check(intro.themeStatus("theme-one") === "ready" && !intro.startupPending && intro.startupOpacity === 0,
              "zero-duration startup completes before the deferred observation")
          }
          test.openingFadeObserved = true
        })
      }
    }
  }
  Timer {
    id: handoff
    interval: 16
    repeat: true
    onTriggered: {
      if (intro.themeToken || !test.openingFadeObserved) {
        if (Date.now() >= test.handoffDeadline) {
          test.check(false, "the ready video releases its cover before the deadline")
          Qt.quit()
        }
        return
      }
      stop()
      test.check(!intro.cover && intro.checked, "OWE taking the background releases the cover")
      test.check(intro.themeToken === "" && Qt.colorEqual(Commons.Color.background, "#123456"), "first-frame handoff starts the palette and wallpaper fade together")
      retainedBackground.suspended = false
      Qt.callLater(function() { test.check(!intro.cover, "resuming the retained background cannot cover or retry playback") })
      completionDeadline = Date.now() + 3000
      completion.start()
    }
  }
  property double completionDeadline: 0
  Timer {
    id: completion
    interval: 16
    repeat: true
    onTriggered: {
      if (intro.themeStatus("theme-one") !== "ready" || !intro.startupSettled) {
        if (Date.now() >= test.completionDeadline) {
          test.check(false, "the fade and launcher complete before the deadline")
          Qt.quit()
        }
        return
      }
      stop()
      test.check(intro.themeStatus("theme-one") === "ready", "the completed crossfade releases app retints")
      intro.prepareTheme("", "failed-theme", Qt.btoa('background = "#654321"'), "")
      intro.finishTheme("failed-theme")
      test.check(Qt.colorEqual(Commons.Color.background, "#654321"), "failed playback still releases its pending palette")
      intro.prepareTheme("", "cancelled-theme", Qt.btoa('background = "#abcdef"'), "")
      intro.cancelTheme()
      intro.finishTheme("cancelled-theme")
      test.check(Qt.colorEqual(Commons.Color.background, "#654321") && !intro.themeToken, "a superseding theme cannot be overwritten by an older completion")
      test.check(!intro.cover, "launcher completion leaves the still uncovered")
      if (!test.failed) console.log("RESULT pass")
      Qt.quit()
    }
  }
}
