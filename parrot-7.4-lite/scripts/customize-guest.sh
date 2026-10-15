#!/bin/bash
set -Eeuo pipefail

export DEBIAN_FRONTEND=noninteractive
export APT_LISTCHANGES_FRONTEND=none
export LC_ALL=C

retry_apt() {
    local attempt=1
    local max_attempts=5
    until apt-get -o Acquire::Retries=3 "$@"; do
        if ((attempt >= max_attempts)); then
            printf 'apt-get %s failed after %d attempts.\n' "$*" "$attempt" >&2
            return 1
        fi
        printf 'apt-get %s failed (attempt %d/%d); retrying in 8 seconds.\n' \
            "$*" "$attempt" "$max_attempts" >&2
        sleep 8
        attempt=$((attempt + 1))
    done
}

purge_matching() {
    local regex="$1"
    local exclude="${2:-}"
    mapfile -t packages < <(
        dpkg-query -W -f='${db:Status-Abbrev}\t${binary:Package}\n' 2>/dev/null \
            | awk -F '\t' -v regex="$regex" -v exclude="$exclude" \
              'substr($1, 1, 2) == "ii" && $2 ~ regex && (exclude == "" || $2 !~ exclude) { print $2 }'
    )
    if ((${#packages[@]})); then
        printf 'Purging packages: %s\n' "${packages[*]}"
        retry_apt purge -y "${packages[@]}"
    fi
}

retry_apt update

# Keep the OS core and user-facing essentials manual while removing the
# automatically-installed dependencies of the Security tool metapackages.
apt-mark manual parrot-core parrot-drivers parrot-updater firefox-esr 2>/dev/null || true

purge_matching '^(parrot-tools-full|parrot-tools-[^:]+|parrot-meta-(devel|privacy|crypto|security|pentest|full))(:.*)?$' '^parrot-tools-base(:.*)?$'
purge_matching '^(libreoffice|libreoffice-[^:]+|calligra|calligra-[^:]+|abiword|gnumeric)(:.*)?$'
purge_matching '^(parrot-desktop-kde|kde-plasma-desktop|kde-standard|kde-full|kde-[^:]+|plasma-[^:]+|sddm|sddm-[^:]+|systemsettings|dolphin|konsole|kate|ark|okular|kcalc|discover|korganizer|kmail|kontact|akonadi-[^:]+)(:.*)?$'
purge_matching '^(calamares|calamares-settings-parrot)(:.*)?$'
purge_matching '^(codium|golang-go|nodejs|npm|default-jdk|openjdk-[^:]+|python3-pip|git|podman|podman-docker|flatpak|flatpak-xdg-utils|remmina|gufw|thunderbird|wine|wine64|neovim|inxi|neofetch|htop|nload|iftop)(:.*)?$'

printf 'lightdm shared/default-x-display-manager select lightdm\n' | debconf-set-selections
retry_apt install -y \
    parrot-desktop-xfce task-xfce-desktop lightdm lightdm-gtk-greeter \
    firefox-esr parrot-updater
apt-mark manual parrot-core parrot-drivers parrot-updater firefox-esr \
    parrot-desktop-xfce task-xfce-desktop lightdm lightdm-gtk-greeter 2>/dev/null || true

# Remove optional apps again in case the desktop task selected any as recommends.
purge_matching '^(libreoffice|libreoffice-[^:]+|calligra|calligra-[^:]+|abiword|gnumeric)(:.*)?$'
purge_matching '^(parrot-tools-full|parrot-tools-[^:]+|parrot-meta-(devel|privacy|crypto|security|pentest|full))(:.*)?$' '^parrot-tools-base(:.*)?$'
purge_matching '^(codium|golang-go|nodejs|npm|default-jdk|openjdk-[^:]+|python3-pip|git|podman|podman-docker|flatpak|flatpak-xdg-utils|remmina|gufw|thunderbird|wine|wine64|neovim|inxi|neofetch|htop|nload|iftop)(:.*)?$'
retry_apt autoremove --purge -y

# Make XFCE/LightDM the selected graphical session.
printf '/usr/sbin/lightdm\n' > /etc/X11/default-display-manager
systemctl disable sddm.service 2>/dev/null || true
systemctl enable lightdm.service 2>/dev/null || true
update-alternatives --set x-session-manager /usr/bin/startxfce4 2>/dev/null || true

apt-get clean
rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*.deb /var/tmp/*
rm -f /root/.bash_history
find /home -maxdepth 2 -name .bash_history -type f -delete 2>/dev/null || true

# Allow systemd to generate a unique machine ID on first boot.
: > /etc/machine-id
rm -f /var/lib/dbus/machine-id

# Fail the image build rather than silently shipping unwanted software.
unwanted="$(dpkg-query -W -f='${db:Status-Abbrev} ${binary:Package}\n' 2>/dev/null \
    | awk 'substr($1, 1, 2) == "ii" && ($2 ~ /^(libreoffice|calligra|abiword|gnumeric|codium|golang-go|nodejs|npm|default-jdk|openjdk-|python3-pip|git|podman|flatpak|remmina|gufw|thunderbird|wine|wine64|neovim|inxi|neofetch|htop|nload|iftop)/ || ($2 ~ /^parrot-tools-/ && $2 !~ /^parrot-tools-base/) || $2 ~ /^parrot-meta-(devel|privacy|crypto|security|pentest|full)(:.*)?$/) { print $2 }')"
if [[ -n "$unwanted" ]]; then
    printf 'Unexpected heavy/security package remains: %s\n' "$unwanted" >&2
    exit 1
fi

dpkg-query -W -f='${db:Status-Abbrev}\n' parrot-desktop-xfce 2>/dev/null | grep -q '^ii' || {
    echo 'XFCE desktop metapackage was not installed' >&2
    exit 1
}
test -x /usr/bin/startxfce4 || {
    echo 'XFCE session launcher is missing' >&2
    exit 1
}
test -x /usr/sbin/lightdm || {
    echo 'LightDM display manager is missing' >&2
    exit 1
}
