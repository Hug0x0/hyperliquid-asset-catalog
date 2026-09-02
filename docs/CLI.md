# CLI reference

Run `hl-catalog --help` for the authoritative command tree. Typer generates completion from that
same tree: use `hl-catalog --show-completion bash`, `zsh`, or `fish`, or run
`hl-catalog --install-completion` for the active shell.

`hl-catalog query` reads the local catalog without network access. Repeat `--where FIELD=VALUE`,
choose a deterministic `--sort-by`, project comma-separated `--fields`, and cap output with
`--limit`. Table, JSON and JSONL formats are supported. Filters use exact case-insensitive matches.
