#!/bin/sh
# 基于本地文件安装 Ollama

set -eu

red="$( (/usr/bin/tput bold || :; /usr/bin/tput setaf 1 || :) 2>&-)"
plain="$( (/usr/bin/tput sgr0 || :) 2>&-)"

status() { echo ">>> $*" >&2; }
error() { echo "${red}ERROR:${plain} $*"; exit 1; }
warning() { echo "${red}WARNING:${plain} $*"; }

[ "$(uname -s)" = "Linux" ] || error 'This script is intended to run on Linux only.'

ARCH=$(uname -m)
case "$ARCH" in
    x86_64) ARCH="amd64" ;;
    aarch64|arm64) ARCH="arm64" ;;
    *) error "Unsupported architecture: $ARCH" ;;
esac

SUDO=
if [ "$(id -u)" -ne 0 ]; then
    if ! command -v sudo >/dev/null; then
        error "This script requires superuser permissions. Please re-run as root."
    fi
    SUDO="sudo"
fi

# 检查本地文件
LOCAL_FILE="/opt/triage/ai"
if [ ! -f "$LOCAL_FILE" ]; then
    error "Local file $LOCAL_FILE not found. Please download it first."
fi

for BINDIR in /usr/local/bin /usr/bin /bin; do
    echo $PATH | grep -q $BINDIR && break || continue
done
OLLAMA_INSTALL_DIR=$(dirname ${BINDIR})

if [ -d "$OLLAMA_INSTALL_DIR/lib/ollama" ] ; then
    status "Cleaning up old version at $OLLAMA_INSTALL_DIR/lib/ollama"
    $SUDO rm -rf "$OLLAMA_INSTALL_DIR/lib/ollama"
fi

status "Installing ollama to $OLLAMA_INSTALL_DIR"
$SUDO install -o0 -g0 -m755 -d $BINDIR
$SUDO install -o0 -g0 -m755 -d "$OLLAMA_INSTALL_DIR/lib/ollama"

status "Using local bundle from $LOCAL_FILE"
$SUDO tar -xzf "$LOCAL_FILE" -C "$OLLAMA_INSTALL_DIR"

if [ "$OLLAMA_INSTALL_DIR/bin/ollama" != "$BINDIR/ollama" ] ; then
    status "Making ollama accessible in the PATH in $BINDIR"
    $SUDO ln -sf "$OLLAMA_INSTALL_DIR/ollama" "$BINDIR/ollama"
fi

# 跳过 GPU 检测和驱动安装（因为我们现在只是测试）

configure_systemd() {
    if ! id ollama >/dev/null 2>&1; then
        status "Creating ollama user..."
        $SUDO useradd -r -s /bin/false -U -m -d /usr/share/ollama ollama
    fi

    status "Adding current user to ollama group..."
    $SUDO usermod -a -G ollama $(whoami)

    status "Creating ollama systemd service..."
    cat <<SERVICE_EOF | $SUDO tee /etc/systemd/system/ollama.service >/dev/null
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=$BINDIR/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="PATH=$PATH"

[Install]
WantedBy=default.target
SERVICE_EOF

    SYSTEMCTL_RUNNING="$(systemctl is-system-running || true)"
    case $SYSTEMCTL_RUNNING in
        running|degraded)
            status "Enabling and starting ollama service..."
            $SUDO systemctl daemon-reload
            $SUDO systemctl enable ollama
            $SUDO systemctl restart ollama
            ;;
        *)
            warning "systemd is not running"
            ;;
    esac
}

if command -v systemctl >/dev/null; then
    configure_systemd
fi

status 'The Ollama API is now available at 127.0.0.1:11434.'
status 'Install complete. Run "ollama" from the command line.'

