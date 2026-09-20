# Contributing to qrgen

Thanks for your interest!

## Ground rules

- **Zero runtime dependencies.** Python 3.9+ standard library only. The
  optional conformance harness (`pyzbar`/`pillow`) lives outside the package.
- **The spec is normative.** Behavior must match ISO/IEC 18004. Changes to
  encoding, placement or masking need a failing test first, plus scanner
  verification via `scripts/conformance.py`.
- **No exceptions on input paths.** Malformed arguments exit 2; data that
  exceeds every version's capacity exits 1 with a clear message.

## Workflow

```sh
python3 -m unittest discover -s tests
```

The suite includes a golden matrix regression: if a change alters any
module of the reference symbol, the test fails — say why the output had to
change and re-verify with the scanner harness.

## Pull requests

1. One feature or fix per PR.
2. New renderers or CLI options need tests and a README row.
3. Keep tables in `spec.py` and the docs in sync; if you touch the tables,
   re-run the full conformance harness.

## Reporting bugs

Open an issue with the exact command line and the payload. If a scanner
cannot read a generated symbol, include the `--ascii` output and the
scanning device/app used.
