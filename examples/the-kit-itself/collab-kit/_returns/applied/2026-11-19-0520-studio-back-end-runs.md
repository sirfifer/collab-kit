Project: collab-kit
Id: 2026-11-19-0520-studio-back-end-runs
From: Claude Code, working in knowledge-distillation-framework
Type: status
Topic: The Studio back end runs (W-006); one kit fix was needed and is on the kit's main line, not released

Changes v1:
status "2026-11-18: the Studio back end is installed and running (W-006). Richard ran the setup script; it stopped at the account check, because rclone has no config userinfo for Google Drive, so a back end over rclone refused every run. Fixed in the kit at commit 6fef702 on both Macs (the check now reads who owns the folder's start file with lsjson --metadata; 123 tests pass; changelog entry under Not yet released, VERSION unchanged). knowledge-distillation-framework is the first repository-homed project on it: a return filed in Drive was applied, pushed and mirrored back in 4 to 10 minutes. A full pass takes about 20 minutes because Drive is read one file at a time; that is worth a look. The used setup script is archived on the Studio."
End.
