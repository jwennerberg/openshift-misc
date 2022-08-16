#!/bin/bash

arch="${OCP_ARCH:-x86_64}"
channel="${OCP_CHANNEL:-fast}"
version="${OCP_VERSION:-4.11}"
bin_dest="${HOME}/bin"

baseurl="https://mirror.openshift.com/pub/openshift-v4/${arch}/clients/ocp/${channel}-${version}"
fullversion=$(curl -s ${baseurl}/release.txt | grep ^Name: | awk '{print $2}')
package_client=openshift-client-linux-${fullversion}.tar.gz
package_install=openshift-install-linux-${fullversion}.tar.gz

tmpdir=$(mktemp -d)

download() {
  cd $tmpdir && curl -s -O $1
}

unpack() {
  cd $tmpdir && tar zxf $1
  [ -f ${tmpdir}/openshift-install ] && mv ${tmpdir}/openshift-install ${bin_dest}/openshift-install-${fullversion}
  [ -f ${tmpdir}/oc ] && mv ${tmpdir}/oc ${bin_dest}/oc-${fullversion}
  [ -f ${tmpdir}/kubectl ] && mv ${tmpdir}/kubectl ${bin_dest}/kubectl-${fullversion}
}

cleanup() {
  [ -d $tmpdir ] && rm -f $tmpdir/{README.md,openshift-*.tar.gz} && rm -df $tmpdir
}

log() (
  echo "[] $1"
)

debug() (
  [ -n "$DEBUG" ] && echo DEBUG: $1
)

trap cleanup EXIT

debug ${baseurl}/openshift-install-linux-${fullversion}.tar.gz
debug ${baseurl}/openshift-client-linux-${fullversion}.tar.gz

if [ -f "${bin_dest}/openshift-install-${fullversion}" ]; then
  log "${bin_dest}/openshift-install-${fullversion} already exists"
else
  log "Downloading ${package_install}"
  download ${baseurl}/${package_install}
  log "Unpacking openshift-install"
  unpack $package_install
fi

if [ -f "${bin_dest}/oc-${fullversion}" -a -f "${bin_dest}/kubectl-${fullversion}" ]; then
  log "${bin_dest}/oc-${fullversion} already exists"
else
  log "Downloading ${package_client}"
  download ${baseurl}/${package_client}
  log "Unpacking openshift-client"
  unpack $package_client
fi

ls -1 ${bin_dest}/*-${fullversion}
