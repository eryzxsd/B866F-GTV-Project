"""Cross-compile helper ARMv7 dan shim Samba; tidak mengubah perangkat."""
import argparse, os, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--go',default='go');p.add_argument('--zig',default='zig');a=p.parse_args()
    out=ROOT/'dist';out.mkdir(exist_ok=True)
    env=os.environ.copy();env.update(GOOS='linux',GOARCH='arm',GOARM='7',CGO_ENABLED='0')
    for folder,name in [('launcher-switch','gtv-launcher-switch'),('samba','gtv-samba-control')]:
        subprocess.run([a.go,'build','-trimpath','-ldflags=-s -w','-o',str(out/name),'.'],cwd=ROOT/'native'/folder,env=env,check=True)
    subprocess.run([a.zig,'cc','-target','arm-linux-android','-shared','-nostdlib','-fPIC','-fno-stack-protector','-O2','-Wl,-soname,libb866f_samba_paths.so','-o',str(out/'libb866f_samba_paths.so'),str(ROOT/'native/samba/compat.c')],check=True)
    print('Helper selesai di dist/')
if __name__=='__main__':main()
