#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Truncated-source tests for GALasm.

Takes the sources of a few successful conformance cases (SOURCES), or of
all of them with --all, and assembles each prefix of each source, from
the empty file up to the whole source:

* a prefix that ends before the end of the DESCRIPTION keyword must be
  rejected without writing any output file;
* a prefix that ends after it must give the same files as the whole
  source;
* the assembler must never be killed by a signal.

Run against a build with sanitizers that abort on error (see README.md),
this also catches any read beyond the end of the input.

Usage:
  test_truncated_sources.py [--galasm PATH] [--all] [-k SUBSTRING] [-v]
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CASES_DIR = os.path.join(HERE, "cases")
DEFAULT_GALASM = os.path.join(HERE, os.pardir, "src", "galasm")

OUTPUT_EXTS = ("jed", "fus", "pin", "chp")
KEYWORD = b"DESCRIPTION"

# Between them, the prefixes of these sources end inside every part of the
# source language, for every type of GAL.  Where the input ends matters,
# not how many sources there are: these find every read beyond the end of
# the input that all the successful cases together found.
SOURCES = [
    "16v8_enable_declared_negated",     # suffixes, a negated pin and target
    "16v8_layout",                      # comments, blank lines, tabs
    "20v8_complex_mode",                # GAL20V8
    "20ra10_mixed",                     # GAL20RA10, .CLK, .ARST, .APRST
    "22v10_ar_sp_vcc",                  # GAL22V10, AR and SP
    "16v8_crlf_source",                 # CR LF line endings
]


class SourceFailure(Exception):
    pass


def sources(names, pattern):
    """Yield (case name, source) for each distinct successful case source
    among names, or among all cases if names is None."""
    seen = set()
    for name in names or sorted(os.listdir(CASES_DIR)):
        path = os.path.join(CASES_DIR, name)
        if pattern not in name:
            continue
        if not os.path.isfile(os.path.join(path, "input.pld")):
            if names is None:
                continue
            raise SourceFailure("%s is not a case with an input.pld" % name)
        with open(os.path.join(path, "case.json"), encoding="utf-8") as f:
            if json.load(f)["expect"] != "success":
                if names is None:
                    continue
                raise SourceFailure("%s is not a successful case" % name)
        with open(os.path.join(path, "input.pld"), "rb") as f:
            source = f.read()
        if source not in seen:
            seen.add(source)
            yield name, source


def assemble(galasm, workdir, source):
    """Assemble source as input.pld in workdir; return (status, console, outputs)."""
    for entry in os.listdir(workdir):
        os.remove(os.path.join(workdir, entry))
    with open(os.path.join(workdir, "input.pld"), "wb") as f:
        f.write(source)
    proc = subprocess.run([galasm, "input.pld"], cwd=workdir,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
    outputs = {}
    for ext in OUTPUT_EXTS:
        p = os.path.join(workdir, "input." + ext)
        if os.path.exists(p):
            with open(p, "rb") as f:
                outputs[ext] = f.read()
    return proc.returncode, proc.stdout.decode("latin-1"), outputs


def check_source(galasm, workdir, source):
    if source.count(KEYWORD) != 1:
        raise SourceFailure("source must contain %s exactly once" % KEYWORD.decode())
    keyword_end = source.index(KEYWORD) + len(KEYWORD)

    status, console, whole = assemble(galasm, workdir, source)
    if status != 0:
        raise SourceFailure("whole source: exit status %d\n%s" % (status, console))

    for length in range(len(source)):
        status, console, outputs = assemble(galasm, workdir, source[:length])
        where = "first %d bytes" % length
        if status < 0:
            raise SourceFailure("%s: killed by signal %d\n%s" % (where, -status, console))
        if length < keyword_end:
            if status == 0:
                raise SourceFailure("%s: accepted, expected failure\n%s" % (where, console))
            if outputs:
                raise SourceFailure("%s: rejected but wrote %s" % (where, sorted(outputs)))
        elif status != 0 or outputs != whole:
            raise SourceFailure("%s: exit status %d, files differ from the whole source's\n%s"
                                % (where, status, console))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--galasm", default=DEFAULT_GALASM,
                    help="assembler executable to test (default: src/galasm)")
    ap.add_argument("--all", action="store_true",
                    help="use the sources of all successful cases, not just SOURCES")
    ap.add_argument("-k", dest="pattern", default="",
                    help="only use the sources of cases whose name contains this text")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="list passing sources too")
    opts = ap.parse_args(argv)

    galasm = os.path.abspath(opts.galasm)
    if not os.path.exists(galasm) and os.path.exists(galasm + ".exe"):
        galasm += ".exe"
    if not os.path.exists(galasm):
        print("assembler not found: %s" % galasm)
        return 2

    try:
        chosen = list(sources(None if opts.all else SOURCES, opts.pattern))
    except SourceFailure as e:
        print(e)
        return 2

    passed = failures = 0
    workdir = tempfile.mkdtemp(prefix="galasm-truncated-")
    try:
        for name, source in chosen:
            try:
                check_source(galasm, workdir, source)
                passed += 1
                if opts.verbose:
                    print("PASS %s" % name)
            except SourceFailure as e:
                failures += 1
                print("FAIL %s: %s" % (name, e))
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    print("%d passed, %d failed" % (passed, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
