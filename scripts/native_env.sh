# Source this file in the Debian cloud environment; it does not install anything.
export CARGO_HOME="${CARGO_HOME:-/workspace/.stanicode-tools/cargo}"
export RUSTUP_HOME="${RUSTUP_HOME:-/workspace/.stanicode-tools/rustup}"
export PATH="$CARGO_HOME/bin:$PATH"
export PKG_CONFIG_SYSROOT_DIR=/workspace/.stanicode-tools/linux-sysroot
export PKG_CONFIG_PATH="$PKG_CONFIG_SYSROOT_DIR/usr/lib/x86_64-linux-gnu/pkgconfig:$PKG_CONFIG_SYSROOT_DIR/usr/share/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
