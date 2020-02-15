#!/bin/sh -e
# script for building the pyhp debian package
# it is recommended to run this script as root or to set the owner and group of the files to root
# you need to build the pyhp-core wheel first

if [ "$1" = "" ]
then read -p "Version: " version
else version=$1
fi

if [ "$2" = "" ]
then read -p "pyhp-core Wheel: " wheel
else wheel=$2
fi

if [ "$3" = "" ]
then read -p "pip executeable: " pip
else pip=$3
fi

package="pyhp_"$version"_all"

mkdir "$package"

# place config file, cache handlers and "executable"
mkdir -p "$package/lib/pyhp/cache_handlers"
cp ../cache_handlers/* "$package/lib/pyhp/cache_handlers"

mkdir "$package/etc"
cp ../pyhp.conf "$package/etc"

mkdir -p "$package/usr/bin"
cp pyhp "$package/usr/bin"
chmod +x "$package/usr/bin/pyhp"

# place pyhp-core files
mkdir -p "$package/usr/lib/python3/dist-packages"
$pip install --target "$package/usr/lib/python3/dist-packages" --ignore-installed $wheel

# place metadata files
mkdir "$package/DEBIAN"
# calculate installed size
cat control | python3 format.py "$version" $(du -sk --apparent-size --exclude "DEBIAN" "$package" 2>/dev/null | cut -f1) > "$package/DEBIAN/control"
cp conffiles "$package/DEBIAN"

mkdir -p "$package/usr/share/doc/pyhp"
cp copyright "$package/usr/share/doc/pyhp"
cp changelog "$package/usr/share/doc/pyhp/changelog.Debian"
gzip -n --best "$package/usr/share/doc/pyhp/changelog.Debian"

# generate md5sums file
chdir "$package"
md5sum $(find . -type d -name "DEBIAN" -prune -o -type f -print) > DEBIAN/md5sums  # ignore metadata files
sha256sum $(find . -type d -name "DEBIAN" -prune -o -type f -print) > DEBIAN/sha256sums
chdir ../

# if root set file permissions, else warn
if [ $(id -u) = 0 ]
then chown root:root -R "$package"
else echo "not running as root, permissions in package may be wrong"
fi

# build debian package
dpkg-deb --build "$package"

# remove build directory
rm -r "$package"

echo "Done"
