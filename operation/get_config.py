#!/usr/bin/env python3
# -*- coding: iso-8859-1 -*-

#pylint: disable=missing-docstring, line-too-long, empty-docstring, too-many-locals, invalid-name, trailing-newlines
#-------------------------------------------------------------------------------
#
# Project:          ViRES-Aeolus
# Purpose:          Aeolus -- get settings from the  "config.ini"  file
#                   registraton/deregistration accordingly
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
# Purpose:          Aeolus -- get settings from the  "config.ini"  file
#                   registraton/deregistration accordingly
# Authors:          Christian Schiller
# Copyright(C):     2017 - EOX IT Services GmbH, Vienna, Austria
# Email:            christian dot schiller at eox dot at
# Date:             2017-05-22
# License:          MIT License (MIT)


0.1: - initial version
0.2: - changed to python 3

"""

from __future__ import print_function
import os.path
import ast
import configparser as configparser


__version__ = '0.2'


def get_config(conf_file=None):
    """
        read the config file provided or use the default in the current dir
    """
    # print("I'm in "+sys._getframe().f_code.co_name)

    config = {}
    cp = configparser.ConfigParser()
    if conf_file is None:
        cfile = os.path.join(os.path.dirname(__file__), "config.ini")
    else:
        if conf_file.startswith('/'):
            cfile = conf_file
        else:
            cfile = os.path.join(os.path.dirname(__file__), conf_file)


    cp.read(cfile)

    for sec in cp.sections():
        name = str.lower(sec)
        for opt in cp.options(sec):
            value = str.strip(cp.get(sec, opt))
            try:
                if value in ('None', 'False', 'True'):
                    config[name +'.'+ str.lower(opt)] = ast.literal_eval(value)

                elif value.startswith(('[', '{')):
                    config[name +'.'+ str.lower(opt)] = ast.literal_eval(value)

                elif value == '/':
                    value = ''  #ast.literal_eval(value)
                    config[name +'.'+ str.lower(opt)] = value

                elif isinstance(value, str) and  value.startswith('/'):
                    if value.endswith('/'):
                        value = value[:-1]
                    config[name +'.'+ str.lower(opt)] = value

                elif isinstance(value, str) and  value.isalnum():
                    value = ast.literal_eval(value)
                    config[name +'.'+ str.lower(opt)] = value

                elif isinstance(value, int):
                    value = ast.literal_eval(value)
                    config[name +'.'+ str.lower(opt)] = value
                else:
                    config[name +'.'+ str.lower(opt)] = value
            except ValueError:
                config[name +'.'+ str.lower(opt)] = value


    return config


