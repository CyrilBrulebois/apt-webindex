#!/usr/bin/python3
# © 2021 Cyril Brulebois <cyril@debamax.com>
"""
Build an index page for a given APT repository, providing an
overview of the available suites, packages, and versions.
"""

import functools
import os
import re
import time

import apt_pkg
import dominate
from dominate.tags import a, attr, br, h1, h4, span, style, table, td, th, tr
from dominate.util import text, raw


TITLE = 'aptly-webindex'

CSS = '''
h1 {
  text-align: center;
  color: #a80030;
  text-decoration: underline;
}
h4 {
  text-align: center;
  font-weight: normal;
}
table {
  width: 100%;
  border: 1px solid #333;
  border-collapse: collapse;
}
th {
  background-color: #a80030;
  color: #FFF;
}
th.distribution {
  background-color: #880020;
}
td {
  vertical-align: top;
  border: 1px solid black;
  padding: 2px 5px;
  white-space: nowrap;
}
td.centered {
  text-align: center;
}
td.versions {
  white-space: normal;
}
.mono {
  font-family: monospace;
}

/* Multi-dist support: try to align columns across tables */
.col1 { width: 15%; }
.col2 { width: 10%; }
.col3 { width:  5%; }
.col4 { width: 70%; }

/* Newness indicators, the higher the hotter */
.hot1 { background-color: #555753; }
.hot2 { background-color: #d3d7cf; }
.hot3 { background-color: #edd400; }
.hot4 { background-color: #f57900; }
.hot5 { background-color: #cc0000; }
'''


def get_time_info(diff):
    """Return a human representation based of the delta against current time"""
    if diff > 60 * 24 * 3600:
        desc = '%d+ months ago' % (diff/(30*24*3600))
        color = 'hot1'
    elif diff > 2 * 24 * 3600:
        desc = '%d+ days ago' % (diff/(1*24*3600))
        color = 'hot2'
    elif diff > 2 * 3600:
        desc = '%d+ hours ago' % (diff/(1*3600))
        color = 'hot3'
    elif diff > 2 * 60:
        desc = '%d+ minutes ago' % (diff/(1*60))
        color = 'hot4'
    else:
        desc = '%d seconds ago' % diff
        color = 'hot5'
    return desc, color


def render_dist_html(dist):
    archs = [re.sub(r'^binary-', '', x)
             for x in os.listdir('dists/%s/main' % dist)
             if x.startswith('binary')]

    # Store [source_arch, package, version, actual_arch, filename]:
    data = []
    for arch in archs:
        with open('dists/%s/main/binary-%s/Packages' % (dist, arch), 'r') as packages_fp:
            tagfile = apt_pkg.TagFile(packages_fp)
            for stanza in tagfile:
                fp = stanza['Package']
                fv = stanza['Version']
                fa = stanza['Architecture']
                ff = stanza['Filename']
                data.append([arch, fp, fv, fa, ff])

    now_ts = time.time()
    packages = sorted(list(set(row[1] for row in data)))
    for package in packages:
        versions = sorted(list(set(row[2] for row in data if row[1] == package)),
                          reverse=True, key=functools.cmp_to_key(apt_pkg.version_compare))

        # Extract version information:
        newest_version = versions[0]
        older_versions = ' | '.join(versions[1:])

        # Filter lines matching newest version:
        newest_items = sorted([row for row in data
                               if row[1] == package and row[2] == newest_version])

        # Extract the dirname of one of the Filename fields:
        pool_dir = re.sub(r'/[^/]+$', '', newest_items[0][4])

        # Prepare links to debs:
        newest_debs = sorted(list(set((row[3], row[4]) for row in newest_items)))

        # XXX: The following could be surprising if one of the builds
        #      is delayed for whatever reason (e.g. missing build-dep
        #      on a CI worker).
        #
        # Get timestamp from the first matching filename:
        file_ts = os.stat(newest_items[0][4]).st_mtime
        diff_desc, time_color = get_time_info(now_ts - file_ts)
        time_desc = time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime(file_ts))
        tooltip = '%s\n%s' % (diff_desc, time_desc)

        with tr():
            td(a(package, href=pool_dir))
            td(newest_version, title=tooltip, _class='centered %s' % time_color)
            with td(_class='centered'):
                # XXX: "manual join"
                for i, row in enumerate(newest_debs):
                    if i != 0:
                        text(' | ')
                    a(row[0], href=row[1])
            td(older_versions, _class='versions')


if __name__ == '__main__':
    # XXX: Better CGI vs. CLI detection?
    if 'REQUEST_METHOD' in os.environ:
        print('Content-Type: text/html; charset=utf-8\n')

    # XXX: Maybe error out if that doesn't return anything, or if
    #      dists/<item>/Release is missing
    dists = sorted(os.listdir('dists'))
    apt_pkg.init_system()

    doc = dominate.document(title=TITLE)

    with doc.head:
        style(CSS)

    with doc.body:
        h1(TITLE)
        with h4():
            text('Available distributions: ')
            # XXX: "manual join"
            for i, dist in enumerate(dists):
                if i != 0:
                    text(' | ')
                a(dist, href='#%s' % dist, _class='mono')

            text(' — ')
            text('direct access: ')
            a('dists', href='dists/', _class='mono')
            text(' | ')
            a('pool', href='pool/', _class='mono')

            text(' — ')
            text('freshness scale: ')
            for i in range(5):
                span('    ', _class='hot%d' % (i+1))

    for dist in dists:
        with doc.add(table()):
            with tr():
                attr(id=dist)
                th('Distribution: %s' % dist, colspan=4, _class='distribution')
            with tr():
                th(raw('Package<br>name'), _class='col1')
                th(raw('Newest<br>versions'), _class='col2')
                th(raw('Newest<br>debs'), _class='col3')
                th(raw('Older<br>versions'), _class='col4')
            render_dist_html(dist)
            br()

    print(doc)
