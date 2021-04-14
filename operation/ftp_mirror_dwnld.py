#!/usr/bin/env python3
# -*- coding: iso-8859-1 -*-

#pylint: disable=missing-docstring, line-too-long, empty-docstring, too-many-locals, invalid-name, trailing-newlines

#-------------------------------------------------------------------------------
#
# Project:          ViRES-Aeolus
# Purpose:          Aeolus -- Mirror data of a ftp-mirror site and trigger
#                   registraton/deregistration accordingly
# Authors:          Christian Schiller
# Copyright(C):     2016 - EOX IT Services GmbH, Vienna, Austria
# Email:            christian dot schiller at eox dot at
# Date:             2019-09-02
# License:          MIT License (MIT)
#
#-------------------------------------------------------------------------------
# The MIT License (MIT):
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies of this Software or works derived from this Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#-------------------------------------------------------------------------------


"""
# Project:          ViRES-Aeolus
# Purpose:          Aeolus -- Mirror data of a ftp-mirror site and trigger
#                   registraton/deregistration accordingly
# Authors:          Christian Schiller
# Copyright(C):     2017 - EOX IT Services GmbH, Vienna, Austria
# Email:            christian dot schiller at eox dot at
# Date:             2019-09-02
# License:          MIT License (MIT)

WHAT:   FtpMirrorDwnld
        to mirror a directory and its subdirectories on a ftp-server
           - download new files
           - check if files are new or reprocessed products
           - extract the received files to a temporary directoy
           - move files from temporary directory to final data-directory
           - locally remove data-files and Zip-files of reprocessed products


TODO:   - multi-curl should use set_opt_xxx functions )and not be hardcoded
        - include verbose and debug
        - enhance to allow usage of wildcards (fnmatch) for ftp-mirror

added 2019-09-02:
       - added support to handle FTP-syncing wiothout actually storing the ZIP-files permanently

0.7    - changed to python 3

"""

from __future__ import print_function
import os
import shutil
import sys
import subprocess
import datetime
import traceback
import logging
import zipfile
import tarfile
#from handle_checksum import create_chksum_entry

import pycurl

    # used for dir-listings with pycurl
try:
    from io import BytesIO
except ImportError:
    from io import StringIO as BytesIO


    # we should ignore SIGPIPE when using pycurl.NOSIGNAL=1 - see
    # the libcurl tutorial for more info.
try:
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
except ImportError:
    pass


today = datetime.datetime.today()


#-------------------------------------------------------------------------------
def now():
    """
        get a time string for messages/logging
    """
    return str(datetime.datetime.strftime(datetime.datetime.utcnow(), '%Y%m%dT%H%M%SZ')).strip()


def copy_data(config, source_prod, target=None):
    """
        if incoming dataset is not compressed, move the downloaded dataset directly
        to its final location
    """
    #print("I am in "+sys._getframe().f_code.co_name)
    #logging.info("I am in "+sys._getframe().f_code.co_name)

    chksum_input_file = config['local.chksum_file']
    encoding = config['local.chksum_encoding']
    result = []

    if not source_prod.startswith(config['local.ftp_inpath']):
        source_prod = config['local.ftp_inpath'] +'/'+ source_prod

    try:
        result = shutil.copy2(source_prod, target+'/')
        if result == target+'/'+source_prod.rsplit('/')[-1]:
            result = [0, source_prod, target]
    except (OSError, IOError) as e:
        logging.error('[%s] -- Bad File, Bad Target, or IOError: %s ', now(), e)
        result = [1, source_prod]

    return result


def move_data(config, source_prod, target=None):
    """
        if incoming dataset is not compressed, move the downloaded dataset directly
        to its final location
    """
    #print("I am in "+sys._getframe().f_code.co_name)
    #logging.info("I am in "+sys._getframe().f_code.co_name)

    chksum_input_file = config['local.chksum_file']
    encoding = config['local.chksum_encoding']
    result = []

    if not source_prod.startswith(config['local.ftp_inpath']):
        source_prod = config['local.ftp_inpath'] +'/'+ source_prod

    try:
        result = os.rename(source_prod, target)
    except (OSError, IOError) as e:
        logging.error('[%s] -- Bad File, Bad Target, or IOError: %s', now(), e)
        result = [1, source_prod]

    return result



def untar_data(config, source_prod, target=None):
    """
        unpack a donwloaded tar-file to a target-dir by first extracting it into a
        temporary-dir and then move it to its final location
    """
    #print("I am in "+sys._getframe().f_code.co_name)
    #logging.info("I am in "+sys._getframe().f_code.co_name)

    chksum_input_file = config['local.chksum_file']
    encoding = config['local.chksum_encoding']
    result = []

    if not source_prod.startswith(config['local.ftp_inpath']):
        source_prod = config['local.ftp_inpath'] +'/'+ source_prod

    if not os.path.exists(target+'/tmpextr/'):
        os.makedirs(target+'/tmpextr/')

##@@ TODO --> add additional datatypes (filenames) handling -->> there are also some Aux and CAL files which are TGZs
    try:
            # check if is is really a tarfile (or already extracted ??? )
        if tarfile.is_tarfile(source_prod):
            sourceTAR = tarfile.open(source_prod, 'r')
            for member in sourceTAR.getmembers():
                if member.name.startswith(('AE_OPER_ALD_U_N_', 'AE_OPER_AUX_MET_12_')) and member.name.endswith(('.DBL', '.dbl')):
                    sourceTAR.extract(member.name, path=target+'/tmpextr/')
                    os.rename(os.path.join(target+'/tmpextr/', member.name), target+'/'+member.name)
                    sourceTAR.close()
                    result = [0, member.name, target]
                         ### generate md5sum entry
#                    create_chksum_entry(chksum_input_file, target+'/'+member.name, encoding)
#                    logging.info('[%s] -- Created chksum entry -- %s ', now(), target+'/'+member.name)
                elif member.name.startswith(('AE_OPER_ALD_U_N_', 'AE_OPER_AUX_MET_12_')) and member.name.endswith(('.HDR', '.hdr')):
                    continue
                else:
                    logging.error('[%s] -- TAR-File %s does not contain a "*.DBL" file', now(), source_prod)
                    result = [1, source_prod]
                    sourceTAR.close()
#        elif source_prod.startswith('AE_OPER_AUX_') and source_prod.endswith('.EEF'):
#            shutil.copy(source_prod, target+'/tmpextr/')
        else:
            logging.error('[%s] -- Not a valid TAR-File %s', now(), source_prod)
            result = [1, source_prod]

    except (tarfile.TarError, IOError) as err:
        logging.error('[%s] -- Bad TARFile or IOError: %s ', now(), err)
        result = [1, source_prod]

    return result




##@@  TODO !!! -->  setup (if there are any ZIP-files at all)
def unzip_data(config, source_prod, target=None):
    """
        unpack a donwloaded zip-file to a target-dir by first extracting it into a
        temporary-dir and then move it to its final location
    """
    #print("I am in "+sys._getframe().f_code.co_name)
    #logging.info("I am in "+sys._getframe().f_code.co_name)

    chksum_input_file = config['local.chksum_file']
    encoding = config['local.chksum_encoding']
    result = []

    if not source_prod.startswith(config['local.ftp_inpath']):
        source_prod = config['local.ftp_inpath'] +'/'+ source_prod

    if not os.path.exists(target+'/tmpextr/'):
        os.makedirs(target+'/tmpextr/')

        #print('ERROR - ZIP Files are not considered yet!')
    logging.error('[%s] -- ERROR - ZIP Files are not considered yet!', now())

    return result


class FtpMirrorDwnld:
    """
        FTP-Mirror-Donwload class
    """



    def __init__(self, config):
        self.config = config
        self.curl_options = {}



        # consolidate the various curl_opt_xxxx into a curl_options dict for further use
    def prepare_curl_options(self, *args):
        # print("I'm in "+sys._getframe().f_code.co_name)
        #logging.info("I am in "+sys._getframe().f_code.co_name)

        for elem in args:
            self.curl_options.update(elem)

        return self.curl_options




        # server access optinos for curl  (-> ! pycurl doesnt like unicode URLs)
    def set_opt_serv(self):
        """
            Server access optinos for curl
            Info: e.g. cu.unsetopt(pycurl.MAXREDIRS)  ## this will reset the respective curl_option to its default value

        """
        # print("I'm in "+sys._getframe().f_code.co_name)
        #logging.info("I am in "+sys._getframe().f_code.co_name)

                # ( newer pycurl (>7.19.3 -  doesn't like unicode URLs // but 7.19.0  doesn't handle the decoded values correctly)
        #curl_opt_serv = self.prepare_curl_options({pycurl.URL : self.config['server.server'].decode('utf-8')})
        curl_opt_serv = self.prepare_curl_options({pycurl.URL : self.config['server.server']})

        if self.config['server.netrc']:
            curl_opt_serv = self.prepare_curl_options({pycurl.NETRC : 1})
            curl_opt_serv = self.prepare_curl_options({pycurl.NETRC_FILE : self.config['server.netrc']})

        if self.config['server.serveruid'] and self.config['server.serverpwd']:
            curl_opt_serv = self.prepare_curl_options({pycurl.USERPWD : self.config['server.serveruid'] +':'+ self.config['server.serverpwd']})

        if self.config['server.proxy']:
            curl_opt_serv = self.prepare_curl_options({pycurl.PROXY : self.config['server.proxy'].decode('utf-8')})

            if self.config['server.proxyuid'] and self.config['server.proxypwd']:
                curl_opt_serv = self.prepare_curl_options({pycurl.PROXYUSERPWD : self.config['server.proxyuid'] +'%3A'+ self.config['server.proxypwd']})

        return curl_opt_serv




            # some, rather general, options for curl
    def set_opt_base(self):
        """
            define basic curl-settings
        """
        #print("I am in "+sys._getframe().f_code.co_name)
        #logging.info("I am in "+sys._getframe().f_code.co_name)

        curl_opt_base = {
            pycurl.VERBOSE : False,
            #pycurl.DEBUGFUNCTION : 'debug_func',
            pycurl.TIMEOUT : 300,
            pycurl.CONNECTTIMEOUT : 30,
            pycurl.NOSIGNAL : 1,
            #pycurl.MAXREDIRS : 3,
            #pycurl.FOLLOWLOCATION : 1,      # shouldn't be need for ftp, though possible
            pycurl.NOPROGRESS: 1,      # no progress
            #pycurl.NOPROGRESS : 0,     # shows curl progress type - needs next option
            #pycurl.NOPROGRESS : progress_function,    # shows self-definde progress type
            pycurl.FTP_USE_EPSV: 0,
            #pycurl.FTP_USE_PRET: 1,
            #pycurl.FTP_SKIP_PASV_IP: 1,
            pycurl.FTP_FILEMETHOD : 3
        }

            # set output to verbos/non-verbose
        if self.config['general.verbose']:
            curl_opt_base.update({pycurl.VERBOSE : True})

            # TODO:  turn on debugging output
        #if config['general.debug'] is True:
            #curl_opt_base.update({pycurl.DEBUGFUNCTION: curl_debug})

        return curl_opt_base




    def set_list_dir(self, indir):
        """
            set directory on the ftp to be evaluated
        """
        # print("I'm in "+sys._getframe().f_code.co_name)
        #logging.info("I am in "+sys._getframe().f_code.co_name)

        cwd_dir = 'cwd '+indir
        curl_opt_list = {
            pycurl.QUOTE :  [cwd_dir]
            }

        return curl_opt_list



    def set_write_type(self, outtype, *args):
        """
            set how output shall be handled -
        """
        # print("I'm in "+sys._getframe().f_code.co_name)
        #logging.info("I am in "+sys._getframe().f_code.co_name)

            # either define outpout as a "writeable file"  or as  "BytesIO()"
        if str.lower(outtype) == 's':
            output = BytesIO()
        if str.lower(outtype) == 'f':
            output = open(args[0], "wb")

            # curl >=7.19.3 can use WRITEDATA with a python object (before only
            # the WRITEFUNCTION is available)
        #curl_opt_write = {
            #pycurl.WRITEDATA : output
            #}
        curl_opt_write = {pycurl.WRITEFUNCTION : output.write}

        return curl_opt_write, output




    def get_listing(self, fmd, indir):
        """
            set all parameters and get the directory listings
        """
        # print("I'm in "+sys._getframe().f_code.co_name)
        #logging.info("I am in "+sys._getframe().f_code.co_name)

        cu = pycurl.Curl()
        curl_opt_serv = self.set_opt_serv()
        curl_opt_base = self.set_opt_base()
        curl_opt_list = self.set_list_dir(indir)
        curl_opt_write, output = self.set_write_type('s')
        self.curl_options = self.prepare_curl_options(curl_opt_serv, curl_opt_base, curl_opt_list, curl_opt_write)

        for k, v in list(self.curl_options.items()):
            cu.setopt(k, v)

        flist = []
        dir_list = []

        try:
            logging.info('[%s] -- Initiating Ftp-Mirroring to: %s', now(), self.config['server.server'])
            cu.perform()
        except:
            logging.error('[%s] -- %s', now(), traceback.print_exc(file=sys.stderr))
            logging.error('[%s] -- %s', now(), sys.exc_info()[0])
            sys.stderr.flush()

        logging.info('DWNLD: %s', cu.getinfo(cu.SIZE_DOWNLOAD))
        inlist = output.getvalue()
        flist, dir_list = self.split_ftp_listing(cu, inlist, flist, dir_list, output, cur_dir=indir)
        output.close()
        cu.close()


# a FIX
            # add a file-filter to allow limitation of download to defined files
        if 'server.file_filter' in self.config:
            file_filter = self.config['server.file_filter']
            flist_filtered = []
            for elem in flist:
                for ffilter in file_filter:
                    if elem.find(ffilter) > -1:
                        flist_filtered.append(elem)
            flist = flist_filtered[:]

        return flist, dir_list




    def cnv_ftp_date(self, fl):
        """
            convert the dates delivered by ftp-listing to YYYY-MM-DD HH:MM:SS'
            used when a long listing (incl. file-size and date/time from the FTP) is requested
        """
        # print("I'm in "+sys._getframe().f_code.co_name)

        if ':' in fl[-2]:
            year_in = str(today.year)
            ftp_date = datetime.datetime.strptime(' '.join([' '.join(fl[5:8]), year_in]), '%b %d  %H:%M %Y')
        else:
            ftp_date = datetime.datetime.strptime(' '.join(fl[5:8]), '%b %d %Y')

        return ftp_date




    def split_ftp_listing(self, cu, inlist, flist, dir_list, output, cur_dir=None):
        """
            split up the file-listing from the ftp to make it comparable with
            locally available files
        """
        # print("I'm in "+sys._getframe().f_code.co_name)
        #logging.info("I am in "+sys._getframe().f_code.co_name)

        new_dir_list = []
        if cur_dir is None:
            cur_dir = self.config['server.dir']

        fl = inlist.splitlines()

        for i in range(len(fl[:])):
            fl[i] = fl[i].split()

        for i in range(len(fl[:])):
            if fl[i][0].startswith(b'd'):
                if (len(cur_dir) == 0) or (cur_dir == '/'):
                    dir_list.append('/'+fl[i][-1])
                    new_dir_list.append('/'+fl[i][-1])
                else:
                    dir_list.append(cur_dir+'/'+fl[i][-1].decode())
                    new_dir_list.append(cur_dir+'/'+fl[i][-1].decode())
            else:
                if (len(cur_dir) == 0) or (cur_dir == '/'):
                    o_file = '/'+fl[i][8].decode()
                    flist.append(o_file)
                else:
                    o_file = cur_dir+'/'+fl[i][8].decode()
                    flist.append(o_file)

            # continue if subdirs are enabled
        if self.config['server.subdir']:
            if len(new_dir_list) > 0:
                for ndir in new_dir_list:
                    output.seek(0)
                    output.truncate(0)
                    cur_dir = ndir

                    cu.setopt(cu.URL, self.config['server.server'])
                    req = 'cwd '+cur_dir+'/'
                    cu.setopt(cu.QUOTE, [req])

                    cu.perform()
                    inlist = output.getvalue()

                    flist, dir_list = self.split_ftp_listing(cu, inlist, flist, dir_list, output, cur_dir)

# DEBUG
# fix to get rid of the doubble '//' in the pathnames
        #flist_1 = []
        #for elem in flist:
        #    flist_1.append(elem.replace('//','/'))

        #return flist_1, dir_list
        return flist, dir_list




    def get_locallist(self):
        """
            get the listing of the local data (target) directory
        """
        # print("I'm in "+sys._getframe().f_code.co_name)
        #logging.info("I am in "+sys._getframe().f_code.co_name)

        loclist = []
        locpath = self.config['local.ftp_inpath']
        for root, _, files in os.walk(locpath):
            for f in files:
                loclist.append(os.path.join(root, f).split(locpath)[1])

        return loclist



    def compare_lists2(self, flist, loclist):
        """
            # <Removing ZIP-Storage>:
            compare ftp- and local file-lists to find out what is new and has to be downloaded
            this version receives the local-list as input (the other calls a function to creates the local-list)
        """
        # print("I'm in "+sys._getframe().f_code.co_name)

        justflist = frozenset(flist).difference(loclist)
        justloclist = frozenset(loclist).difference(flist)
        downloadlist = justflist
        removelist = justloclist

        return downloadlist, removelist




    def compare_lists(self, flist):
        """
            compare ftp- and local file-lists to find out what is new and has to be downloaded
        """
        # print("I'm in "+sys._getframe().f_code.co_name)
        #logging.info("I am in "+sys._getframe().f_code.co_name)

        loclist = self.get_locallist()

        justflist = frozenset(flist).difference(loclist)
        justloclist = frozenset(loclist).difference(flist)
        downloadlist = justflist
        removelist = justloclist

        return downloadlist, removelist




    def make_subdir(self, createdir):
        """
            create the locally required subdirectories during the download from the ftp site
        """
        # print("I'm in "+sys._getframe().f_code.co_name)
        #logging.info("I am in "+sys._getframe().f_code.co_name)

## TODO -- check dir -write-  permission (on vagrant thats always root...)
        try:
            os.makedirs(createdir, 0o775)
            logging.info('[%s] -- Created dir: %s', now(), createdir)
        except IOError as e:
            logging.error('[%s] -- %s - %s', now(), e.errno, e)

        return



    def remove_localfiles(self, removelist, withdirs=False):
        """
            *** CURRENTLY NOT IN USE BY SWARM-VirES-Aeolus ***
            Remove local files which are not on the ftp-server anymore
            ATTENTION: !!!  Verify that these files are de-registered from an EOxServer instance before removing.
            # Not yet activated: also removes empty dirs (even if they might still exist on the ftp-server).
            Input: removelist -- list of path/files (w/o the  config['local.ftp_inpath']  part)
        """
        # print("I'm in "+sys._getframe().f_code.co_name)
        #logging.info("I am in "+sys._getframe().f_code.co_name)

        locpath = self.config['local.ftp_inpath']
        for elem in removelist:
            logging.info('[%s] -- Removing: %s', now(), locpath+elem)
            try:
                os.remove(locpath+elem)
                if withdirs:
                    try:
                        os.removedirs(os.path.dirname(locpath+elem))
                        logging.info('[%s] -- Removing: %s', now(), os.path.dirname(locpath+elem))
                    except OSError:
                        continue
            except OSError:
                if withdirs:
                    try:
                        os.removedirs(os.path.dirname(locpath+elem))
                    except OSError:
                        continue
                else:
                    continue




    def get_files_multi(self, downloadlist, index_serv, num_conn=None, dwnlinfo=None):
        """
            - runs the actual ftp download in a multi-connection mode
            - triggers the unpacking of the products to a temporary directory
               as well as moving them to the final data-directory
        """
        #print("I'm in "+sys._getframe().f_code.co_name())
        #logging.info("I am in "+sys._getframe().f_code.co_name)

        if num_conn is None:
            num_conn = self.config['server.num_conn']

            # a queue with (source, output) tuples
        queue = []

##############!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!######################
## TODO -- added counter (cnt) for testing purpose
## comment-out this block and uncomment 1 line below (see notice)
#        n = 3
#        cnt = 0
#        for elem in downloadlist:
#            if cnt > n:
#                break
#            cnt += 1

##############!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!######################
## TODO: uncomment the line below for regular functionality and comment-out block above
        for elem in downloadlist:
            outfile = str(self.config['local.ftp_inpath']+elem).strip()
            if not os.path.isdir(os.path.dirname(outfile)):
                self.make_subdir(os.path.dirname(outfile))

            source = str(self.config['server.server']+elem).strip()
            if not source or source[-1] == "#":
                continue

            queue.append((source, outfile))

        num_sources = len(queue)
        num_conn = min(num_conn, num_sources)

        assert 1 <= num_conn <= 100, "invalid number of concurrent connections"

        logging.info('[%s] -- Downloading: %s files using %s connections.', now(), num_sources, num_conn)


        mcu = pycurl.CurlMulti()
        mcu.handles = []
        for _ in range(num_conn):

            cu1 = pycurl.Curl()
            cu1.output = None
## TODO -- this (->cu1) should use the above "set_opt_xxx" procedures and not be hardcoded here
#               but somehow this doesn't work properly
#            curl_opt_serv = self.set_opt_serv()
#            curl_opt_base = self.set_opt_base()
#            #curl_opt_write, output = self.set_write_type('f', outfile)
#            self.curl_options = self.prepare_curl_options(curl_opt_serv, curl_opt_base, )
#            for k, v in self.curl_options.items():
#                cu1.setopt(k, v)
#
            if self.config['server.netrc']:
                cu1.setopt(pycurl.NETRC, pycurl.NETRC_REQUIRED)
                cu1.setopt(pycurl.NETRC_FILE, self.config['server.netrc'])
                cu1.setopt(pycurl.FOLLOWLOCATION, 1)
            if self.config['general.verbose']:
                cu1.setopt(pycurl.VERBOSE, True)
            cu1.setopt(pycurl.MAXREDIRS, 5)
            cu1.setopt(pycurl.CONNECTTIMEOUT, 30)
            cu1.setopt(pycurl.FTP_USE_EPSV, 0)
            cu1.setopt(pycurl.TIMEOUT, 300)
            cu1.setopt(pycurl.NOSIGNAL, 1)

            mcu.handles.append(cu1)

        free_hlist = mcu.handles[:]
        num_processed = 0


        while num_processed < num_sources:
                # If there is an source to process and a free curl object, add to multi stack
            while queue and free_hlist:
                source, outfile = queue.pop(0)
                cu1 = free_hlist.pop()
                cu1.output = open(outfile, "wb")
                cu1.setopt(pycurl.WRITEFUNCTION, cu1.output.write)
                cu1.setopt(pycurl.URL, source)
                mcu.add_handle(cu1)
                    # store some info
                cu1.outfile = outfile
                cu1.source = source

                # Run the internal curl state machine for the multi stack
            while 1:
                ret, _ = mcu.perform()
                if ret != pycurl.E_CALL_MULTI_PERFORM:
                    break

                # Check for curl objects which have terminated, and add them to the free_hlist
            while 1:
                num_q, ok_list, err_list = mcu.info_read()
                for cu1 in ok_list:
                    #cu1.output = cu1.buffer.getvalue()
                    cu1.output.close()
                    cu1.output = None
                    mcu.remove_handle(cu1)

                    dwnld_num = num_processed + 1
                    logging.info('[%s] -- Dwnld-Success %s of %s : %s  --> %s ', now(), dwnld_num, num_sources, cu1.source, cu1.outfile)   #, cu1.getinfo(pycurl.EFFECTIVE_URL)
                    free_hlist.append(cu1)

                        # unpack the downloaded data
                    if isinstance(self.config['local.data'], str):
                        outdir_serv = [self.config['local.data']]
                    else:
                        outdir_serv = self.config['local.data']

                        ## adding a check if donwloaded file is a ZIP / TGZ / XML / TAR?
                    ftype_1 = subprocess.check_output(['file', cu1.outfile])
                    ftype = str(ftype_1).split(':')[1].strip().lower()

                        # *EEF files are of ftype='xml'
                    if ftype.startswith('xml'):
                        result = copy_data(self.config, cu1.outfile, target=outdir_serv[index_serv])
                        # TGZs will first be of type gzip
                    elif ftype.startswith('gzip') and str(cu1.outfile).endswith(('.TGZ', '.tgz')):
                        result = untar_data(self.config, cu1.outfile, target=outdir_serv[index_serv])
                    elif ftype.startswith('zip'):
                        result = unzip_data(self.config, cu1.outfile, target=outdir_serv[index_serv])
                    elif ftype.find('tar') > -1:
                        result = untar_data(self.config, cu1.outfile, target=outdir_serv[index_serv])
                    else:
                        result = [1, 'Unknown FileType: '+cu1.outfile]

                    if result[0] == 0:
                        logging.info('[%s] -- Successfully unpacked product - %s in %s ', now(), result[1], result[2])

                            # <Removing ZIP-Storage>: since we don't store the ZIP-files anymore - we can delete them after successful unpacking
                        os.remove(cu1.outfile)
                        logging.info('[%s] -- Successfully removed TGZ/ZIP-file - %s ', now(), cu1.outfile)

                    elif result[0] == 1:
                        logging.error('[%s] -- Could not unpack product - %s', now(), result[1])

                    elif result[0] == 2:
                        logging.error('[%s] -- Could not Convert product - %s', now(), result[1])
                    else:
                        logging.error('[%s] -- Undhandled Error - %s', now(), result[1])

                            # <Removing ZIP-Storage>: since we don't store the ZIP-files anymore - we can delete them after successful unpacking
                        os.remove(cu1.outfile)
                        logging.info('[%s] -- Successfully removed BAD TGZ/ZIP-file - %s ', now(), cu1.outfile)
                            # we also should remove a bad ZIP from the flist(ftp_list_now) -> so it gets downloaded again next time (hopefully corrected)
                            # write the bad_zip-file name into an extra log-file
                        with open(config['local.bad_zips'], 'a') as bz:
                            print(cu1.outfile, file=bz)


                    # TODO -- how to handle failed downloads?  ->  retry, ignore, list in log  ??
                for cu1, errno, errmsg in err_list:
                    cu1.output.close()
                    cu1.output = None
                    mcu.remove_handle(cu1)

                    logging.warning("[%s] -- Failed: %s --> %s - %s, %s", now(), cu1.source, cu1.outfile, errno, errmsg)
                    free_hlist.append(cu1)

                num_processed = num_processed + len(ok_list) + len(err_list)
                if num_q == 0:
                    break
                # no more I/O is pending, calling select() to sleep until something is going on again
            mcu.select(1.0)

            if dwnlinfo:
                self.get_cu1_info(cu1)


            # Cleanup
        for cu1 in mcu.handles:
            if cu1.output is not None:
                cu1.output.close()
                cu1.output = None
            cu1.close()
        mcu.close()




        # prints lots of information (activated via parameter to "get_files_multi" )
    def get_cu1_info(self, cu1):
        """
        Return a dictionary with all info on the last response.
        """
        # print("I'm in "+sys._getframe().f_code.co_name)
        #logging.info("I am in "+sys._getframe().f_code.co_name)

        cu1_info = {
            'effective-url': cu1.getinfo(pycurl.EFFECTIVE_URL),
            'http-code': cu1.getinfo(pycurl.HTTP_CODE),
            'total-time': cu1.getinfo(pycurl.TOTAL_TIME),
            'namelookup-time': cu1.getinfo(pycurl.NAMELOOKUP_TIME),
            'connect-time': cu1.getinfo(pycurl.CONNECT_TIME),
            'pretransfer-time': cu1.getinfo(pycurl.PRETRANSFER_TIME),
            'size-upload': cu1.getinfo(pycurl.SIZE_UPLOAD),
            'size-download': cu1.getinfo(pycurl.SIZE_DOWNLOAD),
            'speed-upload': cu1.getinfo(pycurl.SPEED_UPLOAD),
            'header-size': cu1.getinfo(pycurl.HEADER_SIZE),
            'request-size': cu1.getinfo(pycurl.REQUEST_SIZE),
            'content-length-download': cu1.getinfo(pycurl.CONTENT_LENGTH_DOWNLOAD),
            'content-length-upload': cu1.getinfo(pycurl.CONTENT_LENGTH_UPLOAD),
            'content-type': cu1.getinfo(pycurl.CONTENT_TYPE),
            'response-code': cu1.getinfo(pycurl.RESPONSE_CODE),
            'speed-download': cu1.getinfo(pycurl.SPEED_DOWNLOAD),
            'ssl-verifyresult': cu1.getinfo(pycurl.SSL_VERIFYRESULT),
            'filetime': cu1.getinfo(pycurl.INFO_FILETIME),
            'starttransfer-time': cu1.getinfo(pycurl.STARTTRANSFER_TIME),
            'redirect-time': cu1.getinfo(pycurl.REDIRECT_TIME),
            'redirect-count': cu1.getinfo(pycurl.REDIRECT_COUNT),
            'http-connectcode': cu1.getinfo(pycurl.HTTP_CONNECTCODE),
            'httpauth-avail': cu1.getinfo(pycurl.HTTPAUTH_AVAIL),
            'proxyauth-avail': cu1.getinfo(pycurl.PROXYAUTH_AVAIL),
            'os-errno': cu1.getinfo(pycurl.OS_ERRNO),
            'num-connects': cu1.getinfo(pycurl.NUM_CONNECTS),
            'ssl-engines': cu1.getinfo(pycurl.SSL_ENGINES),
            'cookielist': cu1.getinfo(pycurl.INFO_COOKIELIST),
            'lastsocket': cu1.getinfo(pycurl.LASTSOCKET),
            'ftp-entry-path': cu1.getinfo(pycurl.FTP_ENTRY_PATH),
        }

        logging.info('[%s] -- Additional info on the last response: %s', now(), cu1.source)
        for k, v in list(cu1_info.items()):
            logging.info('%s -- %s', k, v)




