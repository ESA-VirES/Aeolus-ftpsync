#!/usr/bin/env python3
# -*- coding: iso-8859-1 -*-

#pylint: disable=missing-docstring, line-too-long, empty-docstring, too-many-locals, invalid-name, trailing-newlines
#-------------------------------------------------------------------------------
#
# Project:          ViRES-Aeolus
# Purpose:          Aeolus -- Mirror data of a ftp-mirror site - Control structure
# Authors:          Christian Schiller
# Copyright(C):     2016 - EOX IT Services GmbH, Vienna, Austria
# Email:            christian dot schiller at eox dot at
# Date:             2017-05-22
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
# Purpose:          Aeolus -- Mirror data of a ftp-mirror site - Control structure
# Authors:          Christian Schiller
# Copyright(C):     2017 - EOX IT Services GmbH, Vienna, Austria
# Email:            christian dot schiller at eox dot at
# Date:             2017-05-22
# License:          MIT License (MIT)

WHAT:   initates the FtpMirrorDwnld, and manages the workflow
          - get the configration (from cmd-line or default)
          - get listing dir/file-listing from ftp-server
          - get local dir/file-listing
          - compare local and ftp listing
          - download files from ftp (using multi-curl)
          - cleanup the ftp-instances

added 2019-09-02:
        - added support to handle FTP-syncing wiothout actually storing the ZIP-files permanently
0.4     - changed to python 3
"""

#/*************  imports
from __future__ import print_function
import os
import sys
import shutil
import logging
#import time

from get_config import get_config
from ftp_mirror_dwnld import FtpMirrorDwnld
from ftp_mirror_dwnld import now


__version__ = '0.4'





def cleanup(fmd):
    """
        Cleanup ftp_mirror instance
    """
    # print("I'm in "+sys._getframe().f_code.co_name)
    #logging.info("I am in "+sys._getframe().f_code.co_name)

    #sys.stdout.write("...\n")
    sys.stdout.flush()
    fmd = None

    logging.info('[%s] - *** D O N E ***', now())








#/****************************************************************/
#/*                         Main()                               */
#/****************************************************************/
def main():
    """
        Controls the download / file-removal
    """
    # print("I'm in "+sys._getframe().f_code.co_name)
    #logging.info("I am in "+sys._getframe().f_code.co_name)

        # get a config-file from the commandline or us a default one
    if len(sys.argv[1:]) == 1 and sys.argv[1].endswith('.ini'):
        config = get_config(sys.argv[1])
    else:
            # get a default *config.ini file
        config = get_config('ftp_data_config.ini')

    logging.basicConfig(filename=config['general.logfile'], level=logging.INFO)

        # make sure the path to store the ftp-list files exists
    ftp_list_path = config['local.ftp_list_prev'].rsplit('/', 1)[0]
    if os.path.isdir(ftp_list_path) is False:
        os.mkdir(ftp_list_path, 0o775)


        # initialise the download class
    try:
        fmd = FtpMirrorDwnld(config)
    except KeyError as error:
        logging.exception("[%s] -- Missing  %s  entry in provided config-file:  %s", now(), error, sys.argv[1])
        sys.exit()

        # start the donwload process
    indir_serv = config['server.dir']
    if isinstance(indir_serv, str):
        indir_serv = [indir_serv]

    for index_serv in range(len(indir_serv)):
        logging.info('Checking -- %s', indir_serv[index_serv])
        flist, _ = fmd.get_listing(fmd, indir_serv[index_serv])

#======
            # prepare for the ftp-listings to be stored/used
            # <Removing ZIP-Storage>:  where current and previous ftp-lists are stored
        if indir_serv[index_serv].find('Meteorological') >= 0:
            prod_ext = indir_serv[index_serv].rsplit('/')[-1]
        elif indir_serv[index_serv].find('Instrument_Mon') >= 0:
            prod_ext = 'InstMo_'+indir_serv[index_serv].rsplit('/')[-1]
        elif indir_serv[index_serv].find('L2') >= 0:
            prod_ext = 'L1B_L2_'+indir_serv[index_serv].rsplit('/')[-1]
        elif indir_serv[index_serv].find('Cal') >= 0:
            prod_ext = 'L1B_Cal_'+indir_serv[index_serv].rsplit('/')[-1]

        ftp_list_prev = config['local.ftp_list_prev']+'_'+prod_ext
        ftp_list_now = config['local.ftp_list_now']+'_'+prod_ext



            # copy old (ftp_list_now)  ftp-listing to previous (ftp_list_prev)
            # <Removing ZIP-Storage>:
        if os.path.isfile(ftp_list_now) is True and os.stat(ftp_list_now).st_size > 0:
            print('Copying ftp_list_now -> ftp_list_prev...')   #, ftp_list_now, ' -> ', ftp_list_prev
            try:
                shutil.copy2(ftp_list_now, ftp_list_prev)
            except (IOError, os.error) as ee:
                print(ee)
            except Exception as e:
                print(e)


            # <Removing ZIP-Storage>:   read the previous ftp_list_prev
        if os.path.isfile(ftp_list_prev) is True:
            with open(ftp_list_prev, 'r') as ftp_prev:
                print('Reading ftp_list_prev...')
                ftp_prev_list = ftp_prev.read().splitlines()
        else:
            ftp_prev_list = []

#======

            # compare the received file-list with the local file-listing
            # # <Removing ZIP-Storage>:  used with ZIP-files
        #downloadlist, removelist  = fmd.compare_lists(flist)
            # compare the new (flist == ftp_list_now) with the previous (ftp_prev_list) FTP-list
            # # <Removing ZIP-Storage>:  used with PRODUCT-files
        downloadlist, _ = fmd.compare_lists2(flist, ftp_prev_list)

        logging.info('Found Products for Download: %s', len(downloadlist))
        if len(downloadlist) == 0:
            logging.info('[%s] - Nothing to do for: %s', now(), str(indir_serv[index_serv]))
                # <Removing ZIP-Storage>:  finally write the current ftp-list to the file "ftp_list_now.txt"
            with open(ftp_list_now, 'w') as ftp_now:
                print('Writing ftp_list_now...')
                for elem in flist:
                    print(elem, file=ftp_now)

            # download new files
        else:
            try:
                result = fmd.get_files_multi(downloadlist, index_serv, num_conn=config['server.num_conn'], dwnlinfo=config['general.verbose'])
                if result:
                    logging.info('Download results:%s', result)

                    # <Removing ZIP-Storage>:  remove bad-zip-files from the current ftp-list --> so they get downloaded next time again
                if os.path.isfile(config['local.bad_zips']):
                    with open(config['local.bad_zips'], 'r') as bz:
                        bad_zips = bz.read().replace(config['local.ftp_inpath'], '').splitlines()
                    for bad_zip in bad_zips:
                        flist.remove(bad_zip)

                    # <Removing ZIP-Storage>:  finally write the current ftp-list to the file "ftp_list_now.txt"
                with open(ftp_list_now, 'w') as ftp_now:
                    print('Writing ftp_list_now...')
                    for elem in flist:
                        print(elem, file=ftp_now)

                    # now that the ftp_list_now has been written (without the bad zip-files) this file can be removed
                if os.path.isfile(config['local.bad_zips']):
                    os.remove(config['local.bad_zips'])


            except Exception as e:
                logging.error('[%s] - Nothing to do -- %s, %s', now(), sys._getframe().f_code.co_name, e)



    ## To be noted that two REPROCESSING-SCENARIOS apply (lt. Gabriella Costa):
        ## - Products regeneration: in this case a new product with different counter (e.g. 0406 -> 0407) would be generated and available in the "current" directory. The products with the previous counter can either still be present in the "current" directory or be removed from the "current" directory. This scenario applies if only few products need to be re-generated
        ## - Reprocessing: in this case the baseline is modified and the counter re-started (e.g. 0406 -> 0501). In this case the current folder is first  emptied and then is gradually filled with newly generated products and with the reprocessed products. It might take up to a couple of months to regenerate the whole data set and to completely fill the "current' folder. This scenario applies if there is an important change in the algorithm and the whole mission products need to be re-generated




        # call deletion procedure
        # remove files which are not on the ftp-server anymore (but still locally available)
## TODO        # ATTENTION: !!!  Verify that these files are de-registered from an EOxServer instance before removing.
        # also try to remove empty dirs (even if they might still exist on the ftp-server)
        # ATTENTION: !!!  consider REPROCESSING-SCENARIOS described above
        #
        # here in VirES-Aeolus  we do not delete the files at the FTP-mirror directly, but rather from the
        # registration/deregistration procedure to ensure that files are first de-registered correctly
        # and to ensure that the full removal at the ESA FTP does not remove all our files locally !

#    withdirs = False   # default
    #withdirs = True
#    fmd.remove_localfiles(removelist, withdirs)



    cleanup(fmd)


#-------
if __name__ == "__main__":
    sys.exit(main())
