"""Build APK dari source dengan Android SDK/JDK dan key milik pengguna."""
import argparse, hashlib, os, shutil, subprocess, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--component',choices=['tools','profile-compat','settings-overlay','notification-cards','notification-routing','app-drawer'],required=True)
    p.add_argument('--build-tools',type=Path,required=True)
    p.add_argument('--android-jar',type=Path,required=True)
    p.add_argument('--framework-apk',type=Path);p.add_argument('--settings-apk',type=Path)
    p.add_argument('--keystore',type=Path,required=True);p.add_argument('--alias',default='b866f')
    p.add_argument('--javac',default='javac');p.add_argument('--java',default='java')
    p.add_argument('--ecj',type=Path,help='Opsional: Eclipse compiler JAR sebagai pengganti javac')
    a=p.parse_args()
    if not os.environ.get('B866F_KEYSTORE_PASSWORD'):p.error('Set B866F_KEYSTORE_PASSWORD di lingkungan lokal; jangan commit nilainya.')
    src=ROOT/'android'/a.component;b=ROOT/'build'/a.component;b.mkdir(parents=True,exist_ok=True)
    def run(*args):subprocess.run([str(x) for x in args],check=True)
    def tool(name):return a.build_tools/(name+('.exe' if os.name=='nt' else ''))
    run(tool('aapt2'),'compile','--dir',src/'res','-o',b/'compiled.zip') if (src/'res').exists() else None
    link=[tool('aapt2'),'link','--manifest',src/'AndroidManifest.xml','-o',b/'unsigned.apk']
    if a.component=='settings-overlay':
        if not a.framework_apk or not a.settings_apk:p.error('Overlay memerlukan framework-res.apk dan TvSettings.apk dari perangkat lokal.')
        if hashlib.sha256(a.settings_apk.read_bytes()).hexdigest()!='b798e976ac4fea52d39c30f98845682bf20bbbe06224e4c592b4f43165197d1f':p.error('Hash Settings tidak sesuai basis uji.')
        link+=['--package-id','0x7e','--allow-reserved-package-id','-I',a.framework_apk,'-I',a.settings_apk,'--auto-add-overlay']
    else:link+=['-I',a.android_jar]
    if (src/'res').exists():link+=[b/'compiled.zip']
    run(*link)
    sources=list((src/'src').rglob('*.java')) if (src/'src').exists() else []
    if sources:
        classes=b/'classes';dex=b/'dex'
        # Clear only known build subdirectories to avoid stale classes after source removal.
        for path in [classes,dex]:
            if path.exists():shutil.rmtree(path)
            path.mkdir()
        compiler=[a.java,'-jar',a.ecj,'-1.8'] if a.ecj else [a.javac,'-source','8','-target','8']
        # The drawer's lambdas need the Java runtime bootstrap types during compilation.
        classpath_flag='-classpath' if a.component=='app-drawer' else '-bootclasspath'
        run(*compiler,'-encoding','UTF-8',classpath_flag,a.android_jar,'-d',classes,*sources)
        run(a.java,'-cp',a.build_tools/'lib/d8.jar','com.android.tools.r8.D8','--min-api','28','--lib',a.android_jar,'--output',dex,*classes.rglob('*.class'))
        with zipfile.ZipFile(b/'unsigned.apk','a') as z:z.write(dex/'classes.dex','classes.dex')
    run(tool('zipalign'),'-f','4',b/'unsigned.apk',b/'aligned.apk')
    out=ROOT/'dist';out.mkdir(exist_ok=True);apk=out/(a.component+'.apk')
    signer=a.build_tools/'lib/apksigner.jar'
    run(a.java,'-jar',signer,'sign','--ks',a.keystore,'--ks-key-alias',a.alias,'--ks-pass','env:B866F_KEYSTORE_PASSWORD','--key-pass','env:B866F_KEYSTORE_PASSWORD','--out',apk,b/'aligned.apk')
    run(a.java,'-jar',signer,'verify',apk)
    print('APK selesai:',apk)
if __name__=='__main__':main()
