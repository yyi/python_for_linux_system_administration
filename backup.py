#!/usr/bin/env python

import os
import subprocess

svnDir = '/opt/svn'
paths = os.listdir(svnDir)
for path in paths:
    path = os.path.join(svnDir, path)
    if os.path.isdir(path):
        subprocess.call(['/opt/svnbak/svn_backup.py', '-z', '-i', path, '/opt/bak', '-t',
                         'ftp:10.9.10.136:tsm:tsm:/home/tsm'])
