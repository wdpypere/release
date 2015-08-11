#!/usr/bin/env python

from vsc.utils import fancylogger
from vsc.utils.generaloption import simple_option
import sys
import os
from collections import defaultdict
import re


# log setup
logger = fancylogger.getLogger(__name__)
fancylogger.logToScreen(True)
fancylogger.setLogLevelInfo()

template_re = re.compile(r"^\s*(?:(?:object|structure|declaration|unique)\s+)*"
                         r"template\s+(\S+)\s*;")


def is_template(name):
    if name.endswith((".pan", ".tpl")):
        return True
    logger.debug("NOT a pan file.")
    return False

def detect_template_basedir(top, filename):
    # If top = "/path", filename = "/path/a/b/c.tpl", and it starts with
    # "template b/c;", then we want to return (a, b/c.tpl)
    template_name = None
    relpath, ext = os.path.splitext(os.path.relpath(filename, top))
    with open(filename, "r") as fd:
        for line in fd:
            res = template_re.match(line)
            if not res:
                continue
            template_name = res.group(1)
            break

    if template_name and (relpath == template_name or
                          relpath.endswith("/" + template_name)):
        if relpath == template_name:
            return ".", template_name + ext
        else:
            return relpath[:-len(template_name) - 1], template_name + ext
    else:
        # Either we failed to parse the template, or the template name was not
        # correct. The safe choice is to parse the template alone (well, at most
        # together with other templates in the same directory), and let panc
        # sort it out.
        return os.path.dirname(relpath), os.path.basename(relpath) + ext


def findtemplates(location):
    template_bases = defaultdict(list)

    logger.debug("Start tree walk.")
    for root, dirs, files in os.walk(location, topdown=True):
        # Make sure we don't descend into mgmt directories (e.g. .git)
        for i in range(len(dirs) - 1, -1, -1):
            if dirs[i].startswith("."):
                logger.debug("Removing dir %s. Hidden directory." % dirs[i])
                del dirs[i]

        for f in files:
            logger.debug("checking if %s is a pan template." % f)
            if not is_template(f):
                continue

            basedir, tplpath = detect_template_basedir(location, os.path.join(root, f))
            template_bases[basedir].append(tplpath)
    logger.debug(template_bases)
    

def main():
    options = {
        'output_location': ('The location where the output markdown files should be written to.', None, 'store', None, 'o'),
        'java_location': ('The location of the JRE.', None, 'store', None, 'j'),
        'source_location': ('The location where the source template files can be found.', None, 'store', None, 's'),
    }
    go = simple_option(options)
    logger.info("Starting main.")

    if not go.options.output_location:
        logger.error("output location not specified")
        sys.exit(1)
    if not go.options.source_location:
        logger.error("source location not specified")
        sys.exit(1)
        
    if not os.path.exists(go.options.output_location):
        logger.debug("Output location %s does not exist. Creating it." % go.options.output_location)
        os.makedirs(go.options.output_location)

    findtemplates(go.options.source_location)
if __name__ == '__main__':
    main()
