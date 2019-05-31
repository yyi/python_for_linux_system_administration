#!/usr/bin/python
# -*- coding: UTF-8 -*-
import os
import fnmatch
import find_specific_files

images = ['*.jpg', '*.json', '*.jpeg', '*.png', '*.tif', '*.tiff']
matches = []
for file in find_specific_files.find_specific_files(os.path.expanduser('~'), images):
    print (file)
for root, dirnames, filenames in os.walk(os.path.expanduser("~/abc")):
    for extensions in images:
        for filename in fnmatch.filter(filenames, extensions):
            matches.append(os.path.join(root, filename))

print(matches)
