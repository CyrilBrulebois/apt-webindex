#!/usr/bin/python3
# © 2021 Cyril Brulebois <cyril@debamax.com>
"""
Build an index page for a given APT repository, providing an
overview of the available suites, packages, and versions.
"""
# pylint: disable-msg=C0103

import functools
import os
import re
import time

import apt_pkg
import dominate
from dominate.tags import a, attr, br, h1, h4, span, style, table, td, th, tr, div
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

.hot1-delayed { background: linear-gradient(to right, #555753, white); }
.hot2-delayed { background: linear-gradient(to right, #d3d7cf, white); }
.hot3-delayed { background: linear-gradient(to right, #edd400, white); }
.hot4-delayed { background: linear-gradient(to right, #f57900, white); }
.hot5-delayed { background: linear-gradient(to right, #cc0000, white); }
}
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
    """Render the HTML table for the specified distribution"""
    archs = [re.sub(r'^binary-', '', x)
             for x in os.listdir('dists/%s/main' % dist)
             if x.startswith('binary')]

    # Store [source_arch, package, version, actual_arch, filename]:
    data = []
    for arch in archs:
        with open('dists/%s/main/binary-%s/Packages' % (dist, arch), 'r') as packages_fp:
            tagfile = apt_pkg.TagFile(packages_fp)
            for stanza in tagfile:
                # pylint: disable=invalid-name
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

        # With amd64 builds being usually much quicker, announce a delayed build
        # if there's no matching arm64 package. We could also work by excluding
        # Architecture: all packages but we already have a number of packages
        # that only make sense on arm64, so that would give false positives:
        if len(newest_debs) == 1 and newest_debs[0][0] == 'amd64':
            delayed_build = "%s %s-delayed" % (time_color, time_color)
        else:
            delayed_build = ""

        with tr():
            td(a(package, href=pool_dir))
            td(newest_version, title=tooltip, _class='centered %s' % time_color)
            with td(_class='centered %s' % delayed_build):
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
        # XXX: Maybe call cgitb.enable()

    # XXX: Maybe error out if that doesn't return anything, or if
    #      dists/<item>/Release is missing
    dists = sorted(os.listdir('dists'))
    apt_pkg.init_system()

    doc = dominate.document(title=TITLE)

    with doc.head:
        style(CSS)

    with doc.body:
        div(raw('<svg height="48" version="1.1" viewBox="0 0 2048 256" xmlns="http://www.w3.org/2000/svg"><title>APT-Webindex</title><g transform="translate(228)" fill="none" stroke-width="8.0213"><path d="m182.81 125.89a32.085 32.085 0 0 1-16.043 27.787 32.085 32.085 0 0 1-32.085 0 32.085 32.085 0 0 1-16.043-27.787" stroke="#000"/><path d="m182.48 94.125a44.919 44.919 0 0 1 11.626 43.389 44.919 44.919 0 0 1-31.763 31.763 44.919 44.919 0 0 1-43.389-11.626" stroke="#1e010b"/><path d="m150.72 68.134a57.753 57.753 0 0 1 57.753 57.753 57.753 57.753 0 0 1-57.753 57.753" stroke="#3d0217"/><path d="m100.81 75.974a70.587 70.587 0 0 1 68.182-18.269 70.587 70.587 0 0 1 49.913 49.913 70.587 70.587 0 0 1-18.269 68.182" stroke="#5c0423"/><path d="m67.3 256v-130.11a83.421 83.421 0 0 1 83.421-83.421 83.421 83.421 0 0 1 83.421 83.421" stroke="#7a052f"/><path d="m54.466 256v-129.92a96.255 96.255 0 0 1 59.332-89.083 96.255 96.255 0 0 1 104.99 20.829" stroke="#99073b"/><path d="m41.632 256v-130.07a109.09 109.09 0 0 1 31.937-77.165 109.09 109.09 0 0 1 77.153-31.966" stroke="#b80847"/><path d="m28.799 256v-130.57a121.92 121.92 0 0 1 35.71-85.751" stroke="#d70a53"/></g><path d="M74.992 228.88h24.48l20.128-51.408h82.96l20.128 51.408h25.296l-72.352-190.4h-28.016zm51.68-72.896 34.272-91.664 34.544 91.664zM471.33 38.481v21.76h61.744v168.64h23.664v-168.64h61.744v-21.76z" fill="#7a052f"/><path d="M750.3 38.481 l55.488 190.4h28.288l43.248-150.96 43.52 150.96h28.288l55.76-190.4h-24.48l-44.88 159.94-45.152-159.94h-23.936l-46.784 159.94-44.608-159.94zM1018.8 122.26c-5.44 10.88-8.16 23.12-8.16 37.264s2.72 26.384 8.432 37.264 13.872 19.04 24.208 25.024c10.336 5.984 22.304 8.704 36.176 8.704 15.776 0 29.104-4.352 39.984-13.328s17.68-20.672 20.4-34.816h-22.576c-2.448 8.976-7.072 16.048-14.144 20.944s-15.504 7.344-25.296 7.344c-13.056 0-23.392-4.08-31.28-12.24-8.16-8.16-12.24-19.04-12.512-32.64v-1.904h107.71c0.272-4.352 0.544-7.344 0.544-9.52-0.544-13.328-3.536-25.024-8.976-35.088-5.712-9.792-13.328-17.408-23.12-22.848-9.792-5.168-21.216-7.888-33.728-7.888-13.056 0-24.48 2.992-34.272 8.976-10.064 5.984-17.952 14.144-23.392 24.752zm100.37 23.12h-83.776c1.088-10.88 5.44-19.856 13.6-26.928 7.888-6.8 17.136-10.336 27.744-10.336 11.696 0 21.488 3.264 29.104 9.792s12.24 15.776 13.328 27.472zM1272.2 96.961c-10.064-5.44-21.488-8.432-34.272-8.432-20.128 0-36.176 8.16-47.6 23.936v-73.984h-22.304v190.4h19.312l2.992-21.216c4.352 7.072 10.608 12.784 18.768 16.864 7.888 4.08 17.408 5.984 28.832 5.984 12.512 0 23.936-2.992 34.272-8.976 10.064-5.984 17.952-14.144 23.664-25.024 5.712-10.608 8.704-22.848 8.704-36.992 0-14.688-2.992-27.2-8.704-38.08-5.712-10.608-13.6-18.768-23.664-24.48zm-3.264 99.552c-8.432 9.52-19.584 14.144-33.184 14.144-8.976 0-16.864-2.176-23.936-6.528s-12.24-10.336-16.048-18.224-5.712-16.864-5.712-26.928c0-9.792 1.904-18.496 5.712-26.112s8.976-13.6 16.048-17.952 14.96-6.528 23.936-6.528c13.6 0 24.752 4.896 33.184 14.416s12.784 21.76 12.784 36.72c0 15.232-4.352 27.472-12.784 36.992zM1351.6 40.657c-2.72-2.72-6.256-4.08-10.336-4.08-4.352 0-7.616 1.36-10.336 4.08s-4.08 6.256-4.08 10.336c0 4.352 1.36 7.616 4.08 10.336s5.984 4.08 10.336 4.08c4.08 0 7.616-1.36 10.336-4.08s4.08-5.984 4.08-10.336c0-4.08-1.36-7.616-4.08-10.336zm-21.488 49.504v138.72h22.304v-138.72zM1491.2 103.76c-10.336-10.064-23.664-15.232-40.528-15.232-20.128 0-35.36 6.8-45.696 20.4l-2.992-18.768h-19.312v138.72h22.304v-69.36c0-15.504 3.536-27.744 11.152-36.992 7.344-8.976 17.68-13.6 30.736-13.6 11.968 0 21.216 3.808 27.744 11.424s9.792 18.496 9.792 32.64v75.888h22.304v-77.248c0-21.76-5.168-37.536-15.504-47.872zM1666.8 38.481h-22.304v72.896c-4.624-7.072-10.88-12.512-18.768-16.592-8.16-4.08-17.68-6.256-28.832-6.256-12.784 0-24.208 2.992-34.272 8.976-10.336 5.984-18.224 14.416-23.936 25.024-5.712 10.88-8.432 23.12-8.432 36.992 0 14.688 2.72 27.472 8.432 38.08 5.712 10.88 13.6 19.04 23.664 24.48 10.064 5.712 21.488 8.432 34.544 8.432 20.128 0 35.904-7.888 47.6-23.936l2.992 22.304h19.312zm-44.064 165.92c-7.072 4.352-14.96 6.256-23.664 6.256-13.872 0-25.024-4.624-33.456-14.144-8.4321-9.52-12.512-21.76-12.512-36.992 0-14.96 4.0799-27.2 12.512-36.72 8.432-9.52 19.584-14.416 33.456-14.416 8.704 0 16.592 2.176 23.664 6.528s12.512 10.608 16.32 18.496 5.712 16.864 5.712 26.656-1.904 18.768-5.712 26.384-9.248 13.6-16.32 17.952zM1700.4 122.26c-5.44 10.88-8.16 23.12-8.16 37.264s2.72 26.384 8.432 37.264 13.872 19.04 24.208 25.024 22.304 8.704 36.176 8.704c15.776 0 29.104-4.352 39.984-13.328s17.68-20.672 20.4-34.816h-22.576c-2.448 8.976-7.072 16.048-14.144 20.944s-15.504 7.344-25.296 7.344c-13.056 0-23.392-4.08-31.28-12.24-8.16-8.16-12.24-19.04-12.512-32.64v-1.904h107.71c0.272-4.352 0.544-7.344 0.544-9.52-0.544-13.328-3.536-25.024-8.976-35.088-5.712-9.792-13.328-17.408-23.12-22.848-9.792-5.168-21.216-7.888-33.728-7.888-13.056 0-24.48 2.992-34.272 8.976-10.064 5.984-17.952 14.144-23.392 24.752zm100.37 23.12h-83.776c1.088-10.88 5.44-19.856 13.6-26.928 7.888-6.8 17.136-10.336 27.744-10.336 11.696 0 21.488 3.264 29.104 9.792s12.24 15.776 13.328 27.472zM1884 157.62l-52.768 71.264h24.752l40.8-55.76 40.8 55.76h26.656l-53.04-71.264 49.504-67.456h-24.752l-37.536 51.408-36.992-51.408h-26.656z" fill="#333"/></svg>'), style='cursor: pointer;', onclick='location.href=\'https://github.com/CyrilBrulebois/apt-webindex\'')
        #h1(TITLE)
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
