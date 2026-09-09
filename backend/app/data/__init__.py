"""External sources of truth.

Each module wraps one public provider and returns plain pandas/dict results.
Nothing here knows about a user, a portfolio or a verdict: consumers in
`app/finance` decide what to do with the numbers.

- `fred`       : taux, change, inflation (Federal Reserve St. Louis)
- `ecb`        : taux directeur et cours de référence (Banque centrale européenne)
- `eurostat`   : IPC harmonisé France
- `ken_french` : rendements mensuels de marché par région, depuis 1990
- `damodaran`  : rendements annuels des classes US (actions, obligations), depuis 1928
- `shiller`    : S&P 500, IPC et taux longs mensuels, depuis 1871
- `lbma`       : fixings or et argent, depuis 1968
- `openfigi`   : ISIN → ticker / place / nom

None of them needs an account or an API key (ADR-024). `probe.py` checks that
they still answer and reports their coverage.
"""
