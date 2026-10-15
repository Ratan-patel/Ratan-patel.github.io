# Parrot 7.4 Minimal XFCE — unofficial custom build

This folder builds two AMD64 images from Parrot OS 7.4:

- a bootable **ISO** for USB/bare-metal installation or a VM installer
- a preinstalled **QCOW2** disk for QEMU/KVM/Proxmox

It is an **unofficial community remaster**, not an official ParrotOS release.

## Requested configuration

- XFCE desktop instead of KDE Plasma
- remove the full pentesting/security-tool metapackages (including `parrot-tools-full`)
- remove the LibreOffice suite (Writer, Calc, Impress, Math), plus Calligra, AbiWord and Gnumeric if present
- remove optional developer/container/monitoring apps inherited from the full Security image
- keep core Parrot packages, drivers, browser, updater, XFCE and the basic desktop; the ISO retains Calamares for installation, while the preinstalled QCOW2 drops the installer
- AMD64/x86_64 only; WSL is not part of this build

The images are kept out of Git. The GitHub Actions workflow builds them and uploads separate downloadable artifacts (retained for 30 days). Run it from **Actions → Build Parrot 7.4 Minimal XFCE → Run workflow**.

## Size and source

Parrot's official 7.4 Security ISO is about 8.68 GB and its compressed Security QCOW2 is about 9.08 GB. Those include the full security-tool collection. This build removes that package set and uses XFCE, but exact output sizes depend on the rolling package repository and image compression; the build does not promise a fixed 4–5 GB size.

The QCOW2 build starts from Parrot's official 7.4 Security QCOW2, verifies the upstream signed checksum list, removes the security/office packages, installs XFCE, then sparsifies and compresses the virtual disk. The ISO is generated from ParrotSec's live-build configuration using a minimal XFCE package list.

Official sources:

- Downloads: <https://parrotsec.org/download/>
- 7.4 signed hashes: <https://deb.parrot.sh/parrot/iso/7.4/signed-hashes.txt>
- Parrot ISO build configuration: <https://github.com/ParrotSec/parrot-iso-build>
- Parrot signing-key verification guide: <https://parrotsec.org/docs/configuration/hash-and-key-verification/>

## Build locally

Use a Debian/Ubuntu AMD64 machine with root/sudo, internet access, at least 8 GB RAM, and roughly 35 GB free disk space. The build downloads official Parrot packages and the Security QCOW2 source image.

ISO prerequisites:

```bash
sudo apt-get update
sudo apt-get install -y live-build debootstrap squashfs-tools xorriso rsync \
  apt-utils gnupg dctrl-tools curl wget git cpio mtools dosfstools \
  grub-pc-bin grub-efi-amd64-bin isolinux syslinux-common
```

QCOW2 prerequisites:

```bash
sudo apt-get install -y qemu-utils libguestfs-tools xz-utils curl gnupg
```

Build either image (run the QCOW2 builder as an unprivileged user so libguestfs networking can use `passt`):

```bash
sudo bash parrot-7.4-lite/scripts/build-iso.sh
bash parrot-7.4-lite/scripts/build-qcow2.sh
```

Outputs and `SHA256SUMS.txt` are written to `parrot-7.4-lite/artifacts/` (ignored by Git). You can change `OUTPUT_DIR` and use `WORK_DIR` as the temporary-work parent directory. The release recipe is pinned to version `7.4` and architecture `amd64`; the QCOW2 source can be selected with `PARROT_SOURCE_EDITION=security` or `home`.

## Use

- **ISO:** boot from the ISO and use the installer to install to a VM or computer. Double-check the target disk before installation.
- **QCOW2:** import/attach it as an existing disk in QEMU/KVM, virt-manager or Proxmox. Set RAM/CPU/disk to suit the host. The image is derived from Parrot's official VM image, so review its first-boot/login behavior and change the account password immediately.

Verify a downloaded custom artifact with:

```bash
sha256sum -c SHA256SUMS.txt
qemu-img check Parrot-7.4-Minimal-XFCE-amd64.qcow2
```

This is not an official Security Edition after removing its security-tool suite. It is a small, XFCE-based Parrot remaster. Use it only on systems you own or are authorized to administer.
