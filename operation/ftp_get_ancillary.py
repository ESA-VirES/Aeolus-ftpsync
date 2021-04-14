#!/usr/bin/env python3
# -*- coding: iso-8859-1 -*-

#pylint: disable=missing-docstring, line-too-long, empty-docstring, too-many-locals, invalid-name, trailing-newlines
#-------------------------------------------------------------------------------
#
# Project:          VirES-Aeolus
# Purpose:          Get the new "Dst_MJD_1998.dat" and  "Kp_MJD_1998_QL.dat" and Orbit-Count files
# Authors:          Christian Schiller
# Copyright(C):     2017 - EOX IT Services GmbH, Vienna, Austria
# Email:            christian dot schiller at eox dot at
# Date:             2017-07-22
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
# Project:          VirES-Aeolus
# Purpose:          Get the new Auxiliary files from ESA FTP
# Authors:          Christian Schiller
# Copyright(C):     2017 - EOX IT Services GmbH, Vienna, Austria
# Email:            christian dot schiller at eox dot at
# Date:             2017-07-22
# License:          MIT License (MIT)

WHAT:   Get Auxiliary files  ->  eg. for albedo maps


# version 0.3 requires a config file as a comd-line parameter
# version 0.4 added support for reading netrc file
# version 0.5 changed to python 3

"""


from __future__ import print_function
import os
import sys
#import time
import datetime
import logging
#from ftplib import FTP
import ftplib
import netrc
#import calendar

from get_config import get_config


__version__ = '0.5'

config = None





#-------------------------------------------------------------------------------
def now():
    """
        get a time string for messages/logging
    """
    #return str(time.strftime('%Y%m%dT%H%M%S')).strip()
    return str(datetime.datetime.strftime(datetime.datetime.utcnow(), '%Y%m%dT%H%M%SZ')).strip()



def get_listing(ftp):
    """
        get the listing of the files from the target directory
    """
    #print("I'm in "+sys._getframe().f_code.co_name)

    inlist = []
    tmp_inlist = []
    if isinstance(config['server.dir'], list):
        for sdir in config['server.dir']:
            response = ftp.cwd(sdir)
            response = ftp.retrlines('LIST', tmp_inlist.append)
            for i in range(len(tmp_inlist)):
                tmp_inlist[i] += '  ' + sdir

            for elem in tmp_inlist:
                inlist.append(elem)

    elif isinstance(config['server.dir'], str):
        response = ftp.cwd(config['server.dir'])
        response = ftp.retrlines('LIST', inlist.append)
        for i in range(len(inlist)):
            inlist[i] += '  ' +config['server.dir']

    outlist = extract_flist(inlist)

    return outlist



def extract_flist(inlist):
    """
        extract the desired names
    """
    #print("I'm in "+sys._getframe().f_code.co_name)

    outlist = []
    for i in range(0, len(inlist)):
        inli = str.split(inlist[i])

        if len(inli) < 10:
            continue
        if inli[-2].startswith(tuple(config['server.target_file'])):
            outlist.append(inli[-6:])

    return outlist




def chk_flist_status(outlist):
    """
        check the date-time of the target files
    """
    #print("I'm in "+sys._getframe().f_code.co_name)

    dwnl_lst = []
    rem_local = False
    today = datetime.datetime.today()

    loc_list = get_locallist()
    if len(loc_list) == 0:
        for elem in outlist:
            dwnl_lst.append(os.path.join(elem[-1], elem[-2]))

        return dwnl_lst, rem_local, loc_list


    for elem in outlist:
        if ':' in elem[3]:
            year_in = str(today.year)
            fdate = ' '.join(elem[1:4])
            ftpdate = datetime.datetime.strptime(' '.join([fdate, year_in]), '%b %d  %H:%M %Y')
        else:
            ftpdate = datetime.datetime.strptime(' '.join(elem[1:4]), '%b %d %Y')

        if loc_list[0][0] < ftpdate:
            dwnl_lst.append(os.path.join(elem[-1], elem[-2]))

        if loc_list[0][-1].find('ORBCNT') > -1:
            rem_local = True

    return dwnl_lst, rem_local, loc_list



def get_locallist():
    """
        get the listing of the local data (target) directory
    """
    #print("I'm in "+sys._getframe().f_code.co_name)

    loclist = []
    locpath = config['local.data']
    for _, _, files in os.walk(locpath):
        for f in files:
            fp = os.path.join(locpath, f)
            ti = datetime.datetime.fromtimestamp(os.path.getmtime(fp))
            loclist.append([ti, f])

    return loclist




def get_files(ftp, dwnl_lst):
    """
        download the target files from the target directory to a temporary location
    """
    #print("I'm in "+sys._getframe().f_code.co_name)

    cnt = 1
    num = len(dwnl_lst)
    for elem in dwnl_lst:
        elem_1 = elem.split('/')[-1]
        ff = open(os.path.join(config['local.ftp_inpath'], elem_1), 'wb')
        logging.info('[%s] -- Receiving: %s of %s files: %s', now(), cnt, num, elem_1)
        response = ftp.retrbinary('RETR ' + elem, ff.write)
        ff.flush()
        ff.close()
        move_files(elem_1)
        cnt += 1




def move_files(elem):
    """
        move the files from a temporary location to their final target
    """
    #print("I'm in "+sys._getframe().f_code.co_name)

    logging.info('[%s] -- Moving: %s --> %s ', now(), os.path.join(config['local.ftp_inpath'], elem), os.path.join(config['local.data'], elem))
    #print('Moving ', os.path.join(config['local.ftp_inpath'], elem), ' --> ', os.path.join(config['local.data'], elem))
    os.rename(os.path.join(config['local.ftp_inpath'], elem), os.path.join(config['local.data'], elem))


def remove_loclist(loclist):
    """
        remove the previous set of Orbit-Count files
    """
    for elem in loclist:
        try:
            os.remove(os.path.join(config['local.data'], elem[-1]))
            # the following is also logged by the watch process
#            logging.info('[%s] -- Deleted:  %s', now(), os.path.join(config['local.data'], elem[-1]))
        except OSError as e:
            logging.info('[%s] -- [ERROR]: %s', now(), e)



def cleanup(ftp):
    """
        quit /close the ftp connection
    """
    #print("I'm in "+sys._getframe().f_code.co_name)

    response = ftp.quit()
    logging.info('[%s] -- *** DONE *** -- %s', now(), response.splitlines()[0])
    sys.exit()






#/****************************************************************/
#/*                         Main()                               */
#/****************************************************************/
def main():
    """
        check a ftp-site for the existance of newer version of target files
        download target files if newer files are available
    """
    #print("I'm in "+sys._getframe().f_code.co_name)

    global config

        # get the configuration from the config.ini provided at the cmd-line
    if len(sys.argv[1:]) == 1 and sys.argv[1].endswith('.ini'):
        config = get_config(sys.argv[1])
    else:
        print("[%s]  -- ERROR:  No config-file (*.ini) has been supplied" % now())
        sys.exit(1)

    logging.basicConfig(filename=config['general.logfile'], level=logging.DEBUG)

        #ftplib doesn't handle urls (like pycurrl does)
    if config['server.server'].startswith('ftp://'):
        config['server.server'] = config['server.server'][6:]


    if 'server.netrc' in config:
            ## get the login infos from the netrc file
        try:
            auth = netrc.netrc(config['server.netrc']).authenticators(config['server.server'])
            if auth is not None:
                config['server.serveruid'], account, config['server.serverpwd'] = auth
        except (netrc.NetrcParseError, IOError):
            pass

        # get the filelisting from the ftp-server
    try:
        logging.info('[%s] -- Initiating FTP-Server check for new data', now())
        ftp = ftplib.FTP(config['server.server'])
        welcome = ftp.login(config['server.serveruid'], config['server.serverpwd'])
        outlist = get_listing(ftp)
    except ftplib.all_errors as e:
        logging.error('[%s] - %s', now(), e)
        cleanup(ftp)


    if len(outlist) > 0:
        dwnl_lst, rem_local, loclist = chk_flist_status(outlist)
    else:
        logging.info('[%s] -- No data-files found on FTP-Server ...', now())
        cleanup(ftp)

    if len(dwnl_lst) > 0:
        try:
            logging.info('[%s] -- Found %s files for download', now(), len(dwnl_lst))
            get_files(ftp, dwnl_lst)
            if rem_local is True:
                remove_loclist(loclist)
            cleanup(ftp)
        except ftplib.all_errors as e:
            logging.error('[%s] - %s', now(), e)
            cleanup(ftp)

    else:
        logging.info('[%s] -- No new data-files found ... ...', now())
        cleanup(ftp)





if __name__ == "__main__":
    sys.exit(main())
