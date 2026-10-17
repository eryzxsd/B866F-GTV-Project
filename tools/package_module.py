"""Merakit modul lokal; APK Google harus disediakan sendiri, tidak dipublikasikan."""
import argparse, hashlib, json, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--google-tv-system-apk',type=Path,required=True);a=p.parse_args()
    if hashlib.sha256(a.google_tv_system_apk.read_bytes()).hexdigest()!='9177852e231ae4beeb4aabd5a4359d7e76937b01e23250233cc9c4a6d241245c':p.error('Baseline Google TV berbeda. Hanya APK 1.0.331643392 dengan hash basis uji yang diterima.')
    pairs={
        'system/priv-app/GoogleTVHome/base.apk':a.google_tv_system_apk,
        'system/app/EbsSettingsTheme/EbsSettingsTheme.apk':ROOT/'dist/settings-overlay.apk',
        'system/product/overlay/B866FNotificationRouting.apk':ROOT/'dist/notification-routing.apk',
        'bin/gtv-launcher-switch':ROOT/'dist/gtv-launcher-switch',
        'bin/gtv-samba-control':ROOT/'dist/gtv-samba-control',
        'samba/libb866f_samba_paths.so':ROOT/'dist/libb866f_samba_paths.so',
        'samba/runtime.tar.gz':ROOT/'dist/runtime.tar.gz',
    }
    for f in pairs.values():
        if not f.is_file():p.error('Berkas belum tersedia: '+str(f))
    target=ROOT/'dist/B866F-GTV-Project-local-preview.zip'
    hashes={}
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for f in (ROOT/'module').rglob('*'):
            if f.is_file():z.write(f,f.relative_to(ROOT/'module').as_posix())
        for name,f in pairs.items():z.write(f,name);hashes[name]=hashlib.sha256(f.read_bytes()).hexdigest()
    (target.with_suffix('.manifest.json')).write_text(json.dumps(hashes,indent=2)+'\n')
    print('Modul lokal selesai. Berisi APK Google pribadi; JANGAN unggah ZIP ini ke GitHub:',target)
if __name__=='__main__':main()
