#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Black-box conformance test runner for GALasm-compatible assemblers.

Each directory under tests/cases/ is one test case containing:

  case.json       what to run and what to expect (see tests/README.md)
  input.pld       the source file handed to the assembler
  expected.jed    expected outputs for successful cases
  expected.fus    (only the files the case expects to be produced)
  expected.pin
  expected.chp

The runner treats the assembler purely as a black box: it copies input.pld
into an empty temporary directory, runs the assembler there and inspects
the exit status, the console output and the files that were produced.

Usage:
  run_tests.py [--galasm PATH] [-k SUBSTRING] [--update] [-v]

--update writes any missing expected.* files of successful cases from the
output of the assembler under test (existing files are never overwritten;
delete a file to regenerate it).  Read what it writes before committing it.
"""

import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CASES_DIR = os.path.join(HERE, "cases")
DEFAULT_GALASM = os.path.join(HERE, os.pardir, "src", "galasm")

OUTPUT_EXTS = ("jed", "fus", "pin", "chp")
DEFAULT_OUTPUTS = list(OUTPUT_EXTS)

STX = 0x02
ETX = 0x03

# Header lines whose values identify the program that wrote the file.  An
# implementation may put its own name and version there.
PROGRAM_LINE = re.compile(rb"^(Used Program:|GAL-Assembler:)[^\r\n]*", re.M)


class CaseFailure(Exception):
    pass


def load_case(name):
    path = os.path.join(CASES_DIR, name)
    with open(os.path.join(path, "case.json"), encoding="utf-8") as f:
        case = json.load(f)
    case.setdefault("args", ["{input}"])
    case.setdefault("input", "input.pld")
    if case["expect"] == "success":
        case.setdefault("outputs", DEFAULT_OUTPUTS)
    else:
        case.setdefault("outputs", [])
    case["name"] = name
    case["path"] = path
    return case


def run_assembler(galasm, case, workdir):
    src = os.path.join(case["path"], "input.pld")
    if os.path.exists(src):
        dest = os.path.join(workdir, case["input"])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(src, dest)
    args = [a.replace("{input}", case["input"]) for a in case["args"]]
    proc = subprocess.run(
        [galasm] + args,
        cwd=workdir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
    )
    return proc.returncode, proc.stdout.decode("latin-1")


def produced_outputs(case, workdir):
    stem = os.path.splitext(case["input"])[0]
    found = {}
    for ext in OUTPUT_EXTS:
        p = os.path.join(workdir, stem + "." + ext)
        if os.path.exists(p):
            with open(p, "rb") as f:
                found[ext] = f.read()
    return found


def check_line_endings(data, crlf, label):
    if crlf:
        if re.search(rb"(?<!\r)\n", data):
            raise CaseFailure("%s: expected CR LF line endings throughout" % label)
    return data.replace(b"\r\n", b"\n")


def verify_transmission_checksum(raw, label):
    """Check the 4-hex-digit checksum that follows <ETX> against the bytes
    from <STX> to <ETX> inclusive, exactly as they appear in the file."""
    start = raw.find(bytes([STX]))
    end = raw.find(bytes([ETX]))
    if start < 0 and end < 0:
        return
    if start < 0 or end < start:
        raise CaseFailure("%s: <STX>/<ETX> missing or out of order" % label)
    m = re.match(rb"([0-9A-Fa-f]{4})(\r?\n)?$", raw[end + 1:])
    if not m:
        raise CaseFailure("%s: expected 4 hex digits and a newline after <ETX>" % label)
    want = sum(raw[start:end + 1]) % 0x10000
    got = int(m.group(1), 16)
    if want != got:
        raise CaseFailure(
            "%s: transmission checksum after <ETX> is %04x, bytes sum to %04x"
            % (label, got, want))


def normalize_jed(data):
    data = PROGRAM_LINE.sub(lambda m: m.group(1) + b" <program>", data)
    end = data.find(bytes([ETX]))
    if end >= 0:
        data = data[:end + 1] + b"<checksum>\n"
    return data


def compare(label, expected, actual):
    if expected == actual:
        return
    exp = expected.decode("latin-1").splitlines(keepends=True)
    act = actual.decode("latin-1").splitlines(keepends=True)
    diff = "".join(difflib.unified_diff(exp, act, "expected", "actual", n=2))
    lines = diff.splitlines()
    if len(lines) > 40:
        lines = lines[:40] + ["... (%d more diff lines)" % (len(lines) - 40)]
    raise CaseFailure("%s differs from expected:\n%s" % (label, "\n".join(lines)))


def check_case(galasm, case, update=False):
    workdir = tempfile.mkdtemp(prefix="galasm-test-")
    try:
        rc, console = run_assembler(galasm, case, workdir)
        outputs = produced_outputs(case, workdir)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    expect = case["expect"]
    if expect in ("success", "help"):
        if rc != 0:
            raise CaseFailure("exit status %d, expected 0\n%s" % (rc, console))
    else:
        if rc == 0:
            raise CaseFailure("exit status 0, expected failure\n%s" % console)

    if sorted(outputs) != sorted(case["outputs"]):
        raise CaseFailure("produced files %s, expected %s"
                          % (sorted(outputs) or "none", sorted(case["outputs"]) or "none"))

    if "error_line" in case:
        allowed = case["error_line"]
        if not isinstance(allowed, list):
            allowed = [allowed]
        m = re.search(r"Error in line (\d+):", console)
        if not m:
            raise CaseFailure("no 'Error in line N:' message\n%s" % console)
        if int(m.group(1)) not in allowed:
            raise CaseFailure("error reported in line %s, expected line %s\n%s"
                              % (m.group(1), " or ".join(map(str, allowed)), console))

    if "error_pin" in case:
        m = re.search(r"Error, pin (\d+):", console)
        if not m:
            raise CaseFailure("no 'Error, pin N:' message\n%s" % console)
        if int(m.group(1)) != case["error_pin"]:
            raise CaseFailure("error reported for pin %s, expected pin %d\n%s"
                              % (m.group(1), case["error_pin"], console))

    for text in case.get("must_mention", []):
        if text not in console:
            raise CaseFailure("console output does not mention %r\n%s" % (text, console))

    crlf = case.get("crlf", False)
    for ext in case["outputs"]:
        label = case["input"].rsplit(".", 1)[0] + "." + ext
        raw = outputs[ext]
        crlf_here = crlf and ext == "jed"
        if ext == "jed":
            verify_transmission_checksum(raw, label)
        actual = check_line_endings(raw, crlf_here, label)
        exp_path = os.path.join(case["path"], "expected." + ext)
        if update and not os.path.exists(exp_path):
            with open(exp_path, "wb") as f:
                f.write(actual)
            continue
        if not os.path.exists(exp_path):
            raise CaseFailure("missing %s" % os.path.relpath(exp_path, HERE))
        with open(exp_path, "rb") as f:
            expected = f.read()
        if ext == "jed":
            expected, actual = normalize_jed(expected), normalize_jed(actual)
        compare(label, expected, actual)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--galasm", default=DEFAULT_GALASM,
                    help="assembler executable to test (default: src/galasm)")
    ap.add_argument("-k", dest="pattern", default="",
                    help="only run cases whose name contains this text")
    ap.add_argument("--update", action="store_true",
                    help="write missing expected outputs from the assembler under test")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="list passing cases too")
    opts = ap.parse_args(argv)

    galasm = os.path.abspath(opts.galasm)
    if not os.path.exists(galasm) and os.path.exists(galasm + ".exe"):
        galasm += ".exe"
    if not os.path.exists(galasm):
        print("assembler not found: %s" % galasm)
        return 2

    names = sorted(n for n in os.listdir(CASES_DIR)
                   if os.path.isfile(os.path.join(CASES_DIR, n, "case.json"))
                   and opts.pattern in n)
    failures = 0
    for name in names:
        try:
            check_case(galasm, load_case(name), opts.update)
            if opts.verbose:
                print("PASS %s" % name)
        except CaseFailure as e:
            failures += 1
            print("FAIL %s: %s" % (name, e))
        except Exception as e:  # a broken case should not hide the others
            failures += 1
            print("FAIL %s: %s: %s" % (name, type(e).__name__, e))

    print("%d passed, %d failed" % (len(names) - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
