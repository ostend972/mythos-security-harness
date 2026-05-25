<div align="center">

# 🜲 Mythos Preview

### Harnais multi-agents de découverte de vulnérabilités pour Claude Code

*Conçu pour les opérateurs qui veulent **des findings avec PoC, pas des paragraphes de "potentiellement"**.*

[🇬🇧 English](README.md) &nbsp;·&nbsp; **🇫🇷 Français**

[![Status](https://img.shields.io/badge/status-V1%20ship-success?style=flat-square)](docs/V1-ACCEPTANCE.md)
[![Tests](https://img.shields.io/badge/tests-436%20passing-brightgreen?style=flat-square)](tests/)
[![Sandbox](https://img.shields.io/badge/red--team-6%2F6%20bloqu%C3%A9s-success?style=flat-square)](docs/SECURITY.md)
[![Modèle](https://img.shields.io/badge/mod%C3%A8le-Opus%204.7%20%C2%B7%20effort%3Dmax-blueviolet?style=flat-square)](https://code.claude.com/docs/fr/sub-agents)
[![Plateforme](https://img.shields.io/badge/Win11%20%C2%B7%20macOS%20%C2%B7%20Linux-support%C3%A9-informational?style=flat-square)](docs/OPERATIONS.md)
[![Licence](https://img.shields.io/badge/licence-Apache%202.0-lightgrey?style=flat-square)](LICENSE)

</div>

---

## Ce que ça fait

Tu pointes Mythos sur un dépôt de code. Huit agents spécialisés le décortiquent en parallèle, chacun chassant une classe de vulnérabilité dans une fonction à la fois. Les hunters écrivent du code de proof-of-concept, le compilent dans une sandbox Docker hardenée et l'exécutent. Un validateur adversarial génère **son propre PoC indépendant** pour chaque trouvaille et drop tout ce qui ne reproduit pas deux fois.

Ce que tu récupères, c'est un `report.md` de bugs sur lesquels tu peux agir — chacun adossé à un PoC exécutable, trié par sévérité × atteignabilité. Pas de "peut-être", pas de "potentiellement", pas de "en théorie".

## Le pipeline

```
                  ┌─────────────────────────────────────────────────────────────────┐
                  │                  CLAUDE CODE  ·  /mythos start                  │
                  └────────────────────────────┬────────────────────────────────────┘
                                               ▼
   ┌─── 1. RECON ─────┐    archi + build + 100-500 tâches étroites
   │  mythos-recon    │ ────────────────────────────────────────────► architecture.md
   │ spawn scouts × N │                                                task-queue.jsonl
   └──────────────────┘
                                               ▼
   ┌─── 2. HUNT ──────┐    50 hunters × Opus + effort=max, en parallèle
   │ mythos-hunt-lead │ ────────────────────────────────────────────► findings.jsonl
   │  spawn hunters   │     chacun écrit un PoC, tourne en sandbox     coverage.jsonl
   │       × 50       │     pas de PoC = pas de finding (schéma strict) poc/F-XXX/
   └──────────────────┘
                                               ▼  ┌─── 4. GAPFILL ────┐
   ┌─── 3. VALIDATE ──┐  avocat du diable.        │  détecte les gaps │
   │ mythos-validate  │  écrit un PoC INDÉPENDANT │  de couverture,    │
   │ pas d'outil Agent│ ─ drop si désaccord.      │  re-queue          │
   │(anti-corrélation)│                           └──────┬─────────────┘
   └──────────────────┘                           ▲      │ boucle ×3
                                                  └──────┘
                                               ▼
   ┌─── 5. DEDUPE ────┐ ─► dedup-clusters.json
   ├─── 6. TRACE ─────┤    1 traceur par repo consommateur ─────► traces/*.json
   │ mythos-trace     │    "est-ce ATTEIGNABLE depuis l'extérieur ?"
   ├─── 7. FEEDBACK ──┤    traces atteignables → nouvelles tâches ── boucle ×1
   ├─── 8. REPORT ────┤ ─► report.md  +  report.json  (validé par schéma)
   └──────────────────┘
```

## Les gros chiffres

| | |
|---:|:---|
| **12** | agents Claude Opus 4.7 spécialisés (8 leads + 4 workers) |
| **23** | classes de bugs supportées (SQLi, SSRF, désérialisation, JWT confusion, UAF, OOB R/W, IDOR, BFLA, mass-assignment, prototype pollution, SSTI, race condition, double-free, format string, …) |
| **39** | skills cybersécurité curées, auditées avant installation |
| **9** | couches de sécurité Docker empilées (seccomp + AppArmor + cap-drop + read-only + non-root + no-network + cgroup-ns + ulimits + pids_limit) |
| **8** | schémas JSON, Draft 2020-12, stricts (`additionalProperties: false`) |
| **6** | tentatives d'évasion red-team — **toutes bloquées** |
| **436** | tests qui passent (unit + intégration + red-team) |
| **20** | menaces documentées avec mitigations explicites |
| **100%** | couverture de code sur les modules data-safety critiques (paths, locking, redact) |
| **0** | finding sans PoC fonctionnel |

---

## 🔬 Comment Mythos fonctionne — plongée technique approfondie

Cette section explique la mécanique interne pour les ingénieurs qui veulent comprendre ou étendre le harnais.

### Pourquoi 8 phases plutôt qu'un seul gros agent ?

Un agent unique pointé sur un dépôt dérive. Il choisit un fil, le suit, manque de contexte, et oublie les 95% restants de la surface. Mythos **décompose le problème selon deux axes** simultanément :

1. **Axe phases** (vertical) — Recon établit le contexte partagé ; Hunt trouve les hypothèses ; Validate détruit les hypothèses ; Gapfill élargit ; Dedupe condense ; Trace contextualise ; Feedback ferme la boucle ; Report livre.
2. **Axe workers** (horizontal) — chaque phase qui fait du vrai travail se déploie sur plusieurs workers étroits, chacun scopé à *une classe de bug × une fonction*. Le lead n'analyse pas le code ; il coordonne uniquement.

Ce découplage garantit que l'agent qui trouve un bug est **différent** de celui qui le confirme, qui est **différent** de celui qui trace son atteignabilité. Chacun est le bon outil pour sa question.

### Topologie des agents

```
                       skill /mythos (orchestrateur)
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
    8 LEADS                  12 AGENTS                4 WORKERS
   (un par phase)             total                (font le travail)
        │                                                  │
        ├─ mythos-recon  ───spawn N───► mythos-scout
        ├─ mythos-hunt-lead ──lance via subprocess──►  mythos-hunter × 50
        │                                                  │
        │                                                  └─spawn──► mythos-explorer
        ├─ mythos-validate  (pas d'outil Agent — anti-corrélation)
        ├─ mythos-gapfill   (lit les coverage gaps, re-queue)
        ├─ mythos-dedupe    (cluster les findings par cause racine)
        ├─ mythos-trace ────spawn M────► mythos-tracer (un par repo consommateur)
        ├─ mythos-feedback  (transforme les traces atteignables en nouvelles tâches)
        └─ mythos-report    (sortie finale validée par schéma)
```

Tous les agents tournent en **Claude Opus 4.7 avec `effort: max`**. La définition du modèle liste 11 des 12 agents comme sous-agents Claude Code standards ; les 50 hunters parallèles sont spawnés comme **des sous-processus séparés `claude --agent mythos-hunter -p "..."`** via un script Python launcher — c'est ainsi qu'on obtient un vrai parallélisme à 50 voies tout en restant dans la sémantique sous-agent.

### Le principe d'anti-corrélation

Le choix de design avec le plus fort impact dans Mythos est : **l'agent qui confirme un finding n'a pas le droit d'utiliser les outils qui l'ont créé**.

Le frontmatter de `mythos-validate` déclare `tools: Read, Bash, Write` — **pas d'outil `Agent`**. Il ne peut pas spawn d'helpers. Il ne peut pas demander un second avis à un autre modèle. Il doit lire le code source indépendamment, écrire son propre PoC à partir de zéro, l'exécuter dans la sandbox, et seulement après regarder la trouvaille du hunter. Un finding ne survit que si **les deux PoC reproduisent la même cause racine**.

Le test structurel `test_validate_lead_does_not_have_agent_tool` impose ça au niveau fichier — il ferait échouer le build si quelqu'un élargissait accidentellement le toolset de Validate.

### La barrière "pas de PoC = pas de finding"

`finding.schema.json` déclare :

```json
"confidence": {
  "type": "string",
  "enum": ["poc-confirmed"]
}
```

L'enum n'a **qu'une seule valeur**. Pas de `suspected`, pas de `theoretical`, pas de `medium-confidence`. Un finding sans PoC fonctionnel ne peut pas sérialiser vers un record valide selon le schéma, donc il ne peut pas entrer dans `findings.jsonl`. C'est le mécanisme structurel derrière la promesse "pas de paragraphes de potentiellement".

Quand un hunter épuise ses 5 itérations de révision d'hypothèse sans exécution réussie de PoC, il écrit **seulement** un record `coverage.jsonl` (qui utilise un schéma différent) et exit avec `NO_FINDING`. Le bug n'atteint jamais Validate.

### La sandbox — 9 couches empilées

Quand un hunter exécute un PoC, le conteneur est contraint par :

| Couche | Mécanisme | Menace bloquée |
|---|---|---|
| 1 | `cap_drop=ALL` | Toutes les capabilities Linux révoquées — `CAP_SETUID`, `CAP_SYS_ADMIN`, `CAP_NET_ADMIN`, etc. |
| 2 | `no-new-privileges=true` | Les binaires SUID dans le conteneur ne peuvent pas escalader |
| 3 | Profil seccomp custom | ~190 syscalls whitelistés ; `mount`, `ptrace`, `bpf`, `setns`, `unshare`, `kexec_*`, ops kernel modules — tous refusés |
| 4 | Profil AppArmor (Linux uniquement) | Règles de deny sur `/proc/sysrq-trigger`, `/sys/kernel/security`, `/etc/shadow`, `/root/**` |
| 5 | FS racine `read_only=True` | Le conteneur ne peut pas persister des écritures en dehors de deux mounts tmpfs |
| 6 | `user=1000:1000` | Tourne en utilisateur dédié non-root (UID 1000) |
| 7 | `network_mode=none` | Zéro réseau sortant par défaut ; les callbacks OAST utilisent un réseau interne isolé |
| 8 | Limites de ressources | `pids_limit=100`, `mem_limit=512m`, `cpu_quota=100000` (= 1 CPU), `ulimit nofile=256 nproc=200` |
| 9 | `cgroupns=private` | Le conteneur a son propre namespace cgroup |

La suite de tests red-team vérifie chaque couche indépendamment. 6 tentatives d'évasion (isolation de `/etc/passwd`, `setuid(0)`, fork bomb, sortie réseau, accès à `docker.sock`, syscall `mount`) — **les 6 bloquées**.

### Ce qui se passe dans un hunter

```
ENTRÉE (depuis launch_hunters.py via --prompt) :
  task = {
    task_id: "T-A1B2",
    class: "sql-injection",
    scope: "src/api/users.py:update_profile",
    subsystem: "api",
    trust_boundary: "HTTP request",
    priority: 1,
    status: "in_progress"
  }
  architecture_md_excerpt = "<la part pertinente de architecture.md>"

WORKFLOW (max 50 tours, timeout dur 600s) :
  1. Parser task.class → lookup bug-class-mapping.json → "exploiting-sql-injection-vulnerabilities"
  2. Invoquer Skill(exploiting-sql-injection-vulnerabilities) → charge le workflow expert
  3. Lire le metadata bug-class à .claude/agents/mythos/bug-classes/sql-injection.md
     (indicateurs, hunting hints, stratégie PoC)
  4. Lire le fichier/fonction cible + ≤ 5 fichiers liés
  5. Former une hypothèse d'exploitabilité
  6. (Optionnel) Spawn mythos-explorer pour un deep dive
  7. Écrire le PoC vers .mythos/poc/F-<id>/{run.sh, source.<ext>, expected.log}
  8. Exécuter : python mythos_sandbox.py run F-<id>
  9. Lire le résultat. Itérer 4-8 jusqu'à 5 fois.
 10. Confirmé → append à findings.jsonl (file-locked, append-only)
     Échoué → append seulement à coverage.jsonl, exit NO_FINDING

CONTRAT DE SORTIE :
  - chaque ligne de findings.jsonl DOIT valider contre finding.schema.json
  - chaque ligne de coverage.jsonl DOIT valider contre coverage.schema.json
  - hook PostToolUse validate_write.py rejette les écritures hors chemins autorisés
  - hook PreToolUse validate_bash.py rejette 22 patterns de commandes catastrophiques
```

Le hunter est intentionnellement étroit. Il **n'explore pas** l'architecture — `mythos-recon` l'a fait. Il **ne décide pas** quoi chasser — `mythos-hunt-lead` lui a assigné une tâche. Il **ne juge pas** la sévérité en isolation — `mythos-validate` va la reproduire. C'est cette étroitesse qui rend 50 hunters en parallèle productifs au lieu de redondants.

### Sûreté cross-process

Mythos tourne comme une seule conversation Claude Code mais spawn **51+ processus concurrents** pendant Hunt (`mythos-hunt-lead` + 50 hunters via `claude --agent`) plus 50 conteneurs Docker éphémères. Le state directory `.mythos/` est partagé entre tous. Trois mécanismes le maintiennent cohérent :

| Fichier | Stratégie de concurrence |
|---|---|
| `findings.jsonl`, `coverage.jsonl`, `task-queue.jsonl` | Append-only, chaque append passe par `AtomicJsonlAppender` (utilise `filelock`, locks OS via `LockFileEx` sur Windows / `fcntl` ailleurs) |
| `run.json`, `dedup-clusters.json`, `symbols.json` | Overwrite atomique via `write to tmp → os.replace()` |
| `.mythos/poc/F-<id>/` | Un dossier par finding, jamais partagé. Pas besoin de locking. |

Le test concurrent à 20 threads dans `test_locking.py` vérifie que 20 workers simultanés peuvent chacun appender 5 records sans perdre ni corrompre une seule ligne.

### Intégrité d'état & reprise

Avant chaque phase, `snapshot_run.py` :
1. Calcule une **chaîne de hash SHA-256** sur chaque fichier dans `.mythos/` (sauf `snapshots/` lui-même)
2. Écrit un snapshot `.tar.gz` de l'état courant sous `.mythos/snapshots/pre-<phase>-<timestamp>.tar.gz`
3. Met à jour `run.json` avec la nouvelle phase + le nouveau hash

Si l'opérateur lance `/mythos resume` plus tard, l'orchestrateur :
1. Lit `run.json`, recalcule la chaîne de hash, **refuse de continuer si la chaîne ne match pas** (état modifié hors-bande)
2. Restaure le snapshot pris juste avant la dernière phase incomplète
3. Continue le pipeline depuis cette phase

Ça veut dire qu'un crash de session en plein Hunt n'est pas fatal : l'opérateur perd le travail des hunters en cours mais tout ce qui précède (Recon, batches validés antérieurs) est intact.

### Pourquoi JSON Schema Draft 2020-12 + `additionalProperties: false`

Les schémas stricts rendent la couche de données **spécification exécutable**. Le schéma est le contrat. Si un futur contributeur change la sortie de `mythos-hunter.md` sans mettre à jour le schéma, le prochain appel write échoue bruyamment. Les 8 schémas sont validés contre le meta-schéma JSON Schema à la construction (`Draft202012Validator.check_schema`) — donc un schéma malformé fail à l'import, pas à la première utilisation.

`additionalProperties: false` partout signifie qu'un hunter ne peut pas "improviser" des champs supplémentaires. Si un modèle invente `{ "confidence": "high-but-not-poc" }` pour contourner l'enum strict, la ligne est rejetée avant d'être écrite.

### Python cross-platform partout

Tous les scripts sont en Python 3.10+. Paths cross-platform via `pathlib`. Locking cross-platform via `filelock` (utilise `LockFileEx` sur Windows, `fcntl` ailleurs). Docker cross-platform via `docker-py`. Process management cross-platform via `psutil`. Le profil seccomp est chargé **inline en JSON content** dans `security_opt` plutôt qu'en file path parce que Docker Desktop sur Windows avec backend WSL2 ne peut pas lire de manière fiable les paths `/mnt/c/...` pour les profils seccomp — une particularité découverte pendant la phase de validation red-team.

### Et la fuite de secrets ?

`redact.py` ship avec des patterns pour les clés d'accès AWS, tokens GitHub (`gh{p,o,u,s,r}_…`), clés Stripe live/test, JWT, clés privées PEM, et lignes `KEY=value` style `.env` avec des valeurs d'entropie ≥ 16 chars. Le hook PostToolUse `validate_write.py` scanne chaque contenu Write/Edit ; si un pattern match, l'écriture est downgrade en warning (pas bloquée, parce qu'un hunter peut légitimement inclure une payload à haute entropie dans un PoC) mais émet une entrée dans le log d'audit.

Le log d'audit `.mythos/audit.jsonl` est append-only et survit à `/mythos clean` (sauf si `--all` est passé). Chaque event security-relevant est enregistré avec un timestamp.

---

## Démarrage rapide

```bash
# 1. Prérequis (Win/Mac/Linux)
pip install -r .claude/agents/mythos/scripts/requirements.txt
docker build -t mythos-multilang:1.0.0 \
  .claude/agents/mythos/docker/ \
  -f .claude/agents/mythos/docker/Dockerfile.multilang
python .claude/agents/mythos/scripts/install_skills.py

# 2. Vérifier
python .claude/agents/mythos/scripts/preflight.py
python .claude/agents/mythos/scripts/disclaimer.py --accept

# 3. Lancer
claude
```

Dans Claude Code :

```
/mythos start ./ton-repo-cible
```

Puis tu laisses tourner. Mythos snapshot l'état avant chaque phase, calcule une chaîne de hash SHA-256 sur le workspace, et écrit un log d'audit append-only. Si tu fais Ctrl-C en cours de route, `/mythos resume` reprend où tu t'es arrêté.

## En quoi c'est différent de "pointer une IA sur un repo et demander des vulns"

| Approche naïve | Mythos |
|---|---|
| Un agent essaie de tout trouver | 50 hunters en parallèle, chacun scopé à UNE classe × UNE fonction |
| "Potentiellement exploitable" → triage humain | Schéma impose `confidence: poc-confirmed` uniquement |
| Le même modèle revoit son propre travail | `mythos-validate` est **privé de l'outil `Agent`** — il écrit un PoC indépendant from scratch |
| Le PoC tourne sur ta machine | Conteneur Docker éphémère hardené, 9 couches d'isolation |
| Les secrets fuitent dans les rapports | Pipeline `redact.py` qui scrub AWS/GitHub/Stripe/JWT/PEM/.env avant toute écriture |
| Les commandes catastrophiques passent | Hook `PreToolUse` bloque 22 patterns (`rm -rf /`, `~/.ssh/*`, `docker.sock`, sudo, …) |

## Documentation

| | |
|---|---|
| 🚀 [**OPERATIONS.md**](docs/OPERATIONS.md) | Installation, config, run, monitoring, recovery |
| 🛠️ [**DEVELOPMENT.md**](docs/DEVELOPMENT.md) | Ajouter classes de bugs, agents, hooks, fixtures |
| 🛡️ [**SECURITY.md**](docs/SECURITY.md) | Modèle de menaces 20-points avec mitigations + log d'audit |
| ✅ [**V1-ACCEPTANCE.md**](docs/V1-ACCEPTANCE.md) | Checklist de 16 critères pour shipper |
| 📐 [**Design spec**](docs/superpowers/specs/2026-05-25-mythos-preview-design.md) | Document d'architecture complet (1 400 lignes) |
| 📋 [**Plans 1-8**](docs/superpowers/plans/) | Plans d'implémentation, ~15K lignes au total |

## ⚠️ Avertissement double-usage

Mythos génère **du code d'exploit fonctionnel et utilisable comme arme**. Usage permis uniquement sur :

1. Du code que tu possèdes
2. Du code dans le scope d'un bug bounty autorisé
3. Du code sous engagement de pentest signé
4. Du code en recherche sécurité autorisée

Usage non autorisé = illégal dans la plupart des juridictions. Le premier run requiert un `disclaimer.py --accept` explicite.

## Statut

**V1 ship-ready** — voir [V1-ACCEPTANCE.md](docs/V1-ACCEPTANCE.md). Tag : `mythos-v1-ship`.

## Licence

Apache 2.0 — voir [LICENSE](LICENSE). Les skills cybersécurité vendored conservent leurs licences d'origine.

---

<div align="center">

*Findings, pas paragraphes.*

</div>
