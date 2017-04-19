#!/usr/bin/env python
import os
import os.path

kver = "4.9.23-21.lts"

def postInstall(fromVersion, fromRelease, toVersion, toRelease):
    try:
        os.system("/usr/bin/linux-driver-management configure gpu")
        os.system("/sbin/depmod %s" % kver)
    except Exception, e:
        print "Post-install error: %s" % e

def postRemove():
    try:
        os.system("/usr/bin/linux-driver-management configure gpu")
        if os.path.exists("/etc/X11/xorg.conf"):
            os.unlink("/etc/X11/xorg.conf")
    except Exception, e:
        print "Post-remove error: %s" % e
