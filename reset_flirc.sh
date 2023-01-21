#!/usr/local/bin/bash

flirc=`usbconfig|awk -F :  '/flirc/ {print $1}'`
chown admin:polyglot /dev/$flirc
chmod go+rw /dev/$flirc

usbconfig -d $flirc detach_kernel_driver
usbconfig -d $flirc -i 1 detach_kernel_driver
usbconfig -d $flirc -i 2 detach_kernel_driver