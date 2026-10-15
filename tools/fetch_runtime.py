"""Unduh paket Termux ARM yang dipin, verifikasi SHA256, rakit runtime lokal."""
from pathlib import Path, PurePosixPath
import concurrent.futures, hashlib, io, json, tarfile, urllib.request
ROOT=Path(__file__).resolve().parents[1]
BASE='https://packages.termux.dev/apt/termux-main/'
def data_member(data):
    if data[:8]!=b'!<arch>\n':raise ValueError('Format .deb tidak sesuai')
    offset=8
    while offset+60<=len(data):
        h=data[offset:offset+60];name=h[:16].decode().strip().rstrip('/');size=int(h[48:58]);offset+=60
        body=data[offset:offset+size];offset+=size+(size%2)
        if name.startswith('data.tar'):return body
    raise ValueError('Paket tidak mempunyai data.tar')
def main():
    packages=json.loads((ROOT/'third_party/termux/upstream-packages.json').read_text())
    cache=ROOT/'.cache/termux';cache.mkdir(parents=True,exist_ok=True)
    def download(item):
        name,p=item;relative=p['Filename']
        if not relative.startswith('pool/') or '..' in PurePosixPath(relative).parts or '\\' in relative:raise ValueError('Path paket tidak valid')
        # Debian epoch versions contain ':'; replace it for Windows filenames/ADS.
        dest=cache/PurePosixPath(relative).name.replace(':','_')
        if not dest.exists():
            with urllib.request.urlopen(BASE+relative,timeout=90) as r:dest.write_bytes(r.read())
        if hashlib.sha256(dest.read_bytes()).hexdigest()!=p['SHA256']:raise ValueError('SHA256 tidak cocok: '+name)
        return dest
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:files=list(pool.map(download,packages.items()))
    out=ROOT/'dist/runtime.tar.gz';out.parent.mkdir(exist_ok=True)
    prefix='data/data/com.termux/files/usr/'
    with tarfile.open(out,'w:gz',format=tarfile.PAX_FORMAT) as target:
        seen=set()
        for path in files:
            with tarfile.open(fileobj=io.BytesIO(data_member(path.read_bytes())),mode='r:*') as package:
                for member in package:
                    original=member.name.lstrip('./')
                    if not original.startswith(prefix):continue
                    relative=original[len(prefix):]
                    if not relative or '..' in PurePosixPath(relative).parts:continue
                    keep=relative.startswith(('lib/','libexec/samba/','share/samba/','share/licenses/')) or relative in ['bin/smbd','bin/smbpasswd','bin/smbcontrol','bin/testparm','bin/smbclient'] or relative.endswith(('/copyright','/COPYING','/LICENSE'))
                    if not keep or relative in seen:continue
                    seen.add(relative);member.name=relative;member.uid=member.gid=0;member.uname=member.gname='root'
                    if member.issym() and member.linkname.startswith('/'+prefix):member.linkname='/data/adb/modules/ebs_gtv_system_app/samba/runtime/'+member.linkname[len(prefix)+1:]
                    target.addfile(member,package.extractfile(member) if member.isfile() else None)
    print('SHA256 semua paket cocok; runtime lokal selesai:',out)
if __name__=='__main__':main()
