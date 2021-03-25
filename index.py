#!/usr/bin/python3
# © 2021 Cyril Brulebois <cyril@debamax.com>

import functools
import re

import apt_pkg

ARCHES = ['amd64', 'arm64']
DIST = 'buster'

apt_pkg.init_system()

CSS = '''
table {
  width: 100%;
  border: 1px solid #333;
  border-collapse: collapse;
}
th {
  background-color: #a80030;
  color: #FFF;
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

html = '<html><head>\n'
html += '<title>aptly-webindex</title>\n'
html += '<style>%s</style>\n' % CSS
packages = sorted(list(set([row[1] for row in data])))

html += '<table>\n'
html += '<tr><th>Package<br>name</th><th>Newest<br>version</th><th>Newest<br>debs</th><th>Older<br>versions</th></tr>\n'
for package in packages:
    versions = sorted(list(set([row[2] for row in data if row[1] == package])),
                      reverse=True, key=functools.cmp_to_key(apt_pkg.version_compare))

    # Extract version information:
    newest_version = versions[0]
    older_versions = ' | '.join(versions[1:])

    # Filter lines matching newest version:
    newest_items = sorted([row for row in data if row[1] == package and row[2] == newest_version])

    # Build link to pool directory, extracting the dirname of one of the Filename fields:
    pool_dir = re.sub(r'/[^/]+$', '', newest_items[0][4])
    package_info = '<a href="%s">%s</a>' % (pool_dir, package)

    # Build links to debs:
    newest_debs = ' | '.join(sorted(list(set(['<a href="%s">%s</a>' % (row[4], row[3]) for row in newest_items]))))

    html += '<tr><td>%s</td><td class="centered">%s</td><td class="centered">%s</td><td class="versions">%s</td></tr>\n' % (package_info, newest_version, newest_debs, older_versions)

html += '</table>\n'
html += '</body>\n'
html += '</html>\n'
print(html)
