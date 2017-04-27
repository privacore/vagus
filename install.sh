#!/bin/bash

source_dir=`dirname $0`

bin_directory=/usr/local/vagus
conf_directory=/usr/local/vagus
log_directory=/usr/local/vagus


function die() {
	echo "$*" >&2
	exit 99
}


if egrep -q '^vagus:' /etc/passwd; then
	echo "User 'vagus' already exist. Fine"
else
	useradd -c "Vagus service" vagus || die
fi


echo "Creating installation directories"
mkdir -p $bin_directory $conf_directory $log_directory || die

echo "Fixing directory and file ownership"
chown vagus:users $bin_directory $conf_directory $log_directory || die


echo "Copying binaries to $bin_directory"
for f in $source_dir/*.py; do
	b=`basename $f`
	cp -a $f $bin_directory/$b || die
	chown vagus:users $bin_directory/$b || die
done
#*.sh are templates
for f in $source_dir/*.sh; do
	b=`basename $f`
	cat $f | sed -e "s@__BIN_DIRECTORY__@$bin_directory@g" -e "s@__CONF_DIRECTORY__@$conf_directory@g" -e "s@__LOG_DIRECTORY__@$log_directory@g" >$bin_directory/$b || die
	chmod +x $bin_directory/$b || die
	chown vagus:users $bin_directory/$b || die
done


echo "Copying configuration files to $conf_directory"
for f in $source_dir/*.ini $source_dir/*.conf; do
	[ ! -e $f ] && continue
	b=`basename $f`
	cp -a $f $conf_directory/$b || die
	chown vagus:users $conf_directory/$b || die
done

echo "Generating unit files"
cat $source_dir/vagus.service           | sed -e "s@__BIN_DIRECTORY__@$bin_directory@g" -e "s@__CONF_DIRECTORY__@$conf_directory@g" -e "s@__LOG_DIRECTORY__@$log_directory@g" >/etc/systemd/system/vagus.service || die
cat $source_dir/vagus_webserver.service | sed -e "s@__BIN_DIRECTORY__@$bin_directory@g" -e "s@__CONF_DIRECTORY__@$conf_directory@g" -e "s@__LOG_DIRECTORY__@$log_directory@g" >/etc/systemd/system/vagus_webserver.service || die

echo "Reloading systemd unit configuration"
systemctl daemon-reload

systemctl enable vagus.service
systemctl enable vagus_webserver.service
systemctl restart vagus.service
systemctl restart vagus_webserver.service
