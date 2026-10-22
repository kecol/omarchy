# Fork branding assets

`logo.png` is the 800×260 transparent boot/login wordmark. `screensaver.txt` is the stock `logo.txt` text art followed by a centered `sandboxed agents` subtitle. These assets are opt-in. Do not replace `default/plymouth/logo.png`, `default/sddm/omarchy/logo.png`, or `logo.txt`: the restore command needs the stock defaults.

The PNG preserves the stock 800×188 Plymouth wordmark at the top. Its subtitle uses JetBrains Mono Regular at 30 pixels, centered below the wordmark in the original green (`#a8cd76`). To regenerate it from the repository root with ImageMagick and the installed JetBrains Mono font:

```bash
font=$(fc-match -f '%{file}' 'JetBrains Mono')
magick default/plymouth/logo.png \
  -background none -gravity north -extent 800x260 \
  -font "$font" -pointsize 30 -fill '#a8cd76' \
  -gravity south -annotate +0+10 'sandboxed agents' \
  default/branding/fork/logo.png
```

Use `omarchy plymouth preview '#1a1b26' '#ffffff' default/branding/fork/logo.png preview.png` for a static unlock-screen preview. This does not install boot assets. Do not run a real Plymouth daemon over the active desktop. See the [branding manual](../../../manual/41-branding.md#fork-branding-sandboxed-agents) for apply, restore, and boot-image rebuild warnings.
