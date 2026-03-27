#!/usr/bin/env python3

import os
import subprocess
import socket
import sys
import re

HOME = os.path.expanduser("~")
fetch_origin = True
fetch_upstream = True


def run(cmd, cwd=None):
    """Run a shell command, return (stdout, returncode)."""
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.returncode


def clear_dirname(d):
    s = d.replace(f"{HOME}/", "-- -- ")
    s = s.replace("src/", " ")
    s = s.replace("/ceph", " -- -- -- ")
    return s[:18]


def short_st(cwd):
    uptodate = "xxxxxxx"
    _, rc = run(f"git show-branch origin/$(git branch --show-current)", cwd=cwd)
    if rc != 0:
        uptodate = "local-only"
    cst, _ = run("git status -uno --ignore-submodules=all", cwd=cwd)
    if "up to date" in cst:
        uptodate = "up-to-date"
    if "ahead" in cst:
        uptodate = "ahead     "
    if "behind" in cst:
        uptodate = "behind    "
    if "detached" in cst:
        uptodate = "detached  "
    if "diverged" in cst:
        uptodate = "diverged  "
    return uptodate


def refs_diff(cwd):
    origin_url, _ = run("git ls-remote --get-url origin", cwd=cwd)
    upstream_url, _ = run("git ls-remote --get-url upstream", cwd=cwd)
    if "ronen" in origin_url and "ceph" in upstream_url:
        if fetch_upstream:
            run("git fetch upstream main", cwd=cwd)
        df_m_om, _ = run("git rev-list --count main..origin/main", cwd=cwd)
        df_om_um, _ = run("git rev-list --count origin/main..upstream/main", cwd=cwd)
        df_m_om = df_m_om.strip()
        df_om_um = df_om_um.strip()
        s = f"[./o: {df_m_om} o-ms/u-ms:{df_om_um}]"
        return f"{s:<26.26s}"
    else:
        return f"{'{{xx-rt-xx}}':<30.30s}"


def modified_files(cwd):
    origin_url, _ = run("git ls-remote --get-url origin", cwd=cwd)
    if "ronen" in origin_url:
        porcelain, _ = run("git status --ignore-submodules --porcelain", cwd=cwd)
        lines = porcelain.splitlines() if porcelain else []
        n_modified = sum(1 for l in lines if re.match(r"^ [MDR]", l))
        n_added = sum(1 for l in lines if re.match(r"^ A", l))
        s = f"<M:{n_modified} - A:{n_added}>"
        return f"{s:<16.16s}"
    else:
        return f"{'<.....>':<16.16s}"


def old_branches(cwd):
    reflog, _ = run("git log --date=relative --pretty=oneline -g", cwd=cwd)
    if not reflog:
        return
    lines = reflog.splitlines()
    seen = {}
    br_count = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        if "moving from main" in line:
            i += 1
            continue
        m = re.search(r"moving from (\S+) to", line)
        if m:
            branch = m.group(1)
            if branch in seen:
                i += 1
                continue
            dm = re.search(r"\{([^}]*)\}", line)
            date_from = dm.group(0) if dm else ""
            seen[branch] = date_from
            if br_count > 8:
                break
            br_count += 1
            short_hash = line[:8]
            print(f"-\t{short_hash:8.8s} {date_from:15.15s} {branch}")
        i += 1


def build_dir_info(cwd):
    build_path = os.path.join(cwd, "build")
    if os.path.exists(build_path):
        stat = os.stat(build_path)
        from datetime import datetime
        mtime = datetime.fromtimestamp(stat.st_mtime)
        date_str = mtime.strftime("%d-%b %H:%M")
        is_link = " -> " + os.readlink(build_path) if os.path.islink(build_path) else ""
        print(f"\n\t{date_str}  build{is_link}", end="")

        cc_json = os.path.join(build_path, "compile_commands.json")
        if os.path.exists(cc_json):
            with open(cc_json, "r", errors="replace") as f:
                content = f.read(200000)
            comp = "Clang" if "clang" in content.lower() else "G++"
            crimson = "Crimson" if "SEASTAR" in content else "Classic"
            print(f" {comp}  {crimson}  \t", end="")
        else:
            print(" [[no script]] ", end="")

        ninja_path = os.path.join(build_path, "build.ninja")
        if os.path.exists(ninja_path):
            nstat = os.stat(ninja_path)
            nmtime = datetime.fromtimestamp(nstat.st_mtime)
            ndate_str = nmtime.strftime("%d-%b %H:%M")
            print(f" {{ Ninja: {ndate_str} build.ninja }}")
        else:
            print()
    else:
        print(f"\n\t-- no build")


def oneceph(d):
    print()

    if fetch_origin:
        run("git fetch", cwd=d)

    comt, _ = run('git --no-pager log -1 --format="%h %s"', cwd=d)
    branch, _ = run("git rev-parse --abbrev-ref HEAD", cwd=d)
    dirt = clear_dirname(d)

    uptodate = short_st(d)

    print(f"{dirt} -- -- {uptodate} --  {branch}      {refs_diff(d)}")
    print(f"\t{comt}  {modified_files(d)}")

    origin_url, _ = run("git ls-remote --get-url origin", cwd=d)
    if "ronen" not in origin_url:
        print("  ******* irregular origin ***********")

    build_dir_info(d)
    print()
    old_branches(d)


def main():
    global fetch_upstream, fetch_origin

    hostname = socket.gethostname()
    if hostname == "rflap":
        names = "fx7 master rf_sc fix_4 cln_may scrub0 scrub1 s2 scr5 scr6".split()
    elif hostname == "rflap2":
        names = "m1 m2 m3 m4 m5 m6 down".split()
    else:
        names = "k1 k2 k3 k4 k5 k6 k7 k8 k9".split()

    dirs = []
    for u in names:
        p = os.path.join(HOME, "src", u, "ceph")
        if hostname in ("rflap", "rflap2") or os.path.exists(p):
            dirs.append(p)

    if len(sys.argv) > 1:
        fetch_upstream = False
    if len(sys.argv) > 2:
        fetch_origin = False

    for d in dirs:
        oneceph(d)


if __name__ == "__main__":
    main()
