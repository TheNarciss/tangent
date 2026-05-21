"""Module finance — toute la logique mathématique et business du portfolio.

Organisation :
- analytics : fonctions math pures (log_returns, Sharpe, CVaR, Max DD, shrinkage cov, Kelly)
- market    : fetch + cache des données yfinance
- cma       : Capital Market Assumptions (μ blendés CMA + historique)
- envelopes : règles & éligibilité des livrets/PEL/AV
- fees      : tarification brokers (frais ordres, garde, etc.)
- dashboard : orchestration (calcule metrics + frontier + stress tests)
- optimizer : SLSQP optimal portfolios (Max Sharpe, Min Var, target vol, from_strategy)
- timeseries: historique des valorisations
- projection: projection Monte Carlo + reverse projection Bengen
- bengen    : règle des 4% (capital nécessaire pour revenu mensuel cible)
- stress    : stress tests historiques (COVID 2020, Inflation 2022, Banques 2023)
- glide_path: stock allocation Bogle 120-âge
- diagnostic: génération d'insights textuels sur le portfolio
- scanner   : découverte d'actifs PEA-éligibles via ΔSharpe marginal
"""
