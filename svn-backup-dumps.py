#!/usr/bin/env python
#
# svn-backup-dumps.py -- Create dumpfiles to backup a subversion repository.
#
# ====================================================================
#    Licensed to the Apache Software Foundation (ASF) under one
#    or more contributor license agreements.  See the NOTICE file
#    distributed with this work for additional information
#    regarding copyright ownership.  The ASF licenses this file
#    to you under the Apache License, Version 2.0 (the
#    "License"); you may not use this file except in compliance
#    with the License.  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing,
#    software distributed under the License is distributed on an
#    "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#    KIND, either express or implied.  See the License for the
#    specific language governing permissions and limitations
#    under the License.
# ====================================================================
#
# Modified by David Hadka on 06 Oct 2011 to include Dropbox support.
# Modifications are released under the Apache License, Version 2.0.
# Original file from: http://svn.apache.org/repos/asf/subversion/trunk/
#
# This script creates dump files from a subversion repository.
# It is intended for use in cron jobs and post-commit hooks.
#
# The basic operation modes are:
#    1. Create a full dump (revisions 0 to HEAD).
#    2. Create incremental dumps containing at most N revisions.
#    3. Create incremental single revision dumps (for use in post-commit).
#    4. Create incremental dumps containing everything since last dump.
#
# All dump files are prefixed with the basename of the repository. All
# examples below assume that the repository '/srv/svn/repos/src' is
# dumped so all dumpfiles start with 'src'.
#
# Optional functionality:
#    5. Create gzipped dump files.
#    6. Create bzipped dump files.
#    7. Transfer the dumpfile to another host using ftp.
#    8. Transfer the dumpfile to another host using smb.
#    9. Transfer the dumpfile to Dropbox
#
# See also 'svn-backup-dumps.py -h'.
#
#
# 1. Create a full dump (revisions 0 to HEAD).
#
#    svn-backup-dumps.py <repos> <dumpdir>
#
#    <repos>      Path to the repository.
#    <dumpdir>    Directory for storing the dump file.
#
#    This creates a dump file named 'src.000000-NNNNNN.svndmp.gz'
#    where NNNNNN is the revision number of HEAD.
#
#
# 2. Create incremental dumps containing at most N revisions.
#
#    svn-backup-dumps.py -c <count> <repos> <dumpdir>
#
#    <count>      Count of revisions per dump file.
#    <repos>      Path to the repository.
#    <dumpdir>    Directory for storing the dump file.
#
#    When started the first time with a count of 1000 and if HEAD is
#    at 2923 it creates the following files:
#
#    src.000000-000999.svndmp.gz
#    src.001000-001999.svndmp.gz
#    src.002000-002923.svndmp.gz
#
#    Say the next time HEAD is at 3045 it creates these two files:
#
#    src.002000-002999.svndmp.gz
#    src.003000-003045.svndmp.gz
#
#
# 3. Create incremental single revision dumps (for use in post-commit).
#
#    svn-backup-dumps.py -r <revnr> <repos> <dumpdir>
#
#    <revnr>      A revision number.
#    <repos>      Path to the repository.
#    <dumpdir>    Directory for storing the dump file.
#
#    This creates a dump file named 'src.NNNNNN.svndmp.gz' where
#    NNNNNN is the revision number of HEAD.
#
#
# 4. Create incremental dumps relative to last dump
#
#    svn-backup-dumps.py -i <repos> <dumpdir>
#
#    <repos>      Path to the repository.
#    <dumpdir>    Directory for storing the dump file.
#
#    When if dumps are performed when HEAD is 2923,
#    then when HEAD is 3045, is creates these files:
#
#    src.000000-002923.svndmp.gz
#    src.002924-003045.svndmp.gz
#
#
# 5. Create gzipped dump files.
#
#    svn-backup-dumps.py -z ...
#
#    ...          More options, see 1-4, 7, 8.
#
#
# 6. Create bzipped dump files.
#
#    svn-backup-dumps.py -b ...
#
#    ...          More options, see 1-4, 7, 8.
#
#
# 7. Transfer the dumpfile to another host using ftp.
#
#    svn-backup-dumps.py -t ftp:<host>:<user>:<password>:<path> ...
#
#    <host>       Name of the FTP host.
#    <user>       Username on the remote host.
#    <password>   Password for the user.
#    <path>       Subdirectory on the remote host.
#    ...          More options, see 1-6.
#
#    If <path> contains the string '%r' it is replaced by the
#    repository name (basename of the repository path).
#
#
# 8. Transfer the dumpfile to another host using smb.
#
#    svn-backup-dumps.py -t smb:<share>:<user>:<password>:<path> ...
#
#    <share>      Name of an SMB share in the form '//host/share'.
#    <user>       Username on the remote host.
#    <password>   Password for the user.
#    <path>       Subdirectory of the share.
#    ...          More options, see 1-6.
#
#    If <path> contains the string '%r' it is replaced by the
#    repository name (basename of the repository path).
#
# 9. Transfer the dumpfile to Dropbox
#
#    svn-backup-dumps.py -t dropbox:<share>:<user>:<password>:<path> ...
#
#    <share>      Currently unused.
#    <user>       Username on Dropbox.
#    <password>   Password for the user.
#    <path>       Subdirectory in Dropbox, must start with /.
#    ...          More options, see 1-6.
#
#    If <path> contains the string '%r' it is replaced by the
#    repository name (basename of the repository path).
#
# TODO:
#  - find out how to report smbclient errors
#  - improve documentation
#

__version = "0.6"

import sys
import os

if os.name != "nt":
    import fcntl
    import select
import gzip
import os.path
import re
from optparse import OptionParser
from ftplib import FTP
from subprocess import Popen, PIPE
import urllib2
import json
import time

try:
    import bz2

    have_bz2 = True
except ImportError:
    have_bz2 = False

try:
    import mechanize

    have_mechanize = True
except ImportError:
    have_mechanize = False


class SvnBackupOutput:

    def __init__(self, abspath, filename):
        self.__filename = filename
        self.__absfilename = os.path.join(abspath, filename)

    def open(self):
        pass

    def write(self, data):
        pass

    def close(self):
        pass

    def get_filename(self):
        return self.__filename

    def get_absfilename(self):
        return self.__absfilename


class SvnBackupOutputPlain(SvnBackupOutput):

    def __init__(self, abspath, filename):
        SvnBackupOutput.__init__(self, abspath, filename)

    def open(self):
        self.__ofd = open(self.get_absfilename(), "wb")

    def write(self, data):
        self.__ofd.write(data)

    def close(self):
        self.__ofd.close()


class SvnBackupOutputGzip(SvnBackupOutput):

    def __init__(self, abspath, filename):
        SvnBackupOutput.__init__(self, abspath, filename + ".gz")

    def open(self):
        self.__compressor = gzip.GzipFile(filename=self.get_absfilename(),
                                          mode="wb")

    def write(self, data):
        self.__compressor.write(data)

    def close(self):
        self.__compressor.flush()
        self.__compressor.close()


class SvnBackupOutputBzip2(SvnBackupOutput):

    def __init__(self, abspath, filename):
        SvnBackupOutput.__init__(self, abspath, filename + ".bz2")

    def open(self):
        self.__compressor = bz2.BZ2Compressor()
        self.__ofd = open(self.get_absfilename(), "wb")

    def write(self, data):
        self.__ofd.write(self.__compressor.compress(data))

    def close(self):
        self.__ofd.write(self.__compressor.flush())
        self.__ofd.close()


class SvnBackupOutputCommand(SvnBackupOutput):

    def __init__(self, abspath, filename, file_extension, cmd_path,
                 cmd_options):
        SvnBackupOutput.__init__(self, abspath, filename + file_extension)
        self.__cmd_path = cmd_path
        self.__cmd_options = cmd_options

    def open(self):
        cmd = [self.__cmd_path, self.__cmd_options]

        self.__ofd = open(self.get_absfilename(), "wb")
        try:
            proc = Popen(cmd, stdin=PIPE, stdout=self.__ofd, shell=False)
        except:
            print (256, "", "Popen failed (%s ...):\n  %s" % (cmd[0],
                                                              str(sys.exc_info()[1])))
            sys.exit(256)
        self.__proc = proc
        self.__stdin = proc.stdin

    def write(self, data):
        self.__stdin.write(data)

    def close(self):
        self.__stdin.close()
        rc = self.__proc.wait()
        self.__ofd.close()


class SvnBackupException(Exception):

    def __init__(self, errortext):
        self.errortext = errortext

    def __str__(self):
        return self.errortext


class SvnBackup:

    def __init__(self, options, args):
        # need 3 args: progname, reposname, dumpdir
        if len(args) != 3:
            if len(args) < 3:
                raise SvnBackupException("too few arguments, specify"
                                         " repospath and dumpdir.\nuse -h or"
                                         " --help option to see help.")
            else:
                raise SvnBackupException("too many arguments, specify"
                                         " repospath and dumpdir only.\nuse"
                                         " -h or --help option to see help.")
        self.__repospath = args[1]
        self.__dumpdir = args[2]
        # check repospath
        rpathparts = os.path.split(self.__repospath)
        if len(rpathparts[1]) == 0:
            # repospath without trailing slash
            self.__repospath = rpathparts[0]
        if not os.path.exists(self.__repospath):
            raise SvnBackupException("repos '%s' does not exist." % self.__repospath)
        if not os.path.isdir(self.__repospath):
            raise SvnBackupException("repos '%s' is not a directory." % self.__repospath)
        for subdir in ["db", "conf", "hooks"]:
            dir = os.path.join(self.__repospath, subdir)
            if not os.path.isdir(dir):
                raise SvnBackupException("repos '%s' is not a repository." % self.__repospath)
        rpathparts = os.path.split(self.__repospath)
        self.__reposname = rpathparts[1]
        if self.__reposname in ["", ".", ".."]:
            raise SvnBackupException("couldn't extract repos name from '%s'." % self.__repospath)
        # check dumpdir
        if not os.path.exists(self.__dumpdir):
            raise SvnBackupException("dumpdir '%s' does not exist." % self.__dumpdir)
        elif not os.path.isdir(self.__dumpdir):
            raise SvnBackupException("dumpdir '%s' is not a directory." % self.__dumpdir)
        # set options
        self.__rev_nr = options.rev
        self.__count = options.cnt
        self.__quiet = options.quiet
        self.__deltas = options.deltas
        self.__relative_incremental = options.relative_incremental

        # svnadmin/svnlook path
        self.__svnadmin_path = "svnadmin"
        if options.svnadmin_path:
            self.__svnadmin_path = options.svnadmin_path
        self.__svnlook_path = "svnlook"
        if options.svnlook_path:
            self.__svnlook_path = options.svnlook_path

        # check compress option
        self.__gzip_path = options.gzip_path
        self.__bzip2_path = options.bzip2_path
        self.__zip = None
        compress_options = 0
        if options.gzip_path != None:
            compress_options = compress_options + 1
        if options.bzip2_path != None:
            compress_options = compress_options + 1
        if options.bzip2:
            compress_options = compress_options + 1
            self.__zip = "bzip2"
        if options.gzip:
            compress_options = compress_options + 1
            self.__zip = "gzip"
        if compress_options > 1:
            raise SvnBackupException("--bzip2-path, --gzip-path, -b, -z are "
                                     "mutually exclusive.")

        self.__overwrite = False
        self.__overwrite_all = False
        if options.overwrite > 0:
            self.__overwrite = True
        if options.overwrite > 1:
            self.__overwrite_all = True
        self.__transfer = None
        if options.transfer != None:
            self.__transfer = options.transfer.split(":")
            if len(self.__transfer) != 5:
                if len(self.__transfer) < 5:
                    raise SvnBackupException("too few fields for transfer '%s'." % self.__transfer)
                else:
                    raise SvnBackupException("too many fields for transfer '%s'." % self.__transfer)
            if self.__transfer[0] not in ["ftp", "smb", "dropbox"]:
                raise SvnBackupException("unknown transfer method '%s'." % self.__transfer[0])

    def set_nonblock(self, fileobj):
        fd = fileobj.fileno()
        n = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, n | os.O_NONBLOCK)

    def exec_cmd(self, cmd, output=None, printerr=False):
        if os.name == "nt":
            return self.exec_cmd_nt(cmd, output, printerr)
        else:
            return self.exec_cmd_unix(cmd, output, printerr)

    def exec_cmd_unix(self, cmd, output=None, printerr=False):
        try:
            proc = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=False)
        except:
            return (256, "", "Popen failed (%s ...):\n  %s" % (cmd[0],
                                                               str(sys.exc_info()[1])))
        stdout = proc.stdout
        stderr = proc.stderr
        self.set_nonblock(stdout)
        self.set_nonblock(stderr)
        readfds = [stdout, stderr]
        selres = select.select(readfds, [], [])
        bufout = ""
        buferr = ""
        while len(selres[0]) > 0:
            for fd in selres[0]:
                buf = fd.read(16384)
                if len(buf) == 0:
                    readfds.remove(fd)
                elif fd == stdout:
                    if output:
                        output.write(buf)
                    else:
                        bufout += buf
                else:
                    if printerr:
                        sys.stdout.write("%s " % buf)
                    else:
                        buferr += buf
            if len(readfds) == 0:
                break
            selres = select.select(readfds, [], [])
        rc = proc.wait()
        if printerr:
            print("")
        return (rc, bufout, buferr)

    def exec_cmd_nt(self, cmd, output=None, printerr=False):
        try:
            proc = Popen(cmd, stdout=PIPE, stderr=None, shell=False)
        except:
            return (256, "", "Popen failed (%s ...):\n  %s" % (cmd[0],
                                                               str(sys.exc_info()[1])))
        stdout = proc.stdout
        bufout = ""
        buferr = ""
        buf = stdout.read(16384)
        while len(buf) > 0:
            if output:
                output.write(buf)
            else:
                bufout += buf
            buf = stdout.read(16384)
        rc = proc.wait()
        return (rc, bufout, buferr)

    def get_head_rev(self):
        cmd = [self.__svnlook_path, "youngest", self.__repospath]
        r = self.exec_cmd(cmd)
        if r[0] == 0 and len(r[2]) == 0:
            return int(r[1].strip())
        else:
            print(r[2])
        return -1

    def get_last_dumped_rev(self):
        filename_regex = re.compile("(.+)\.\d+-(\d+)\.svndmp.*")
        # start with -1 so the next one will be rev 0
        highest_rev = -1

        for filename in os.listdir(self.__dumpdir):
            m = filename_regex.match(filename)
            if m and (m.group(1) == self.__reposname):
                rev_end = int(m.group(2))

                if rev_end > highest_rev:
                    # determine the latest revision dumped
                    highest_rev = rev_end

        return highest_rev

    def transfer_ftp(self, absfilename, filename):
        rc = False
        try:
            host = self.__transfer[1]
            user = self.__transfer[2]
            passwd = self.__transfer[3]
            destdir = self.__transfer[4].replace("%r", self.__reposname)
            ftp = FTP(host, user, passwd)
            ftp.cwd(destdir)
            ifd = open(absfilename, "rb")
            ftp.storbinary("STOR %s" % filename, ifd)
            ftp.quit()
            rc = len(ifd.read(1)) == 0
            ifd.close()
        except Exception, e:
            raise SvnBackupException("ftp transfer failed:\n  file:  '%s'\n  error: %s" % \
                                     (absfilename, str(e)))
        return rc

    def transfer_smb(self, absfilename, filename):
        share = self.__transfer[1]
        user = self.__transfer[2]
        passwd = self.__transfer[3]
        if passwd == "":
            passwd = "-N"
        destdir = self.__transfer[4].replace("%r", self.__reposname)
        cmd = ("smbclient", share, "-U", user, passwd, "-D", destdir,
               "-c", "put %s %s" % (absfilename, filename))
        r = self.exec_cmd(cmd)
        rc = r[0] == 0
        if not rc:
            print(r[2])
        return rc

    def transfer_dropbox(self, absfilename, filename):
        user = self.__transfer[2]
        passwd = self.__transfer[3]
        destdir = self.__transfer[4].replace("%r", self.__reposname)
        return upload_file_dropbox(absfilename, destdir, filename, user, passwd)

    def transfer(self, absfilename, filename):
        if self.__transfer == None:
            return
        elif self.__transfer[0] == "ftp":
            self.transfer_ftp(absfilename, filename)
        elif self.__transfer[0] == "smb":
            self.transfer_smb(absfilename, filename)
        elif self.__transfer[0] == "dropbox":
            self.transfer_dropbox(absfilename, filename)
        else:
            print("unknown transfer method '%s'." % self.__transfer[0])

    def create_dump(self, checkonly, overwrite, fromrev, torev=None):
        revparam = "%d" % fromrev
        r = "%06d" % fromrev
        if torev != None:
            revparam += ":%d" % torev
            r += "-%06d" % torev
        filename = "%s.%s.svndmp" % (self.__reposname, r)
        output = None
        if self.__bzip2_path:
            output = SvnBackupOutputCommand(self.__dumpdir, filename, ".bz2",
                                            self.__bzip2_path, "-cz")
        elif self.__gzip_path:
            output = SvnBackupOutputCommand(self.__dumpdir, filename, ".gz",
                                            self.__gzip_path, "-cf")
        elif self.__zip:
            if self.__zip == "gzip":
                output = SvnBackupOutputGzip(self.__dumpdir, filename)
            else:
                output = SvnBackupOutputBzip2(self.__dumpdir, filename)
        else:
            output = SvnBackupOutputPlain(self.__dumpdir, filename)
        absfilename = output.get_absfilename()
        realfilename = output.get_filename()
        if checkonly:
            return os.path.exists(absfilename)
        elif os.path.exists(absfilename):
            if overwrite:
                print("overwriting " + absfilename)
            else:
                print("%s already exists." % absfilename)
                return True
        else:
            print("writing " + absfilename)
        cmd = [self.__svnadmin_path, "dump",
               "--incremental", "-r", revparam, self.__repospath]
        if self.__quiet:
            cmd[2:2] = ["-q"]
        if self.__deltas:
            cmd[2:2] = ["--deltas"]
        output.open()
        r = self.exec_cmd(cmd, output, True)
        output.close()
        rc = r[0] == 0
        if rc:
            self.transfer(absfilename, realfilename)
        return rc

    def export_single_rev(self):
        return self.create_dump(False, self.__overwrite, self.__rev_nr)

    def export(self):
        headrev = self.get_head_rev()
        if headrev == -1:
            return False
        if self.__count is None:
            return self.create_dump(False, self.__overwrite, 0, headrev)
        baserev = headrev - (headrev % self.__count)
        rc = True
        cnt = self.__count
        fromrev = baserev - cnt
        torev = baserev - 1
        while fromrev >= 0 and rc:
            if self.__overwrite_all or \
                    not self.create_dump(True, False, fromrev, torev):
                rc = self.create_dump(False, self.__overwrite_all,
                                      fromrev, torev)
                fromrev -= cnt
                torev -= cnt
            else:
                fromrev = -1
        if rc:
            rc = self.create_dump(False, self.__overwrite, baserev, headrev)
        return rc

    def export_relative_incremental(self):
        headrev = self.get_head_rev()
        if headrev == -1:
            return False

        last_dumped_rev = self.get_last_dumped_rev();
        if headrev < last_dumped_rev:
            # that should not happen...
            return False

        if headrev == last_dumped_rev:
            # already up-to-date
            return True

        return self.create_dump(False, False, last_dumped_rev + 1, headrev)

    def execute(self):
        if self.__rev_nr != None:
            return self.export_single_rev()
        elif self.__relative_incremental:
            return self.export_relative_incremental()
        else:
            return self.export()


# The upload_file_dropbox method is derived from
# https://github.com/jncraton/PythonDropboxUploader
#
# Copyright (c) 2010, Jon Craton
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer. Redistributions in
# binary form must reproduce the above copyright notice, this list of
# conditions and the following disclaimer in the documentation and/or other
# materials provided with the distribution. Neither the name of Jon Craton
# nor the names of its contributors may be used to endorse or promote
# products derived from this software without specific prior written
# permission. THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING,
# BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

class DropboxConnection:
    """ Creates a connection to Dropbox """

    email = ""
    password = ""
    root_ns = ""
    token = ""
    uid = ""
    request_id = ""
    browser = None

    def __init__(self, email, password):
        self.email = email
        self.password = password

        self.login()

    def login(self):
        """ Login to Dropbox and return mechanize browser instance """

        # Fire up a browser using mechanize
        self.browser = mechanize.Browser()
        self.browser.set_handle_robots(False)

        # Browse to the login page
        login_src = self.browser.open('https://www.dropbox.com/login').read()

        # Enter the username and password into the login form
        isLoginForm = lambda l: (
                                        l.action == "https://www.dropbox.com/ajax_captcha_login" or l.action == "https://www.dropbox.com/ajax_login") and l.method == "POST"

        try:
            self.browser.select_form(predicate=isLoginForm)
        except:
            self.browser = None
            raise (Exception('Unable to find login form'))

        self.get_constants(login_src)

        self.browser.form.new_control('text', 't', {'value': ''})
        self.browser.form.fixup()

        self.browser['login_email'] = self.email
        self.browser['login_password'] = self.password
        self.browser['t'] = self.token

        # Send the form
        response = self.browser.submit()

    def get_constants(self, src):
        """ Load constants from page """

        try:
            self.root_ns = re.findall(r"\"root_ns\": (\d+)", src)[0]
            self.token = re.findall(r"\"TOKEN\": ['\"](.+?)['\"]", src)[0].decode('string_escape')

        except:
            raise (Exception("Unable to find constants for AJAX requests"))

    def refresh_constants(self):
        """ Update constants from page """

        src = self.browser.open('https://www.dropbox.com/home').read()

        try:
            self.root_ns = re.findall(r"\"root_ns\": (\d+)", src)[0]
            self.token = re.findall(r"\"TOKEN\": ['\"](.+?)['\"]", src)[0].decode('string_escape')
            self.uid = re.findall(r"\"id\": (\d+)", src)[0]
            self.request_id = re.findall(r"\"REQUEST_ID\": ['\"]([a-z0-9]+)['\"]", src)[0]

        except:
            raise (Exception("Unable to find constants for AJAX requests"))

    def upload_file(self, local_file, remote_dir, remote_file):
        """ Upload a local file to Dropbox """

        if (not self.is_logged_in()):
            raise (Exception("Can't upload when not logged in"))

        self.browser.open('https://www.dropbox.com/')

        # Add our file upload to the upload form
        isUploadForm = lambda u: u.action == "https://dl-web.dropbox.com/upload" and u.method == "POST"

        try:
            self.browser.select_form(predicate=isUploadForm)
        except:
            raise (Exception('Unable to find upload form'))

        self.browser.form.find_control("dest").readonly = False
        self.browser.form.set_value(remote_dir, "dest")
        self.browser.form.find_control("mtime_utc").readonly = False
        self.browser.form.set_value(str(int(time.time())), "mtime_utc")
        self.browser.form.add_file(open(local_file, "rb"), "", remote_file)

        # Submit the form with the file
        self.browser.submit()

    def get_dir_list(self, remote_dir):
        """ Get file info for a directory """

        self.refresh_constants()

        if (not self.is_logged_in()):
            raise (Exception("Can't download when not logged in"))

        req_vars = "ns_id=" + self.root_ns + "&referrer=&t=" + self.token + "&is_xhr=true" + "&parent_request_id=" + self.request_id

        req = urllib2.Request('https://www.dropbox.com/browse' + remote_dir + '?_subject_uid=' + self.uid,
                              data=req_vars)
        req.add_header('Referer', 'https://www.dropbox.com/home' + remote_dir)

        dir_info = json.loads(self.browser.open(req).read())

        dir_list = {}

        for item in dir_info['file_info']:
            if (item['is_dir'] == False):
                # get local filename
                absolute_filename = item['ns_path']
                local_filename = re.findall(r".*\/(.*)", absolute_filename)[0]

                # get file URL and add it to the dictionary
                file_url = item['href']
                dir_list[local_filename] = file_url

        return dir_list

    def get_download_url(self, remote_dir, remote_file):
        """ Get the URL to download a file """

        return self.get_dir_list(remote_dir)[remote_file]

    def download_file_from_url(self, url, local_file):
        """ Store file locally from download URL """

        fh = open(local_file, "wb")
        fh.write(self.browser.open(url).read())
        fh.close()

    def download_file(self, remote_dir, remote_file, local_file):
        """ Download a file and save it locally """

        self.download_file_from_url(self.get_download_url(remote_dir, remote_file), local_file)

    def is_logged_in(self):
        """ Checks if a login has been established """
        if (self.browser):
            return True
        else:
            return False


def upload_file_dropbox(local_file, remote_dir, remote_file, email, password):
    """ Upload a local file to Dropbox """

    if not have_mechanize:
        raise SvnBackupException("mechanize required for Dropbox uploads, try running 'easy_install mechanize'")

    try:
        conn = DropboxConnection(email, password)
        conn.upload_file(local_file, remote_dir, remote_file)
    except:
        print("Upload to DropBox failed")
        return False

    return True


if __name__ == "__main__":
    usage = "usage: svn-backup-dumps.py [options] repospath dumpdir"
    parser = OptionParser(usage=usage, version="%prog " + __version)
    parser.add_option("-b",
                      action="store_true",
                      dest="bzip2", default=False,
                      help="compress the dump using python bzip2 library.")
    parser.add_option("-i",
                      action="store_true",
                      dest="relative_incremental", default=False,
                      help="perform incremental relative to last dump.")
    parser.add_option("--deltas",
                      action="store_true",
                      dest="deltas", default=False,
                      help="pass --deltas to svnadmin dump.")
    parser.add_option("-c",
                      action="store", type="int",
                      dest="cnt", default=None,
                      help="count of revisions per dumpfile.")
    parser.add_option("-o",
                      action="store_const", const=1,
                      dest="overwrite", default=0,
                      help="overwrite files.")
    parser.add_option("-O",
                      action="store_const", const=2,
                      dest="overwrite", default=0,
                      help="overwrite all files.")
    parser.add_option("-q",
                      action="store_true",
                      dest="quiet", default=False,
                      help="quiet.")
    parser.add_option("-r",
                      action="store", type="int",
                      dest="rev", default=None,
                      help="revision number for single rev dump.")
    parser.add_option("-t",
                      action="store", type="string",
                      dest="transfer", default=None,
                      help="transfer dumps to another machine " +
                           "(s.a. --help-transfer).")
    parser.add_option("-z",
                      action="store_true",
                      dest="gzip", default=False,
                      help="compress the dump using python gzip library.")
    parser.add_option("--bzip2-path",
                      action="store", type="string",
                      dest="bzip2_path", default=None,
                      help="compress the dump using bzip2 custom command.")
    parser.add_option("--gzip-path",
                      action="store", type="string",
                      dest="gzip_path", default=None,
                      help="compress the dump using gzip custom command.")
    parser.add_option("--svnadmin-path",
                      action="store", type="string",
                      dest="svnadmin_path", default=None,
                      help="svnadmin command path.")
    parser.add_option("--svnlook-path",
                      action="store", type="string",
                      dest="svnlook_path", default=None,
                      help="svnlook command path.")
    parser.add_option("--help-transfer",
                      action="store_true",
                      dest="help_transfer", default=False,
                      help="shows detailed help for the transfer option.")
    (options, args) = parser.parse_args(sys.argv)
    if options.help_transfer:
        print("Transfer help:")
        print("")
        print("  FTP:")
        print("    -t ftp:<host>:<user>:<password>:<dest-path>")
        print("")
        print("  SMB (using smbclient):")
        print("    -t smb:<share>:<user>:<password>:<dest-path>")
        print("")
        sys.exit(0)
    rc = False
    try:
        backup = SvnBackup(options, args)
        rc = backup.execute()
    except SvnBackupException, e:
        print("svn-backup-dumps.py: %s" % e)
    if rc:
        print("Everything OK.")
        sys.exit(0)
    else:
        print("An error occured!")
        sys.exit(1)

# vim:et:ts=4:sw=4
