"""Fail closed on unreviewed publication content; inspect staged bytes, not filenames alone."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
GIT=os.environ.get('GIT_EXE','git')
def git(*args, input=None):
    return subprocess.run([GIT,'-C',str(ROOT),*args],input=input,capture_output=True,check=True).stdout

def main():
    staged=git('diff','--cached','--name-only','--diff-filter=ACMR','-z').decode().split('\0')
    staged=[x for x in staged if x]
    paths=git('ls-files','-z').decode().split('\0')
    paths=[x for x in paths if x]
    if not paths:
        raise SystemExit('FAIL: no staged or tracked files to audit')
    source='index' if staged else 'HEAD'
    allowed={'.py','.md','.json','.txt','.toml','.yml','.cff'}
    special={'.gitignore','.gitattributes','LICENSE'}
    patterns={
        'private key':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        'GitHub token':r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})',
        'AWS access key':r'AKIA[A-Z0-9]{16}',
        'OpenAI key':r'sk-(?:proj-)?[A-Za-z0-9_-]{30,}',
        'personal local path':r'(?:[A-Za-z]:[\\/]+Users[\\/]|[/](?:home|Users)[/])',
        'record UUID':r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b',
        'SSN-shaped value':r'\b\d{3}-\d{2}-\d{4}\b',
        'assigned secret':r'''(?im)(?:password|api_key|access_token|secret_key)\s*[:=]\s*["'][^"'\n]{8,}["']''',
    }
    failures=[];total=0;contents={}
    for name in paths:
        data=git('show',(':'+name) if source=='index' else ('HEAD:'+name))
        contents[name]=data;total+=len(data)
        if len(data)>1024*1024:failures.append([name,'file exceeds 1 MiB'])
        if Path(name).suffix not in allowed and name not in special:failures.append([name,'unapproved file type'])
        try:text=data.decode('utf-8-sig')
        except UnicodeDecodeError:
            failures.append([name,'non-text content']);continue
        for label,pattern in patterns.items():
            if re.search(pattern,text):failures.append([name,label])
    manifest=json.loads(contents['docs/source_manifest.json'])
    for entry in manifest:
        if 'archived_as' in entry:
            name=entry['archived_as']
            if hashlib.sha256(contents[name]).hexdigest()!=entry.get('decoded_sha256',entry['sha256']):
                failures.append([name,'original hash mismatch'])
    ignored=['.env','.local/run/data.csv','data/patients.csv','results/patients.csv',
             'results/private.parquet','results/database.duckdb','docs/secret.pem',
             'docs/private.docx','unrelated.txt','src/rxguard/__pycache__/module.pyc']
    for name in ignored:
        result=subprocess.run([GIT,'-C',str(ROOT),'check-ignore','--no-index','-q',name])
        if result.returncode!=0:failures.append([name,'ignore rule failed'])
    result={'status':'FAIL' if failures else 'PASS','source':source,'files':len(paths),
            'bytes':total,'ignore_probes':len(ignored),'failures':failures,
            'scope':'Pattern checks plus byte-hash provenance; manual aggregate review is additionally required.'}
    print(json.dumps(result,indent=2))
    return bool(failures)

if __name__=='__main__':
    sys.exit(main())
