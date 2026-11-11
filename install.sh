#!/data/data/com.termux/files/usr/bin/bash
# Install Code Puppy + DroidPuppy on Android through Termux.
set -eu

DROIDPUPPY_REPO="${DROIDPUPPY_REPO:-https://github.com/kvandre12-commits/DroidPuppy}"
DROIDPUPPY_REF="${DROIDPUPPY_REF:-main}"
DRY_RUN=0
INSTALL_ENGINE=1
INSTALL_OPTIONAL=1
ENGINE_PROFILE="android-0720"

usage() {
    cat <<'EOF'
Usage: install.sh [options]

Install Code Puppy and the DroidPuppy Android capability overlay in Termux.
The installer is safe to rerun; DroidPuppy plugins are refreshed in place.

Options:
  --dry-run        Print the installation plan without changing anything
  --skip-engine    Install only DroidPuppy (Code Puppy is already installed)
  --minimal        Skip optional ADB and Termux:API command packages
  --engine-profile PROFILE
                   Install a versioned engine profile (default: android-0720)
  -h, --help       Show this help
EOF
}

say() { printf '\n\033[1;36mDroidPuppy>\033[0m %s\n' "$*"; }
fail() { printf '\nDroidPuppy install failed: %s\n' "$*" >&2; exit 1; }

quote_command() {
    printf '  $'
    printf ' %q' "$@"
    printf '\n'
}

run() {
    quote_command "$@"
    [ "$DRY_RUN" -eq 1 ] || "$@"
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --dry-run) DRY_RUN=1 ;;
        --skip-engine) INSTALL_ENGINE=0 ;;
        --minimal) INSTALL_OPTIONAL=0 ;;
        --engine-profile)
            [ "$#" -ge 2 ] || fail "--engine-profile requires a profile name"
            ENGINE_PROFILE="$2"
            shift
            ;;
        -h|--help) usage; exit 0 ;;
        *) fail "Unknown option: $1" ;;
    esac
    shift
done

case "$ENGINE_PROFILE" in
    android-0720)
        ENGINE_SPEC="code-puppy==0.0.720"
        CONSTRAINTS_RELATIVE_PATH="constraints/android-0720.txt"
        CONSTRAINTS_SHA256="ed134a1a15af7a0f79872661fc456c4e0006496471b4c8b23dba5747c9a7a287"
        ;;
    *) fail "Unknown engine profile: $ENGINE_PROFILE" ;;
esac

if [ "$DRY_RUN" -ne 1 ]; then
    command -v pkg >/dev/null 2>&1 || fail \
        "Run this inside Termux from F-Droid or GitHub—not a generic Android shell."
    case "${PREFIX:-}" in
        *com.termux*) ;;
        *) fail "This installer supports Android Termux only (PREFIX=$PREFIX)." ;;
    esac
fi

say "Installing the Android build tools Code Puppy needs"
run pkg install -y python rust clang git curl ripgrep libjpeg-turbo
if [ "$INSTALL_OPTIONAL" -eq 1 ]; then
    say "Installing optional phone-control helpers"
    run pkg install -y android-tools termux-api
fi

export PATH="$HOME/.local/bin:$PATH"

say "Preparing the DroidPuppy source and engine profile"
if [ "$DRY_RUN" -eq 1 ]; then
    source_dir="\$WORK_DIR/DroidPuppy-$DROIDPUPPY_REF"
    printf '  Download %s/archive/%s.tar.gz\n' "$DROIDPUPPY_REPO" "$DROIDPUPPY_REF"
    printf '  Verify %s with SHA-256 %s\n' \
        "$CONSTRAINTS_RELATIVE_PATH" "$CONSTRAINTS_SHA256"
else
    work_dir="$(mktemp -d)"
    trap 'rm -rf "$work_dir"' EXIT HUP INT TERM
    archive="$work_dir/droidpuppy.tar.gz"
    run curl --fail --location --silent --show-error \
        "$DROIDPUPPY_REPO/archive/$DROIDPUPPY_REF.tar.gz" -o "$archive"
    run tar -xzf "$archive" -C "$work_dir"
    source_dir="$(find "$work_dir" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
    [ -n "$source_dir" ] || fail "The DroidPuppy archive was empty."
fi

constraints_file="$source_dir/$CONSTRAINTS_RELATIVE_PATH"
if [ "$DRY_RUN" -ne 1 ]; then
    [ -f "$constraints_file" ] || fail \
        "Engine profile constraints are missing: $CONSTRAINTS_RELATIVE_PATH"
    actual_hash="$(sha256sum "$constraints_file")"
    actual_hash="${actual_hash%% *}"
    [ "$actual_hash" = "$CONSTRAINTS_SHA256" ] || fail \
        "Engine profile checksum mismatch; refusing an unverified install."
fi

if [ "$INSTALL_ENGINE" -eq 1 ]; then
    if command -v code-puppy >/dev/null 2>&1; then
        say "Code Puppy is already installed; leaving its version unchanged"
    else
        say "Installing Code Puppy with engine profile $ENGINE_PROFILE"
        run python -m pip install --user pipx
        run python -m pipx ensurepath
        run python -m pipx install --backend pip \
            --pip-args "--constraint $constraints_file" "$ENGINE_SPEC"
    fi
fi

say "Installing the DroidPuppy capability overlay"
if [ "$DRY_RUN" -eq 1 ]; then
    printf '  Install plugins into %s/.code_puppy/plugins\n' "$HOME"
else
    run python "$source_dir/scripts/install_overlay.py" --overwrite
fi

say "Verifying the installation"
if [ "$DRY_RUN" -eq 1 ]; then
    printf '  Check code-puppy and installed DroidPuppy plugins\n'
else
    command -v code-puppy >/dev/null 2>&1 || fail \
        "code-puppy is not on PATH. Restart Termux, then run code-puppy -i."
    plugin_count="$(find "$HOME/.code_puppy/plugins" -mindepth 2 -maxdepth 2 \
        -name register_callbacks.py | wc -l | tr -d ' ')"
    [ "$plugin_count" -gt 0 ] || fail "No DroidPuppy plugins were installed."
    printf '  code-puppy: %s\n' "$(command -v code-puppy)"
    printf '  plugins:    %s\n' "$plugin_count"
fi

cat <<'EOF'

Installation complete.

Start your phone agent with:

  code-puppy -i

The first install can take 10–20 minutes while Android compiles native Python
packages. Browser control additionally requires Android Developer options and
Wireless debugging; ordinary coding and phone handoff tools do not.
EOF
