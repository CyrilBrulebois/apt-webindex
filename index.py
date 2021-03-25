#!/usr/bin/python3
# © 2021 Cyril Brulebois <cyril@debamax.com>

import functools
import re

import apt_pkg

ARCHES = ['amd64', 'arm64']
DIST = 'buster'

apt_pkg.init_system()

# Store [source_arch, package, version, actual_arch, filename]:
data = []
for arch in ARCHES:
    with open('dists/%s/main/binary-%s/Packages' % (DIST, arch), 'r') as packages_fp:
        tagfile = apt_pkg.TagFile(packages_fp)
        for stanza in tagfile:
            p = stanza['Package']
            v = stanza['Version']
            a = stanza['Architecture']
            f = stanza['Filename']
            data.append([arch, p, v, a, f])

html = ''
packages = sorted(list(set([row[1] for row in data])))

html += '<table border=1 style="border-collapse: collapse">\n'
html += '<tr><th>Package<br>name</th><th>Newest<br>version</th><th>Newest<br>debs</th><th>Older<br>versions</th></tr>\n'
for package in packages:
    versions = sorted(list(set([row[2] for row in data if row[1] == package])),
                      reverse=True, key=functools.cmp_to_key(apt_pkg.version_compare))
    # Basic info:
    newest = versions[0]
    older = ' | '.join(versions[1:])

    newest_items = sorted([row for row in data if row[1] == package and row[2] == newest])
    newest_info = newest + '</td><td style="text-align: center">' + ' | '.join(sorted(list(set(['<a href="%s">%s</a>' % (row[4], row[3]) for row in newest_items]))))

    pool_dir = re.sub(r'/[^/]+$', '', newest_items[0][4])
    package_info = '<a href="%s">%s</a>' % (pool_dir, package)

    older_info = older

    html += '<tr><td>%s</td><td style="text-align: center">%s</td><td>%s</td></tr>\n' % (package_info, newest_info, older_info)
html += '</table>\n'
print(html)
