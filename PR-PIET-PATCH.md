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
   - **Copilot-stijl (commit `1181155`, 2026-08-28):** de beschrijving van
     `suggested_fix` laat het model niet meer "empty string" gebruiken bij
     onzekerheid. In plaats daarvan: ALWAYS een concrete best-effort fix geven,
     óók voor een mogelijke/onzekere bevinding, en de bevinding markeren met een
     duidelijke onzekerheids-marker in `issue_content` (`UNCERTAIN: ...` /
     `not verified`). Empty alleen als er écht geen code-change de bevinding
     adresseert. Aanleiding: PR #8 (guardian-llmprovider-gateway) produceerde
     een key-issue met een lege `suggested_fix` (geen Apply-knop) omdat het
     model de "use empty string"-uitweg koos bij een onzekere bevinding.
   - E2E-bewijs (m0nklabs/pr-piet-test, probes met de fork): een bevinding
     krijgt nu wél een gevulde `suggested_fix` → ` ```suggestion ``` `-fence met
     Apply-knop. **Bekende beperking:** deepseek-v4-flash-0731 zet de
     `UNCERTAIN:`-markering niet consequent in de output (het model benoemt
     twijfel intern in de reasoning, maar drukt het zelden in `issue_content`);
     de best-effort-fix-kant werkt, de onzekerheids-vlag niet betrouwbaar.
2. `pr_agent/tools/pr_reviewer.py`
   - `self.vars` krijgt `'require_suggested_fix':
     get_settings().pr_reviewer.get('require_suggested_fix', False)`
     (string-safe gecoerceerd, zoals `is_true()`).
3. `action.yaml` + `Dockerfile.github_action`
   - `image: 'Dockerfile.github_action'` (from-source build) i.p.v.
     `Dockerfile.github_action_dockerhub` (**CRUCIAAL**: de dockerhub-variant
     is alleen `FROM pragent/pr-agent:github_action` — een prebuilt upstream
     image van Docker Hub. Zonder deze wijziging komt de fork-broncode nóóit
     in de container en heeft patch 1+2 geen effect; de settings zien de env-
     var wél, maar het draaiende pr-agent-pakket kent het veld niet.)
   - **Sync 2026-09-23:** upstream heeft `Dockerfile.github_action` verwijderd
     (commit `e8077630`, "fold github_action Dockerfile ... into existing
     definitions") en bouwt het GHA-image nu als target `github_action` in
     `docker/Dockerfile` (uv-gebaseerd: `uv sync --frozen` uit
     `pyproject.toml` + `uv.lock`, daarna `COPY pr_agent pr_agent`).
     GitHub docker-actions kunnen geen `--target` meegeven, dus deze fork
     houdt een standalone `Dockerfile.github_action` bij die de upstream
     `base`-stage + `github_action`-stage 1:1 kopieert. **Keep-in-sync:
     bij upstream-wijzigingen aan `docker/Dockerfile` die kopij herhalen.**
     E2E-les (pr-piet-test PR #15, run 35859322161): zonder dit bestand faalt
     de docker build met "Dockerfile.github_action: no such file or
     directory" — de merge dropt het bestand geruisloos (fork wijzigde
     action.yaml, upstream verwijderde het Dockerfile: geen conflict).
4. `pr_agent/algo/ai_handlers/litellm_ai_handler.py` (commit `3934878`)
   - Opt-in reasoning-budget voor OpenAI-compatibele gateway-modellen:
     `config.reasoning_max_tokens > 0` → `extra_body.reasoning.max_tokens=N`
     + logregel `Applying reasoning budget for {model}: reasoning.max_tokens={N}`.
     Gate: alleen modellen met prefix `openai/`. **Upstream heeft (na de
     litellm-refactor, 2026-09) wél native reasoning-budget, maar uitsluitend
     via `openrouter.reasoning_max_tokens` in `_apply_openrouter_request_controls`,
     dat alleen activeert voor `openrouter/`-modellen** — voor onze
     `openai/`-gerouteerde gateway-modellen (`openai/z-ai/glm-5.3-flash`)
     bestaat geen upstream-native equivalent, dus dit blok blijft nodig.
     PR-Piet zet `config.reasoning_max_tokens=32000` (workflow-env).

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
2. Verifieer dat ALLE patches uit "Wijzigingen t.o.v. upstream" de merge
   overleven — inclusief het bestand `Dockerfile.github_action`: git ziet
   "fork wijzigt action.yaml / upstream verwijdert Dockerfile" als
   non-overlapping en conflicteert NIET; de E2E docker-build is de enige
   betrouwbare controle.
3. Her-test: Jinja-render van `pr_reviewer_prompts.toml` met
   `require_suggested_fix` true/false moet zonder `StrictUndefined`-errors
   renderen, en E2E op `m0nklabs/pr-piet-test`.
