#!/usr/bin/env python2
"""
quattor-pod-doc generates markdown documentation from the
pod's in configuration-modules-core and creates a index for
the website on http://quattor.org.

@author: Wouter Depypere (Ghent University)

"""
import sys
import os
import re
from vsc.utils.generaloption import simple_option
from vsc.utils import fancylogger
from vsc.utils.run import run_asyncloop

MAILREGEX = re.compile(("([a-z0-9!#$%&'*+\/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+\/=?^_`"
                        "{|}~-]+)*(@|\sat\s)(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(\.|"
                        "\sdot\s))+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)"))
PATHREGEX = re.compile(r'(\s+)((?:/[\w{}]+)+\.?\w*)(\s*)')
EXAMPLEMAILS = ["example", "username", "system.admin"]
logger = fancylogger.getLogger()
DOCDIR = "docs"

REPOMAP = {
    "configuration-modules-core": {"sitesubdir": "components",
                                   "prefix": "ncm-",
                                   "target": "/NCM/Component/"},
    #"aii": {"sitesubdir": "AII",
    #        "prefix": "aii-",
    #        "target": " "},
    "CAF": {"sitesubdir": "CAF",
            "prefix": "",
            "target": "/CAF/"},
    "CCM": {"sitesubdir": "CCM",
            "prefix": "",
            "target": "EDG/WP4/CCM/"},
#    "build-scripts": {"sitesubdir": "maven-tools",
#                    "prefix": "",
#                    "target": ""},
    }


def mavencleancompile(repo_location, repository):
    """
    Executes mvn clean and mvn compile in the given modules_location.
    """
    repoloc = os.path.join(repo_location, repository)
    logger.info("Doing maven clean in %s." % repoloc)
    output = run_asyncloop("mvn clean", startpath=repoloc)
    logger.debug(output)

    logger.info("Doing maven compile in %s." % repoloc)
    output = run_asyncloop("mvn compile", startpath=repoloc)
    logger.debug(output)


def generatemds(repo, sources, location):     # , subdir, prefix):
    """
    Takes a list of components with podfiles and generates a md file for it.
    """
    logger.info("Generating md files.")
    counter = 0
    mdfiles = []

    comppath = os.path.join(location, DOCDIR , REPOMAP[repo]['sitesubdir']) 
    if not os.path.exists(comppath):
        os.makedirs(comppath)

    for source in sources:
        if source.endswith(".pan"):
            mdfile = os.path.split(source)[-2] + "schema.md"
            #print "found pan file, making pan annotations."
        else:
            sourcename = source.split(REPOMAP[repo]['target'])[-1]
            mdfile = os.path.splitext(sourcename)[0].replace("/", "::").lower() + ".md"
            
            convertpodtomarkdown(source, os.path.join(comppath , mdfile))
            mdfiles.append(mdfile)

    logger.info("Written %s md files." % len(mdfiles))
    return mdfiles


def convertpodtomarkdown(podfile, outputfile):
    """
    Takes a podfile and converts it to a markdown with the help of pod2markdown.
    """
    logger.debug("Running pod2markdown on %s." % podfile)
    output = run_asyncloop("pod2markdown %s" % podfile)
    logger.debug("writing output to %s." % outputfile)
    logger.debug(output)
    with open(outputfile, "w") as fih:
        fih.write(output[1])


def generatetoc(pods, outputloc, indexname, subdir, prefix, title):
    """
    Generates a TOC for the parsed components.
    """
    logger.info("Generating TOC as %s." % os.path.join(outputloc, indexname))

    with open(os.path.join(outputloc, indexname), "w") as fih:
        fih.write("site_name: %s\n\n" % title)
        fih.write("theme: 'readthedocs'\n\n")
        fih.write("pages:\n")
        fih.write("- ['index.md', 'introduction']\n")

        for component in sorted(pods):
            name = component.replace(prefix, '')
            if name == "target":
                name = title
            linkname = "%s/%s.md" % (subdir, name)
            writeifexists(outputloc, linkname, subdir, fih)
            if len(pods[component]) > 1:
                for pod in sorted(pods[component][1:]):
                    subname = os.path.splitext(os.path.basename(pod))[0]
                    linkname = "%s/%s::%s.md" % (subdir, name, subname)
                    writeifexists(outputloc, linkname, subdir, fih)
        fih.write("\n")


def writeifexists(outputloc, linkname, subdir, fih):
    """
    Checks if the MD exists before adding it to the TOC.
    """
    if os.path.exists(os.path.join(outputloc, DOCDIR, linkname)):
        logger.debug("Adding %s to toc." % linkname)
        fih.write("- ['%s', '%s']\n" % (linkname, subdir))
    else:
        logger.warn("Expected %s but it does not exist. Not adding to toc."
                    % os.path.join(outputloc, DOCDIR, linkname))


def removemailadresses(mdfiles):
    """
    Removes the email addresses from the markdown files.
    """
    logger.info("Removing emailaddresses from md files.")
    counter = 0
    for mdfile in mdfiles:
        with open(mdfile, 'r') as fih:
            mdcontent = fih.read()
        replace = False
        for email in re.findall(MAILREGEX, mdcontent):
            logger.debug("Found %s." % email[0])
            replace = True
            if email[0].startswith('//'):
                replace = False
            for ignoremail in EXAMPLEMAILS:
                if ignoremail in email[0]:
                    replace = False

        if replace:
            logger.debug("Removed it from line.")
            mdcontent = mdcontent.replace(email[0], '')
            with open(mdfile, 'w') as fih:
                fih.write(mdcontent)
            counter += 1
    logger.info("Removed %s email addresses." % counter)


def removewhitespace(mdfiles):
    """
    Removes extra whitespace (\n\n\n).
    """
    logger.info("Removing extra whitespace from md files.")
    counter = 0
    for mdfile in mdfiles:
        with open(mdfile, 'r') as fih:
            mdcontent = fih.read()
        if '\n\n\n' in mdcontent:
            logger.debug("Removing whitespace in %s." % mdfile)
            mdcontent = mdcontent.replace('\n\n\n', '\n')
            with open(mdfile, 'w') as fih:
                fih.write(mdcontent)
            counter += 1
    logger.info("Removed extra whitespace from %s files." % counter)


def decreasetitlesize(mdfiles):
    """
    Makes titles smaller, e.g. replace "# " with "### ".
    """
    logger.info("Downsizing titles in md files.")
    counter = 0
    for mdfile in mdfiles:
        with open(mdfile, 'r') as fih:
            mdcontent = fih.read()
        if '# ' in mdcontent:
            logger.debug("Making titles smaller in %s." % mdfile)
            mdcontent = mdcontent.replace('# ', '### ')
            with open(mdfile, 'w') as fih:
                fih.write(mdcontent)
            counter += 1
    logger.info("Downsized titles in %s files." % counter)


def removeheaders(mdfiles):
    """
    Removes MAINTAINER and AUTHOR headers from md files.
    """
    logger.info("Removing AUTHOR and MAINTAINER headers from md files.")
    counter = 0
    for mdfile in mdfiles:
        with open(mdfile, 'r') as fih:
            mdcontent = fih.read()
        if '# MAINTAINER' in mdcontent:
            logger.debug("Removing # MAINTAINER in %s." % mdfile)
            mdcontent = mdcontent.replace('# MAINTAINER', '')
            with open(mdfile, 'w') as fih:
                fih.write(mdcontent)
            counter += 1
        if '# AUTHOR' in mdcontent:
            logger.debug("Removing # AUTHOR in %s." % mdfile)
            mdcontent = mdcontent.replace('# AUTHOR', '')
            with open(mdfile, 'w') as fih:
                fih.write(mdcontent)
            counter += 1

    logger.info("Removed %s unused headers." % counter)


def codifypaths(mdfiles):
    """
    Puts paths inside code tags
    """
    logger.info("Putting paths inside code tags.")
    counter = 0
    for mdfile in mdfiles:
        with open(mdfile, 'r') as fih:
            mdcontent = fih.read()

        logger.debug("Tagging paths in %s." % mdfile)
        mdcontent, counter = PATHREGEX.subn(r'\1`\2`\3', mdcontent)
        with open(mdfile, 'w') as fih:
            fih.write(mdcontent)

    logger.info("Code tagged %s paths." % counter)


def checkinputandcommands(sourceloc, outputloc, runmaven):
    """
    Check if the directories are in place.
    Check if the required binaries are in place.
    """
    logger.info("Checking if the given paths exist.")
    if not sourceloc:
        logger.error("Repo location not specified.")
        sys.exit(1)
    if not outputloc:
        logger.error("output location not specified")
        sys.exit(1)
    if not os.path.exists(sourceloc):
        logger.error("Repo location %s does not exist" % sourceloc)
        sys.exit(1)
    for repo in REPOMAP.keys():
        if not os.path.exists(os.path.join(sourceloc, repo)):
            logger.error("Repo location %s does not exist" % os.path.join(sourceloc, repo))
            sys.exit(1)
    if not os.path.exists(outputloc):
        logger.error("Output location %s does not exist" % outputloc)
        sys.exit(1)

    logger.info("Checking if required binaries are installed.")
    if runmaven:
        if not which("mvn"):
            logger.error("The command mvn is not available on this system, please install maven.")
            sys.exit(1)
    if not which("pod2markdown"):
        logger.error("The command pod2markdown is not available on this system, please install pod2markdown.")
        sys.exit(1)


def listperlmodules(module_location):
    """
    return a list of perl modules in module_location.
    """
    listtt = []
    for path, dirs, files in os.walk(module_location):
        if is_wanted_dir(path, files):
            for f in files:
                if is_wanted_file(path, f):
                    # pod takes preference over 
                    fname = os.path.join(path, f)
                    duplicate = ""
                    if "doc/pod" in fname:
                        duplicate = fname.replace('doc/pod', 'lib/perl')
                        if f.endswith('.pod'):
                            duplicate = duplicate.replace(".pod", ".pm")
                        if duplicate in listtt:
                            listtt[listtt.index(duplicate)] = fname
                            continue
                            
                    duplicate = ""
                    if "lib/perl" in fname:
                        duplicate = fname.replace('lib/perl', 'doc/pod' )
                        if f.endswith('.pm'):
                            duplicate = duplicate.replace(".pm", ".pod" )
                        if not duplicate in listtt:
                            listtt.append(fname)
                            continue
                    listtt.append(os.path.join(path,f))
                    
    return listtt

def is_wanted_dir(path, files):
    #must be in target
    if not 'target' in path: return False
    #directory must have files
    if len(files) == 0 : return False
    #must qualify one of these
    if not True in [ x in path for x in ["doc/pod", "lib/perl", "pan"]]: return False
    return True
    
    

def is_wanted_file(path, filename):
    # extension says it is perl
    if True in [ filename.endswith(ext) for ext in [".pod", ".pm", ".pl"]]: return True
    # it is a schema 
    if filename == "schema.pan": return True
    # it is a file without extension, check if it is perl
    if len(filename.split(".")) < 2: 
        with open(os.path.join(path, filename), 'r') as f:
            if 'perl' in f.readline(): return True
    return False

def which(command):
    """
    Check if given command is available for the current user on this system.
    """
    found = False
    for direct in os.getenv("PATH").split(':'):
        if os.path.exists(os.path.join(direct, command)):
            found = True

    return found

def main(repoloc, outputloc):
    mdfiles = {}
    for repo in REPOMAP.keys():
        logger.info("Processing %s." % repo)
        if GO.options.maven_compile:
            logger.info("Doing maven clean and compile.")
            mavencleancompile(repoloc, repo)
        else:
            logger.info("Skipping maven clean and compile.")

        pmodules = listperlmodules(os.path.join(repoloc, repo))
        mdfiles[REPOMAP[repo]['sitesubdir']] = generatemds(repo, pmodules, outputloc)
        
    print mdfiles
if __name__ == '__main__':
    OPTIONS = {
        'modules_location': ('The location of the repo checkout.', None, 'store', None, 'm'),
        'output_location': ('The location where the output markdown files should be written to.', None, 'store', None, 'o'),
        'maven_compile': ('Execute a maven clean and maven compile before generating the documentation.', None, 'store_true', False, 'c'),
        'index_name': ('Filename for the index/toc for the components.', None, 'store', 'mkdocs.yml', 'i'),
        'remove_emails': ('Remove email addresses from generated md files.', None, 'store_true', True, 'r'),
        'remove_whitespace': ('Remove whitespace (\n\n\n) from md files.', None, 'store_true', True, 'w'),
        'remove_headers': ('Remove unneeded headers from files (MAINTAINER and AUTHOR).', None, 'store_true', True, 'R'),
        'small_titles': ('Decrease the title size in the md files.', None, 'store_true', True, 's'),
        'codify_paths': ('Put paths inside code tags.', None, 'store_true', True, 'p'),
    }
    GO = simple_option(OPTIONS)
    logger.info("Starting main.")

    checkinputandcommands(GO.options.modules_location, GO.options.output_location, GO.options.maven_compile)

    main(GO.options.modules_location, GO.options.output_location)
        

#    PODS = listpods(GO.options.modules_location, COMPS, TARGET)

#    MDS = generatemds(PODS, GO.options.output_location, SUBDIR, PREFIX)
#    generatetoc(PODS, GO.options.output_location, GO.options.index_name, SUBDIR, PREFIX, NAME)

#    if GO.options.remove_emails:
#        removemailadresses(MDS)

#    if GO.options.remove_headers:
#        removeheaders(MDS)

#    if GO.options.small_titles:
#        decreasetitlesize(MDS)

#    if GO.options.remove_whitespace:
#        removewhitespace(MDS)

#    if GO.options.codify_paths:
#        codifypaths(MDS)

    logger.info("Done.")
