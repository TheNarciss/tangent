# Changelog

## [1.1.0](https://github.com/TheNarciss/tangent/compare/v1.0.0...v1.1.0) (2026-06-02)


### Features

* **account:** full account management (password, OAuth, banks, delete) ([#33](https://github.com/TheNarciss/tangent/issues/33)) ([a503483](https://github.com/TheNarciss/tangent/commit/a50348391f292eea75d7c7818ffa372b715634a1))
* **accounts:** hide soft-deleted bank_accounts from list and get ([#45](https://github.com/TheNarciss/tangent/issues/45)) ([f5dc7c8](https://github.com/TheNarciss/tangent/commit/f5dc7c83fe5aaa0cf804517fa62e3d9014fbf2d9))
* **aggregator:** introduce IBankAggregator protocol + PowensAggregator skeleton (Phase A, ADR-008) ([de80eb6](https://github.com/TheNarciss/tangent/commit/de80eb6ae4da78f26d3aec3ba8ffc29422f1bf39))
* **aggregator:** merge Phase A multi-account aggregator foundations ([d9b4866](https://github.com/TheNarciss/tangent/commit/d9b48668652a89f7e0e7ed9a9c3b32f889463699))
* **api:** add /accounts routes for multi-account read + sync (Phase A3, ADR-008) ([4d84f9f](https://github.com/TheNarciss/tangent/commit/4d84f9f182d67e41dfe068fd0de490dd5680c5cf))
* **auth:** add Google OAuth login + account linking (ADR-014) ([#25](https://github.com/TheNarciss/tangent/issues/25)) ([1850d7c](https://github.com/TheNarciss/tangent/commit/1850d7cea021482d0eb35e0f169d03bf1bbfd4f7))
* **bridge:** include checking account balances in legacy cash ([431f1c4](https://github.com/TheNarciss/tangent/commit/431f1c4cde36519110608ba599e7531bbb36cfbe))
* **db:** add multi-account tables + repos + tests (Phase A2, ADR-008) ([7ba5c51](https://github.com/TheNarciss/tangent/commit/7ba5c51638bb5fb5327e494aaa5ec103469939be))
* **frontend:** add 'Comptes' tab with bank accounts, holdings + transactions (Phase A4, ADR-008) ([79f3592](https://github.com/TheNarciss/tangent/commit/79f359202a220741d97965a1b038501b0fb224cf))
* **legal:** add privacy, terms, about pages (GDPR + DSP2) ([#28](https://github.com/TheNarciss/tangent/issues/28)) ([d06e7ba](https://github.com/TheNarciss/tangent/commit/d06e7baa7504363225bef3d8e98a52345ff6ac09))
* **legal:** add privacy, terms, about pages (GDPR + DSP2) ([#28](https://github.com/TheNarciss/tangent/issues/28)) ([#29](https://github.com/TheNarciss/tangent/issues/29)) ([b4860b1](https://github.com/TheNarciss/tangent/commit/b4860b1b34d53e7ae0806a8f54014a9639b12362))
* **llm,ui:** SSE review endpoints + IA tab as landing page (5+6/6) ([#49](https://github.com/TheNarciss/tangent/issues/49)) ([4c716b5](https://github.com/TheNarciss/tangent/commit/4c716b5ea89cee360a8f7f22536a5fe7e6097ffd))
* **llm:** bootstrap LLM module per ADR-015 ([#46](https://github.com/TheNarciss/tangent/issues/46)) ([f99c842](https://github.com/TheNarciss/tangent/commit/f99c8423b7a06c049cc2158115da06753281b1ae))
* **llm:** cost tracker with USD 5/day kill switch ([#47](https://github.com/TheNarciss/tangent/issues/47)) ([3648d02](https://github.com/TheNarciss/tangent/commit/3648d020ae75eb0dc13cf33c2c3765797cff464a))
* **llm:** prompt builder + review generator (3+4/6) ([#48](https://github.com/TheNarciss/tangent/issues/48)) ([a15349c](https://github.com/TheNarciss/tangent/commit/a15349cdcbab0c4ec474f4ea534487f582fca072))
* **optimizer:** explicit reason when efficient frontier cannot be plotted ([#44](https://github.com/TheNarciss/tangent/issues/44)) ([1515506](https://github.com/TheNarciss/tangent/commit/151550652e41f806120c18e16b9506d9094dd05a))
* **powens:** extended BankAccount schema + Loan support (ADR-013 Phase 1) ([#21](https://github.com/TheNarciss/tangent/issues/21)) ([deca123](https://github.com/TheNarciss/tangent/commit/deca123b76d0877debd65ccc3ad8a5f3170510fb))
* **powens:** map institution_name from /connections to BankAccount ([820d475](https://github.com/TheNarciss/tangent/commit/820d4752d00f7f25d2f4e82912c2f617b66f31a6))
* **prod:** multi-stage Caddy image with frontend Vite build baked in ([9bfa31b](https://github.com/TheNarciss/tangent/commit/9bfa31bc79e108e2fd9a5a080dc960ed3c1ba489))
* **prod:** SPA via Caddy + accordion + bridge test + tech debt cleanup ([8f345fb](https://github.com/TheNarciss/tangent/commit/8f345fb3f101bb2c4274d153408553e62f17a888))
* **profile,projection:** UI broker selector + multi-broker warning ([#41](https://github.com/TheNarciss/tangent/issues/41)) ([3f57730](https://github.com/TheNarciss/tangent/commit/3f5773055793b777cc07740e7691b75f0afc9acd))
* **profile:** per-user default_broker with autodetect at first sync ([#40](https://github.com/TheNarciss/tangent/issues/40)) ([d9c8dce](https://github.com/TheNarciss/tangent/commit/d9c8dce7a006a8ce90c5dc522e42ab7c097e5e7e))
* **ui:** rich account cards grouped by category ([#22](https://github.com/TheNarciss/tangent/issues/22)) ([0595fe9](https://github.com/TheNarciss/tangent/commit/0595fe9d69ec08d35e2a18caabbed032d0a22b8a))
* **wealth:** introduce Wealth domain model (Phase 2 PR 1/6) ([#34](https://github.com/TheNarciss/tangent/issues/34)) ([fc3a979](https://github.com/TheNarciss/tangent/commit/fc3a9798311fbe2a8309513ba5df1dcfac5579ec))
* **wealth:** migrate Aperçu to surface net worth + livrets + loans (Phase 2 PR 2/6) ([#35](https://github.com/TheNarciss/tangent/issues/35)) ([b0d1e45](https://github.com/TheNarciss/tangent/commit/b0d1e45e0997f9361447a4dcce780348afac4496))
* **wealth:** remove legacy Portfolio/Position (Phase 2 PR 6/6) [BREAKING] ([#38](https://github.com/TheNarciss/tangent/issues/38)) ([ee8e6e0](https://github.com/TheNarciss/tangent/commit/ee8e6e036c2eff266716ff10eea3152350fc6351))


### Bug Fixes

* **accounts:** guard double-sync with synchronous in-flight ref ([#43](https://github.com/TheNarciss/tangent/issues/43)) ([85cc1b6](https://github.com/TheNarciss/tangent/commit/85cc1b6ece334364a65e61b19da2ed019d21db85))
* **accounts:** move /connections route before /{account_id} (was 422'd) ([f8fed34](https://github.com/TheNarciss/tangent/commit/f8fed343a4a686b7d536397bd271560c7f1bcb57))
* **accounts:** remove orphan %d in _do_sync log format string ([#42](https://github.com/TheNarciss/tangent/issues/42)) ([ce7de19](https://github.com/TheNarciss/tangent/commit/ce7de190e0023eca22801a51a61edc379a9fec52))
* **caddy:** force X-Forwarded-Proto: https for backend (OAuth fix) ([#27](https://github.com/TheNarciss/tangent/issues/27)) ([818d945](https://github.com/TheNarciss/tangent/commit/818d945e1fd860371939f0d67c1448a35614783d))
* **caddy:** proxy /accounts/* routes to backend ([18046dc](https://github.com/TheNarciss/tangent/commit/18046dca8400d443a1efb0274bc8242b61f4db23))
* **caddy:** use handle blocks to prevent try_files from rewriting API paths ([be6b3c6](https://github.com/TheNarciss/tangent/commit/be6b3c639c549bd327e35c4102981847a7631413))
* **ci:** increase CD timeout to 30min + add Docker cleanup step ([1753658](https://github.com/TheNarciss/tangent/commit/1753658d4ee9c22ae280923846a25b8f33b01115))
* **ci:** reload caddy after deploy to pick up Caddyfile changes ([e6d9948](https://github.com/TheNarciss/tangent/commit/e6d99481e38acc5b32e4bd159804b1223d237259))
* **deploy:** uvicorn --proxy-headers for HTTPS redirect_uri ([#26](https://github.com/TheNarciss/tangent/issues/26)) ([6a48a64](https://github.com/TheNarciss/tangent/commit/6a48a64f6c19c6089854485fa84ba3de65363aa3))
* **holdings:** UPSERT + orphan cleanup + advisory lock to dodge race on concurrent sync ([d7344a5](https://github.com/TheNarciss/tangent/commit/d7344a5d4fa13b2d305b437dc10d6cf16052ecb3))
* **portfolio:** flush deletes before inserts in replace_positions ([35ce13a](https://github.com/TheNarciss/tangent/commit/35ce13a56a7dd6edf61db3a110c2c55e93fa6a33))
* **powens:** expand connector and bank in /connections to get institution name ([27bb0a2](https://github.com/TheNarciss/tangent/commit/27bb0a2cf48cd50977537643bd6cb7828125432c))
* **powens:** map institution_name from /connections, set last_synced_at ([e8c81ca](https://github.com/TheNarciss/tangent/commit/e8c81ca3a93223524ead5bd5020bb85853a732da))
* **powens:** restore market_suffixes block in powens.yaml ([d1fd42f](https://github.com/TheNarciss/tangent/commit/d1fd42f31f19656b95ac93c213fcf49479801782))
* **powens:** use /accounts/sync instead of legacy /sync/powens after OAuth callback ([9bbddad](https://github.com/TheNarciss/tangent/commit/9bbddad0bc006fe8ecc500324d73c651f1c0a53e))
* **powens:** use temporary_code to add banks to same Powens user ([#31](https://github.com/TheNarciss/tangent/issues/31)) ([87d0ef8](https://github.com/TheNarciss/tangent/commit/87d0ef8068b7a3c283a4f02c302121967e0720ed))
* **prod:** align container names (tangent-caddy) ([08b641d](https://github.com/TheNarciss/tangent/commit/08b641d545c3cc99793b59adc7bd0311d0351422))
* **prod:** unblock Phase A - subprocess alembic, no --reload, Tabs unconditional, legacy bridge ([6f9abe1](https://github.com/TheNarciss/tangent/commit/6f9abe1d7a32314e496582f2eeb7486fa27ffa9a))
* **profile:** convert raw % to fraction at API boundary + strip extra fields ([f99f684](https://github.com/TheNarciss/tangent/commit/f99f68429236be60e0eecea1e9d78cd7d9c41e91))
* **ui:** minor tweak on account cards ([#23](https://github.com/TheNarciss/tangent/issues/23)) ([394dde6](https://github.com/TheNarciss/tangent/commit/394dde69caa7185b6f5a3637ef2f3ef25b646ae9))
* **wealth:** pass ticker+qty+avg_cost to _asset_metric instead of stale position ([88373ef](https://github.com/TheNarciss/tangent/commit/88373efc504439fd28feca59939935316def2187))


### Performance Improvements

* **docker:** add BuildKit cache mount for npm ([eaf3844](https://github.com/TheNarciss/tangent/commit/eaf3844248b5ed0fc709f644656ed9f528015eef))
* **docker:** add BuildKit cache mount for pip ([2ae836f](https://github.com/TheNarciss/tangent/commit/2ae836fc0b50b6b781feb3b0dbf6769924cc44bd))

## 1.0.0 (2026-05-24)


### Features

* add adr ([3fa4b70](https://github.com/TheNarciss/tangent/commit/3fa4b70031f81096d77a1ccef8429d053e02bf45))
* add assets search and fix ux / ui ([4a89171](https://github.com/TheNarciss/tangent/commit/4a891718dfb8105d59b8ccd2664524a9f33c7101))
* **db:** switch from create_all to Alembic migrations ([e21a444](https://github.com/TheNarciss/tangent/commit/e21a444d9be6367f24e5adbebd9ca364f1d01c4b))
* **fees:** broker fees from YAML, applied per-month in DCA projection ([2c67023](https://github.com/TheNarciss/tangent/commit/2c6702364140a9acfbdb4573102a6936d3eef09a))


### Bug Fixes

* **ci:** embed token in fetch URL to bypass macOS keychain ([fbe9786](https://github.com/TheNarciss/tangent/commit/fbe978690b51b55a72e1f9ad9cc72523e86808f4))
* **ci:** use GITHUB_TOKEN for git fetch on self-hosted runner ([764dd5b](https://github.com/TheNarciss/tangent/commit/764dd5ba76ecc7f77657bf78f4ada234b1ea30c2))
* **frontend:** replace 'any' with 'unknown' in migrate() helpers ([866c10c](https://github.com/TheNarciss/tangent/commit/866c10c70a947dc64d2aa3c88a999eeaf290533e))
* **security:** resolve Semgrep findings + re-enable strict mode ([5072fd8](https://github.com/TheNarciss/tangent/commit/5072fd8875541798bc0207430fc222ee219507c0))
* **tests:** align asyncio_default_test_loop_scope to session ([d298dd3](https://github.com/TheNarciss/tangent/commit/d298dd3628539579fca1764fa13f77a67d9d992c))
* **tests:** use Alembic in conftest instead of create_all ([95e41ed](https://github.com/TheNarciss/tangent/commit/95e41ed7f7245695c409c6ee6947d70739f45b40))
* **typing:** resolve 17 mypy errors across 5 files ([afcb746](https://github.com/TheNarciss/tangent/commit/afcb7466aece622f7a349a3a6d5efab7950da688))
