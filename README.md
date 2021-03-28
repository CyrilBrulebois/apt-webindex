# apt-webindex

## Introduction

The purpose of this script is to replace the web server's `autoindex`
function, and provide with a sweet summary of the contents of a given
repository.

It does so by diving into the `dists/` directory, detecting suites and
architectures, and providing per-suite tables with per-package rows
with useful links (to the last version for all architectures), and all
versions.

It might be particularly helpful for repositories published by tools
supporting multiple versions for a package within a single suite,
e.g. holding many snapshots built from a CI pipeline (`aptly` supports
that natively, `reprepro` requires a patch).


## Dependencies

* python3
* python3-apt (for proper version sorting)
* python3-dominate (for HTML generation)


## Development tips

Since the `apt_pkg` module is a C extension module, one might want to
run `pylint` this way:

    pylint --extension-pkg-whitelist=apt_pkg apt-webindex.py


## Disclaimer

This tool was written on the side, to help
[DEBAMAX](https://debamax.com/) customers keep track of their local
repositories. While a number of features are expected to appear
shortly (reading from compressed `Packages` files, detecting whether
the 4th column makes sense, auto-detecting CGI environments,
implementing some caching), the initial intent was not to build a
bullet-proof tool that would work perfectly for all repositories.

Also, it's very likely the code could be improved and be made more
Pythonic, but releasing early made sense, so here we are!
