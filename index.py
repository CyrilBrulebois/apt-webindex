#!/usr/bin/python3
# © 2021 Cyril Brulebois <cyril@debamax.com>

import functools
import re

import apt_pkg
import dominate
from dominate.tags import *
from dominate.util import text, raw


TITLE = 'aptly-webindex'

ARCHES = ['amd64', 'arm64']
DIST = 'buster'

apt_pkg.init_system()

CSS = '''
h1 {
  text-align: center;
  color: #a80030;
  text-decoration: underline;
}
h4 {
  text-align: center;
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
'''

# Store [source_arch, package, version, actual_arch, filename]:
data = []
for arch in ARCHES:
    with open('dists/%s/main/binary-%s/Packages' % (DIST, arch), 'r') as packages_fp:
        tagfile = apt_pkg.TagFile(packages_fp)
        for stanza in tagfile:
            fp = stanza['Package']
            fv = stanza['Version']
            fa = stanza['Architecture']
            ff = stanza['Filename']
            data.append([arch, fp, fv, fa, ff])

doc = dominate.document(title=TITLE)

with doc.head:
    style(CSS)

with doc.body:
    h1(TITLE)
    with h4():
        text('Available distributions: ')
        a('buster', href='#buster', _class='mono')
        text(' — ')
        text('direct access: ')
        a('dists', href='dists/', _class='mono')
        text(' | ')
        a('pool', href='pool/', _class='mono')

with doc.add(table()):
    with tr():
        attr(id=DIST)
        th('Distribution: %s' % DIST, colspan=4, _class='distribution')
    with tr():
        th(raw('Package<br>name'))
        th(raw('Newest<br>versions'))
        th(raw('Newest<br>debs'))
        th(raw('Older<br>versions'))

    packages = sorted(list(set([row[1] for row in data])))
    for package in packages:
        versions = sorted(list(set([row[2] for row in data if row[1] == package])),
                          reverse=True, key=functools.cmp_to_key(apt_pkg.version_compare))

        # Extract version information:
        newest_version = versions[0]
        older_versions = ' | '.join(versions[1:])

        # Filter lines matching newest version:
        newest_items = sorted([row for row in data if row[1] == package and row[2] == newest_version])

        # Extract the dirname of one of the Filename fields:
        pool_dir = re.sub(r'/[^/]+$', '', newest_items[0][4])

        # Prepare links to debs:
        newest_debs = sorted(list(set([(row[3], row[4]) for row in newest_items])))

        with tr():
            td(a(package, href=pool_dir))
            td(newest_version, _class='centered')
            with td(_class='centered'):
                for row in newest_debs:
                    a(row[0], href=row[1])
            td(older_versions, _class='versions')

print(doc)
