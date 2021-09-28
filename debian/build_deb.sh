#!/bin/sh -e
# script for building the pyhp debian package
# it is recommended to run this script as root or to set the owner and group of the files to root

version=$(python3 setup.py --version)
maintainer=$(python3 setup.py --maintainer)
email=$(python3 setup.py --maintainer-email)
homepage=$(python3 setup.py --url)
description=$(python3 setup.py --description)
licence=$(python3 setup.py --licence)

package="python3-pyhp-core_${version}-1_all"
mkdir "$package"

# place pyhp-core files
python3 setup.py install --install-layout=deb --no-compile --single-version-externally-managed --root="$package"

# strip python version from .egg-info directory
mv $package/usr/lib/python3/dist-packages/pyhp_core-${version}-*.egg-info "$package/usr/lib/python3/dist-packages/pyhp_core-${version}.egg-info"

# place config file
mkdir "${package}/etc"
cp pyhp.toml "${package}/etc"

# place metadata files
mkdir "$package/DEBIAN"

# place control
cat debian/control | python3 debian/format.py \
	"$version" \
	"$maintainer" "$email" \
	$(du -sk --apparent-size --exclude "DEBIAN" "${package}" 2>/dev/null | cut -f1) \
	"$homepage" \
	"$description" \
	> "${package}/DEBIAN/control"

# place conffiles
cp debian/conffiles "$package/DEBIAN"

# place postinst
cp debian/postinst "$package/DEBIAN"
chmod 755 "$package/DEBIAN/postinst"

# place prerm
cp debian/prerm "$package/DEBIAN"
chmod 755 "$package/DEBIAN/prerm"

# place copyright and changelog
mkdir -p "${package}/usr/share/doc/python3-pyhp-core"
cat debian/copyright | python3 debian/format.py \
	"$maintainer" "$email" \
	"$homepage" \
	"$licence" \
	> "${package}/usr/share/doc/python3-pyhp-core/copyright"
cp debian/changelog "${package}/usr/share/doc/python3-pyhp-core/changelog.Debian"
gzip -n --best "${package}/usr/share/doc/python3-pyhp-core/changelog.Debian"

# generate md5sums and sha256sums file
cd "$package"
md5sum $(find . -type d -name "DEBIAN" -prune -o -type f -print) > "DEBIAN/md5sums"  # ignore metadata files
sha256sum $(find . -type d -name "DEBIAN" -prune -o -type f -print) > "DEBIAN/sha256sums"
cd ..

# if root set file permissions, else warn
if [ $(id -u) = 0 ]
then chown root:root -R "$package"
else echo "Warning: not running as root, permissions in package may be wrong"
fi

# build debian package
dpkg-deb --build "$package"

# remove build directory
rm -r "$package"

echo "Done"

exit 0
