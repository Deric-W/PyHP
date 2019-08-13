echo "Name of package?"
read package
mkdir $package

mkdir $package/etc
wget -nv -O $package/etc/pyhp.conf --tries=3 https://raw.githubusercontent.com/Deric-W/PyHP-Interpreter/master/pyhp.conf
chown root $package/etc/pyhp.conf
chgrp root $package/etc/pyhp.conf

mkdir $package/lib
mkdir $package/lib/pyhp
mkdir $package/lib/pyhp/cache_handlers
wget -nv -O $package/lib/pyhp/cache_handlers/files_mtime.py --tries=3 https://raw.githubusercontent.com/Deric-W/PyHP-Interpreter/master/cache_handlers/files_mtime.py
chown root $package/lib/pyhp/cache_handlers/files_mtime.py
chgrp root $package/lib/pyhp/cache_handlers/files_mtime.py

mkdir $package/usr
mkdir $package/usr/bin
wget -nv -O $package/usr/bin/pyhp --tries=3 https://raw.githubusercontent.com/Deric-W/PyHP-Interpreter/master/pyhp.py
chown root $package/usr/bin/pyhp
chgrp root $package/usr/bin/pyhp
chmod +x $package/usr/bin/pyhp

mkdir $package/DEBIAN
wget -nv -O $package/DEBIAN/control --tries=3 https://raw.githubusercontent.com/Deric-W/PyHP-Interpreter/master/debian/control
chown root $package/DEBIAN/control
chgrp root $package/DEBIAN/control

wget -nv -O $package/DEBIAN/conffiles --tries=3 https://raw.githubusercontent.com/Deric-W/PyHP-Interpreter/master/debian/conffiles
chown root $package/DEBIAN/conffiles
chgrp root $package/DEBIAN/conffiles

mkdir $package/usr/share
mkdir $package/usr/share/doc
mkdir $package/usr/share/doc/pyhp
wget -nv -O $package/usr/share/doc/pyhp/copyright --tries=3 https://raw.githubusercontent.com/Deric-W/PyHP-Interpreter/master/debian/copyright
chown root $package/usr/share/doc/pyhp/copyright
chgrp root $package/usr/share/doc/pyhp/copyright

wget -nv -O $package/usr/share/doc/pyhp/changelog.Debian --tries=3 https://raw.githubusercontent.com/Deric-W/PyHP-Interpreter/master/debian/changelog
gzip -n --best $package/usr/share/doc/pyhp/changelog.Debian
chown root $package/usr/share/doc/pyhp/changelog.Debian.gz
chgrp root $package/usr/share/doc/pyhp/changelog.Debian.gz

chdir $package
md5sum etc/pyhp.conf >> DEBIAN/md5sums
md5sum lib/pyhp/cache_handlers/files_mtime.py >> DEBIAN/md5sums
md5sum usr/bin/pyhp >> DEBIAN/md5sums
md5sum usr/share/doc/pyhp/copyright >> DEBIAN/md5sums
md5sum usr/share/doc/pyhp/changelog.Debian.gz >> DEBIAN/md5sums
chdir ../

dpkg-deb --build $package

rm -rf $package
