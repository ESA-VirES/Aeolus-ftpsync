#!/usr/bin/env python3
# -*- coding: iso-8859-1 -*-

#pylint3: disable=missing-docstring, line-too-long, empty-docstring, too-many-locals, invalid-name, trailing-newlines

#-------------------------------------------------------------------------------
#
# Project:          VirES-AEOLUS
# Purpose:          get the listing of the ESA FTP public data and link already
#                      existing products to public Collections
# Authors:          Christian Schiller
# Copyright(C):     2020 - EOX IT Services GmbH, Vienna, Austria
# Email:            christian dot schiller at eox dot at
# Date:             2020-04-09
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
Project:          VirES-AEOLUS
Purpose:          get the listing of the ESA FTP public data and link already
                      existing products to public Collections
Authors:          Christian Schiller
Copyright(C):     2020 - EOX IT Services GmbH, Vienna, Austria
Email:            christian dot schiller at eox dot at
Date:             2020-04-09
License:          MIT License (MIT)


versions:
0.1.: - first version

"""

from __future__ import print_function
import os
import sys
import datetime
import socket
import fnmatch
import logging

sys.path.append('/var/www/aeolus.services/production/eoxs')
sys.path.append('/usr/local/vires/ftp_mirror_and_register/')

from get_config import get_config
from ftp_mirror_dwnld import FtpMirrorDwnld

try:
    from aeolus_register import link_public_product as link_pub_prod
    from aeolus_register import get_public_collection_list as get_pub_col_lst
except ImportError:
    pass

    # used for dir-listings with pycurl
try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO


    # we should ignore SIGPIPE when using pycurl.NOSIGNAL=1 - see
    # the libcurl tutorial for more info.
try:
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
except ImportError:
    pass



#-------------------------------------------------------------------------------
def now():
    """
        get a time string for messages/logging
    """
    return str(datetime.datetime.strftime(datetime.datetime.utcnow(), '%Y%m%dT%H%M%SZ')).strip()


def findfile(inmask, path, recursive=True, splitpath=False):
    """
        find a file in a directory tree , including sub-dirs (default),
        simple wildcards *, ?, and character ranges expressed with [] will be matched
            Usage:  result = findfile(path, inmask, recursive=True, splitpath=True)
    """
    # print "I'm in "+sys._getframe().f_code.co_nameout_not_reg

    result = []
    if recursive is True:
        for root, _, files in os.walk(path):
            for file in files:
                if fnmatch.fnmatch(file, inmask):
                    if splitpath is False:
                        result.append(os.path.join(root, file))
                    else:
                        result.append([file, root])
        return result
    else:
        files = os.listdir(path)
        if splitpath is False:
            result = fnmatch.filter(files, inmask)
        else:
            res = fnmatch.filter(files, inmask)
            for elem in res:
                result.append([elem, path])
        return result


def linking_public_product(flist, logger):
    """
        link public products to a public Collection
    """
    # print("I'm in "+sys._getframe().f_code.co_name)

    not_reg = []
    for elem in flist:
        file_found = findfile(elem+'*', '/mnt/data/aeolus/L1B_L2_Products')
        if file_found:
            for item in file_found:
                prod_id = os.path.basename(item)[:-4]
                coll_name = prod_id[8:18]+'_public'

                try:
                    link_pub_prod(prod_id, coll_name, logger)
                except Exception as ee:
                    logger.error("Product could not be linked to Collection -- %s" %  str(ee+'\n'))
        else:
            logger.error("Public Product not found as regular Product -- %s" % elem)
            not_reg.append(elem)

    return not_reg


def set_outfiles(config, time=False):
    """
        set parameters for outfiles and cleanup already existing outfiles
    """
    # print("I'm in "+sys._getframe().f_code.co_name)

    if time is True:
        timestamp = '_'+now()
    else:
        timestamp = ''

    target_outpath = os.path.dirname(config['local.bad_zips'])
    host = socket.gethostname().split('.')[0]

    outftp_list = target_outpath+'/ftp-ftp_publist_'+host+timestamp
    outftp_list_long = outftp_list+'_long'
    out_not_reg = target_outpath+'/ftp-ftp_notreg_pub_'+host+timestamp
    out_list_registered = target_outpath+'/ftp-ftp_is_reg_pub_'+host+timestamp
    out_2be_reg = target_outpath+'/ftp-ftp_2be_reg_pub_'+host+timestamp

    return outftp_list, outftp_list_long, out_not_reg, out_list_registered, out_2be_reg



def write_lists_out(out_list_name, out_list):
    """
        write the outfiles
    """
    # print("I'm in "+sys._getframe().f_code.co_name)

    with open(out_list_name, 'w') as ftp_list:
        #print('Writing  %s' % out_list_name)
        for elem in out_list:
            print(elem, file=ftp_list)



def create_public_symlink(src, dest, infile, logger):
    """
        create symlinks for the respective public files iin public directories pointing to the real data
    """
    # print("I'm in "+sys._getframe().f_code.co_name)

    try:
        os.symlink(src+'/'+infile, dest+'/'+infile)
    except FileExistsError as fee:
        #logging.error("[%s] - Error - SymLink already exists - %s - %s" % (now(), infile, fee))
        logger.error("SymLink already exists - %s - %s" % infile, str(fee+'\n'))
        pass


def get_pub_ftp_list(config, logger):
    """
        get the ftp listing for the public products
    """
    # print("I'm in "+sys._getframe().f_code.co_name)

        # initialise the download class
    try:
        fmd = FtpMirrorDwnld(config)
    except KeyError as error:
        logger.error("Missing  %s  entry in config-file:  %s" % (str(error), config))
        pass

        # start the download process
    indir_serv = config['server.dir']
    if isinstance(indir_serv, str):
        indir_serv = [indir_serv]

    flist_short = []
    flist_long = []
    total_prod = 0

    for index_serv, _ in enumerate(indir_serv):
        logger.info("Checking -- %s" % indir_serv[index_serv])
        try:
            flist, _ = fmd.get_listing(fmd, indir_serv[index_serv])
            logger.info("Gathering ftp_list -- %s -- %s" % (indir_serv[index_serv], len(flist)))
            total_prod += len(flist)
        except Exception as eef:
            logger.error("Error-FTP gathering Public Producs list - %s" %  str(eef+'\n'))

#------
#            # add extra checking for MCO/MLI/MIO/MMA products - only get the _SHA_ (but not the _VAL_) from the ADDS
#        ffilter = ('_VAL_', '_VALi', '_SHAi')
#        for elem in ffilter:
#            flist = [e for e in flist if elem not in e]
#------

        for elem in flist:
            flist_long.append(elem)

        ftp_filt = ('.EEF', '.TGZ')
        for elem in flist:
            for item in ftp_filt:
                if elem.endswith(item):
                    flist_short.append(os.path.basename(elem[:-(len(item))]))
                    break

    flist_short.sort()
    flist_long.sort()

    #logger.info("Total products found -- %s" % total_prod)
    return flist_short, flist_long


def cleanup(logger):
    """
        Cleanup ftp_mirror instance
    """
    # print("I'm in "+sys._getframe().f_code.co_name)

    logger.info("*** D O N E ***")



#/****************************************************************/
#/*                         Main()                               */
#/****************************************************************/
def main():
    """
        Controls the donwload / file-removal
    """
    # print("I'm in "+sys._getframe().f_code.co_name)

        ## create outfiles or not
    #IS_OUTFILE = False
    IS_OUTFILE = True
        ## just get the filelisting without performing any other actions
    FLIST_ONLY = False
    #FLIST_ONLY = True


        ## get a config-file from the commandline or us a default one
    if len(sys.argv[1:]) >= 1 and sys.argv[1].endswith('.ini'):
        config = get_config(sys.argv[1])
    else:
        log.error('No *config.ini file provided')
        sys.exit(1)

        # logging.basicConfig  is not working with Django -->
    #logging.basicConfig(filename=config['general.logfile'], level=logging.INFO)

        # set up a logger working with django
    log_file = config['general.logfile']
    log = logging.getLogger('aeolus_proc_pubdata')
    log.setLevel(logging.INFO)
        # create file handler which logs even debug messages
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.INFO)
        # create console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
        # create formatter and add it to the handlers
    formatter = logging.Formatter("%(asctime)s -- %(levelname)s -- %(message)s", "[%Y%m%dT%H%M%SZ]")
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
        # add the handlers to the logger
    log.addHandler(fh)
    log.addHandler(ch)

    if len(sys.argv[1:]) == 2 and sys.argv[2] == '--list_only':#
        #print('List Only')
        FLIST_ONLY = True


    if FLIST_ONLY:
            # execute the ftp to gather filelisting of public products
        log.info("#--------------------------------------------------------#")
        log.info('Gathering Public Product lists only - no further actions performed')
        flist_short, flist_long = get_pub_ftp_list(config, log)
        host = socket.gethostname().split('.')[0]

        write_lists_out('/home/schillerc/info_registered/ftp-ftp_list_'+host+'_'+now(), flist_short)
        write_lists_out('/home/schillerc/info_registered/ftp-ftp_list_'+host+'_'+now()+'_long', flist_long)

        log.info("Output: /home/schillerc/info_registered/ftp-ftp_list_"+host+'_'+now())
        log.info("Output: /home/schillerc/info_registered/ftp-ftp_list_"+host+'_'+now()+'_long')
        log.info("*** DONE ***")
        log.info("#--------------------------------------------------------#")
        sys.exit(0)


        # turn on/off outfiles -- configure outfiles
    if IS_OUTFILE:
        outftp_list, outftp_list_long, out_not_reg, out_list_registered, out_2be_reg = set_outfiles(config, time=False)


            # execute the ftp to gather file-listing of public products
    try:
        flist_short, flist_long = get_pub_ftp_list(config, log)
        log.info('Available on ADDF -- %s' % len(flist_short))
    except Exception as eo:
        log.error("Getting ADDF list -- %s" % str(eo+'\n'))

        # get a list of the already registered public datasets
    coll_names = config['local.coll_names']

            # get a list of already linked products
    try:
        pub_list_reg = get_pub_col_lst(coll_names, log)
        log.info("Available local -- %s" % len(pub_list_reg))
    except Exception as ep:
        log.error("Getting local list -- %s" % str(ep+'\n'))

    pub_list_2reg = []
    pub_list_registered = []

    for prod in flist_short:
        if prod not in pub_list_reg:
            pub_list_2reg.append(prod)
        else:
            pub_list_registered.append(prod)

    pub_list_2reg.sort()
    log.info("Products to be linked -- %s " % len(pub_list_2reg))

    try:
        not_registered = linking_public_product(pub_list_2reg, log)
        log.info("Products not registered -- %s " % len(not_registered))
    except Exception as er:
        log.error("Products not registered -- %s" % str(er+'\n'))

        # create the symlink for the products from public directories to the actual data storage
#    create_public_symlink(src, dest, infile, logging)


        # turn on/off outfiles -- write outfiles
    if IS_OUTFILE:
            # remove old versions
        if os.path.isfile(outftp_list):
            os.remove(outftp_list)

        if os.path.isfile(outftp_list_long):
            os.remove(outftp_list_long)

        if os.path.isfile(out_not_reg):
            os.remove(out_not_reg)

        if os.path.isfile(out_list_registered):
            os.remove(out_list_registered)

            # write new files
        write_lists_out(outftp_list, flist_short)
        write_lists_out(outftp_list_long, flist_long)
        write_lists_out(out_not_reg, not_registered)
        write_lists_out(out_list_registered, pub_list_registered)
        if pub_list_2reg:
            write_lists_out(out_2be_reg, pub_list_2reg)

    cleanup(log)


#-------
if __name__ == "__main__":
    sys.exit(main())


