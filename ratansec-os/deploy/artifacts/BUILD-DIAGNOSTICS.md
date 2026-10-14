# RatanSec image build diagnostics

Run: 38647374825 · 2026-10-14T22:30:35+00:00 · ref: arena/f71ea5d9-ratan-patel-github-io

## preflight.log
```
virt-customize 1.52.0
Formatting '/tmp/preflight.img', fmt=qcow2 cluster_size=65536 extended_l2=off compression_type=zlib size=209715200 lazy_refcounts=off refcount_bits=16
[   0.0] Examining the guest ...
virt-customize: error: libguestfs error: passt exited with status 1

If reporting bugs, run virt-customize with debugging enabled and include the complete output:

  virt-customize -v -x [...]
preflight exit: 0
```

## stage-download.log
```

[36m╔══════════════════════════════════════════════════════════════╗[0m
[36m║[0m   [1mRatanSec OS — VM image builder[0m v1.0.0                     [36m║[0m
[36m╚══════════════════════════════════════════════════════════════╝[0m
  [36m·[0m distro=noble arch=amd64 types=qcow2,vmdk,vdi
  [36m·[0m stages: download
  [36m·[0m work=/tmp/imgbuild out=/home/runner/work/Ratan-patel.github.io/Ratan-patel.github.io/ratansec-os/artifacts

[1m▶ Stage: download — Ubuntu noble (amd64) cloud image[0m
  [32m✓[0m qemu-img 8.2.2 · curl · python3 present
  [36m·[0m download: https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0  0  596M    0 98304    0     0   106k      0  1:35:38 --:--:--  1:35:38  106k  0  596M    0 2496k    0     0  1315k      0  0:07:44  0:00:01  0:07:43 1315k  4  596M    4 25.9M    0     0  8943k      0  0:01:08  0:00:02  0:01:06 8941k 16  596M   16 96.0M    0     0  24.0M      0  0:00:24  0:00:03  0:00:21 24.0M 23  596M   23  140M    0     0  27.4M      0  0:00:21  0:00:05  0:00:16 27.4M 33  596M   33  199M    0     0  33.7M      0  0:00:17  0:00:05  0:00:12 39.8M 45  596M   45  273M    0     0  38.7M      0  0:00:15  0:00:07  0:00:08 52.5M 59  596M   59  356M    0     0  44.9M      0  0:00:13  0:00:07  0:00:06 66.6M 69  596M   69  416M    0     0  46.4M      0  0:00:12  0:00:08  0:00:04 64.4M 77  596M   77  464M    0     0  46.5M      0  0:00:12  0:00:09  0:00:03 66.5M 84  596M   84  504M    0     0  46.2M      0  0:00:12  0:00:10  0:00:02 60.8M 93  596M   93  557M    0     0  46.2M      0  0:00:12  0:00:12 --:--:-- 56.7M100  596M  100  596M    0     0  46.8M      0  0:00:12  0:00:12 --:--:-- 49.9M
  [32m✓[0m download complete (597M)
  [32m✓[0m image valid (qemu-img info OK)

[32m╔══════════════════════════════════════════════════════════════╗[0m
[32m║[0m   [1m✅ RatanSec OS build stage(s) complete[0m                   [32m║[0m
[32m╚══════════════════════════════════════════════════════════════╝[0m
   SHA256SUMS.txt                               0

   [1mVM me kaise daalein:[0m deploy/IMAGE_GUIDE.md

```

## stage-bake.log
```

[36m╔══════════════════════════════════════════════════════════════╗[0m
[36m║[0m   [1mRatanSec OS — VM image builder[0m v1.0.0                     [36m║[0m
[36m╚══════════════════════════════════════════════════════════════╝[0m
  [36m·[0m distro=noble arch=amd64 types=qcow2,vmdk,vdi
  [36m·[0m stages: bake
  [36m·[0m work=/tmp/imgbuild out=/home/runner/work/Ratan-patel.github.io/Ratan-patel.github.io/ratansec-os/artifacts

[1m▶ Stage: bake — app + first-boot installer image me daal raha hoon[0m
  [32m✓[0m virt-customize present (LIBGUESTFS_BACKEND=direct)
  [32m✓[0m working copy banayi (597M)
  [32m✓[0m staged: 452K
  [32m✓[0m firstboot script ready
  [36m·[0m virt-customize #1: app source inject (/opt/ratansec-os)…
[   0.0] Examining the guest ...
[   5.4] Setting a random seed
virt-customize: warning: random seed could not be set for this type of guest
[   5.4] Setting the machine ID in /etc/machine-id
[   5.4] Setting the hostname: ratansec-os
[   6.2] Making directory: /opt
[   6.2] Copying: /tmp/imgbuild/stage/ratansec-os to /opt
[   6.2] Running: mkdir -p /etc/motd.d /opt/ratansec-os
[   6.3] Writing: /etc/motd.d/ratansec
[   6.3] SELinux relabelling
[   6.4] Finishing off
  [36m·[0m virt-customize #2: first-boot unit install (--firstboot = HOST file path)…
[   0.0] Examining the guest ...
[   2.5] Setting a random seed
virt-customize: warning: random seed could not be set for this type of guest
[   2.6] Installing firstboot script: /tmp/imgbuild/firstboot.sh
[   2.6] SELinux relabelling
[   3.0] Finishing off
  [32m✓[0m image bake ho gayi: /tmp/imgbuild/ratansec-os-1.0.0-amd64-build.img
```

