#!/usr/bin/python
import os.path

NoStrip = ["/"]

from pisi.actionsapi import get, shelltools, pisitools, autotools, kerneltools
import commands

wdir = "NVIDIA-Linux-x86_64-%s" % get.srcVERSION()

# Required... built in tandem with kernel update
kversion = "4.8.2"

def setup():
    shelltools.system("sh NVIDIA-Linux-x86_64-%s.run --extract-only" % get.srcVERSION())
    shelltools.cd(wdir)
    shelltools.system("patch -p0 < ../nv-drm.patch")
    shelltools.system("patch -p1 < ../0001-nv-lock-Port-to-Linux-4.7-API.patch")
    shelltools.system("patch -p1 < ../0002-nv-linux-Explicitly-disable-mtrr-use-deprecated.patch")
    shelltools.cd("kernel")

def build():
    shelltools.cd(wdir + "/kernel")
    autotools.make("\"SYSSRC=/lib64/modules/%s/build\" module" % kversion)

def link_install(lib, libdir='/usr/lib64', abi='1', cdir='.'):
    ''' Install a library with necessary links '''
    pisitools.dolib("%s/%s.so.%s" % (cdir, lib, get.srcVERSION()), libdir)
    pisitools.dosym("%s/%s.so.%s" % (libdir, lib, get.srcVERSION()), "%s/%s.so.%s" % (libdir, os.path.basename(lib), abi))
    pisitools.dosym("%s/%s.so.%s" % (libdir, lib, abi), "%s/%s.so" % (libdir, os.path.basename(lib)))

def install():
    # driver portion
    shelltools.cd(wdir)
    pisitools.dolib("nvidia_drv.so", "/usr/lib64/xorg/modules/drivers")

    kdir = "/lib64/modules/%s/kernel/drivers/video" % kversion

    # libGL replacement - conflicts
    libs = ["libGL", "libglx"]
    for lib in libs:
        abi = '2' if lib == "libGLESv2" else "1"
        link_install(lib, "/usr/lib64/glx-provider/nvidia", abi)
        if lib != "libglx":
            link_install(lib, "/usr/lib32/glx-provider/nvidia", abi, cdir='32')

    # mesa/EGL compat

    compat = dict()
    compat["libEGL"] = "1.0.0"
    compat["libGLESv1_CM"] = "1.1.0"
    compat["libGLESv2"] = "2.0.0"

    for lib in compat:
        version = compat[lib]
        versionMajor = version.split(".")[0]

        for suffix in ["lib64", "lib32"]:
            pisitools.dosym("/usr/%s/glx-provider/default/%s.so.%s" % (suffix, lib, version), "/usr/%s/glx-provider/nvidia/%s.so" % (suffix, lib))
            pisitools.dosym("/usr/%s/glx-provider/default/%s.so.%s" % (suffix, lib, version), "/usr/%s/glx-provider/nvidia/%s.so.%s" % (suffix, lib, versionMajor))
            pisitools.dosym("/usr/%s/glx-provider/default/%s.so.%s" % (suffix, lib, version), "/usr/%s/glx-provider/nvidia/%s.so.%s" % (suffix, lib, version))

    # non-conflict libraries
    libs =  ["libnvidia-glcore", "libnvidia-ml", "libcuda",
             "libnvidia-compiler", "libnvidia-opencl"]

    native_libs = ["libnvidia-cfg", "libnvcuvid"]
    for lib in libs:
        link_install(lib)
        link_install(lib, libdir='/usr/lib32', cdir='32')
    for lib in native_libs:
        link_install(lib)

    # vdpau provider
    link_install("libvdpau_nvidia", "/usr/lib64/vdpau")
    link_install("32/libvdpau_nvidia", "/usr/lib32/vdpau")

    # TLS
    link_install("tls/libnvidia-tls")
    link_install("tls/libnvidia-tls", libdir='/usr/lib32', cdir='32')

    # binaries
    bins = ["nvidia-debugdump", "nvidia-xconfig", "nvidia-settings",
        "nvidia-bug-report.sh", "nvidia-smi"]
    for bin in bins:
        pisitools.dobin(bin)

    # data files
    pisitools.dosed("nvidia-settings.desktop", "__UTILS_PATH__", "/usr/bin")
    pisitools.dosed("nvidia-settings.desktop", "__PIXMAP_PATH__", "/usr/share/pixmaps")
    pisitools.insinto("/usr/share/applications", "nvidia-settings.desktop")
    pisitools.insinto("/usr/share/pixmaps", "nvidia-settings.png")
    pisitools.insinto("/usr/share/OpenCL/vendors", "nvidia.icd")

    # kernel portion, i.e. /lib/modules/3.19.7/kernel/drivers/video/nvidia.ko
    shelltools.cd("kernel")
    pisitools.dolib_a("nvidia.ko", kdir)

    # install modalias
    pisitools.dodir("/usr/share/doflicky/modaliases")
    with open("%s/usr/share/doflicky/modaliases/%s.modaliases" % (get.installDIR(), get.srcNAME()), "w") as outp:
        inp = commands.getoutput("../../nvidia_supported nvidia %s ../README.txt nvidia.ko" % get.srcNAME())
        outp.write(inp)

