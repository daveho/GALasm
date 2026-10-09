# GALasm conformance tests

A black-box test suite for GALasm-compatible GAL assemblers.  It runs the
assembler as a command-line program and checks its exit status, its error
reports and the `.jed`, `.fus`, `.pin` and `.chp` files it writes.  It knows
nothing about how the assembler is implemented, so it catches any change in
behaviour, whatever the change to the code.

Everything in this directory is under the MIT license (see `LICENSE`).

## Running

Requires Python 3 (standard library only).

```sh
cd src && make && make check                 # build, then run the suite
python3 tests/run_tests.py                   # test src/galasm
python3 tests/run_tests.py --galasm path/to/other-assembler
python3 tests/run_tests.py -k 22v10 -v       # only cases whose name contains "22v10"
```

The runner exits with status 0 when every case passes.

`test_makefile.py` separately checks `src/Makefile` (linking with `$(CC)`,
`make clean`, and the `ARCHS` option for macOS universal binaries).  It
builds in a temporary copy of `src/`:

```sh
python3 tests/test_makefile.py
```

`test_truncated_sources.py` assembles every prefix of the sources of a
few successful cases, chosen so that between them the prefixes end
inside every part of the source language.  A prefix that ends before the
`DESCRIPTION` keyword must be rejected without writing any file, one that
ends after it must give the same files as the whole source, and no run
may crash.  It is mainly useful against a sanitizer build (below):

```sh
python3 tests/test_truncated_sources.py                 # test src/galasm
python3 tests/test_truncated_sources.py --galasm path/to/other-assembler
python3 tests/test_truncated_sources.py --all           # every successful case
```

### With sanitizers

A build with AddressSanitizer and UndefinedBehaviorSanitizer turns any
read beyond the end of the source, or other memory error, into a crash,
which both the suite and `test_truncated_sources.py` report.  With GCC or
Clang:

```sh
cd src && make clean
make CFLAGS="-g -O1 -fsanitize=address,undefined -fno-sanitize-recover=all" \
     LDFLAGS="-fsanitize=address,undefined"
export ASAN_OPTIONS=abort_on_error=1 UBSAN_OPTIONS=abort_on_error=1
make check && python3 ../tests/test_truncated_sources.py
```

## Case format

Each directory in `cases/` is one case:

| File | Purpose |
|---|---|
| `case.json` | What to run and what to expect |
| `input.pld` | Source file, copied into an empty temporary directory before the run |
| `expected.jed` / `.fus` / `.pin` / `.chp` | Expected output files (successful cases only) |

`case.json` keys:

| Key | Meaning |
|---|---|
| `description` | One line saying what the case covers |
| `expect` | `success`: exit status 0 and the expected files; `error`: non-zero exit status and no output files; `usage`: non-zero exit status and no output files; `help`: exit status 0 and no output files |
| `args` | Command-line arguments; `{input}` is replaced by the input file name. Default `["{input}"]` |
| `input` | Name to give the copied input file; may include a directory. Default `input.pld` |
| `outputs` | Output extensions that must be produced, and no others. Default: all four for `success`, none otherwise |
| `error_line` | The console output must contain `Error in line N:` with this N, or with one of the Ns if a list is given |
| `error_pin` | The console output must contain `Error, pin N:` with this N |
| `crlf` | The `.jed` file must use CR LF line endings throughout |
| `must_mention` | Strings the console output must contain |

Whatever `expect` says, a run in which the assembler is killed by a
signal, such as a crash, fails.

## How outputs are compared

* **Line endings.** CR LF is converted to LF before comparing, so native Windows line endings are accepted. For cases with `"crlf": true`, the `.jed` file must use CR LF on every line.
* **JEDEC transmission checksum.** The four hex digits after `<ETX>` are checked against the byte sum of the file as written, from `<STX>` to `<ETX>` inclusive. They are then left out of the comparison.
* **Program name.** The values of the `Used Program:` and `GAL-Assembler:` header lines are ignored, so a change of version number does not invalidate the expected files.
* **Everything else.** The rest of every file must match byte for byte, including the fuse checksum (`*C`).

The console output is only checked for the `Error in line N:` and
`Error, pin N:` prefixes and for any `must_mention` strings. Banner,
progress and the rest of the error-message text are free.

## Where the expectations come from

* **Inputs.** Every `input.pld` was written for this suite.
* **Expected outputs.** These were captured with `run_tests.py --update` from GALasm 2.1 at commit `c376d56`. The exception is `16v8_hand_derived`, whose expected files were worked out by hand from the device architecture and the JEDEC format. That case cross-checks the captured outputs. `16v8_crlf_source` shares its expected files with its LF twin, `16v8_crlf_source_lf_twin`.
* **Error line numbers.** These were predicted by hand first and then confirmed against the assembler.

`--update` only writes expected files that are missing. To regenerate one
on purpose, delete it and run `--update`.

## Adding a case

1. Create `cases/<name>/input.pld` and `cases/<name>/case.json`.
2. For a success case, run `python3 tests/run_tests.py --update -k <name>`.
3. Read the generated files and convince yourself they are right before
   committing them.

Name cases by device or area (`16v8_`, `20v8_`, `22v10_`, `20ra10_`,
`cli_`, `err_`).
