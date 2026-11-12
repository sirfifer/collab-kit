# captures/

{{captures_note}}

Returns left in the mirror's `_returns/` folder by conversations, copied here by the integration job (`tools/kb/nightly.sh`) exactly as they arrived. Never edited. Each one is registered as a source (`C01`, `C02`, ... in date order, through the `[[collections]]` entry in `tools/kb/manifest.toml`), so concepts, answers, and agenda items can cite it, and its substance is folded into concepts, answers, the agenda, or proposals by the curation pass.
