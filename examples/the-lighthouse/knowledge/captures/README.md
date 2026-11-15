<!-- managed by Collab Kit 0.5.0: rendered from tools/kb/config.toml by kit/install.py apply. Edit the config or the kit, not this file. To make it the project's own, delete this line. -->
# captures/

This project commits returns to git (`[returns].captures_in_git = true`): the integration job (`tools/kb/nightly.sh`) copies each one here exactly as it arrived. Never edited.

Returns left in the mirror's `_returns/` folder by conversations, copied here by the integration job (`tools/kb/nightly.sh`) exactly as they arrived. Never edited. Each one is registered as a source (`C01`, `C02`, ... in date order, through the `[[collections]]` entry in `tools/kb/manifest.toml`), so concepts, answers, and agenda items can cite it, and its substance is folded into concepts, answers, the agenda, or proposals by the curation pass.
