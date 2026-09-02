# TradeXYZ documentation monitoring

Documentation enrichment is disabled by default. Operators may run
`hl-catalog monitor-tradexyz-docs URL` for an explicitly selected page. The command respects the
site's `robots.txt`, identifies columns by header name rather than position, caches results for one
day, and exits with code 2 when a supported symbol table disappears or its headers change.

Documentation can only enrich instruments already returned by Hyperliquid's public API; it cannot
create a tradable market. Review the site's terms before enabling redistribution.
