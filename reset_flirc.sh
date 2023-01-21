#!/usr/local/bin/bash

flirc=`usbconfig|awk -F :  '/flirc/ {print $1}'`
chown admin:polyglot /dev/$flirc
chmod go+rw /dev/$flirc

usbconfig -d $flirc detach_kernel_driver
