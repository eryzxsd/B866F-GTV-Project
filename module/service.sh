#!/system/bin/sh
MODDIR=${0%/*}
tries=0
while [ "$(getprop sys.boot_completed)" != "1" ]; do
  tries=$((tries + 1))
  [ "$tries" -ge 120 ] && exit 0
  sleep 2
done
[ -f "$MODDIR/disable" ] && exit 0
[ -f "$MODDIR/remove" ] && exit 0
if [ -x "$MODDIR/bin/gtv-notification-panel" ]; then
  if [ -f "$MODDIR/disable_gtv_notifications" ]; then
    "$MODDIR/bin/gtv-notification-panel" restore --refresh
  else
    "$MODDIR/bin/gtv-notification-panel" apply --refresh
  fi
fi
if [ ! -f "$MODDIR/disable_twopanel" ]; then
  if cmd overlay fabricate --target com.android.tv.settings --name EbsTvSettingsTwoPanel com.android.tv.settings:string/config_tvSettingsFlavor string TwoPanel; then
    if cmd overlay enable --user 0 com.android.shell:EbsTvSettingsTwoPanel; then
      am force-stop com.android.tv.settings
    fi
  fi
fi
if [ ! -f "$MODDIR/disable_settings_theme" ] && [ ! -f "$MODDIR/disable_twopanel" ]; then
  cmd overlay enable --user 0 com.local.ebs.settingstheme
else
  cmd overlay disable --user 0 com.local.ebs.settingstheme
fi
am force-stop com.android.tv.settings
if [ ! -f "$MODDIR/disable_launcher_switch" ] && [ -x "$MODDIR/bin/gtv-launcher-switch" ]; then
  if [ -f "$MODDIR/launcher-switch.log" ]; then
    size=$(wc -c < "$MODDIR/launcher-switch.log")
    [ "$size" -gt 32768 ] && mv -f "$MODDIR/launcher-switch.log" "$MODDIR/launcher-switch.log.previous"
  fi
  nohup "$MODDIR/bin/gtv-launcher-switch" </dev/null >>"$MODDIR/launcher-switch.log" 2>&1 &
fi

if [ ! -f "$MODDIR/disable_samba" ] && [ -x "$MODDIR/bin/gtv-samba-control" ]; then
  nohup "$MODDIR/bin/gtv-samba-control" </dev/null >>"$MODDIR/samba-control.log" 2>&1 &
fi
