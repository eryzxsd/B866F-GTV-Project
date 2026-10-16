# Basis firmware dibatasi agar overlay resource tidak diterapkan pada ROM lain.
[ "$BOOTMODE" = true ] || abort "Pasang dari aplikasi Magisk setelah Android hidup."
[ "$(getprop ro.product.model)" = 'B866F V1.1' ] || abort "Model bukan B866F V1.1."
[ "$(getprop ro.build.version.release)" = '14' ] || abort "Basis bukan Android 14."
settings_apk=$(pm path com.android.tv.settings | head -n 1 | cut -d: -f2-)
[ -f "$settings_apk" ] || abort "APK Settings tidak ditemukan."
settings_hash=$(sha256sum "$settings_apk" | cut -d' ' -f1)
[ "$settings_hash" = b798e976ac4fea52d39c30f98845682bf20bbbe06224e4c592b4f43165197d1f ] || abort "Hash Settings berbeda; modul dibatalkan."
# Pertahankan jurnal komponen HOME saat upgrade, agar pilihan dapat dipulihkan.
previous_launcher=/data/adb/modules/ebs_gtv_system_app/launcher-managed-components.json
if [ "$MODPATH/launcher-managed-components.json" != "$previous_launcher" ] && [ -f "$previous_launcher" ]; then
  cp "$previous_launcher" "$MODPATH/launcher-managed-components.json"
  set_perm "$MODPATH/launcher-managed-components.json" 0 0 0600
fi
set_perm "$MODPATH/service.sh" 0 0 0755
set_perm "$MODPATH/bin/gtv-notification-panel" 0 0 0755
set_perm "$MODPATH/bin/gtv-launcher-switch" 0 0 0755
set_perm "$MODPATH/bin/gtv-samba-control" 0 0 0755
if [ -f "$MODPATH/samba/runtime.tar.gz" ]; then
  mkdir -p "$MODPATH/samba/runtime"
  tar -xzf "$MODPATH/samba/runtime.tar.gz" -C "$MODPATH/samba/runtime" || abort "Samba runtime extraction failed"
  set_perm_recursive "$MODPATH/samba/runtime" 0 0 0755 0644
  for samba_program in "$MODPATH/samba/runtime/bin/"* "$MODPATH/samba/runtime/libexec/samba/"*; do
    [ -f "$samba_program" ] && set_perm "$samba_program" 0 0 0755
  done
  set_perm "$MODPATH/samba/libb866f_samba_paths.so" 0 0 0644
  samba_previous=/data/adb/modules/ebs_gtv_system_app/samba/config.json
  if [ "$MODPATH/samba/config.json" != "$samba_previous" ] && [ -f "$samba_previous" ]; then
    cp "$samba_previous" "$MODPATH/samba/config.json"
    set_perm "$MODPATH/samba/config.json" 0 0 0600
  fi
fi
