# -*- coding: utf-8 -*-
# Copyright (c) 2016, TeamBoB.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.

"""

=====
Saber
=====

Saber is an AI challenge platform for Anokha'16
For more information, see http://github.com/arrow-/saber

"""

__all__ = ['quantum', 'map_util', 'util', 'engine', 'house']

# Definition of the version number
version_info = 0, 1, 0, 'dev1'  # major, minor, patch, extra

# Nice string for the version (mimic how IPython composes its version str)
__version__ = '-'.join(map(str, version_info)).replace('-', '.').strip('-')