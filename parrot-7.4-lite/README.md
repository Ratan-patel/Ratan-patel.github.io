# Parrot 7.4 XFCE — curated security-tool build

This folder builds two AMD64 images from Parrot OS 7.4:

- a bootable **ISO** for USB/bare-metal installation or a VM installer
- a preinstalled **QCOW2** disk for QEMU/KVM/Proxmox

It is an **unofficial community remaster**, not an official ParrotOS release.

## Configuration

- XFCE desktop instead of KDE Plasma
- The ISO and QCOW2 contain the same four curated security-testing sections with four individual tools each; neither installs Parrot's full security-tool metapackages
- Remove LibreOffice (Writer, Calc, Impress, Math), plus Calligra, AbiWord and Gnumeric if present
- Remove optional developer/container/monitoring apps inherited from the full Security image unless a selected tool needs them (for example, Git may remain as a dependency)
- Keep core Parrot packages, drivers, browser, updater and XFCE; the ISO retains Calamares, while the QCOW2 drops the installer
- AMD64/x86_64 only; WSL is not part of this build

## Curated tool sections (both images)

| Section | Tools |
| --- | --- |
| Reconnaissance and service discovery | Nmap, Masscan, DNSRecon, DNSenum |
| Web application assessment | OWASP ZAP, sqlmap, ffuf, Nikto |
| Vulnerability validation and controlled access testing | Nuclei, WPScan, Metasploit Framework, Hydra |
| Post-access and AD/credential assessment | Impacket scripts, NetExec, SMBMap, Hashcat |

The post-access tools are for authorized lab and assessment work. Covert persistence implants and backdoor toolkits are intentionally excluded. Use these tools only on systems you own or have explicit permission to test.

The images are kept out of Git. GitHub Actions uploads separate downloadable artifacts retained for 30 days. Run the workflow from **Actions → Build Parrot 7.4 Minimal XFCE → Run workflow**. A commit marked `[iso-only]` skips the QCOW2 job; `[qcow2-only]` skips the ISO job.

## Size and source

Parrot's official 7.4 Security ISO is about 8.68 GB and its compressed Security QCOW2 is about 9.08 GB. Both custom images retain only the curated tool list above, use XFCE, and omit office apps and the full security-tool suites. Exact output sizes depend on the rolling package repository and compression, so the build does not promise a fixed 4–5 GB size.

The QCOW2 build starts from Parrot's official 7.4 Security QCOW2, verifies the upstream signed checksum list, removes the full security/office suites, installs XFCE and the curated tools, then sparsifies and compresses the virtual disk. The ISO is generated from ParrotSec's live-build configuration with a minimal XFCE package list plus the same selected tools.

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

Build either image (run the QCOW2 builder as an unprivileged user so libguestfs networking can use the configured backend):

```bash
sudo bash parrot-7.4-lite/scripts/build-iso.sh
bash parrot-7.4-lite/scripts/build-qcow2.sh
```

Outputs and `SHA256SUMS.txt` are written to `parrot-7.4-lite/artifacts/` (ignored by Git). You can change `OUTPUT_DIR` and use `WORK_DIR` as the temporary-work parent directory. The release recipe is pinned to version `7.4` and architecture `amd64`; the QCOW2 source can be selected with `PARROT_SOURCE_EDITION=security` or `home`.

## Use

- **ISO:** boot from the ISO and use the installer to install to a VM or computer. Double-check the target disk before installation. The curated tools are for authorized testing only.
- **QCOW2:** import/attach it as an existing disk in QEMU/KVM, virt-manager or Proxmox. Set RAM/CPU/disk to suit the host. It includes the same curated tools for authorized testing. Review its first-boot/login behavior and change the account password immediately.

Verify a downloaded custom artifact with:

```bash
sha256sum -c SHA256SUMS.txt
qemu-img check Parrot-7.4-Minimal-XFCE-amd64.qcow2
```

This is not the full Parrot Security Edition: both images have a deliberately curated subset of tools and an XFCE desktop. Use them only on systems you own or are authorized to administer.
