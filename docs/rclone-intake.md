# rclone dependency intake

**Component:** [rclone](https://github.com/rclone/rclone), external CLI. **Reviewed:** 2026-11-15, v1.76.0
(a research pass during the 0.5 build; the pins below were cross-checked there against three sources
and must be re-verified with the pin-bump commands before rclone is first installed).
**Verdict:** accept with conditions (section 6).

Collab Kit runs the binary as a subprocess for Google Drive, using only `lsjson`, `cat`, `rcat`, `copyto`,
`moveto` and `mkdir` (`engine/collab_kit/store.py`, `RcloneStore`). Not linked, vendored or shipped.

## 1. License

MIT ([COPYING](https://github.com/rclone/rclone/blob/master/COPYING)), compatible with our MIT license;
invoking a binary creates no derivative work. The binary statically links about 270 Go modules, some
MPL-2.0. Downloading it from upstream in a workflow is not redistribution. Bundling it would require the
license, third-party notices and a source pointer. Rule: never redistribute.

## 2. Maintenance health

- Latest stable **v1.76.0, 2026-11-06**. 17 releases in 12 months: a minor release about every three
  months, patches roughly monthly. OpenSSF Scorecard "Maintained" 10/10.
- **Bus factor is low:** one maintainer authored most recent commits, owns every core path, and alone
  signs releases; he works on it full time, funded by sponsors and support contracts.

## 3. Known vulnerabilities

- The [repository advisories](https://github.com/rclone/rclone/security/advisories) list 51 entries, all
  patched at or before 1.76.0. None names the drive backend or the commands we use (the clusters are
  `serve`, `rcd`, `--auth-proxy`, local links and metadata, archives, and redirect leaks in other backends).
- **OSV lags rclone's own advisories** (many recent ones were not in OSV on 2026-11-15): watch the
  repository advisories too, not only OSV-Scanner.
- **Relevant:** [GHSA-w33h-3qgq-8mv8](https://github.com/rclone/rclone/security/advisories/GHSA-w33h-3qgq-8mv8)
  (`selfupdate` trusted a hash from the unsigned part of `SHA256SUMS`; fixed in 1.75.2) confirms the
  never-selfupdate rule; we hash only signature-verified bytes.
- **Expected false positive:** [GHSA-66qv-66mg-9h74](https://github.com/rclone/rclone/security/advisories/GHSA-66qv-66mg-9h74)
  (`serve sftp`) states its range as "<= 1.76.0" while listing 1.76.0 as patched. Unreachable for us.

## 4. Security posture

- [OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/rclone/rclone) about 4.8/10:
  strong on maintenance, security policy and workflows; zero on code review, pinned dependencies, token
  permissions, SAST, fuzzing and signed releases.
- **Signing:** `SHA256SUMS` is PGP clearsigned ([docs](https://rclone.org/release_signing/)), but with an
  old DSA-1024 key and SHA-1. The PGP signature is corroboration; **our committed SHA-256 pins are the
  trust anchor**.
- No provenance, attestations, SBOM, or reproducible-build claim upstream. We record rclone in our own
  SBOM notes (`go version -m rclone` or syft).
- **Disclosure:** private vulnerability reporting or email, 48-hour acknowledgement, fixes on the latest
  release only ([SECURITY.md](https://github.com/rclone/.github/blob/main/SECURITY.md)).

## 5. Google Drive behaviour (v1.76.0)

- **IDs:** `rcat`, or `copyto`/`moveto` from a local file, onto an existing path updates the file in place:
  the **ID is kept**. Drive-to-Drive `copyto`/`moveto` onto an existing destination replaces it with a new
  ID. Collab Kit writes with `rcat` (or `copyto` from a local temporary file) and copies only to new names.
- `rcat` input under 100 KiB is buffered and retried; larger input streams without retry. Collab Kit
  spools writes over 90 KiB (a margin below that limit) to a temporary file and uses `copyto`.
- **Duplicates:** Drive allows same-named siblings; single-file commands silently pick one. Collab Kit
  fails closed on a duplicate name in a listing.
- **Conversion:** `--drive-import-formats ""` prevents any config from converting uploads.
- **Google-native files** appear under an export name (`notes.docx`) with `Size` -1. Collab Kit treats a
  negative size as native: such a file is set aside, never read.
- **OAuth:** rclone's shared client ID stops working during 2026. Create your own OAuth client and
  **publish it to production** (Testing grants expire after a week, which would break unattended runs).
  `drive.file` sees only files created through that client, so a folder also written by Drive for desktop
  or the web needs the full `drive` scope. Service accounts need Workspace. The back end reads the
  remote's section of the rclone config file (no rclone command) and, when a Google Drive remote has
  no `client_id`, lists it as a problem at the top of the agenda's front page (`agenda/00-PRESSING.md`).
  To give an existing remote its own client, by hand, once (add `--config <file>` when the back end
  uses its own config file): `rclone config update <remote> client_id=... client_secret=...
  config_refresh_token=false`, then `rclone config reconnect <remote>:` (a browser sign-in).

## 6. Verdict: accept with conditions

1. Pin an exact version and per-platform SHA-256 (`engine/collab_kit/rclone.lock`). Every bump is a reviewed
   change that repeats this intake. The wrapper refuses any other `rclone version`.
2. Only the six commands, through one wrapper that passes argument lists (no shell) and strips inherited
   `RCLONE_*` variables. When `backend.toml` names an `account` (the template leaves it empty), every
   back end run checks the Google account the folder belongs to (an exact match, ignoring case) with
   `lsjson --metadata`: the owner of the folder's start file. (`config userinfo` does not
   work for Google Drive: found on the first real run, 2026-11-18.) Never
   `selfupdate`, `serve`, `rcd`, or any other `config` command in automation.
3. Fail closed on a duplicate name in a listing.
4. Where IDs matter, `rcat` or `copyto` from a local file; payloads over 90 KiB are spooled (a margin
   below rclone's 100 KiB buffer).
5. Our own published OAuth client and a dedicated config file (mode 0600). In GitHub Actions, write it from a
   secret into `$RUNNER_TEMP`, with `permissions: contents: read` and no third-party setup action.
6. Re-check the advisories on every rclone release.

**How a back end's pass uses them** (DESIGN-0.5 section 22): one `lsjson -R --hash --hash-type md5` of
the whole folder, then `cat` only for a file whose md5 the back end's own cache lacks; writes as
above. The minute check is one filtered `lsjson -R` of the inboxes.

**Always passed by the wrapper:** `--config <conf> --ask-password=false --drive-import-formats ""
--drive-use-trash=true`.

**v1.76.0 pins** (verify with the commands below before first use):

```
e72dc90b70f4947a7b72b61bde4a4fbba5777b2874fb448951ffdde67ebd0ab7  rclone-v1.76.0-osx-arm64.zip
4f5835733d52b818340f97b1fc0348a70461534d123363a183ca2b660219595a  rclone-v1.76.0-osx-amd64.zip
b00f00b3266c3764413afe599d3ec316f6f43b3e0ea8a0bc1d186d2133e46df7  rclone-v1.76.0-linux-amd64.zip
ee169016675e23a69d77240565133ff7dbc9b33d16fa8f7053d4af39f1eaeb78  rclone-v1.76.0-linux-arm64.zip
```

**Pin bump** (once per version):

```sh
V=v1.76.0
curl -fsSLO https://downloads.rclone.org/$V/SHA256SUMS
gpg --keyserver keyserver.ubuntu.com --recv-keys FBF737ECE9F8AB18604BD2AC93935E02FF3B54FA
gpg --verify SHA256SUMS && gpg -o SHA256SUMS.signed --decrypt SHA256SUMS
comm -13 <(gh api repos/rclone/rclone/releases/tags/$V --jq \
  '.assets[]|"\(.digest|ltrimstr("sha256:"))  \(.name)"' | sort) \
  <(sort SHA256SUMS.signed)   # must print nothing
```

**Install** (launchd, systemd, Actions with `shell: bash`):

```sh
V=v1.76.0 P=linux-amd64 SHA=<pin>
curl -fsSLo rclone.zip "https://downloads.rclone.org/$V/rclone-$V-$P.zip"
echo "$SHA  rclone.zip" | sha256sum -c -   # macOS: shasum -a 256 -c -
unzip -joq rclone.zip "rclone-$V-$P/rclone" -d "$BIN"
"$BIN/rclone" version | head -1            # must be: rclone v1.76.0
```
