#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests for src/Makefile.

Each test runs make against a fresh copy of src/ in a temporary directory,
so the real build tree is never touched.

Usage:
  test_makefile.py [--make MAKE]
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(HERE, os.pardir, "src")

MAKE = "make"


def run_make(workdir, *args):
    proc = subprocess.run([MAKE, *args], cwd=workdir, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, universal_newlines=True)
    return proc.returncode, proc.stdout


def dry_run_lines(workdir, *args):
    status, out = run_make(workdir, "-n", "-B", *args)
    if status != 0:
        raise AssertionError("make -n failed:\n" + out)
    return [line.strip() for line in out.splitlines() if line.strip()]


def compile_lines(lines):
    return [line for line in lines if " -c " in line or line.endswith(" -c")]


def link_lines(lines):
    return [line for line in lines if "-o galasm" in line]


def test_link_uses_cc(workdir):
    links = link_lines(dry_run_lines(workdir, "CC=fakecc"))
    assert links, "no link command found"
    for line in links:
        assert line.startswith("fakecc "), "link does not use $(CC): " + line


def test_clean_without_objects_is_quiet(workdir):
    status, out = run_make(workdir, "clean")
    assert status == 0, "make clean failed:\n" + out
    assert "ignored" not in out, "make clean reported errors:\n" + out


def test_default_build_has_no_arch_flags(workdir):
    for line in dry_run_lines(workdir):
        assert "-arch" not in line, "unexpected -arch flag: " + line


def test_archs_adds_arch_flags(workdir):
    lines = dry_run_lines(workdir, "ARCHS=x86_64 arm64")
    commands = compile_lines(lines) + link_lines(lines)
    assert len(compile_lines(lines)) == 4, "expected 4 compiles:\n" + "\n".join(lines)
    assert link_lines(lines), "no link command found"
    for line in commands:
        assert "-arch x86_64 -arch arm64" in line, "missing -arch flags: " + line


def test_archs_survives_cflags_override(workdir):
    lines = dry_run_lines(workdir, "ARCHS=arm64", "CFLAGS=-O0")
    for line in compile_lines(lines) + link_lines(lines):
        assert "-arch arm64" in line, "missing -arch flag: " + line


def test_universal_binary_on_macos(workdir):
    if platform.system() != "Darwin":
        return "skipped (not macOS)"
    status, out = run_make(workdir, "ARCHS=x86_64 arm64")
    assert status == 0, "universal build failed:\n" + out
    archs = subprocess.run(["lipo", "-archs", "galasm"], cwd=workdir,
                           stdout=subprocess.PIPE, universal_newlines=True,
                           check=True).stdout.split()
    assert sorted(archs) == ["arm64", "x86_64"], "lipo reports %s" % archs


TESTS = [
    test_link_uses_cc,
    test_clean_without_objects_is_quiet,
    test_default_build_has_no_arch_flags,
    test_archs_adds_arch_flags,
    test_archs_survives_cflags_override,
    test_universal_binary_on_macos,
]


def fresh_src(tmp):
    workdir = os.path.join(tmp, "src")
    shutil.copytree(SRC_DIR, workdir, ignore=shutil.ignore_patterns(
        "*.o", "*.a", "galasm", "galasm.exe"))
    return workdir


def main():
    global MAKE
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--make", default=MAKE, help="make program to test with")
    MAKE = parser.parse_args().make

    failures = 0
    for test in TESTS:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                note = test(fresh_src(tmp))
                print("PASS  %s%s" % (test.__name__, " " + note if note else ""))
            except AssertionError as e:
                failures += 1
                print("FAIL  %s\n      %s" % (test.__name__,
                                            str(e).replace("\n", "\n      ")))
    print("%d passed, %d failed" % (len(TESTS) - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
