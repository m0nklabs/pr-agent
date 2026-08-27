# PR-Piet fork-patch

Deze fork wijkt minimaal af van upstream [The-PR-Agent/pr-agent](https://github.com/The-PR-Agent/pr-agent).
Doel: **één modelcall** (`/review`) levert per key-issue óók een exacte fix
(`suggested_fix`), zodat de PR-Piet-stack (m0nklabs/pr-piet) daar
` ```suggestion ``` `-fences met GitHub "Apply"-knop van kan bouwen — zonder de
aparte `/improve`-call.

## Wijzigingen t.o.v. upstream

1. `pr_agent/settings/pr_reviewer_prompts.toml`
   - `KeyIssuesComponentLink` krijgt een conditioneel veld `suggested_fix`
     (Jinja `{%- if require_suggested_fix %}`), incl. voorbeelden in de
     system-prompt en het `duplicate_prompt_examples`-blok.
2. `pr_agent/tools/pr_reviewer.py`
   - `self.vars` krijgt `'require_suggested_fix':
     get_settings().pr_reviewer.get('require_suggested_fix', False)`
     (string-safe gecoerceerd, zoals `is_true()`).
3. `action.yaml`
   - `image: 'Dockerfile.github_action'` (from-source build) i.p.v.
     `Dockerfile.github_action_dockerhub` (**CRUCIAAL**: de dockerhub-variant
     is alleen `FROM pragent/pr-agent:github_action` — een prebuilt upstream
     image van Docker Hub. Zonder deze wijziging komt de fork-broncode nóóit
     in de container en heeft patch 1+2 geen effect; de settings zien de env-
     var wél, maar het draaiende pr-agent-pakket kent het veld niet.)

## Gedrag

- **Default (`pr_reviewer.require_suggested_fix = false`, upstream-default):
  identiek aan upstream.** Het veld wordt niet aan het model gevraagd; geen
  extra tokens, geen output-wijziging.
- Met `pr_reviewer.require_suggested_fix = true` (bijv. via GitHub Actions env
  `pr_reviewer.require_suggested_fix: "true"`) vraagt de reviewer-prompt het
  model per key-issue om de exacte vervangingscode voor
  `start_line..end_line`. Het veld stroomt ongewijzigd door naar de
  action-output (`github_action_config.enable_output=true`, key `review` →
  `key_issues_to_review[].suggested_fix`). De gerenderde markdown-body verandert
  niet (rendering leest alleen de bekende velden).

## Upstream sync-procedure

1. Sync de fork met upstream.
2. Her-appliqueer deze patch (2 files; zie git-blame op dit bestand voor de
   commit).
3. Her-test: Jinja-render van `pr_reviewer_prompts.toml` met
   `require_suggested_fix` true/false moet zonder `StrictUndefined`-errors
   renderen, en E2E op `m0nklabs/pr-piet-test`.
