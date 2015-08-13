#!/usr/bin/env python

from vsc.utils import fancylogger
from vsc.utils.generaloption import simple_option
from vsc.utils.run import run_asyncloop

import sys
import os
from collections import defaultdict
import re
import tempfile
import shutil
from lxml import etree

# log setup
logger = fancylogger.getLogger(__name__)
fancylogger.logToScreen(True)
fancylogger.setLogLevelInfo()

template_re = re.compile(r"^\s*(?:(?:object|structure|declaration|unique)\s+)*"
                         r"template\s+(\S+)\s*;")


def is_template(name):
    if name.endswith(("schema.pan", "schema.tpl")):
        return True
    logger.debug("NOT a pan file.")
    return False

def detect_template_basedir(top, filename):
    """
    also insane, cleanup with find_templates
    """
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
    
    """
    this is insane, cleanup
    """
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
    for relpath in sorted(template_bases.keys()):
        logger.info("scanning templates relative to %s", relpath)
        tpls = template_bases[relpath]

    return tpls

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

    templates = findtemplates(go.options.source_location)
    
    tmpdir = tempfile.mkdtemp()
    logger.debug("Temporary directory: %s " % tmpdir)

    panccommand = ["panc-annotations", "--output-dir", tmpdir, "--base-dir", go.options.source_location]
    panccommand.extend([tpl for tpl in templates])
    logger.debug(panccommand)
    output = run_asyncloop(panccommand)
    logger.debug(output)

    ns = "{http://quattor.org/pan/annotations}"

    for tpl in templates:
        tpl = tpl + ".annotation.xml"
        xml = etree.parse(os.path.join(tmpdir, tpl))

        root = xml.getroot()

        print " - Types"

        for stype in root.findall('%stype' % ns):
            name = stype.get('name')
            print "  - /software/ceph/" + name
            for doc in stype.findall(".//%sdesc" % ns ):
                print "   - decription: " + doc.text

            for field in stype.findall(".//%sfield" % ns ):
                print "   - /software/ceph/" + name + "/" + field.get('name')
                required = field.get('required')
                if required == "true":
                    print "    - required"
                else:
                    print "    - optional"


                for ffs in field.findall(".//%sbasetype" % ns):
                    fieldtype = ffs.get('name')
                    print "    - type: " + fieldtype
                    if fieldtype == "long" and ffs.get('range'):
                        fieldrange = ffs.get('range')
                        print "    - range: " + fieldrange

      #          print "    - type: " + field.findall(".//%sbasetype" % ns )[0].get('name')
        
            print "\n------------------------------------------------------------------------\n"

        print "\n - Functions"
        

        for fnname in root.findall('%sfunction' % ns):
            name = fnname.get('name')
            print "  - " + name
            for doc in fnname.findall(".//%sdesc" % ns ):
                print "   description: " + doc.text
            for arg in fnname.findall(".//%sarg" % ns):
                print "   - arg: " + arg.text

            print "\n------------------------------------------------------------------------\n"

                
    logger.debug("Removing temporary directory: %s " % tmpdir)
    shutil.rmtree(tmpdir)

if __name__ == '__main__':
    main()
