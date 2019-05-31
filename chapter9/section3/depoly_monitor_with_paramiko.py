#!/usr/bin/python
# -*- coding: UTF-8 -*-
from __future__ import print_function
import paramiko


def depoly_monitor(ip):
    with paramiko.SSHClient() as client:
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, 22, username='pi', password='yangyi', timeout=300)

        stdin, stdout, stderr = client.exec_command('ls -l')
        print(stdout.readlines())

        with client.open_sftp() as sftp:
            sftp.put('depoly_monitor_with_paramiko.py', 'depoly_monitor_with_paramiko.py')
            sftp.chmod('depoly_monitor_with_paramiko.py', 0o755)


def main():
    with open('hosts') as f:
        for line in f:
            depoly_monitor(line.strip())


if __name__ == '__main__':
    main()
