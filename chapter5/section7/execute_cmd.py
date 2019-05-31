import subprocess


def execute_cmd(cmd):
    p = subprocess.Popen(cmd,
                         shell=True,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        return p.returncode, stderr
    return p.returncode, stdout


if __name__ == '__main__':
    returncode, out = execute_cmd('ls')
    print("retruncode:{0},out:{1}".format(returncode, out))
