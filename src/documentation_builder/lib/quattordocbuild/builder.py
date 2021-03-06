"""Build documentation from quattor sources."""

import os
import sys
import re
import codecs
from sourcehandler import get_source_files
from rsthandler import generate_rst, cleanup_content
from config import build_repository_map
from vsc.utils import fancylogger
from multiprocessing import Pool

logger = fancylogger.getLogger()
RESULTS = {}

def build_documentation(repository_location, cleanup_options, compile, output_location, singlet=False):
    """Build the whole documentation from quattor repositories."""
    if not check_input(repository_location, output_location):
        sys.exit(1)
    if not check_commands(compile):
        sys.exit(1)
    repository_map = build_repository_map(repository_location)
    if not repository_map:
        sys.exit(1)

    rstlist = {}

    if singlet:
        for repository in repository_map.keys():
            repository, result = build_docs(repository, repository_location, repository_map, cleanup_options)
            RESULTS[repository] = result
    else:
        pool = Pool()
        for repository in repository_map.keys():
            pool.apply_async(build_docs, args=(repository, repository_location, repository_map, cleanup_options), callback = log_result)
        pool.close()
        pool.join()

    site_pages = build_site_structure(RESULTS, repository_map)
    # site_pages = make_interlinks(site_pages) # disabled for now
    write_site(site_pages, output_location, "docs")
    return True

def log_result(result):
    repository = result[0]
    result = result[1]
    RESULTS[repository] = result

def build_docs(repository, repository_location, repository_map, cleanup_options):
    logger.info("Building documentation for %s." % repository)
    fullpath = os.path.join(repository_location, repository)
    if repository_map[repository]["subdir"]:
        fullpath = os.path.join(fullpath, repository_map[repository]["subdir"])
    logger.info("Path: %s." % fullpath)
    sources = get_source_files(fullpath, compile)
    logger.debug("Sources: %s" % sources)
    sources = make_titles(sources, repository_map[repository]['targets'])
    rst = generate_rst(sources)
    cleanup_content(rst, cleanup_options)
    return repository, rst

def which(command):
    """Check if given command is available for the current user on this system."""
    found = False
    for direct in os.getenv("PATH").split(':'):
        if os.path.exists(os.path.join(direct, command)):
            found = True

    return found


def check_input(sourceloc, outputloc):
    """Check input and locations."""
    logger.info("Checking if the given paths exist.")
    if not sourceloc:
        logger.error("Repo location not specified.")
        return False
    if not outputloc:
        logger.error("output location not specified")
        return False
    if not os.path.exists(sourceloc):
        logger.error("Repo location %s does not exist" % sourceloc)
        return False
    if not os.path.exists(outputloc):
        logger.error("Output location %s does not exist" % outputloc)
        return False
    if not os.listdir(outputloc) == []:
        logger.error("Output location %s is not empty." % outputloc)
        return False
    return True


def check_commands(runmaven):
    """Check required binaries."""
    if runmaven:
        if not which("mvn"):
            logger.error("The command mvn is not available on this system, please install maven.")
            return False
    if not which("pod2rst"):
        logger.error("The command pod2rst is not available on this system, please install pod2rst.")
        return False
    return True


def make_titles(sources, targets):
    """Add titles to sources."""
    new_sources = {}
    for source in sources:
        title = make_title_from_source_path(source, targets)
        new_sources[title] = source

    return new_sources


def rreplace(s, old, new):
    """Replace right most occurence of a substring."""
    li = s.rsplit(old, 1) #Split only once
    return new.join(li)

def make_title_from_source_path(source, targets):
    """Make a title from source path."""
    found = False
    for target in targets:
        logger.debug("target: %s" % target)
        if target in source and not found:
            title = source.split(target)[-1]
            if title.replace('.pod', '') == '':
                title = target
                return title
            title = os.path.splitext(title)[0].replace("/", "\::")
            title = "%s%s" % (target.lstrip('/').replace("/", "\::"), title)

            if title.startswith('components\::'):
                title = title.replace('components', 'NCM\::Component')
                title = rreplace(title, '\::', ' - ')

            if title.startswith('pan\::quattor'):
                title = title.replace('pan\::quattor', 'NCM\::Component')
                title = rreplace(title, '\::', ' - ')

            logger.debug("title: %s" % title)
            return title
    if not found:
        logger.error("No suitable target found for %s in %s." % (source, targets))

    return False


def build_site_structure(rstlist, repository_map):
    """Make a mapping of files with their new names for the website."""
    sitepages = {}
    for repo, rsts in rstlist.iteritems():
        sitesection = repository_map[repo]['sitesection']

        sitepages[sitesection] = {}

        targets = repository_map[repo]['targets']
        for source, rst in rsts.iteritems():
            found = False
            for target in targets:
                if target in source and not found:
                    newname = source.split(target)[-1]
                    if newname.replace('.pod', '') == '':
                        newname = target
                    newname = os.path.splitext(newname)[0].replace("/", "_") + ".rst"
                    sitepages[sitesection][newname] = rst
                    found = True
            if not found:
                logger.error("No suitable target found for %s in %s." % (source, targets))

    logger.debug("sitepages: %s" % sitepages)
    return sitepages


def make_interlinks(pages):
    """Make links in the content based on pagenames."""
    logger.info("Creating interlinks.")
    newpages = pages
    for subdir in pages:
        for page in pages[subdir]:
            basename = os.path.splitext(page)[0]
            link = '../%s/%s' % (subdir, page)
            regxs = []
            regxs.append("`%s`" % basename)
            regxs.append("`%s::%s`" % (subdir, basename))

            cpans = "https://metacpan.org/pod/"

            if subdir == 'CCM':
                regxs.append("\[{2}::{0}\]\({1}{2}::{0}\)".format(basename, cpans, "EDG::WP4::CCM"))
            if subdir == 'Unittest':
                regxs.append("\[{2}::{0}\]\({1}{2}::{0}\)".format(basename, cpans, "Test"))
            if subdir in ['components', 'components-grid']:
                regxs.append("\[{2}::{0}\]\({1}{2}::{0}\)".format(basename, cpans, "NCM::Component"))
                regxs.append("`ncm-%s`" % basename)
                regxs.append("ncm-%s" % basename)

            for regex in regxs:
                newpages = replace_regex_link(newpages, regex, basename, link)

    return newpages


def replace_regex_link(pages, regex, basename, link):
    """Replace links in a bunch of pages based on a regex."""
    regex = r'( |^|\n)%s([,. $])' % regex
    for subdir in pages:
        for page in pages[subdir]:
            content = pages[subdir][page]
            if (basename not in page or basename == "Quattor") and basename in content:
                content = re.sub(regex, "\g<1>[%s](%s)\g<2>" % (basename, link), content)
                pages[subdir][page] = content
    return pages


def write_site(sitepages, location, docsdir):
    """Write the pages for the website to disk."""
    for subdir, pages in sitepages.iteritems():
        fullsubdir = os.path.join(location, docsdir, subdir)
        if not os.path.exists(fullsubdir):
            os.makedirs(fullsubdir)
        for pagename, content in pages.iteritems():
            with codecs.open(os.path.join(fullsubdir, pagename), 'w', encoding='utf-8') as fih:
                fih.write(content)
