# PLAN.md — QAIA (QA Intelligence Agent)

> Document de cadrage. **Aucun code n'est écrit tant que ce plan n'est pas validé.**
> Objet : poser un squelette propre et extensible sur la **tranche MVP**, sans construire
> l'E2E, le self-healing ni le ticketing.

---

## 1. Objectif & périmètre

### Vision finale (contexte — **PAS** à construire maintenant)
- **Entrée** : feature Gherkin **OU** ticket (Jira/Linear via MCP).
- **Génération** : tests API (pytest + httpx) **ET** E2E (Playwright).
- **Sortie** : code des tests + **PR GitHub** ; la CII fait tourner les tests sur la PR.
- **Deux modules découplés et interchangeables** :
  1. **GÉNÉRATION** — déterministe, relisable, appel API Anthropic one-shot, sortie structurée.
  2. **EXÉCUTION + SELF-HEALING** — agentique, `claude -p` headless en subprocess, en sandbox `--allowedTools`.

### Tranche à construire MAINTENANT (et uniquement ça)
`.feature` Gherkin → **génération structurée via l'API Anthropic** → écriture dans
`tests/generated/` → **ouverture d'une PR GitHub**.
Pas d'E2E, pas de self-healing, pas de ticketing. Leurs *coutures* (ports, enums, package
`execution/` vide, `allowed_tools.yaml`) sont **réservées mais non implémentées**.

### Modèle retenu : Ports & Adapters (hexagonal)
Le cœur = quelques types de domaine Pydantic + des `Protocol`. Les adapters dépendent des
ports, **jamais les uns des autres**. GÉNÉRATION et (futur) EXÉCUTION ne communiquent **que**
via le type de domaine `GeneratedTestSuite` → ils n'importent jamais l'un l'autre. C'est ce qui
rend le futur **additif** (un nouveau `SpecLoader` pour Jira/Linear, un nouveau `TestGenerator`
pour Playwright) au lieu d'une réécriture.

---

## 2. Structure du dépôt

```
gotyeah-QAIA/
├── CLAUDE.md                       # Conventions + Sécurité (source de vérité)
├── README.md
├── PLAN.md                         # ce document
├── pyproject.toml                  # PEP 621 ; deps + ruff + mypy(strict) + pytest
├── uv.lock                         # lock reproductible (uv)
├── .python-version                 # 3.12
├── .env.example                    # NOMS uniquement : ANTHROPIC_API_KEY=  GITHUB_TOKEN=  GITHUB_REPO=
├── .gitignore                      # .env, __pycache__, ...
├── .dockerignore
├── .pre-commit-config.yaml         # ruff, mypy, gitleaks/detect-secrets
├── Dockerfile                      # multi-stage, python:3.12-slim (pin par digest), non-root, arm64
├── docker-compose.yml              # runtime Pi : env_file, read_only, cap_drop:[ALL], no-new-privileges
├── config/
│   └── allowed_tools.yaml          # FUTURE whitelist --allowedTools — déclarée, INUTILISÉE au MVP
├── src/
│   └── qaia/
│       ├── settings.py             # pydantic-settings ; SecretStr ; env-only ; fail-fast
│       ├── logging.py              # logging structuré + filtre de redaction des secrets
│       ├── domain/
│       │   ├── models.py           # SpecInput, LlmTestArtifacts, GeneratedTestSuite, ... enums
│       │   └── errors.py           # hiérarchie d'exceptions typées
│       ├── ports.py                # Protocols : SpecLoader, StructuredLLM, TestGenerator,
│       │                           #   TestWriter, PrPublisher, Executor (FUTURE stub)
│       ├── pipeline.py             # composition root : load → generate → write → publish
│       ├── cli.py                  # Typer : `qaia generate <feature>` (entrypoint MVP)
│       ├── api/
│       │   ├── app.py              # FastAPI : /health + /version SEULEMENT au MVP
│       │   └── deps.py             # wiring DI + dépendance bearer-auth réservée (futur trigger)
│       ├── specs/
│       │   └── feature_loader.py   # FeatureFileSpecLoader : lit + valide léger .feature → SpecInput
│       ├── generation/             # MODULE 1 — déterministe, AUCUN shell/tool/FS hors Anthropic
│       │   ├── client.py           # AnthropicStructuredLLM : wrap messages.parse(...)
│       │   ├── prompts.py          # prompts versionnés et relisables
│       │   └── generator.py        # PytestHttpxGenerator(TestGenerator) → GeneratedTestSuite
│       ├── writer/
│       │   └── file_writer.py      # LocalFsTestWriter : écriture confinée à tests/generated/
│       ├── github/
│       │   └── pr.py               # GitHubPrPublisher : REST GitHub via httpx (pas de subprocess)
│       └── execution/              # FUTUR module — package vide + README (frontière sandbox)
├── examples/
│   └── sample.feature
├── tests/                          # tests DE L'OUTIL (≠ tests générés)
│   ├── conftest.py                 # fakes ; exclut tests/generated/ de la collecte
│   ├── unit/                       # settings, feature_loader, generator (mock LLM),
│   │                               #   file_writer (anti path-traversal), pr (httpx.MockTransport)
│   ├── integration/test_pipeline.py
│   ├── fixtures/sample.feature
│   └── generated/.gitkeep          # puits de sortie ; exclu de la collecte pytest
└── .github/workflows/
    ├── ci.yml                      # ruff + mypy --strict + pytest (tout mocké, sans secret)
    ├── deploy.yml                  # buildx arm64 → GHCR → SSH vers le Pi (main, env protégé)
    └── generated-tests.yml         # exécute tests/generated/ sur les PR (sandbox runner GitHub)
```

---

## 3. Modules & responsabilités (cœur)

| Fichier | Responsabilité |
|---|---|
| `settings.py` | Config typée, **env-only** (pydantic-settings). Clés en `SecretStr` (non imprimables). Champs : `github_repo`, `default_base_branch="main"`, `generation_model="claude-sonnet-4-6"`, `max_tokens=16000`, `generated_tests_dir=Path("tests/generated")`, `branch_prefix="qaia"`. **Fail-fast** si une clé requise manque. |
| `domain/models.py` | Types Pydantic v2 partagés à travers toutes les coutures. Sépare le **schéma rempli par le LLM** (`LlmTestArtifacts`) de **l'objet de domaine** (`GeneratedTestSuite`, qui ajoute la provenance : `test_kind`, `feature_name`). Enums `SourceKind`/`TestKind` → E2E/Playwright et Jira/Linear deviennent additifs. |
| `ports.py` | Les coutures comme `Protocol` **uniquement** (zéro implémentation). |
| `pipeline.py` | Composition linéaire typée sur les ports : `load → generate → write → publish`. Param `executor` optionnel (no-op aujourd'hui) = point d'insertion du futur self-healing entre `write` et `publish`. |
| `cli.py` | `qaia generate <feature>` (Typer). Job **run-and-exit** : la plus petite surface d'attaque pour un process qui détient des creds (dépense API + write GitHub). |
| `api/app.py` | FastAPI **minimal** : `/health` + `/version` seulement au MVP. Pas d'endpoint de génération non authentifié sur un Pi qui détient des secrets. |
| `specs/feature_loader.py` | Lit le `.feature`, validation légère in-house (présence de `Feature:`, extraction du nom), renvoie `SpecInput` portant le **texte Gherkin brut**. Pas de parser Gherkin lourd : le modèle parse nativement. |
| `generation/client.py` | **Seul** fichier qui touche le SDK. `messages.parse(model="claude-sonnet-4-6", output_format=LlmTestArtifacts)`. Pur : pas de shell/subprocess/FS/MCP. |
| `generation/generator.py` | `PytestHttpxGenerator` : appelle le port LLM, reçoit `LlmTestArtifacts`, l'emballe en `GeneratedTestSuite` en **estampillant la provenance** (que le LLM ne possède pas). |
| `writer/file_writer.py` | **Frontière de sortie** : sanitize chaque nom de fichier, rejette `/ \ ..` et chemins absolus, vérifie que le chemin résolu reste **dans** `tests/generated/`, écrit en UTF-8 inerte (jamais importé/exécuté). |
| `github/pr.py` | Ouvre la PR via **REST GitHub sur httpx** (pas de `gh` CLI → pas de subprocess). Ne pousse jamais sur la branche par défaut, ne merge jamais. |
| `execution/` | **Futur** : package vide + README documentant la frontière sandbox/`--allowedTools`. Sa vacuité *garantit* que la génération n'a aucune capacité d'exécution. |

---

## 4. Interfaces (ports) — les coutures stables

```python
# SpecInput(feature_name: str, raw_text: str, source_kind: SourceKind)
class SpecLoader(Protocol):
    source_kind: ClassVar[SourceKind]
    def load(self, ref: Path) -> SpecInput: ...

T = TypeVar("T", bound=BaseModel)
class StructuredLLM(Protocol):
    def parse(self, *, model: str, max_tokens: int, system: str,
              messages: list[dict[str, object]], output_format: type[T]) -> T: ...

# GenerationOptions(model: str, max_tokens: int, extra_instructions: str | None)
class TestGenerator(Protocol):
    test_kind: ClassVar[TestKind]
    def generate(self, spec: SpecInput, options: GenerationOptions) -> GeneratedTestSuite: ...

class TestWriter(Protocol):
    def write(self, suite: GeneratedTestSuite, dest: Path) -> list[Path]: ...

# PublishTarget(repo, base_branch, branch_prefix, title, body, labels)
# PublishResult(pr_url, branch, commit_sha)
class PrPublisher(Protocol):
    def publish(self, suite: GeneratedTestSuite, target: PublishTarget) -> PublishResult: ...

# --- FUTUR (déclaré, non implémenté au MVP) ---
# ExecutionContext(workspace, allowed_tools: list[str], max_iterations, timeout_seconds)
class Executor(Protocol):
    def run_and_heal(self, suite: GeneratedTestSuite, ctx: ExecutionContext) -> ExecutionReport: ...
```

La signature `Executor` **porte déjà la whitelist `allowed_tools`** : le contrat de sandbox est
encodé avant qu'une seule ligne d'exécution n'existe.

---

## 5. Contrat de génération

- **Un seul appel déterministe** :
  `messages.parse(model="claude-sonnet-4-6", max_tokens=16000, system=<instructions QA>, messages=[{role:"user", content:<Gherkin brut>}], output_format=LlmTestArtifacts)`.
  Pas de prefill, pas de `budget_tokens`, `thinking` omis (déterminisme).
- **Schéma plat** (bon pour `json_schema` + `additionalProperties=false`) — le LLM ne possède que le contenu, pas la provenance :
  ```python
  class GeneratedFile(BaseModel):
      filename: str; content: str; description: str
  class LlmTestArtifacts(BaseModel):           # == schéma output_format
      files: list[GeneratedFile]; requirements: list[str]; notes: str | None = None
  class GeneratedTestSuite(BaseModel):         # objet de domaine estampillé
      test_kind: TestKind; feature_name: str
      files: list[GeneratedFile]; requirements: list[str]; notes: str | None = None
  ```
- **Consigne au modèle** : un test pytest par scénario Gherkin ; cibler la fixture **`base_url`/`client`** (jamais d'URL en dur) ; asserter status + body par scénario. Le générateur émet aussi un **`conftest.py`** dont la fixture lit la variable d'env **`BASE_URL`** (convention validée §13.2).
- **Mapping → `tests/generated/`** : `LocalFsTestWriter` valide chaque `filename` (`^test_[A-Za-z0-9_]+\.py$`), confine dans `tests/generated/`, écrit en texte inerte, et émet un `generation_manifest.json` (feature, fichiers, model id, timestamp) pour la provenance/PR. **La même liste `suite.files` en mémoire** est ce que commit la PR → disque et PR ont une source unique.

---

## 6. Flux PR GitHub

`GitHubPrPublisher` via **REST GitHub sur httpx** (Bearer `GITHUB_TOKEN`), **Git Data API** (pas de checkout local → marche dans un conteneur arm64 minimal) :
1. `GET …/git/ref/heads/{base}` → SHA + tree de base ;
2. créer un blob par fichier ;
3. `POST` un nouveau tree au-dessus du tree de base ;
4. `POST` un commit (1 commit, tous les fichiers) ;
5. `POST` une branche unique `qaia/<feature-slug>-<short-uuid>` ;
6. `POST …/pulls` (titre dérivé du nom de feature ; body = feature source + nb de scénarios + descriptions + model id ; label `qaia:generated`).

**Règles dures** : jamais cibler/pousser la branche par défaut, jamais d'auto-merge → **la PR est la barrière de revue humaine**. Choix `httpx` (vs PyGithub/`gh`) : typage complet, zéro binaire, **pas de subprocess** (respecte la frontière no-shell de la génération), entièrement mockable via `httpx.MockTransport`.

---

## 7. Modèle de sécurité (frontière de privilège dure)

- **GÉNÉRATION = transform pur texte→données structurées.** Aucun shell, aucun subprocess (PR via httpx), aucun MCP/tool, aucune écriture hors `tests/generated/`.
  *Pourquoi* : un `.feature` est une **entrée non fiable** et un vecteur d'injection de prompt. Privée de capacité, le pire qu'une spec hostile produit = du *texte de test* qu'un humain relit en PR.
- **Code généré = donnée non fiable** : jamais `eval`/`exec` par l'outil ni sur le Pi. Il s'exécute uniquement dans la CI de la PR (sandbox éphémère GitHub) et, plus tard, dans la sandbox d'exécution dédiée.
- **Secrets** : exactement deux — `ANTHROPIC_API_KEY` (auto-lue par le SDK ; on vérifie juste la présence) et `GITHUB_TOKEN`. **Env-only**, `SecretStr`, filtre de redaction des logs, `.env` gitignored, `.env.example` = noms seulement, hook **gitleaks/detect-secrets**.
- **GitHub token** : PAT fine-grained, scope minimal (`Contents: write` + `Pull requests: write`) sur **un** dépôt cible.
- **Sandbox future anticipée maintenant** : `Executor` prend une whitelist `allowed_tools` explicite ; `config/allowed_tools.yaml` en est le foyer versionné/diffable ; l'exécution tournera en **subprocess dans un conteneur durci séparé** — la whitelist `--allowedTools` appartient **uniquement** à l'exécution.
- **Runtime Pi (arm64)** : image `python:3.12-slim` multi-stage (pin par digest), `USER` non-root, `read_only` rootfs + tmpfs, `cap_drop:[ALL]`, `no-new-privileges`, HEALTHCHECK ; secrets via `env_file` root:0600, jamais dans les layers.

---

## 8. CLAUDE.md (plan des sections)

Project Overview · Architecture & frontières de modules · Repository Layout · Dev Workflow (uv) ·
Conventions de code (3.12, type hints, mypy --strict, ruff, Pydantic v2) · Configuration (env-only, SecretStr) ·
Contrat du module Génération · Conventions PR GitHub · **Sécurité (section obligatoire)** ·
Testing · CI/CD & Deploy · Docker / Runtime Pi · Guide d'extension (nouveau SpecLoader / TestGenerator / Executor).

---

## 9. Stratégie de tests (de l'outil lui-même)

`tests/generated/` **exclu** de la collecte (jamais importé). Couches :
- `test_settings.py` : secrets chargés depuis l'env, jamais dans `repr`/log ;
- `test_feature_loader.py` : validation `.feature` + extraction du nom + rejet du malformé ;
- `test_generator.py` : **`FakeStructuredLLM`** (zéro réseau) → on vérifie l'estampillage `test_kind`/`feature_name`. *C'est ainsi qu'on mocke l'appel Anthropic : le SDK est caché derrière le port `StructuredLLM`.*
- `test_file_writer.py` : **suite critique** anti path-traversal (`../x`, `/etc/x`, `a/b.py`, noms non conformes → `UnsafePathError`) ;
- `test_pr.py` : `httpx.MockTransport` → séquence exacte ref/blob/tree/commit/ref/pulls + jamais la branche par défaut ;
- `integration/test_pipeline.py` : pipeline complet câblé avec fakes.
CI = ruff + mypy --strict + pytest **entièrement mocké** (ni secret ni réseau sur le runner).

---

## 10. Choix techniques retenus (par défaut — modifiables)

| Sujet | Choix | Justification courte |
|---|---|---|
| Gestionnaire de paquets | **uv** (`pyproject.toml` + `uv.lock`) | Rapide, lock reproductible, gère le toolchain 3.12, builds arm64 déterministes. PEP 621 → rien ne nous y enferme. |
| SDK LLM | **anthropic** | Imposé. Clé auto-lue de l'env. `messages.parse(output_format=…)` = voie structurée connue-bonne. |
| Modèles/config | **pydantic v2 + pydantic-settings** | Le `BaseModel` est à la fois le contrat inter-module ET le `output_format`. `SecretStr` = secrets non imprimables. |
| PR GitHub | **httpx (REST brut)** | Déjà présent (transitive d'anthropic) ; runtime des tests générés ; pas de binaire ; mockable. |
| CLI | **Typer** | Typé, mypy-friendly ; entrypoint run-and-exit = surface d'attaque minimale. |
| API | **FastAPI + uvicorn** (minimal) | Imposé par la stack/déploiement ; volontairement réduit (`/health`,`/version`). |
| Qualité | mypy --strict, ruff, pytest, pre-commit, gitleaks | « mypy-clean + tests sur l'outil ». Mocks via `httpx.MockTransport` + fakes (pas de lib mock en plus). |

---

## 11. Ordre de construction du slice (une fois validé)

1. `pyproject.toml` (uv) + tooling (ruff/mypy/pytest/pre-commit) + `CLAUDE.md`.
2. `domain/models.py` + `domain/errors.py` + `ports.py` (les coutures d'abord).
3. `settings.py` + `logging.py`.
4. `specs/feature_loader.py` + `examples/sample.feature` (+ tests).
5. `generation/` (client + prompts + generator) avec `FakeStructuredLLM` (+ tests).
6. `writer/file_writer.py` (+ tests anti-traversal).
7. `github/pr.py` (+ tests `httpx.MockTransport`).
8. `pipeline.py` + `cli.py` (+ `integration/test_pipeline.py`).
9. `api/app.py` minimal + `Dockerfile` + `docker-compose.yml`.
10. `.github/workflows/` (ci, generated-tests, deploy).
11. `execution/` (README) + `config/allowed_tools.yaml` (réservation, non implémenté).

---

## 12. Hypothèses (à corriger si fausses)

- BUILD NOW = seulement le slice ; les coutures du futur sont réservées mais **non** construites.
- **La PR est la barrière humaine** ; rien n'est auto-mergé ; l'outil n'exécute **jamais** le code généré au MVP.
- **CLI + FastAPI** livrés tous deux, mais le **CLI** (`qaia generate`) est l'entrypoint opérationnel ; FastAPI = `/health`+`/version` seulement.
- `.feature` envoyé en **Gherkin brut** au modèle (validation légère uniquement, pas de parser lourd).
- Génération **one-shot** `claude-sonnet-4-6`, `thinking` omis, `max_tokens=16000`.
- Cible : Python 3.12, Docker **arm64** sur le Pi 5 ; images cross-build via buildx → GHCR.
- L'accesseur exact du résultat parsé (`.parsed_output`) est confirmé contre le SDK installé et isolé dans `AnthropicStructuredLLM`.

---

## 13. Décisions (validées)

1. **Cible des PR** — `GITHUB_REPO` lu depuis l'env, **fourni plus tard par l'utilisateur** (dépôt pas encore en place). Le code reste repo-agnostique ; `PublishTarget.repo` est un paramètre. Aucun blocage pour construire : les tests PR sont entièrement mockés (`httpx.MockTransport`).
2. **URL du SUT** — **`BASE_URL` (variable d'env) + fixture `conftest` générée**. Le générateur émet aussi un `conftest.py` avec une fixture `base_url`/`client` httpx lisant `BASE_URL` ; le modèle est instruit de cibler cette fixture, jamais une URL en dur.
3. **Auth GitHub** — **PAT fine-grained**, scope minimal `Contents: write` + `Pull requests: write` sur le dépôt cible. Acquisition du token isolée dans `GitHubPrPublisher` → bascule vers GitHub App possible plus tard sans toucher au flux PR.
4. **Périmètre entrypoint MVP** — **CLI-first + FastAPI minimal** : `qaia generate <feature>` opérationnel ; FastAPI = `/health` + `/version` seulement.

**Différée (hors slice, à trancher au moment du déploiement)** :
- **Accès du runner GitHub Actions au Pi pour le SSH deploy** — Tailscale/WireGuard (reco) / Cloudflare Tunnel / port-forward. Non bloquant pour le slice génération→PR.
