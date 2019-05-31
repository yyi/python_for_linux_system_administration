from fabric.api import run, sudo
from fabric.api import env

env.hosts= ['yyifamily.ml']
env.port= 22
env.user='pi'
env.password='yangyi'

def hostname():
    run('hostname')

def ls(path='.'):
    run('ls {}'.format(path))

def tail(path='/etc/passwd', line=10):
    sudo('tail -n {0} {1}'.format(line, path))
