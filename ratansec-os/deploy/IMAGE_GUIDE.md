# 📦 ISO vs QCOW2 vs VMDK vs VDI — kya chahiye, kahan use hota hai

## 🎯 Ready files (aaj hi download karo) — GitHub Release
**Link:** https://github.com/Ratan-patel/Ratan-patel.github.io/releases/tag/ratansec-os-image-v1.0.0

### 📥 Direct download links (click karo, seedha download shuru)

| # | File | Size | Kis VM ke liye | Download |
|---|---|---|---|---|
| 1 | **`ratansec-os-1.0.0-amd64.qcow2`** | 597 MB | **Oracle Cloud custom image import** · Proxmox · KVM/libvirt · GCP | [⬇ Download](https://github.com/Ratan-patel/Ratan-patel.github.io/releases/download/ratansec-os-image-v1.0.0/ratansec-os-1.0.0-amd64.qcow2) |
| 2 | **`ratansec-os-1.0.0-amd64.img.gz`** | 548 MB | **raw disk** — providers jo `raw .img` maangte hain (AWS/GCP import, kuch VPS). Pehle unzip: `gzip -d ratansec-os-1.0.0-amd64.img.gz` | [⬇ Download](https://github.com/Ratan-patel/Ratan-patel.github.io/releases/download/ratansec-os-image-v1.0.0/ratansec-os-1.0.0-amd64.img.gz) |
| 3 | `ratansec-os-1.0.0-amd64.vmdk` | 568 MB | VMware Workstation/ESXi · VirtualBox | [⬇ Download](https://github.com/Ratan-patel/Ratan-patel.github.io/releases/download/ratansec-os-image-v1.0.0/ratansec-os-1.0.0-amd64.vmdk) |
| 4 | `ratansec-os-1.0.0-amd64.vdi` | 1.8 GB | VirtualBox (seedha attach, convert nahi karna padta) | [⬇ Download](https://github.com/Ratan-patel/Ratan-patel.github.io/releases/download/ratansec-os-image-v1.0.0/ratansec-os-1.0.0-amd64.vdi) |
| 5 | `ratansec-seed.iso` | 40 KB | **cloud-init config** — kisi bhi Ubuntu cloud VM me 2nd CD-ROM me lagao (first boot par auto-install) | [⬇ Download](https://github.com/Ratan-patel/Ratan-patel.github.io/releases/download/ratansec-os-image-v1.0.0/ratansec-seed.iso) |
| 6 | `SHA256SUMS.txt` | 1 KB | checksum verify (`sha256sum -c SHA256SUMS.txt`) | [⬇ Download](https://github.com/Ratan-patel/Ratan-patel.github.io/releases/download/ratansec-os-image-v1.0.0/SHA256SUMS.txt) |

**Release page (sab ek jagah):** https://github.com/Ratan-patel/Ratan-patel.github.io/releases/tag/ratansec-os-image-v1.0.0

> **qcow2 vs img.gz — kya farq?**
> `.qcow2` = compressed, **import-friendly** (Oracle custom image, Proxmox `qm importdisk`, GCP import). Ye zyadatar logon ke liye sahi hai.
> `.img.gz` = **raw disk** (unzip karne par ~3.5 GB). Un providers/tools ke liye jo `raw` format maangte hain. Kabhi kabhi `dd` se bhi use hota hai.

> **ISO vs image:** `.iso` (seed ISO) koi OS nahi hai — wo 40 KB ka **config disc** hai jo kisi bhi Ubuntu VM ko batata hai ki first boot par kya install karna hai. Poora OS **qcow2/vmdk/vdi/img** images ke andar hai.

> **ARM VM (Oracle Ampere free tier) chahiye?** GitHub → Actions → *"Build RatanSec OS VM images"* → **Run workflow** → `arch: arm64` → 20 min me ARM image release me aa jayegi.

**Image ke andar kya hai:** RatanSec OS ka poora code + installer (baked). Pehla boot par khud install hota hai (tools + systemd service, 4-6 min), phir `http://<VM-IP>:8000` par dashboard. Password: VM me `/root/ratansec-credentials.txt`.

---

Bhai simple mein: **yeh sab "VM ki file" ke different formats hain.** Har VM platform apna format maangta hai. Neeche table dekh ke apna chuno.

| Format | Kya hai | Kahan chalta hai |
|---|---|---|
| **`.qcow2`** | QEMU/KVM ka disk image (compressed, growable) | **Oracle Cloud custom image import** · Proxmox · libvirt/virt-manager · OpenStack · GCP (`gcloud images import`) |
| **`.vmdk`** | VMware ka disk format | VMware Workstation/Fusion, **ESXi**, VirtualBox (attach/convert) |
| **`.vdi`** | VirtualBox ka native disk | VirtualBox (seedha attach) |
| **`.img` (raw)** | Bina wrapper ka raw disk | Cloud providers jahan raw maangte hain (AWS AMI import, kuch PaaS) |
| **`.iso` (seed ISO)** | Chhoti (~40 KB) config disc — cloud-init isse padhta hai | **Sabse aasan:** koi bhi Ubuntu/Debian cloud image + yeh ISO = first boot par RatanSec OS auto-install |

> **Confusion?** Do raste best hain:
> **1) Ready-made image (baked)** → `.qcow2` (Oracle/Proxmox/KVM) ya `.vdi` (VirtualBox) import karo → boot karo → 4-6 min baad ready.
> **2) Stock Ubuntu + seed ISO** → koi bhi Ubuntu cloud image chalao, yeh 40 KB ISO 2nd drive me lagao → wahi kaam ho jayega (image ki zarurat hi nahi).

---

## 📥 File dobara banao (agar chahiye ho)

**GitHub Actions se (kuch install nahi):** repo → **Actions** → *"Build RatanSec OS VM images"* → **Run workflow** → arch/distro chuno → 20-30 min → nayi release/artifact ready.
**Apne Linux box par:**

### Tarika 2 — apne Linux/VM par khud banao
```bash
sudo apt-get install -y qemu-utils libguestfs-tools curl python3-pip
git clone https://github.com/Ratan-patel/Ratan-patel.github.io.git
cd Ratan-patel.github.io
sudo bash ratansec-os/deploy/build-image.sh --arch amd64 --types qcow2,vmdk,vdi
# → ratansec-os/artifacts/ me saari files
```
ARM (Oracle Ampere free tier) ke liye: `--arch arm64` (usko ARM VM me hi chalao).

---

## ☁️ 1) Oracle Cloud (free tier) — qcow2 import

### A) Oracle ARM free VM (Ampere A1) par
1. `--arch arm64` wali **qcow2** download karo (arm64 image ARM shape par hi chalegi).
2. Oracle Console → **Storage → Buckets** → ek bucket banao → qcow2 file **upload** karo.
3. **Compute → Custom Images → Import image**:
   - Name: `ratansec-os`
   - **Object Storage object**: apni bucket + uploaded qcow2 select karo
   - Image type: **QCOW2**
   - Operating system: **Ubuntu** · Version: **24.04**
   - ✅ **"Use cloud-init"** (ya "Cloud-init supported") — ON rakho (isse SSH keys inject hongi)
4. Image ban jane par **Create Instance** → shape: `VM.Standard.A1.Flex` (ARM free tier) → **Image: ratansec-os** → **SSH key upload** karo → Create.
5. Boot ke 4-6 min baad SSH: `ssh ubuntu@<VM-IP>`
   ```bash
   sudo cat /root/ratansec-credentials.txt     # dashboard password
   curl -s localhost:8000/api/health
   ```
6. **Networking → VCN → Security Lists → Default → Add Ingress Rule**: Source `0.0.0.0/0`, Protocol `TCP`, Destination Port `8000`
7. Browser: `http://<VM-IP>:8000` → password → **dashboard** 🎉

### B) Oracle X86 free VM (VM.Standard.E2.1.Micro) par
Wahi steps, par **amd64** qcow2 use karo aur shape `VM.Standard.E2.1.Micro` select karo (1 GB RAM → VM me `--lite` wala setup theek rahega; tools install me thoda time lagega).

### C) Bina custom image (super aasan)
Ubuntu 24.04 ki **stock image** se VM banao (Oracle me "Canonical Ubuntu 24.04" platform image) → VM banate waqt hi **cloud-init / user-data** me humari `deploy/cloud-init/user-data` copy-paste kar do → first boot par sab install ho jayega. (UI me "Advanced options → Management → cloud-init script")

---

## 🟦 2) Proxmox VE — qcow2 import

```bash
# qcow2 file Proxmox host par le jao (scp/gui upload)
scp ratansec-os-1.0.0-amd64.qcow2 root@proxmox:/var/lib/vz/template/

# naya VM banao (UI: Create VM → OS type Linux, disk skip/no disk, RAM 2-4 GB)
qm create 900 --name ratansec-os --memory 4096 --cores 2 --net0 virtio,bridge=vmbr0
qm importdisk 900 /var/lib/vz/template/ratansec-os-1.0.0-amd64.qcow2 local-lvm
qm set 900 --scsi0 local-lvm:vm-900-disk-0 --ide2 local-lvm:cloudinit --boot order=scsi0
qm set 900 --serial0 socket --vga serial0     # console ke liye
qm set 900 --ciuser ubuntu --sshkeys ~/.ssh/authorized_keys
qm start 900
```
Console (noVNC) me login ke baad: `sudo cat /root/ratansec-credentials.txt` → browser: `http://<VM-IP>:8000`

---

## 🟩 3) KVM / libvirt / virt-manager — qcow2

```bash
virt-install --name ratansec-os --memory 4096 --vcpus 2 --import \
  --disk /path/ratansec-os-1.0.0-amd64.qcow2,format=qcow2,bus=virtio \
  --cloud-init user-data=/path/user-data.yaml \
  --os-variant ubuntu24.04 --graphics none --console pty,target_type=serial
```
(`--cloud-init` ki jagah seed ISO bhi de sakte ho: `--disk ratansec-seed.iso,device=cdrom`)

---

## 🟨 4) VirtualBox — vdi ya vmdk

**Sabse aasan:** `ratansec-os-1.0.0-amd64.vdi` ko direct attach karo:
```bash
VBoxManage createvm --name RatanSecOS --ostype Ubuntu_64 --register
VBoxManage modifyvm RatanSecOS --memory 4096 --cpus 2 --nic1 nat
VBoxManage storagectl RatanSecOS --name SATA --add sata --controller IntelAhci
VBoxManage storageattach RatanSecOS --storagectl SATA --port 0 --device 0 \
  --type hdd --medium /path/ratansec-os-1.0.0-amd64.vdi
VBoxManage storagectl RatanSecOS --name IDE --add ide
VBoxManage storageattach RatanSecOS --storagectl IDE --port 1 --device 0 \
  --type dvddrive --medium /path/ratansec-seed.iso        # cloud-init ke liye
VBoxManage modifyvm RatanSecOS --natpf1 "dash,tcp,,8000,,8000"
VBoxManage startvm RatanSecOS
```
`qcow2` se convert karna ho to: `VBoxManage clonemedium disk in.qcow2 out.vdi --format VDI`

> **Login problem?** VirtualBox par cloud-init ko metadata chahiye hota hai — humari **baked image** ka first-boot khud chalta hai, SSH key ki zarurat nahi. Console me: user `ubuntu` (password blank?) → nahi khule to seed ISO (above) laga do, ya baked image me `ubuntu` ka password set karo:
> `VBoxManage guestproperty …` nahi chalega — isliye VirtualBox me **seed ISO wala rasta** use karo (wo `ubuntu` user ke liye password/auth handle karta hai).
> Alternative: image ko boot karke console me "Ubuntu" user ke liye recovery... aasaan tareeka — **seed ISO attach karo, ram 2 GB+, aur boot ke baad 5 min wait**; dashboard password `/root/ratansec-credentials.txt` me milega (root login console se: `sudo -i`).

---

## 🟪 5) VMware Workstation / ESXi — vmdk

**Workstation:** New VM → "I will install the OS later" → disk type **Use an existing virtual disk** → `ratansec-os-1.0.0-amd64.vmdk` → RAM 4 GB → Network: Bridged/NAT → Start.
Console login ke baad: `sudo cat /root/ratansec-credentials.txt`

**ESXi/vCenter:** Datastore browser → vmdk upload → naya VM → "Existing hard disk" → attach.

---

## 🟫 6) Google Cloud — qcow2 import

```bash
gcloud storage buckets create gs://tera-bucket-images
gcloud storage cp ratansec-os-1.0.0-amd64.qcow2 gs://tera-bucket-images/
gcloud compute images import ratansec-os --source-file=gs://tera-bucket-images/ratansec-os-1.0.0-amd64.qcow2 \
  --os=ubuntu-2404 --boot-disk-size=20GB
gcloud compute instances create ratansec --image=ratansec-os \
  --zone=asia-south1-a --machine-type=e2-medium --tags=ratansec-web
gcloud compute firewall-rules create ratansec-8000 --allow tcp:8000 --target-tags=ratansec-web --source-ranges=0.0.0.0/0
```
SSH: `gcloud compute ssh ratansec -- 'sudo cat /root/ratansec-credentials.txt'`

---

## 🅰️ Sabse aasan rasta (kuch import nahi) — **seed ISO**

1. Kisi bhi platform par **Ubuntu 24.04 cloud image** se VM banao (Oracle/GCP/AWS/Proxmox/Multipass/VMware sab me).
2. **`ratansec-seed.iso`** ko us VM me **second CD-ROM / additional drive** me attach karo (pehle se bane VM me bhi lagaya ja sakta hai).
3. VM boot karo → cloud-init user-data padhega → 4-6 min me install (tools + systemd service).
4. Login karke: `sudo cat /root/ratansec-credentials.txt` → browser `http://<VM-IP>:8000`

Khud seed ISO banana (apni key + scope ke saath):
```bash
bash ratansec-os/deploy/build-seed-iso.sh \
  --key sk-or-v1-TUMHARI-KEY --scope "tera-domain.com" --branch main \
  --out ratansec-seed.iso
```

**Multipass examples:**
```bash
multipass launch 24.04 --name ratansec --memory 4G --disk 20G --cloud-init deploy/cloud-init/user-data
multipass exec ratansec -- sudo cat /root/ratansec-credentials.txt
```
*(user-data me placeholders ki jagah apni values daal lo, ya seed ISO build script se bani hui file use karo — wahi final `user-data` hoti hai.)*

---

## 🔧 Image ke andar kya-kya hai

| Cheez | Detail |
|---|---|
| Base | Ubuntu 24.04 LTS cloud image (noble), `ubuntu` user + cloud-init enabled |
| RatanSec OS | `/opt/ratansec-os` (app + `.env` + `.venv`) · systemd service **`ratansecos`** (boot par auto-start) |
| First boot | Tools install (nmap, nikto, whatweb, sqlmap, gobuster, ffuf, nuclei, hydra, whois, dig…) — 4-6 min |
| Dashboard | `http://<VM-IP>:8000` · password `/root/ratansec-credentials.txt` me |
| Helper CLI | `ratansec status|logs|restart|password|update` |
| Logs | `sudo journalctl -u ratansecos -f` · first boot: `/var/log/ratansec-firstboot.log` |

**Credentials/AI key badalna:**
```bash
sudo nano /opt/ratansec-os/.env      # APP_PASSWORD, OPENROUTER_API_KEY, ALLOWED_TARGETS
ratansec restart
```

---

## 🧪 Verify + troubleshooting

```bash
sha256sum -c SHA256SUMS.txt                     # download sahi hua?
qemu-img info ratansec-os-1.0.0-amd64.qcow2     # image readable?
```
| Problem | Fix |
|---|---|
| VM boot hua par dashboard nahi | 6-8 min wait (tools install ho rahe hain) → `sudo journalctl -u ratansecos -n 50` · `cat /var/log/ratansec-firstboot.log` |
| `http://IP:8000` nahi khulta | **Cloud firewall** me inbound TCP 8000 allow karo (Oracle: Security List · GCP: firewall rule) |
| ARM VM par image boot nahi | `--arch arm64` wali image use karo (amd64 ARM par nahi chalti) |
| 1 GB RAM par slow | `.env` me `MAX_CONCURRENT_SCANS=1`, aur VM me swap add karo |
| Password bhool gaya | VM ke andar: `ratansec password` |
| SSH hi nahi ho raha | Instance banate waqt SSH key do; ya VM console (serial) se login karo — user `ubuntu`, `/root/ratansec-credentials.txt` |
| Image import fail (Oracle) | File **qcow2** honi chahiye + bucket object select kiya ho + OS type Ubuntu 24.04 |

---

## ⚠️ Yaad rakho

- Image tumhare **authorized testing** ke liye hai — scan karna legal sirf apne/pemission wale targets par.
- Default me **scope khaali** hai → har scan par dashboard me **Approve/Deny** aayega (safety). Apne targets `.env` ke `ALLOWED_TARGETS` me daalo.
- Public IP par dashboard khula hai → **strong password** rakho (first boot khud random password set karta hai).
- Image bada hai (~1-1.5 GB compressed) — 25 MB me VM image + tools possible nahi hain; yeh reality hai.
