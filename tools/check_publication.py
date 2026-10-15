"""Periksa file repo yang akan dipublikasikan, tanpa membaca direktori privat."""
from pathlib import Path
import re, subprocess
ROOT=Path(__file__).resolve().parents[1]
def main():
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    errors=[]
    for name in filter(None,tracked):
        p=ROOT/name
        if p.suffix.lower() in {'.pk8','.pem','.jks','.p12','.keystore','.apk','.apkm','.zip','.log'} or p.name in {'config.json','smbpasswd'}:errors.append('Berkas privat/biner yang tidak diizinkan: '+name)
        if p.suffix in {'.png','.gpg'}:continue
        try:text=p.read_text(encoding='utf-8')
        except UnicodeDecodeError:errors.append('Biner tidak dikenal: '+name);continue
        for pattern in [r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'gh[pousr]_[A-Za-z0-9]{30,}',r'github_pat_[A-Za-z0-9_]{30,}',r'C:[/\\]Users[/\\]USER',r'192\.168\.1\.3']:
            if re.search(pattern,text):errors.append('Pola rahasia/lokal: '+name)
        if p.suffix=='.sh' and b'\r\n' in p.read_bytes():errors.append('Shell CRLF: '+name)
    if not tracked or tracked==['']:errors.append('Tidak ada file Git yang diperiksa')
    if errors:raise SystemExit('\n'.join(errors))
    print('LULUS:',len(list(filter(None,tracked))),'file; tidak ada private key, APK firmware, kredensial umum, atau path lokal.')
    print('Pemeriksaan otomatis tetap perlu peninjauan manual.')
if __name__=='__main__':main()
