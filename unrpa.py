#!/usr/bin/env python2

"""
unrpa is a tool to extract files from Ren'Py archives (.rpa).

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import optparse
import sys
import pickle


class UnRPA:
    NAME = "unrpa"

    def __init__(self, filename, verbosity=1, path=None, mkdir=False, version=None):
        self.verbose = verbosity
        if path:
            self.path = os.path.abspath(path)
        else:
            self.path = os.getcwd()
        self.mkdir = mkdir
        self.version = version
        self.archive = filename

    def log(self, verbosity, message):
        if self.verbose > verbosity:
            print("{}: {}".format(UnRPA.NAME, message))

    def exit(self, message):
        sys.exit("{}: error: {}".format(UnRPA.NAME, message))

    def extract_files(self):
        self.log(0, "extracting files.")
        if self.mkdir:
            self.make_directory_structure(self.path)
        if not os.path.isdir(self.path):
            self.exit("path doesn't exist, if you want to create it, use -m.")

        index = self.get_index()
        total_files = len(index)
        for file_number, (item, data) in enumerate(index.iteritems()):
            self.make_directory_structure(os.path.join(self.path, os.path.split(item)[0]))
            raw_file = self.extract_file(item, data, file_number, total_files)
            with open(os.path.join(self.path, item.encode('UTF-8')), "wb") as f:
                f.write(raw_file)

    def list_files(self):
        self.log(1, "listing files:")
        paths = self.get_index().keys()
        for path in sorted(paths):
            print(path.encode('utf-8'))

    def extract_file(self, name, data, file_number, total_files):
        self.log(1, "[{:04.2%}] {:>3}".format(file_number / float(total_files), name))
        offset, dlen, start = data[0]
        with open(self.archive, "rb") as f:
            f.seek(offset)
            raw_file = start + f.read(dlen - len(start))
        return raw_file

    def make_directory_structure(self, name):
        self.log(2, "creating directory structure: {}".format(name))
        if not os.path.exists(name):
            os.makedirs(name)

    def get_index(self):
        if not self.version:
            self.version = self.detect_version()

        if not self.version:
            self.exit("file doesn't look like an archive, if you are sure it is, use -f.")

        with open(self.archive, "rb") as f:
            offset = 0
            if self.version == 2:
                offset = int(f.readline()[8:], 16)
            elif self.version == 3:
                line = f.readline()
                parts = line.split()
                offset = int(parts[1], 16)
                key = int(parts[2], 16)
            f.seek(offset)
            index = pickle.loads(f.read().decode("zlib"))
            if self.version == 3:
                index = self.deobfuscate_index(index, key)

        if "/" != os.sep:
            return {item.replace("/", os.sep): data for item, data in index.iteritems()}
        else:
            return index

    def detect_version(self):
        ext = os.path.splitext(self.archive)[1].lower()
        if ext == ".rpa":
            with open(self.archive, "rb") as f:
                line = f.readline()
                if line.startswith("RPA-3.0 "):
                    return 3
                if line.startswith("RPA-2.0 "):
                    return 2
                else:
                    return None
        elif ext == ".rpi":
            return 1

    def deobfuscate_index(self, index, key):
        return {k: self.deobfuscate_entry(key, v) for k, v in index.iteritems()}

    def deobfuscate_entry(self, key, entry):
        if len(entry[0]) == 2:
            return [(offset ^ key, dlen ^ key, '') for offset, dlen in entry]
        else:
            return [(offset ^ key, dlen ^ key, start) for offset, dlen, start in entry]


if __name__ == "__main__":
    parser = optparse.OptionParser(usage="usage: %prog [options] pathname", version="%prog 1.1")

    parser.add_option("-v", "--verbose", action="count", dest="verbose", help="explain what is being done [default]")
    parser.add_option("-s", "--silent", action="store_const", const=0, dest="verbose", default=1, help="make no output")
    parser.add_option("-l", "--list", action="store_true", dest="list", default=False,
                      help="only list contents, do not extract")
    parser.add_option("-p", "--path", action="store", type="string", dest="path", default=None,
                      help="will extract to the given path")
    parser.add_option("-m", "--mkdir", action="store_true", dest="mkdir", default=False,
                      help="will make any non-existent directories in extraction path")
    parser.add_option("-f", "--force", action="store", type="int", dest="version", default=None,
                      help="forces an archive version. May result in failure.")

    (options, args) = parser.parse_args()

    if not len(args) == 1:
        if options.verbose:
            parser.print_help()
        parser.error("incorrect number of arguments.")

    if options.list and options.path:
        parser.error("option -p: only valid when extracting.")

    if options.mkdir and not options.path:
        parser.error("option -m: only valid when --path (-p) is set.")

    if options.list and options.verbose == 0:
        parser.error("option -l: can't be silent while listing data.")

    filename = args[0]

    extractor = UnRPA(filename, options.verbose, options.path, options.mkdir, options.version)
    if options.list:
        extractor.list_files()
    else:
        extractor.extract_files()