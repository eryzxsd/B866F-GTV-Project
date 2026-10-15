"""Pemeriksaan hanya-baca; tidak meminta atau mencetak kredensial."""
import argparse, hashlib, json, subprocess, sys

EXPECTED = 'b798e976ac4fea52d39c30f98845682bf20bbbe06224e4c592b4f43165197d1f'
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--serial',required=True);p.add_argument('--adb',default='adb');a=p.parse_args()
    def shell(*args):
        return subprocess.check_output([a.adb,'-s',a.serial,'shell',*args],text=True).strip()
    info={k:shell('getprop',k) for k in ['ro.product.model','ro.build.version.release','ro.build.version.security_patch','ro.board.platform']}
    info['kernel']=shell('uname','-r')
    paths=shell('pm','path','com.android.tv.settings').splitlines()
    apk=next((x[8:] for x in paths if x.startswith('package:') and x.endswith('.apk')),None)
    if not apk:raise SystemExit('APK Settings tidak ditemukan')
    digest=shell('sha256sum',apk).split()[0]
    info['settings_sha256']=digest
    info['basis_cocok']=info['ro.product.model']=='B866F V1.1' and info['ro.build.version.release']=='14' and digest==EXPECTED
    print(json.dumps(info,indent=2,ensure_ascii=False))
    if not info['basis_cocok']:raise SystemExit('Basis berbeda; jangan pasang overlay/modul ini.')
    print('Basis Settings cocok. Ini bukan pemeriksaan recovery atau jaminan aman flashing.')
if __name__=='__main__':main()
