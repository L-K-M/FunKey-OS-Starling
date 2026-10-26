#!/usr/bin/env python3
"""Write Third-Party-Notices.txt for a Starling filesystem or the SDK.

Buildroot's legal-info lists every package an output tree builds, with its
license, and copies the license files each package names. This turns that
into one plain-text file and adds what legal-info cannot know, all recorded
in notices.ini next to this script:

- license texts for packages whose Buildroot metadata names none (a custom
  kernel tarball, the prebuilt toolchain, gcc);
- the emulator cores picoarch clones and builds inside its own build step;
- the fonts and sounds in the rootfs overlay, including inside its zips.

It fails, listing every problem, when a bundled component has no license
text, unless notices.ini records it as a gap with a reason. A gap is printed
in the output as such rather than left out.

Python 3.8+, standard library only: it runs in Buildroot's post-build step
and in CI.
"""

import argparse
import configparser
import csv
import fnmatch
import hashlib
import os
import subprocess
import sys
import textwrap
import zipfile

RULE = "-" * 80
BANNER = "=" * 80

# File names that hold license texts in a core's tree. Matched in lower case
# against the base name; files with these extensions are code or generated
# copies, not license texts.
CORE_LICENSE_NAMES = ("copying", "copying.*", "copyright", "license",
                      "license.*", "license-*", "licence", "licence.*",
                      "notice", "notice.*")
CORE_SKIP_SUFFIXES = (".c", ".h", ".cpp", ".hpp", ".py", ".pl", ".sh",
                      ".rtf", ".html", ".htm", ".in", ".am", ".xml", ".o",
                      ".d", ".a", ".so")


class Notices:
    def __init__(self, config_path):
        self.config_dir = os.path.dirname(os.path.abspath(config_path))
        self.config = configparser.ConfigParser(interpolation=None)
        self.config.optionxform = str
        with open(config_path, encoding="utf-8") as f:
            self.config.read_file(f)
        self.errors = []
        self.gaps = []

    def error(self, message):
        self.errors.append(message)

    def sections(self, kind):
        """Return {name: section} for every '[<kind> <name>]' section."""
        prefix = kind + " "
        return {s[len(prefix):]: self.config[s]
                for s in self.config.sections() if s.startswith(prefix)}

    def vendored(self, section, what):
        """Read the 'texts' a section names, relative to notices.ini."""
        texts = []
        for rel in section.get("texts", "").split():
            path = os.path.normpath(os.path.join(self.config_dir, rel))
            text = read_text(path)
            if text is None:
                self.error("%s: vendored text %s is missing" % (what, rel))
                continue
            texts.append((os.path.basename(rel), text))
        return texts


def read_text(path):
    """Return a file's text as UTF-8 with LF line ends, or None if absent."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        # Older license files are Latin-1; the output is UTF-8 throughout.
        text = data.decode("latin-1")
    return text.replace("\r\n", "\n").replace("\r", "\n").strip("\n") + "\n"


def unknown(gap):
    """The License field of a component notices.ini records as a gap."""
    return "unknown (%s)" % gap.rstrip(".")


def shown(path):
    """An overlay path as it appears on the device."""
    archive, _, member = path.partition("!")
    return "%s in /%s" % (member, archive) if member else "/" + archive


def words(section, key):
    return section.get(key, "").split()


def lines(section, key):
    return [l.strip() for l in section.get(key, "").splitlines() if l.strip()]


# ------------------------------------------------------------------ packages

def read_manifest(path):
    if not os.path.isfile(path):
        return None
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        rows = list(csv.reader(f))
    return [r for r in rows if r and r[0] != "PACKAGE"]


def packages(notices, legal_info, build_dir, host_packages):
    """Entries for the packages in a legal-info directory."""
    rows = []
    target = read_manifest(os.path.join(legal_info, "manifest.csv"))
    host = read_manifest(os.path.join(legal_info, "host-manifest.csv"))
    if target is None or host is None:
        notices.error("%s has no manifest.csv or host-manifest.csv; "
                      "run 'make legal-info' for this tree first" % legal_info)
        return []
    rows += [("target", r) for r in target]
    # Buildroot itself is a row of the host manifest. Its skeleton, init
    # scripts and SDK helpers end up in every artifact, so it is always in.
    rows += [("host", r) for r in host if host_packages or r[0] == "buildroot"]

    overrides = notices.sections("package")
    entries = []
    for kind, row in rows:
        raw, version, license_, files, archive, site = (row + [""] * 6)[:6]
        if raw == "buildroot":
            name, licdir, pkgdir = raw, "buildroot", None
        else:
            name = raw if kind == "target" else "host-" + raw
            base = raw + "-" + version if version else raw
            licdir = base
            pkgdir = name + "-" + version if version else name
        what = "package %s" % name
        over = overrides.get(name, {})

        texts = []
        licroot = os.path.join(legal_info, "licenses" if kind == "target"
                               else "host-licenses", licdir)
        for rel in files.split():
            text = read_text(os.path.join(licroot, rel))
            if text is None:
                notices.error("%s: legal-info did not save %s" % (what, rel))
                continue
            texts.append((rel, text))
        # License files Buildroot does not name, read from the package's
        # extracted source.
        for rel in words(over, "files"):
            text = read_text(os.path.join(build_dir, pkgdir or "", rel))
            if text is None:
                notices.error("%s: %s is not in %s/%s"
                              % (what, rel, build_dir, pkgdir))
                continue
            texts.append((rel, text))
        texts += notices.vendored(over, what) if over else []

        license_ = over.get("license", license_).strip()
        gap = over.get("gap", "").strip()
        if not gap:
            if not license_ or license_.lower() == "unknown":
                notices.error("%s: no license; set <PKG>_LICENSE or add "
                              "[package %s] to notices.ini" % (what, name))
            if not texts:
                notices.error("%s: no license text; set <PKG>_LICENSE_FILES "
                              "or add [package %s] to notices.ini"
                              % (what, name))

        source = lines(over, "source")
        site = site.replace('"', "")
        if not source and site and site != "not saved":
            source = ["%s (%s)" % (site, archive) if archive else site]
        entries.append({
            "title": "%s %s" % (over.get("name", name), version)
                     if version else over.get("name", name),
            "fields": [("License", unknown(gap) if gap else license_)]
                      + [("Source", s) for s in source],
            "texts": texts,
            "same": (raw, version, repr(texts)),
        })
        if gap:
            notices.gaps.append("%s: %s" % (what, gap))

    # The SDK builds some packages for both the host and the target from
    # the same source; list those once, under the target name.
    unique = {}
    for e in sorted(entries, key=lambda e: e["title"].startswith("host-")):
        unique.setdefault(e.pop("same"), e)
    return sorted(unique.values(), key=lambda e: e["title"].lower())


# --------------------------------------------------------------------- cores

def core_license_files(core_dir):
    found = []
    for root, dirs, files in os.walk(core_dir):
        dirs[:] = sorted(d for d in dirs if d != ".git")
        for f in sorted(files):
            low = f.lower()
            if low.endswith(CORE_SKIP_SUFFIXES):
                continue
            if any(fnmatch.fnmatchcase(low, p) for p in CORE_LICENSE_NAMES):
                found.append(os.path.relpath(os.path.join(root, f), core_dir))
    return found


def git_commit(path):
    # Only the core's own clone: from anywhere else under the build tree, git
    # would find Starling's repository and report its commit instead.
    if not os.path.exists(os.path.join(path, ".git")):
        return None
    try:
        out = subprocess.run(["git", "-C", path, "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip() or None


def cores(notices, target_dir, cores_dir):
    """Entries for the libretro cores installed in /usr/games."""
    configured = notices.sections("core")
    by_library = {sec.get("library", name + "_libretro.so"): name
                  for name, sec in configured.items()}
    games = os.path.join(target_dir, "usr", "games")
    installed = sorted(f for f in os.listdir(games)
                       if f.endswith("_libretro.so")) \
        if os.path.isdir(games) else []

    entries = []
    for library in installed:
        name = by_library.pop(library, None)
        if name is None:
            notices.error("core /usr/games/%s: no [core ...] section in "
                          "notices.ini" % library)
            continue
        sec = configured[name]
        what = "core %s" % name
        core_dir = os.path.join(cores_dir, name)
        if not os.path.isdir(core_dir):
            notices.error("%s: %s does not exist" % (what, core_dir))
            continue

        texts = []
        rels = core_license_files(core_dir)
        rels += [r for r in words(sec, "files") if r not in rels]
        for rel in rels:
            text = read_text(os.path.join(core_dir, rel))
            if text is None:
                notices.error("%s: %s is missing" % (what, rel))
                continue
            texts.append((name + "/" + rel, text))
        if not texts:
            notices.error("%s: no license file found in %s" % (what, core_dir))
        if not sec.get("license", "").strip():
            notices.error("%s: no license in notices.ini" % what)

        commit = git_commit(core_dir)
        source = sec.get("source", "").strip()
        fields = [("License", sec.get("license", "").strip()),
                  ("Source", "%s (commit %s)" % (source, commit)
                   if commit else source),
                  ("Installed as", "/usr/games/" + library)]
        if os.path.isdir(os.path.join(cores_dir, "patches", name)):
            fields.append(("Modified", "patched by picoarch, see its "
                                       "patches/%s/" % name))
        entries.append({"title": name, "fields": fields, "texts": texts})

    for library, name in sorted(by_library.items()):
        notices.error("core %s: in notices.ini but /usr/games/%s is not "
                      "installed" % (name, library))
    return entries


# -------------------------------------------------------------------- assets

def overlay_files(overlay, patterns):
    """{path: sha256 or None} for every overlay file and every 'zip!member'
    of its zips. Only files whose names match patterns, the ones that must
    be attributed, are hashed."""
    found = {}

    def covered(path):
        base = path.rsplit("/", 1)[-1].lower()
        return any(fnmatch.fnmatchcase(base, p.lower()) for p in patterns)

    for root, dirs, files in os.walk(overlay):
        dirs.sort()
        for f in sorted(files):
            path = os.path.join(root, f)
            rel = os.path.relpath(path, overlay).replace(os.sep, "/")
            found[rel] = None
            if covered(rel):
                with open(path, "rb") as fh:
                    found[rel] = hashlib.sha256(fh.read()).hexdigest()
            if f.lower().endswith(".zip"):
                with zipfile.ZipFile(path) as z:
                    for m in z.namelist():
                        if m.endswith("/"):
                            continue
                        found["%s!%s" % (rel, m)] = \
                            hashlib.sha256(z.read(m)).hexdigest() \
                            if covered(m) else None
    return found


def assets(notices, overlay):
    """Entries for the overlay files notices.ini attributes.

    A section claims files by path ('paths', globs relative to the overlay,
    'archive.zip!member' inside a zip) or by content ('sha256'), for files
    such as theme sounds that ship under the same name with different
    contents.
    """
    patterns = words(notices.config["overlay"], "cover") \
        if notices.config.has_section("overlay") else []
    files = overlay_files(overlay, patterns)
    configured = notices.sections("asset")

    def claims(sec, path):
        return (files[path] is not None
                and files[path] in words(sec, "sha256")) or \
            any(fnmatch.fnmatchcase(path, p) for p in lines(sec, "paths"))

    # Every covered file (a hash is set) needs exactly one owner; other
    # files are listed under the section that names them, if any.
    matched = {name: [] for name in configured}
    for path in sorted(files):
        owners = [name for name, sec in configured.items()
                  if claims(sec, path)]
        if files[path] is None and len(owners) < 2:
            if owners:
                matched[owners[0]].append(path)
            continue
        if len(owners) != 1:
            notices.error("asset %s: attributed by %s in notices.ini"
                          % (path, " and ".join("[asset %s]" % o
                                                for o in owners)
                             or "no [asset ...] section"))
            continue
        matched[owners[0]].append(path)

    entries = []
    for name, sec in configured.items():
        what = "asset %s" % name
        for pattern in lines(sec, "paths"):
            if not any(fnmatch.fnmatchcase(p, pattern) for p in files):
                notices.error("%s: '%s' matches no file in the overlay"
                              % (what, pattern))
        for digest in words(sec, "sha256"):
            if digest not in files.values():
                notices.error("%s: no file in the overlay has sha256 %s"
                              % (what, digest))
        texts = notices.vendored(sec, what)
        gap = sec.get("gap", "").strip()
        if gap:
            notices.gaps.append("%s: %s" % (what, gap))
        else:
            if not sec.get("license", "").strip():
                notices.error("%s: no license in notices.ini" % what)
            if not texts and not sec.get("copyright", "").strip():
                notices.error("%s: neither a copyright notice nor a license "
                              "text in notices.ini" % what)
        fields = [("License", unknown(gap) if gap
                   else sec.get("license", "").strip())]
        fields += [("Copyright", c) for c in lines(sec, "copyright")]
        fields += [("Source", s) for s in lines(sec, "source")]
        fields += [("Note", n) for n in lines(sec, "note")]
        fields += [("File", shown(p)) for p in sorted(matched[name])]
        entries.append({"title": name, "fields": fields, "texts": texts})
    return sorted(entries, key=lambda e: e["title"].lower())


# -------------------------------------------------------------------- output

def render_entry(e):
    out = [RULE, e["title"]]
    out += ["%s: %s" % (k, v) for k, v in e["fields"] if v]
    for label, text in e["texts"]:
        out += ["", "--- %s ---" % label, text.rstrip("\n")]
    out.append("")
    return out


def render(notices, stamp, title, sections):
    own = notices.config["own"]
    name = own.get("name")
    source = own.get("source", "").replace("{stamp}", stamp)
    heading = "Third-party notices: %s, %s" % (stamp, title)
    intro = ("This %s contains components that keep their own licenses. "
             "Each entry below names one, with its license, its source and "
             "its verbatim license texts. licenses/notices.py writes this "
             "file at build time from Buildroot's legal-info and "
             "licenses/notices.ini in %s's source." % (title, name))
    out = [heading, "=" * len(heading), "", textwrap.fill(intro, 72), "",
           "%s's own code: %s" % (name, own.get("license")),
           "Source code: %s" % source,
           ""]
    out += render_entry({"title": stamp,
                         "fields": [("License", own.get("license")),
                                    ("Source code", source)],
                         "texts": notices.vendored(own, "own")})
    for section_title, _, entries in sections:
        if not entries:
            continue
        out += ["", BANNER, "%s (%d)" % (section_title, len(entries)),
                BANNER, ""]
        for e in entries:
            out += render_entry(e)
    return "\n".join(out).rstrip("\n") + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--config", required=True, help="notices.ini")
    ap.add_argument("--stamp", required=True,
                    help="release name, e.g. Starling-3.1.3")
    ap.add_argument("--title", required=True,
                    help="what the file describes, e.g. 'FunKey root "
                         "filesystem'")
    ap.add_argument("--legal-info", help="a Buildroot legal-info directory")
    ap.add_argument("--host-packages", action="store_true",
                    help="include host packages (the SDK ships them)")
    ap.add_argument("--build-dir", help="the Buildroot build directory")
    ap.add_argument("--overlay", help="rootfs overlay whose assets to cover")
    ap.add_argument("--target-dir", help="target directory with the cores")
    ap.add_argument("--cores-dir", help="picoarch's build directory")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    if args.legal_info and not args.build_dir:
        ap.error("--legal-info needs --build-dir")
    if bool(args.target_dir) != bool(args.cores_dir):
        ap.error("--target-dir and --cores-dir go together")

    notices = Notices(args.config)
    sections = []
    if args.legal_info:
        sections.append(("Packages built by Buildroot", "packages",
                         packages(notices, args.legal_info, args.build_dir,
                                  args.host_packages)))
    if args.cores_dir:
        sections.append(("Emulator cores built by picoarch", "cores",
                         cores(notices, args.target_dir, args.cores_dir)))
    if args.overlay:
        sections.append(("Fonts, sounds and other files", "assets",
                         assets(notices, args.overlay)))

    for gap in notices.gaps:
        print("notices: gap: %s" % gap)
    if notices.errors:
        for e in notices.errors:
            print("notices: error: %s" % e, file=sys.stderr)
        print("notices: %d error(s); %s not written"
              % (len(notices.errors), args.output), file=sys.stderr)
        return 1

    text = render(notices, args.stamp, args.title, sections)
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    tmp = args.output + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(tmp, 0o644)
    os.replace(tmp, args.output)
    counts = ", ".join("%d %s" % (len(e), short) for _, short, e in sections)
    print("notices: %s -> %s" % (counts or "nothing", args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
