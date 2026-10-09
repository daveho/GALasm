# GALasm: Behavioural Specification

Version 1.0 (October 2026), describing GALasm 2.1 as in this repository.

This document is under the MIT license, like the test suite (see
`tests/LICENSE`).

---

## 0. About this document

### 0.1 Purpose

This document specifies the behaviour of GALasm: the command-line
interface, the source language, how sources are turned into fuse maps for
four GAL devices, and the exact formats of the files it writes.

It describes the command-line `galasm` program.  The GALer documentation
in `galer/` describes the Amiga program GALasm grew out of; where the two
differ, this document is authoritative for `galasm`.

The accompanying test suite in `tests/` is the executable part of this
specification.  Where this document and the suite disagree, treat it as a
bug in one of them and resolve it deliberately.

### 0.2 Conventions

* **MUST**, **SHOULD**, and **MAY** have their usual RFC 2119 meanings.
* Sections marked *(non-normative)* explain or advise and impose no
  requirements.
* Pin numbers are physical DIP package pin numbers.
* A *fuse* has a value of 0 or 1 as written in the JEDEC file.
* `LF` is byte 0x0A, `CR` is 0x0D, `TAB` is 0x09, `STX` is 0x02, `ETX` is 0x03.
* Hexadecimal numbers are written `0x..`.
* `%2d`, `%3d` mean a decimal number right-aligned in 2 or 3 characters,
  padded with spaces.  `%04d` means at least 4 digits, padded with zeros.

### 0.3 Exact outputs

For every input this document accepts, GALasm MUST produce exactly the
`.jed`, `.fus`, `.pin` and `.chp` files it describes, byte for byte, with
three exceptions:

* the values of the two program-identification lines in the JEDEC header,
  which change with the version (§9.2);
* the transmission checksum, which changes when those lines do (§9.5);
* native line endings on platforms whose text files use CR LF.

For every input this document rejects, GALasm MUST reject it and MUST
NOT write any output file.

---

## 1. Supported devices

| Device | Pins | GND pin | VCC pin | Output cells (OLMCs) | Fuse-array rows × columns |
|---|---|---|---|---|---|
| GAL16V8 | 20 | 10 | 20 | 8, on pins 12–19 | 64 × 32 = 2048 |
| GAL20V8 | 24 | 12 | 24 | 8, on pins 15–22 | 64 × 40 = 2560 |
| GAL22V10 | 24 | 12 | 24 | 10, on pins 14–23 | 132 × 44 = 5808 |
| GAL20RA10 | 24 | 12 | 24 | 10, on pins 14–23 | 80 × 40 = 3200 |

An *OLMC pin* is a pin that has an output logic macrocell and so can be
driven by an equation.  Every other pin is an *input-only pin*.

---

## 2. Command line

```
galasm [options] <file>
```

### 2.1 Options

Options come before the file name.  Each is a `-` followed by one or more
option letters.  Letters may be combined: `-sfp` is the same as
`-s -f -p`.  Option letters are case-insensitive.

| Letter | Effect |
|---|---|
| `s` | Set the security fuse (`*G1` in the JEDEC file instead of `*G0`) |
| `c` | Do not write the `.chp` file |
| `f` | Do not write the `.fus` file |
| `p` | Do not write the `.pin` file |
| `a` | Omit `<STX>`, `<ETX>` and the transmission checksum from the JEDEC file (§9.6) |
| `w` | Write the JEDEC file with CR LF line endings on every platform |
| `v` | Verbose: also explain on the console why the GAL16V8/GAL20V8 mode was chosen (§10) |
| `h` or `?` | Print usage help and exit with status 0 without assembling anything |

A lone `-`, and an argument starting with `--`, end option processing.
The next argument is then taken as the file name.

Once the file name has been seen, option processing has ended: every
later argument is another file name, even one that starts with `-`.  So
`galasm design.pld -s` is a usage error.

These are usage errors:
* an unknown option letter;
* no file name;
* more than one file name.

On a usage error GALasm MUST print a usage message, MUST NOT assemble
anything, and MUST exit with a non-zero status (currently 5).  The help
printed for `-h` or `-?` goes to standard output.

### 2.2 Output files

The output files go next to the input file.  Their names are the input
path with its extension replaced:

* Only the file name, the last component of the path, is examined.
  Directory names are never changed.
* If the file name contains a `.`, everything from its last `.` onwards
  is replaced by `.jed`, `.fus`, `.pin` or `.chp`.  So `my.design.pld`
  gives `my.design.jed`.
* Otherwise the extension is appended, so `design` gives `design.jed`, and
  `dir.v2/design` gives `dir.v2/design.jed`.

The `.jed` file is always written.  The other three are written unless
suppressed by an option.  The files are written in the order `.jed`,
`.fus`, `.pin`, `.chp`.  If assembly fails because of an error in the
source (§8), no file is written.

If an output file cannot be written, GALasm MUST report it and MUST exit
with a non-zero status.  It stops at that file: the files written before
it are left in place, and no later file is written.

### 2.3 Exit status

| Situation | Status |
|---|---|
| Success, or `-h` | 0 |
| Usage error | non-zero (currently 5) |
| Source error (§8) | non-zero (currently 255) |
| Input file cannot be opened or read, output file cannot be written (§2.2), or out of memory | non-zero (currently 254) |

If the input file cannot be opened or read, the error message MUST say
so and MUST include the file name as given on the command line.

---

## 3. Source file structure

A source file has four parts, in this order:

1. **Line 1**: the device type (§3.2).
2. **Line 2**: the signature (§3.3).
3. **Pin declarations**: starting on line 3 (§4).
4. **Equations**: ending with the keyword `DESCRIPTION` (§5).

Everything after `DESCRIPTION` is ignored.

### 3.1 Characters, whitespace and comments

These rules apply to the pin declarations and the equations, not to
lines 1 and 2.

* **Whitespace.** Space, TAB and LF separate tokens.  Any byte outside
  the printable ASCII range 0x21–0x7E is also treated as whitespace.
  That includes CR and bytes ≥ 0x7F.
* **Comments.** A `;` starts a comment that runs to the end of the line.
* **Names** are made of the ASCII letters `A–Z`, `a–z`, the digits
  `0–9` and the underscore `_`.  These are the *name characters*.  An
  underscore may appear anywhere in a name, including first.  Names are
  case-sensitive.
* **Operators:**

  | Meaning | Characters |
  |---|---|
  | Negation | `/` or `!` |
  | AND | `*` or `&` |
  | OR | `+` or `#` |
  | Assignment | `=` |
  | Suffix separator | `.` |

* **Line numbers** start at 1.  Every LF ends a line.

**Line endings.** Both LF and CR LF line endings MUST be accepted, and
must give identical results.  A CR immediately before an LF is part of
the line ending, everywhere in the file, including lines 1 and 2.

### 3.2 Line 1: device type

The file MUST begin, at its very first byte, with one of `GAL16V8`,
`GAL20V8`, `GAL22V10` or `GAL20RA10`.  The match is case-sensitive.  The
next byte MUST be a space, TAB or line ending.  Otherwise the file is
rejected with error E1, reported at line 1.  If the file ends right
after the device type, report E2 (unexpected end of file) instead.

Anything else on line 1 is ignored.

### 3.3 Line 2: signature

The signature is taken from the bytes at the start of line 2, up to the
first line ending or TAB or 8 bytes, whichever comes first.  Spaces and every
other byte are part of the signature, including `;`.  The rest of line 2
is ignored.

If the file ends before line 2 exists, report E2 (unexpected end of file).

Each signature byte gives 8 signature fuses, most significant bit first.
Byte *k* (0-based) gives signature fuses 8*k* … 8*k*+7.  Signature fuses
beyond the given bytes are 0.  There are always 64 signature fuses.

---

## 4. Pin declarations

Pin declarations start at the beginning of line 3.  There are exactly as
many pin names as the device has pins (20 or 24).  They are assigned to
pins 1, 2, 3, … in order.  Names may be spread over any number of lines,
separated by whitespace and comments.

### 4.1 Pin name syntax

A pin name is an optional negation sign (`/` or `!`) followed directly by
1–8 name characters.  The negation, if present, is stored as part of the
declared name; this matters for the output files, see §9.

The *base name* is the name without its negation sign.

### 4.2 Checks

Each name is checked when it is read, in the order below.  The first
failing check is reported, at the line where the name is.

| # | Check | Error |
|---|---|---|
| 1 | The first character must be a negation sign or a name character | E5 |
| 2 | A negation sign may only appear as the first character | E10 |
| 3 | A negation sign must be followed directly by a name character | E3 |
| 4 | At most 8 name characters (not counting the negation sign) | E4 |
| 5 | Unless the base name is `NC`, it must differ from the base names of all earlier pins | E9 |
| 6 | Only the GND pin may have the base name `GND` | E6 |
| 7 | The GND pin must be declared exactly `GND` | E8 |
| 8 | Only the VCC pin may have the base name `VCC` | E6 |
| 9 | The VCC pin must be declared exactly `VCC` | E7 |
| 10 | GAL22V10 only: the declared name must not be exactly `AR` or `SP` | E18 |

Checks 6 and 8 compare base names, so `/VCC` declared on pin 2 is E6 at
pin 2.  Checks 7 and 9 then also reject `/GND` or `/VCC` on the power pin
itself.

How a name ends affects which check fails:

* A name ends at the first character that is not a name character or a
  negation sign.
* If that character is something other than whitespace or a comment, for
  example `%` in `B%C`, the name before it (`B`) is accepted.  The `%`
  then fails check 1 as the start of the next name.
* A `/` inside a name (`B/C`) fails check 2.  So does a second negation
  sign (`//B` or `!/B`): unlike equations (§5.2), a pin declaration
  allows at most one.

If the file ends before all pins are declared, report E2.

A pin whose base name is `NC` is *not connected*.  `NC` may be declared
on any number of pins, with or without a negation sign, so `NC`, `/NC`
and `!NC` may all appear in one pin list.  Not-connected pins cannot be
used in equations: the name `NC` in an equation is always E12.

---

## 5. Equations

### 5.1 Grammar

```
equations   := equation { equation } "DESCRIPTION"
equation    := lhs "=" term { op term }
lhs         := { neg } target [ "." suffix ]
target      := pin-name | "AR" | "SP"           ; AR, SP: GAL22V10 only
term        := { neg } pin-name
op          := and | or
neg         := "/" | "!"
and         := "*" | "&"
or          := "+" | "#"
```

* Whitespace and comments may appear between any two tokens, except:
  * between two negation signs, or between a negation sign and the
    following name;
  * between `.` and the suffix letters.
* An equation ends when a term is not followed by an operator.  The next
  token then starts a new equation, or is `DESCRIPTION`.
* `DESCRIPTION` is recognised where an equation would start, if the text
  there begins with the 11 characters `DESCRIPTION`.  It is
  case-sensitive.
* If `DESCRIPTION` is the first token after the pin declarations, report
  E33 at that line.
* Where the grammar requires a pin name, for a target or a term, and the
  text there is not one, report E49 at the line where the target or term
  begins (the line of its first negation sign, if it has any).
  Examples: `R = * A`; `R = / A` and `R = / /A`, where whitespace
  follows a negation sign; and `=` where an equation should start.
* If the file ends before `DESCRIPTION`, report E2.  Reaching the end of
  the input at any point is always reported this way; GALasm
  MUST NOT read beyond the end of the input.

### 5.2 Semantics

* The right-hand side is a sum of products.  AND binds tighter than OR.
  There are no parentheses.
* Each maximal run of terms joined by AND is one *product term*.
* Every term refers to a pin by its base name: the name is looked up
  without the negation sign from its declaration.

**Runs of negation signs.** A target or term written with an odd number
of negation signs is *negated*; with an even number, including none, it
is not.  So `//A` and `!/A` mean `A`, and `/!/A` means `/A`.  `/` and
`!` may be mixed freely.  This applies to every rule about a negated
target or term, including E25 and E32: `//VCC` is accepted and means
`VCC`, while `/!/VCC` is E25.

**Polarity of a term.** A term is inverted if exactly one of these holds:
* the term is negated;
* the referenced pin was declared with a negation sign.

For example, with pin 1 declared `/A`, the term `A` means "pin 1 low" and
`/A` means "pin 1 high".

**Polarity of an output.** Combine the negation on the left-hand side with
the negation in the target pin's declaration in the same way.  An
inverted result makes the output *active low*; otherwise it is *active
high*.

**VCC and GND.** These may appear as the only term of an equation (no
operator before or after them).
* `GND` makes that product term constantly false.
* `VCC` makes it constantly true.

### 5.3 Suffixes

The suffix letters are read up to the first non-letter.  More than 6
letters gives error E13.  The suffix is then identified as follows; any
other suffix is E13.

| Suffix | How it is recognised | Meaning | Allowed on |
|---|---|---|---|
| none | | Output; the type is chosen by the assembler (§6) | all |
| `.T` | any suffix whose first letter is `T` | Tristate output | all |
| `.R` | any suffix whose first letter is `R` | Registered output | all |
| `.E` | any suffix whose first letter is `E` | Output-enable product term for a `.T` or `.R` output | all |
| `.CLK` | exactly `CLK` | Clock product term of a registered output | GAL20RA10; elsewhere E34 |
| `.ARST` | exactly `ARST` | Asynchronous reset product term of a registered output | GAL20RA10; elsewhere E35 |
| `.APRST` | exactly `APRST` | Asynchronous preset product term of a registered output | GAL20RA10; elsewhere E36 |

Matching is case-sensitive, so `.t` is E13.  Because only the first letter
is checked for T, R and E, `.Tri`, `.Reg` and `.Enable` are accepted.

The order of checks when a `.` follows the target is:
1. GAL22V10 only: if the target is AR or SP, report E39.
2. Unknown suffix: E13.
3. Device restriction: E34, E35 or E36.

### 5.4 AR and SP (GAL22V10)

On the GAL22V10, `AR` (asynchronous reset) and `SP` (synchronous preset)
may be used as equation targets for the device-wide reset and preset
product terms.  The rules:

* They are recognised only where the name is not a declared pin name.
* They are recognised only as a whole name.  A name that merely begins
  with `AR` or `SP`, such as `AR_X` or `SP1`, is an ordinary name: if it
  is not declared, it is E11.
* They may not carry a suffix (E39).
* They may not be negated (E32).
* They may not be used as terms (E31).
* They may be defined at most once each (E40).
* Each is a single product term, so an OR gives E29.

---

## 6. Classifying outputs and choosing the mode

Before any fuse is computed, the whole equation section is read once to
classify every OLMC.  The fuse map depends on decisions that a later
equation can change, so this complete pass is required.

### 6.1 OLMC states

Each OLMC (plus AR and SP on the GAL22V10) starts *unused*.  The
equations are processed in file order.

**Target of an equation.** First the target must be valid:
* E12 if it is `NC` (§4.2);
* E11 if it is not a declared name (or AR/SP on the 22V10);
* E32 if it is a negated AR or SP;
* E15 if it is a declared pin without an OLMC.

The equation then acts on the target OLMC according to its suffix:

| Suffix | Action |
|---|---|
| none, `.T`, `.R` | If the OLMC is *unused* or *input*, it becomes an output with the polarity from §5.2.  The kind is *undecided* (no suffix), *tristate* (`.T`) or *registered* (`.R`).  If it is already an output: E40 for AR/SP, E16 otherwise. |
| `.E` | In this order: the OLMC already has an `.E` → E22; the OLMC is unused or input → E17; registered output on a GAL16V8/20V8 → E23; undecided output (defined without suffix) → E24.  Otherwise record that the OLMC has an enable equation. |
| `.CLK` / `.ARST` / `.APRST` | In this order: the OLMC is unused → E42 / E43 / E44; this suffix already given for this OLMC → E45 / E46 / E47; the OLMC is not a registered output → E48.  Otherwise record it.  (An OLMC in the *input* state passes the "unused" check and then fails with E48.) |

**Terms of an equation.** Each term must be valid:
* E12 if it is `NC` (§4.2);
* E11 if it is not a declared pin name;
* E31 if it is AR or SP (22V10).

A term that refers to an OLMC pin marks that OLMC as *fed back*.  If the
OLMC is still *unused*, it becomes *input*.

Negation signs on the target of an `.E`, `.CLK`, `.ARST` or `.APRST`
equation are allowed and ignored, however many there are.  These equations always describe the
condition that enables, clocks, resets or presets, so `R.E = A` and
`/R.E = A` mean the same.  The same holds whether or not the pin was
declared with a negation sign.

If the token after the target (and suffix) is not `=`, report E14.

### 6.2 Mode of the GAL16V8 and GAL20V8

These devices have three global modes.  The mode is chosen by the first
rule that applies:

1. If any OLMC is a registered output, the mode is **registered** (mode 3).
2. Otherwise, if any OLMC is a tristate output, the mode is **complex**
   (mode 2).
3. Otherwise, the mode is **complex** if either of these is fed back (an
   *input*, or an undecided output used as a term):
   * on the GAL16V8, the OLMC on pin 15 or 16;
   * on the GAL20V8, the OLMC on pin 18 or 19.

   In simple mode those pins have no path into the array.
4. Otherwise the mode is **simple** (mode 1).

| Mode | SYN | AC0 |
|---|---|---|
| simple | 1 | 0 |
| complex | 1 | 1 |
| registered | 0 | 1 |

Then every undecided output is resolved:
* in simple mode it becomes **combinational**;
* in complex and registered mode it becomes **tristate with a permanently
  enabled output** (§7.3).

### 6.3 GAL22V10 and GAL20RA10

These devices have no global mode.  Undecided outputs become tristate
outputs with permanently enabled output.

### 6.4 Architecture bits

Each OLMC has a *polarity bit* (XOR on the 16V8/20V8, S0 on the
22V10/20RA10):
* 1 if the OLMC is an output (of any kind) and active high;
* 0 otherwise, which includes unused and input OLMCs.

The GAL16V8 and GAL20V8 also have an **AC1** bit per OLMC, and the
GAL22V10 an **S1** bit per OLMC:
* 1 if the OLMC is an *input* or a tristate output;
* 0 otherwise (combinational, registered or unused).

The GAL16V8 and GAL20V8 also have 64 **PT** (product-term disable) bits,
which are always 1.

These per-OLMC bits are stored with the **highest-numbered OLMC pin
first**.  For example, the GAL16V8 XOR fuses 2048 … 2055 belong to pins
19, 18, …, 12.

---

## 7. Fuse map generation

### 7.1 Array organisation

The fuse array has R rows (product terms) of C columns (fuses).  Fuse
number *r*·C + *c* is row *r*, column *c*.

Every input signal reaching the array occupies two adjacent columns:
* the even column *k* is the true signal;
* column *k*+1 is the complement.

A fuse of **0** puts that signal into the row's product term.  A fuse of
**1** leaves it out.  So a row of all 1s is constantly true, and a row of
all 0s is constantly false.

**Initial state.** All array fuses start at 1.

**Literals.** A term adds a literal to the current row by setting one
fuse to 0:
* column *k* for the term's pin, if the term's polarity (§5.2) is not
  inverted;
* column *k*+1 if it is inverted.

### 7.2 Signal columns

The *k* for each pin is given in the tables below.  "–" means the pin has
no column.

**GAL16V8**

| Pin | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| simple | 2 | 0 | 4 | 8 | 12 | 16 | 20 | 24 | 28 | 30 | 26 | 22 | 18 | – | – | 14 | 10 | 6 |
| complex | 2 | 0 | 4 | 8 | 12 | 16 | 20 | 24 | 28 | 30 | – | 26 | 22 | 18 | 14 | 10 | 6 | – |
| registered | – | 0 | 4 | 8 | 12 | 16 | 20 | 24 | 28 | – | 30 | 26 | 22 | 18 | 14 | 10 | 6 | 2 |

**GAL20V8**

| Pin | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| simple | 2 | 0 | 4 | 8 | 12 | 16 | 20 | 24 | 28 | 32 | 36 | 38 | 34 | 30 | 26 | 22 | – | – | 18 | 14 | 10 | 6 |
| complex | 2 | 0 | 4 | 8 | 12 | 16 | 20 | 24 | 28 | 32 | 36 | 38 | 34 | – | 30 | 26 | 22 | 18 | 14 | 10 | – | 6 |
| registered | – | 0 | 4 | 8 | 12 | 16 | 20 | 24 | 28 | 32 | 36 | – | 38 | 34 | 30 | 26 | 22 | 18 | 14 | 10 | 6 | 2 |

**GAL22V10**

| Pin | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| column | 0 | 4 | 8 | 12 | 16 | 20 | 24 | 28 | 32 | 36 | 40 | 42 | 38 | 34 | 30 | 26 | 22 | 18 | 14 | 10 | 6 | 2 |

**GAL20RA10**

| Pin | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| column | – | 0 | 4 | 8 | 12 | 16 | 20 | 24 | 28 | 32 | 36 | – | 38 | 34 | 30 | 26 | 22 | 18 | 14 | 10 | 6 | 2 |

**Pins that cannot be used as terms.**

* *Simple mode.* The 16V8/20V8 pins with no column in simple mode can
  never be reached as terms, because using them forces complex mode
  (§6.2).
* *Complex mode, 16V8 pins 12 and 19.* Using these as a term is E20.
* *Complex mode, 20V8 pins 15 and 22.* Using these as a term is E21.
* *Registered mode, 16V8 pins 1 and 11.* These are the clock and output
  enable; using them as a term is E26.
* *Registered mode, 20V8 pins 1 and 13.* Likewise E27.
* *GAL20RA10 pins 1 and 13.* These are /PL and /OE; using them as a term
  is E37 and E38 respectively.

These checks need the mode, so they happen in the second reading
(§8.2).

**GAL22V10 registered feedback.** When a term refers to an OLMC pin
whose OLMC is a *registered, active-high* output (S1 = 0 and S0 = 1), the
term's polarity is inverted once more before choosing the column.  This
rule applies only to the GAL22V10.

### 7.3 Rows belonging to each OLMC

**GAL16V8 and GAL20V8.**

Rows: each OLMC owns 8 consecutive rows.  The highest OLMC pin owns rows
0–7, the next pin down rows 8–15, and so on:
* GAL16V8: pin 19 → rows 0–7, …, pin 12 → rows 56–63;
* GAL20V8: pin 22 → rows 0–7, …, pin 15 → rows 56–63.

| OLMC kind (after §6.2) | Row 0 of the OLMC | Rows for the sum | Max. product terms |
|---|---|---|---|
| Combinational (simple mode) | part of the sum | 0–7 | 8 |
| Registered (registered mode) | part of the sum | 0–7 | 8 |
| Tristate (complex or registered mode) | output enable | 1–7 | 7 |

**GAL22V10.**

| Rows | Owner | Product terms |
|---|---|---|
| 0 | AR | 1 |
| 1–9 | pin 23 | 8 |
| 10–20 | pin 22 | 10 |
| 21–33 | pin 21 | 12 |
| 34–48 | pin 20 | 14 |
| 49–65 | pin 19 | 16 |
| 66–82 | pin 18 | 16 |
| 83–97 | pin 17 | 14 |
| 98–110 | pin 16 | 12 |
| 111–121 | pin 15 | 10 |
| 122–130 | pin 14 | 8 |
| 131 | SP | 1 |

The first row of each OLMC is its output enable.  The remaining rows hold
the sum, so the product-term limit is the number of rows minus one.

**GAL20RA10.** Each OLMC owns 8 rows: pin 23 → rows 0–7, pin 22 → 8–15,
…, pin 14 → 72–79.  Within an OLMC whose first row is *b*:

| Row | Use |
|---|---|
| *b* | output enable (`.E`) |
| *b*+1 | clock (`.CLK`) |
| *b*+2 | asynchronous reset (`.ARST`) |
| *b*+3 | asynchronous preset (`.APRST`) |
| *b*+4 … *b*+7 | sum: at most 4 product terms |

### 7.4 Writing an equation into the array

Equations are read a second time, in file order, now with the mode and
every OLMC's final kind known.

**Control equations** are `.E`, `.CLK`, `.ARST`, `.APRST`, and AR and SP on
the GAL22V10.  Each writes exactly one row: the dedicated row from §7.3.
All of its terms are ANDed into that row.  An OR in a control equation is
E29, reported at the term that follows the OR.

**Sum equations** are all other equations.  They write their product
terms into consecutive rows starting at the OLMC's first sum row (§7.3):
* each OR moves to the next row;
* going past the last row of the OLMC is E30, reported at the term after
  the OR that overflowed.

After the last term, every remaining sum row of the OLMC is set to all
0s.  Those rows are then constantly false and do not affect the output.

**Checks on each term.** These are done in this order:

1. The mode or device pin restrictions of §7.2 (E20, E21, E26, E27, E37,
   E38).
2. If the term is the VCC or GND pin:
   * negated → E25;
   * any operator before it in the same equation, or directly after it →
     E28;
   * `GND`: the current row is set to all 0s;
   * `VCC`: the current row is left as it is (all 1s).
3. Otherwise the literal is written as in §7.1.

**Rows that are not written stay all 1s.** As a result:
* a tristate output with no `.E` equation is always enabled, because its
  enable row stays true;
* on the GAL20RA10, a combinational output has its reset and preset rows
  left true.  That is how this device selects combinational
  (register-bypass) operation.

### 7.5 Final clean-up

After all equations have been written:

1. **Unused and input OLMCs.** Every row of each OLMC that is *unused* or
   *input* is set to all 0s.
2. **GAL22V10 AR and SP.** If AR is not defined, row 0 is set to all 0s.
   If SP is not defined, row 131 is set to all 0s.  Nothing else affects
   these rows; in particular, `VCC` or `GND` terms in other equations do
   not.
3. **GAL20RA10.** Process each OLMC that is not *unused* (input OLMCs
   included), from pin 14 upwards:
   1. If it is a registered output with no `.CLK`, report error E41 for
      that pin (§8.3) and stop.
   2. If it has no `.CLK`, set row *b*+1 to all 0s.
   3. If it is a registered output, set row *b*+2 to all 0s when there is
      no `.ARST`, and row *b*+3 to all 0s when there is no `.APRST`.

---

## 8. Errors

### 8.1 Error list

Assembly stops at the first error.  The error identifiers below are used
by this document.  E1–E48 are the positions of the corresponding messages
in `AsmErrorArray` (`src/localize.c`).  E49 has no message of its own:
GALasm reports it with the message for E11.  The wording of messages is
not specified.

| Id | Condition |
|---|---|
| E1 | Line 1 does not start with a supported device type followed by space, TAB or LF |
| E2 | Unexpected end of file |
| E3 | Negation sign in a pin declaration not followed by a name |
| E4 | Pin name longer than 8 characters |
| E5 | Illegal character in the pin declarations |
| E6 | `GND` or `VCC` declared on the wrong pin |
| E7 | VCC pin not declared as `VCC` |
| E8 | GND pin not declared as `GND` |
| E9 | Pin name declared twice |
| E10 | Negation sign inside a pin name |
| E11 | Unknown pin name in an equation |
| E12 | `NC` used in an equation |
| E13 | Unknown suffix |
| E14 | `=` expected |
| E15 | Equation target has no OLMC |
| E16 | Output defined more than once |
| E17 | `.E` before the output is defined |
| E18 | GAL22V10: `AR` or `SP` declared as a pin name |
| E19 | Not used: GALasm 2.1 rejected a negated control-equation target; it is now accepted (§6.1) |
| E20 | GAL16V8 complex mode: pin 12 or 19 used as a term |
| E21 | GAL20V8 complex mode: pin 15 or 22 used as a term |
| E22 | `.E` defined twice for one output |
| E23 | GAL16V8/20V8: `.E` for a registered output |
| E24 | `.E` for an output defined without `.T` |
| E25 | Negated `VCC` or `GND` |
| E26 | GAL16V8 registered mode: pin 1 or 11 used as a term |
| E27 | GAL20V8 registered mode: pin 1 or 13 used as a term |
| E28 | `VCC` or `GND` combined with other terms |
| E29 | More than one product term in a control equation |
| E30 | Too many product terms for the OLMC |
| E31 | GAL22V10: `AR` or `SP` used as a term |
| E32 | GAL22V10: negated `AR` or `SP` |
| E33 | No equations |
| E34 | `.CLK` on a device other than the GAL20RA10 |
| E35 | `.ARST` on a device other than the GAL20RA10 |
| E36 | `.APRST` on a device other than the GAL20RA10 |
| E37 | GAL20RA10: pin 1 used as a term |
| E38 | GAL20RA10: pin 13 used as a term |
| E39 | GAL22V10: suffix on `AR` or `SP` |
| E40 | GAL22V10: `AR` or `SP` defined twice |
| E41 | GAL20RA10: registered output without `.CLK` |
| E42 | `.CLK` before the output is defined |
| E43 | `.ARST` before the output is defined |
| E44 | `.APRST` before the output is defined |
| E45 | `.CLK` defined twice for one output |
| E46 | `.ARST` defined twice for one output |
| E47 | `.APRST` defined twice for one output |
| E48 | `.CLK`, `.ARST` or `.APRST` for an output that is not registered |
| E49 | Pin name expected in an equation (§5.1) |

### 8.2 Files with more than one error

Assembly stops at the first error found.  When a source file contains
more than one error, which one is reported is not specified.

*(Non-normative.)* Some checks need the GAL16V8/20V8 mode (E20, E21,
E26, E27), and the mode depends on every equation in the file.  So these
checks can only be completed after all equations have been classified.
E41 can only be checked once every equation has been seen.

### 8.3 Error report format and line numbers

**Format.** Errors are reported on the console in one of two forms:

```
Error in line N: <message>
Error, pin P: <message>
```

The second form is used only for E41, where P is the pin of the
offending output.  The test suite looks only for these two prefixes, in
standard output and standard error combined (§10).

**Line N** is assigned as follows:

| Kind of error | N is the line of… |
|---|---|
| E1 | line 1 |
| Pin declaration errors | the line where the offending pin name is |
| Errors about the target name itself (E11, E12, E32) | the target name |
| Other errors about an equation's target: suffix and classification errors (E13–E17, E22–E24, E34–E36, E39, E40, E42–E48) | the target name, or the first token after it (the `.` or `=`); in practice these are almost always on the same line |
| Errors about a term (E11, E12, E20, E21, E25–E31, E37, E38) | the term |
| E33 | `DESCRIPTION` |
| E49 | the start of the target or term (its first negation sign, if any) |
| E2 | unspecified; tests only require failure |

---

## 9. Output file formats

All four files are text files written with the platform's native line
endings, except that `-w` forces CR LF in the JEDEC file.  In the
descriptions below `\n` stands for one line ending.

### 9.1 Fuse numbering

Each device's fuses are numbered as follows.

**GAL16V8** (2194 fuses)

| Fuses | Contents |
|---|---|
| 0–2047 | array |
| 2048–2055 | XOR |
| 2056–2119 | signature |
| 2120–2127 | AC1 |
| 2128–2191 | PT |
| 2192 | SYN |
| 2193 | AC0 |

**GAL20V8** (2706 fuses)

| Fuses | Contents |
|---|---|
| 0–2559 | array |
| 2560–2567 | XOR |
| 2568–2631 | signature |
| 2632–2639 | AC1 |
| 2640–2703 | PT |
| 2704 | SYN |
| 2705 | AC0 |

**GAL22V10** (5892 fuses)

| Fuses | Contents |
|---|---|
| 0–5807 | array |
| 5808–5827 | S0/S1 pairs: S0 then S1 of pin 23, then pin 22, …, pin 14 |
| 5828–5891 | signature |

**GAL20RA10** (3274 fuses)

| Fuses | Contents |
|---|---|
| 0–3199 | array |
| 3200–3209 | S0 of pins 23 … 14 |
| 3210–3273 | signature |

### 9.2 JEDEC file (`.jed`)

The file consists of these lines, in order.  Spaces shown are literal.

```
<STX>\n                              (omitted with -a)
Used Program:   <program>\n
GAL-Assembler:  <program>\n
Device:         <device>\n            <device> = GAL16V8 | GAL20V8 | GAL22V10 | GAL20RA10
\n
*F0\n
*G0\n                                 (*G1 with -s)
*QF<total fuses>\n                    2194 | 2706 | 5892 | 3274
<array lines>
<architecture lines>
*C<fuse checksum>\n
*\n
<ETX><transmission checksum>\n       (omitted with -a)
```

The header lines in detail:
* **Program lines.** `Used Program:` is followed by 3 spaces,
  `GAL-Assembler:` by 2 spaces, and `Device:` by 9 spaces.  The values of
  the first two lines identify the program and its version, such as
  `GALasm 2.1`.  The test suite ignores them, so a change of version does
  not invalidate its expected files, but the labels and spacing MUST be
  as shown.
* **`*F0`** declares that fuses not listed are 0.
* **Fuse lines.** Each starts with `*L`, then the address of its first
  fuse as a decimal number of at least 4 digits (zero-padded, `%04d`),
  then a space, then the fuse values as the characters `0` and `1`.

**Array lines.** One line per array row that contains at least one 1, in
row order.  Each line holds the C fuses of that row and is labelled with
the row's first fuse number.  Rows of all 0s are omitted.

**Architecture lines.** These are always present, even when all their
fuses are 0.

| Device | Lines, in order |
|---|---|
| GAL16V8, GAL20V8 | XOR (8 fuses), signature (64), AC1 (8), PT (64), SYN (1), AC0 (1): six lines |
| GAL22V10 | the 20 S0/S1 fuses, then the signature (64): two lines |
| GAL20RA10 | the 10 S0 fuses, then the signature (64): two lines |

### 9.3 Example

For a GAL16V8 with signature `HAND`, pins `A B C D E F G H I GND J K L M N O
P Q R VCC`, and the single equation `R = A * /B`, the file is:

```
<STX>
Used Program:   GALasm 2.1
GAL-Assembler:  GALasm 2.1
Device:         GAL16V8

*F0
*G0
*QF2194
*L0000 10011111111111111111111111111111
*L2048 10000000
*L2056 0100100001000001010011100100010000000000000000000000000000000000
*L2120 00000000
*L2128 1111111111111111111111111111111111111111111111111111111111111111
*L2192 1
*L2193 0
*C0d18
*
<ETX>45be
```

How the example's lines come about:
* **Array.** Pin 19 owns rows 0–7.  In simple mode `A` (pin 1) is column 2
  and `B` (pin 2) is column 0.  So row 0 has fuse 2 (A true) and fuse 1
  (B complement) at 0.  Rows 1–63 are all 0 and omitted.
* **XOR.** The output on pin 19 is active high, so the first XOR fuse is
  1.

`45be` is the transmission checksum (§9.5), computed for the file as
shown, with LF line endings; it changes with the program lines.  This
example is the test case `16v8_hand_derived`.

### 9.4 Fuse checksum (`*C`)

1. Take all fuses of the device in fuse-number order, from 0 to
   total − 1.
2. Pack them into bytes, 8 at a time: fuse 8*i* is bit 0 (least
   significant) of byte *i*, fuse 8*i*+7 is bit 7.  If the total is not a
   multiple of 8, the last byte is padded with zeros.
3. Add the bytes, modulo 65536.
4. Write the result as exactly 4 lowercase hexadecimal digits.

The checksum covers every fuse, including the architecture fuses and the
signature.  It is written whether or not `-a` is given.

### 9.5 Transmission checksum

Without `-a`:
* The file begins with `<STX>` and a line ending.
* After the closing `*` line comes `<ETX>`, immediately followed by the
  transmission checksum and a line ending.

The transmission checksum is the sum, modulo 65536, of the bytes of the
file as written, from `<STX>` to `<ETX>` inclusive.  It includes any CR
bytes of CR LF line endings.  It is written as exactly 4 lowercase
hexadecimal digits.

### 9.6 Effect of `-a`

With `-a`:
* `<STX>` and its line ending are omitted, so the file starts with
  `Used Program:`;
* the file ends with the `*` line: no `<ETX>` and no transmission
  checksum.

### 9.7 Fuse listing (`.fus`)

The listing contains, in order:

1. **GAL22V10 only, first:** two line endings, the text `AR`, then row 0
   in the row format below.
2. **For each OLMC, from the highest pin down** (16V8: 19…12; 20V8:
   22…15; 22V10 and 20RA10: 23…14):
   * two line endings, then `Pin %2d = ` followed by the declared pin
     name (including any negation sign);
   * spaces to pad the name to 13 characters (none if it is longer);
   * then, depending on the device:
     * 16V8/20V8: `XOR = <x>   AC1 = <a>`;
     * 22V10: `S0 = <x>   S1 = <s>`;
     * 20RA10: `S0 = <x>`.

     There are three spaces before `AC1` and `S1`; `<x>`, `<a>`, `<s>`
     are single digits;
   * then each row owned by the OLMC (8 rows, or the OLMC's row count on
     the 22V10, enable row included) in the row format.
3. **GAL22V10 only, after the OLMC on pin 14:** two line endings, the
   text `SP`, then row 131 in the row format.
4. **Finally**, two line endings.

**Row format.** A line ending, then the row number right-aligned in 3
characters, then a space.  Then for each column *c* from 0:
* a space if *c* is a multiple of 4;
* then `-` if the fuse is 1, or `x` if it is 0.

So `x` marks a connected literal.

Example (GAL22V10, AR = H * /I):

```


AR
  0  ---- ---- ---- ---- ---- ---- ---- ---- x--- -x-- ----

Pin 23 = Q9           S0 = 0   S1 = 0
  1  xxxx xxxx xxxx xxxx xxxx xxxx xxxx xxxx xxxx xxxx xxxx
```

### 9.8 Pin listing (`.pin`)

```
\n
\n
 Pin # | Name     | Pin Type\n
-----------------------------\n
```

That is 29 dashes.  Then one line per pin, from 1 to N:

```
  %2d   | <name><pad>| <type>\n
```

* `<name>` is the declared name, including any negation sign.
* `<pad>` is spaces bringing the name to 9 characters (none if it is
  longer).
* After the VCC pin's line, one extra line ending follows.

`<type>` is decided by the first rule that matches:

| Pin | Type |
|---|---|
| the GND pin | `GND` |
| the VCC pin | `VCC` |
| 16V8/20V8 in registered mode, pin 1 | `Clock` |
| 16V8 in registered mode, pin 11; 20V8 in registered mode, pin 13 | `/OE` |
| GAL22V10 pin 1 | `Clock/Input` |
| an OLMC pin whose OLMC is *input* | `Input` |
| an OLMC pin whose OLMC is any kind of output | `Output` |
| an OLMC pin whose OLMC is *unused* | `NC` |
| any other pin (including 20RA10 pins 1 and 13) | `Input` |

### 9.9 Chip diagram (`.chp`)

The chip diagram is a picture of the DIP package seen from above, with
each pin's declared name, including any negation sign, beside its
number.  Pins 1 to N/2 run down the left side and pins N/2+1 to N up
the right side, so each line shows a pin and the pin facing it: 1 and
N, 2 and N−1, and so on.  The notch in the top edge marks the end with
pin 1.

The file starts with two empty lines.  Then come the device title and
an empty line, and then the package.  Columns are counted from 1:

* **Title.** It starts in column 32.  It is ` GAL16V8`, ` GAL20V8` or
  ` GAL22V10`, each with a leading space, or `GAL20RA10` without one.
* **Outline.** Every outline line starts in column 27.  The top edge is
  `-------\___/-------` and the bottom edge is 19 dashes.  Between two
  pin lines is a line showing only the sides of the package: `|`, 17
  spaces, `|`.
* **Pin lines.** The left pin's name is right-aligned to end in column
  25; a name has at most 9 characters, so it always fits.  The rest of
  the line is ` | `, the left pin number as `%2d`, 11 spaces, the right
  pin number as `%2d`, ` | ` and the right pin's name.

Every line, including the last, ends with a line ending.  For the
example of §9.3, after the two empty lines, the file is:

```
                                GAL16V8

                          -------\___/-------
                        A |  1           20 | VCC
                          |                 |
                        B |  2           19 | R
                          |                 |
                        C |  3           18 | Q
                          |                 |
                        D |  4           17 | P
                          |                 |
                        E |  5           16 | O
                          |                 |
                        F |  6           15 | N
                          |                 |
                        G |  7           14 | M
                          |                 |
                        H |  8           13 | L
                          |                 |
                        I |  9           12 | K
                          |                 |
                      GND | 10           11 | J
                          -------------------
```

---

## 10. Console output

**Streams.** GALasm writes all of its console output to standard output,
including error messages and the usage help.  The test suite reads
standard output and standard error combined.

*(Non-normative.)* GALasm prints, in order:
* a banner;
* a line per assembly pass;
* a summary such as `GAL16V8; Operation mode: simple; Security fuse off`
  (the mode is shown for the 16V8/20V8 only);
* finally, either a success or a failure line.

With `-v` it also explains the mode choice for the 16V8/20V8, naming each
pin that forced it.  The wording of all of this is not specified.  The
only requirement is the error prefixes of §8.3.

---

## 11. Behaviour not specified

The following may change between versions of GALasm, and the test suite
does not depend on them:

* the exact usage, help and error message texts;
* which stream each message is written to (§10);
* exit status values, beyond zero for success and non-zero for failure;
* the line number reported for unexpected end of file;
* which error is reported when a file contains several (§8.2).

---

## 12. Glossary

* **OLMC.** Output Logic Macrocell: the configurable output stage behind
  an output pin.
* **Product term.** One row of the AND array: the AND of the literals
  whose fuses are 0.
* **Sum.** The OR of an OLMC's sum rows, which drives the output.
* **Enable row.** The product term controlling an OLMC's tristate buffer.
* **JEDEC file.** The industry-standard fuse-map file format (JESD3)
  understood by device programmers.
