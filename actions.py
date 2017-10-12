#!/usr/bin/python
import os.path

NoStrip = ["/"]

from pisi.actionsapi import get, shelltools, pisitools, autotools, kerneltools
import commands

# Required... built in tandem with kernel update
kernel_trees = {
    "linux-lts": "4.9.56-52.lts",
    "linux-current": "4.13.6-25.current"
}

def patch_dir(kernel):
    """ Handle patching for each kernel type """
    olddir = os.getcwd()
    shelltools.cd(kernel)

    # See: https://github.com/Hoshpak/void-packages/tree/master/srcpkgs/nvidia304/files
    if kernel == "linux-lts":
        shelltools.system("patch -p0 < ../nv-drm.patch")
    shelltools.cd(olddir)

def setup():
    """ Extract the NVIDIA binary for each kernel tree and rename it each time
        to match the desired tree, to ensure we don't have them conflicting. """
    blob = "NVIDIA-Linux-x86_64-%s" % get.srcVERSION()
    for kernel in kernel_trees:
        shelltools.system("sh %s.run --extract-only" % blob)
        shelltools.move(blob, kernel)
        patch_dir(kernel)

def build():
    for kernel in kernel_trees:
        build_kernel(kernel)

def build_kernel(typename):
    version = kernel_trees[typename]
    olddir = os.getcwd()
    shelltools.cd(typename + "/kernel")
    autotools.make("\"SYSSRC=/lib64/modules/%s/build\" module" % version)
    shelltools.cd(olddir)

def install_kernel(typename):
    olddir = os.getcwd()
    version = kernel_trees[typename]

    kdir = "/lib64/modules/%s/kernel/drivers/video" % version
    # kernel portion, i.e. /lib/modules/3.19.7/kernel/drivers/video/nvidia.ko
    shelltools.cd(typename + "/kernel")
    pisitools.dolib_a("nvidia.ko", kdir)
    shelltools.cd(olddir)

def install_modalias(typename):
    """ install_modalias will generate modaliases for the given tree, which will
        only be linux-lts for now
    """
    olddir = os.getcwd()
    shelltools.cd(typename + "/kernel")

    # install modalias
    pisitools.dodir("/usr/share/doflicky/modaliases")
    modfile = "%s/usr/share/doflicky/modaliases/%s.modaliases" % (get.installDIR(), get.srcNAME())
    shelltools.system("sh -e ../../nvidia_supported nvidia %s ../README.txt nvidia.ko > %s" %
                     (get.srcNAME(), modfile))

    shelltools.cd(olddir)


def link_install(lib, libdir='/usr/lib64', abi='1', cdir='.'):
    ''' Install a library with necessary links '''
    pisitools.dolib("%s/%s.so.%s" % (cdir, lib, get.srcVERSION()), libdir)
    pisitools.dosym("%s/%s.so.%s" % (libdir, lib, get.srcVERSION()), "%s/%s.so.%s" % (libdir, os.path.basename(lib), abi))
    pisitools.dosym("%s/%s.so.%s" % (libdir, lib, abi), "%s/%s.so" % (libdir, os.path.basename(lib)))

def install():
    for kernel in kernel_trees:
        install_kernel(kernel)
    install_modalias("linux-lts")

    # glx portion, always build from the linux-lts tree
    shelltools.cd("linux-lts")
    pisitools.dolib("nvidia_drv.so", "/usr/lib64/xorg/modules/drivers")

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
