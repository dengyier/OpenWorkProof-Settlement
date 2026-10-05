# Step-1 toolchain setup (macOS Apple Silicon)

This records the tooling actually used on 2026-10-05. Run commands from the repository root. Node 23.11.0, npm 10.9.2, Python 3.12.13 and Xcode were already installed. Other platforms require the corresponding official release artifacts; these commands are not a cross-platform installer.

The release downloader only fetches files and verifies SHA-256; execution/extraction is separate. It uses bounded parallel HTTP ranges to work around slow single-connection downloads. Each whole artifact must match its release checksum.

```sh
mkdir -p .tools/bin .tools/platform-tools
node scripts/download-tool.mjs https://github.com/anza-xyz/agave/releases/download/v4.3.0/solana-release-aarch64-apple-darwin.tar.bz2 .tools/solana-release-aarch64-apple-darwin.tar.bz2 77042691 0bfbd769a55e32f0a1fe1b92f76f360f01ee19475facf8c31cb90f99dcca7fe0
tar -xjf .tools/solana-release-aarch64-apple-darwin.tar.bz2 -C .tools
node scripts/download-tool.mjs https://github.com/otter-sec/anchor/releases/download/v1.2.0/anchor-1.2.0-aarch64-apple-darwin .tools/bin/anchor 28087904 986d99392a520dfc50b63caf4eda9b9d7619c78ffb53fc57b6f8677c60b6d27e
node scripts/download-tool.mjs https://static.rust-lang.org/rustup/dist/aarch64-apple-darwin/rustup-init .tools/bin/rustup-init 11319056 ec1b9233e7f72990ecd8e62063fa7f6c3dfc2bec8e97f88bff165f9100ac696a
chmod +x .tools/bin/anchor .tools/bin/rustup-init
export CARGO_HOME="$PWD/.tools/cargo"
export RUSTUP_HOME="$PWD/.tools/rustup"
export PATH="$PWD/.tools/bin:$PWD/.tools/solana-release/bin:$CARGO_HOME/bin:$PATH"
.tools/bin/rustup-init -y --no-modify-path --profile minimal --default-toolchain none
node scripts/download-tool.mjs https://github.com/anza-xyz/platform-tools/releases/download/v1.57/platform-tools-osx-aarch64.tar.bz2 .tools/platform-tools-osx-aarch64.tar.bz2 430747800 48c32c2ec3ac3729b5caf1fdd6c4145496125edf043b2662b0586bfbc932b34a
tar -xjf .tools/platform-tools-osx-aarch64.tar.bz2 -C .tools/platform-tools
rustup toolchain link solana "$PWD/.tools/platform-tools/rust"
rustup default solana
```

`cargo-build-sbf` 4.3.0 requires its SDK at the user's `.cache/solana/v1.57/platform-tools` path, even with `--skip-tools-install`. Its source computes this path from the existing home directory; it has no project-cache override. On this machine `/Users/molin/.cache/solana/v1.57/platform-tools` was absent, so a new symlink was created pointing to `/Users/molin/Project/dorahacks/colosseum/.tools/platform-tools`. No existing cache was replaced. On another machine, inspect the equivalent path before creating a link; reuse a valid v1.57 installation, never overwrite an existing target. This cache link is the sole tooling addition outside the project. No global shell, wallet or Solana network configuration was changed.

Verified versions:

- Solana CLI / validator / cargo-build-sbf: 4.3.0.
- Anchor CLI / Rust dependencies: 1.2.0.
- Solana platform tools: v1.57, `rustc 1.95.0-dev (ae660768a 2026-08-17)`.

Anchor 1.2's token-account initialization macro references the Token-2022 interface, so `anchor-spl` enables `token_2022` to compile the macro. The actual program still uses `Program<Token>` and legacy `Mint`/`TokenAccount`, which reject Token-2022 program/accounts. Enabling this build feature is not a claim of Token-2022 support.

The compiler may report Anchor macro `unexpected_cfgs` and cdylib/lib LTO warnings; these are recorded rather than suppressed. Rust dependencies and install artifacts are large and the first build can take several minutes. `.tools`, build output and local ledgers are ignored by Git. The generated deployment keypair is also ignored and does not match the fixed local-genesis address; do not use it to deploy this program unchanged.

References: [Agave releases](https://github.com/anza-xyz/agave/releases/tag/v4.3.0), [platform-tools release](https://github.com/anza-xyz/platform-tools/releases/tag/v1.57), [Anchor release](https://github.com/otter-sec/anchor/releases/tag/v1.2.0), [official Anchor installation](https://www.anchor-lang.com/docs/installation).
