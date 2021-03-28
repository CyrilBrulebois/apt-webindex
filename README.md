# apt-webindex

The purpose of this script is to replace the web server's `autoindex`
function, and provide with a sweet summary of the contents of a given
repository.

It does so by detecting suites and architectures, and providing
per-suite tables with per-package rows with useful links (to the last
version for all architectures), and all versions.
