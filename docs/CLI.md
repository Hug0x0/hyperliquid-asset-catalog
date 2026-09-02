# CLI reference

Run `hl-catalog --help` for the authoritative command tree. Typer generates completion from that
same tree: use `hl-catalog --show-completion` or `hl-catalog --install-completion` in the active
shell. Source the version-controlled wrappers in `completions/` for Bash, Zsh, or Fish when a
system-wide installation is preferred.

`hl-catalog query` reads the local catalog without network access. Repeat `--where FIELD=VALUE`,
choose a deterministic `--sort-by`, project comma-separated `--fields`, and cap output with
`--limit`. Table, JSON and JSONL formats are supported. Filters use exact case-insensitive matches.
