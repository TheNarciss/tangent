"""Module finance — toute la logique mathématique et business du portfolio.

Organisation :
- analytics : fonctions math pures (log_returns, Sharpe, CVaR, Max DD, shrinkage cov, Kelly)
- market    : fetch + cache des données yfinance
- cma       : Capital Market Assumptions (μ blendés CMA + historique)
- envelopes : règles & éligibilité des livrets/PEL/AV
- withdrawal: taux de retrait soutenable (config/verdicts.yaml)
- fees      : tarification brokers (frais ordres, garde, etc.)
- dashboard : orchestration (calcule metrics + stress tests)
- optimizer : SLSQP optimal portfolios (Max Sharpe, Min Var, target vol, from_strategy)
- timeseries: historique des valorisations
- projection: projection Monte Carlo + reverse projection Bengen
- stress    : stress tests historiques (COVID 2020, Inflation 2022, Banques 2023)
"""
