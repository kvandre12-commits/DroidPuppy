# Android `0.0.720` Recovery Profile Validation

## Validated boundary

The `android-0720` profile was validated on Android ARM64 in Termux with Python
3.14.6. The proof used fresh, isolated `HOME`, `PIPX_HOME`, `PIPX_BIN_DIR`, and
`PIPX_MAN_DIR` directories. It did not read from or modify the preserved working
Code Puppy environment.

The profile installed:

- `pipx==1.18.16`
- `code-puppy==0.0.720`
- `code-puppy-core-plugins==0.0.4`
- the complete 88-package constraints closure
- all 39 DroidPuppy plugins

## Commands under test

The engine was installed with the same bounded operation used by `install.sh`:

```bash
python -m pipx install \
  --backend pip \
  --pip-args "--constraint constraints/android-0720.txt" \
  "code-puppy==0.0.720"
```

The pip backend is explicit because pipx's uv backend does not accept arbitrary
`--constraint` arguments.

## Passed checks

- Complete dependency resolution dry-run: passed
- Fresh pipx environment creation: passed
- Native Android dependency builds: passed
- `import code_puppy`: passed
- Engine version equals `0.0.720`: passed
- Core plugin version equals `0.0.4`: passed
- `pydantic-monty` absent: passed
- Tree-sitter base package absent: passed
- Tree-sitter language bundle absent: passed
- `code-puppy --help`: exit 0
- DroidPuppy overlay install: passed
- Installed DroidPuppy plugin count: 39
- Repository test suite: 65 passed

The fresh native build took roughly 13 minutes and temporarily used about 1.1
GiB. New-phone instructions therefore recommend power, an awake Termux session,
and at least 2 GiB of free storage.

## Honest remaining boundary

This proves the Python engine/profile/overlay path on Android and reproduces the
known-good runtime without Monty or the mandatory Tree-sitter grammar bundle.
It does not claim that every Android vendor image or workplace device policy is
identical. Termux must still be current, and managed-device policy may block
Termux, wireless debugging, app control, or other Android capabilities.
