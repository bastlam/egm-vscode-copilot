# EGM pour GitHub Copilot dans VS Code

Package d'installation de [Elephant-Goldfish Model (EGM)](https://github.com/google/elephant-goldfish-model)
pour GitHub Copilot dans VS Code, sous Linux et Windows. Pas de serveur MCP,
d'extension VSIX ni de clé API supplémentaire.

EGM aide à explorer une idée, rédiger une spécification et la faire relire
par des sous-agents disposant de nouveaux contextes. Ce package installe les
workflows officiels, un agent `egm` et huit profils de revue en lecture seule.
Il ne contient pas de modèle d'IA.

**Statut : adaptateur VS Code expérimental.** Les tests de ce dépôt valident
l'installation et les fichiers générés, pas l'exécution des workflows par un
modèle ni l'isolation effective des reviewers. L'adaptateur Copilot amont vise
principalement la CLI et ne constitue pas une validation VS Code.

## Prérequis

- Python 3.10 ou plus récent ; Git pour télécharger EGM.
- VS Code récent avec GitHub Copilot connecté et un accès aux fonctionnalités agents.
- Une session prenant en charge les skills, agents personnalisés et sous-agents.
- Accès HTTPS à GitHub pour l'installation en ligne ; aucune élévation requise.

Les scripts ne téléchargent pas Python ou Git et ne modifient pas les réglages
de sécurité du système. Ils utilisent seulement la bibliothèque standard Python.
Les dépendances propres à certains workflows EGM restent celles de l'amont.

## Installation Rapide

Depuis une copie locale de ce dépôt, choisir **une** des deux portées.
Les chemins entre guillemets peuvent contenir des espaces.

### Linux

Pour un projet :

```bash
bash ./install.sh --scope project --project "/chemin/mon-projet"
```

Pour tous vos projets :

```bash
bash ./install.sh --scope user
```

### Windows (PowerShell)

Pour un projet :

```powershell
.\install.ps1 --scope project --project "C:\Projets\mon-projet"
```

Pour tous vos projets :

```powershell
.\install.ps1 --scope user
```

Si une politique PowerShell bloque le script, respecter la politique de votre
organisation ou utiliser directement Python, sans la modifier :

```powershell
py -3 -m egm_copilot install --scope project --project "C:\Projets\mon-projet"
```

Sans `--project`, la portée projet utilise le répertoire courant, pas le dossier
du script. `EGM_PYTHON` permet de choisir l'exécutable Python des installateurs.

## Dans VS Code

1. Ouvrir le projet cible, exécuter `Developer: Reload Window` puis ouvrir un nouveau chat avec le harness Copilot.
2. Sélectionner l'agent **egm** dans le sélecteur d'agents.
3. Invoquer un workflow et fournir ses arguments :

```text
/egm-brainstorm Ajouter des webhooks avec reprise sur erreur.
/egm-draft
/egm-review docs/designs/webhooks.md
```

Autres commandes disponibles : `/egm-review-loop`, `/egm-resolve`,
`/egm-bootstrap` et `/egm-drift-report`. La disponibilité d'une commande ne
garantit pas que tous les outils requis par son workflow sont disponibles.
Les workers de bootstrap demandant plus que la lecture/recherche ne sont pas
couverts par cet adaptateur : l'agent doit alors s'arrêter et signaler la limite.

Les skills sont invoqués explicitement, pas chargés automatiquement. Les
validations humaines d'EGM restent obligatoires. Les échanges, drafts,
spécifications et rapports suivent la langue demandée explicitement ; sinon,
ils suivent celle de la conversation. Le français est accepté sans traduction
préalable. L'adaptateur remplace les exigences d'anglais de l'amont par cette
règle : "Plain-English" signifie ici un langage clair et direct. Les fichiers
officiels restent inchangés ; les noms de fichiers, identifiants et marqueurs
techniques requis par les workflows sont conservés.

```text
/egm-draft Rédige la spécification en français à partir du brief existant.
```

Après une mise à jour de ce package, relancer l'installation avec la même
portée et le même projet, recharger VS Code puis ouvrir un nouveau chat pour
éviter de conserver les anciennes consignes d'anglais dans le contexte.
Pour choisir un dossier de travail des livrables, ajouter au message :

```text
EGM artifact directory: .dev/docs
```

L'agent `egm` sert à la conception et à la revue, pas à exécuter des commandes
terminal. Revenir à l'agent général pour implémenter la spécification approuvée.

## Fichiers Installés

| Portée | Contenu EGM | Skills | Agents VS Code |
| --- | --- | --- | --- |
| Projet | `.github/egm-copilot/runtime/` | `.github/skills/egm-*/` | `.github/agents/egm*.agent.md` |
| Utilisateur | `~/.copilot/egm-copilot/runtime/` | `~/.copilot/skills/egm-*/` | `~/.copilot/agents/egm*.agent.md` |

`~` désigne votre dossier personnel (`%USERPROFILE%` sous Windows).
Le harness Copilot de VS Code utilise ces dossiers natifs sans configuration.
L'ancien harness Local de VS Code utilise un stockage de profil différent et
est annoncé comme obsolète. Pour ce mode uniquement, un dossier d'agents
personnalisé peut être indiqué, par exemple son dossier de prompts :

```bash
bash ./install.sh --scope user --vscode-prompts-dir "/chemin/profil/prompts"
```

L'option `--vscode-prompts-dir` est aussi acceptée par le script PowerShell.
Exemples historiques de profils Local : `~/.config/Code/User/prompts` sous Linux
et `%APPDATA%\Code\User\prompts` sous Windows. Préférer les dossiers natifs
et le harness Copilot pour les versions récentes de VS Code.
En SSH, WSL ou conteneur, préférer la portée projet et exécuter l'installation
dans l'environnement du workspace. Aucune modification de `settings.json`,
`AGENTS.md` ou des instructions Copilot existantes n'est effectuée.
Éviter d'installer les mêmes noms à la fois au niveau projet et utilisateur.

Le runtime conserve `skills/`, `agents/`, `resources/`, `docs/`, `assets/`,
les profils Copilot amont, `plugin.json`, `README.md` et `LICENSE`.
Les skills visibles dans VS Code sont de petits points d'entrée vers ce runtime,
pas une réécriture des workflows. Les liens projet restent valides après un
déplacement du projet. Ne pas ignorer le runtime si l'installation projet doit
être partagée par Git ; le partager intégralement avec les agents et skills.

## Version, Mise À Jour Et Suppression

Le téléchargement est fixé au commit EGM
`72d06f52a2482885d9a64bd24b291c6e8628942c`, et non à la branche `main`.
Git vérifie le commit obtenu ; le manifeste local enregistre la révision et
les empreintes SHA-256 des fichiers. Le SHA choisi n'est pas une signature de
l'éditeur. Examiner une nouvelle révision avant de l'utiliser :

```bash
python3 -m egm_copilot install --scope project --project "/chemin/mon-projet" --revision <SHA_COMPLET_40_CARACTERES>
python3 -m egm_copilot status --scope project --project "/chemin/mon-projet"
python3 -m egm_copilot uninstall --scope project --project "/chemin/mon-projet"
```

Ces commandes s'exécutent depuis ce dépôt ; sous Windows, remplacer `python3`
par `py -3`. Pour la portée globale, remplacer `--scope project --project ...`
par `--scope user` et réutiliser `--vscode-prompts-dir` si personnalisé.

Relancer l'installation met à jour les fichiers gérés, sans les autres fichiers.
Un fichier préexistant non géré ou un fichier géré modifié provoque un refus
avant toute écriture/suppression. Sauvegarder puis déplacer le fichier en conflit
ou restaurer consciemment sa version installée avant de recommencer. Il n'y a
pas d'option d'écrasement forcé. Ne pas lancer deux installations simultanées.
`status` vérifie les fichiers gérés et sort avec le code 1 s'ils sont modifiés
ou manquants. Relancer l'installation restaure les fichiers gérés manquants.

Pour installer hors ligne depuis une copie complète et de confiance d'EGM :

```bash
bash ./install.sh --project "/chemin/mon-projet" --source "/chemin/elephant-goldfish-model"
```

Cette copie est marquée `local-unverified` : le package ne prétend pas vérifier
son commit ou son origine. Les scripts ne sont pas exécutés lors de l'installation.

## Encodage UTF-8

La documentation et les fichiers texte générés utilisent UTF-8 sans BOM.
Les accents sont conservés dans les livrables français, les noms de fichiers,
les chemins et les manifestes JSON. Les ressources EGM sont copiées octet pour
octet, sans conversion de leur encodage d'origine.

Le fichier `.editorconfig` fixe UTF-8 pour les éditeurs compatibles. Les règles
Git conservent les fins de ligne LF des scripts Bash et CRLF des scripts
PowerShell. Les scripts d'installation restent en ASCII, compatible UTF-8,
pour ne pas nécessiter de BOM sous Windows PowerShell 5.1.

## Distribution Python

Les scripts fonctionnent sans installation pip. Le projet est aussi un package
Python installable dans un environnement virtuel et distribuable en wheel :

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/egm-copilot install --scope user
```

Sous Windows, les exécutables du venv sont dans `.venv\Scripts\`.
Pour construire les distributions : `python -m pip install build` puis
`python -m build`. Aucun paquet n'est publié automatiquement sur PyPI.
La wheel contient l'installateur, pas EGM : utiliser le réseau ou `--source`.

## Vérification Et Limites

```bash
python3 -m unittest discover -s tests -v
bash -n install.sh
```

La CI exécute les tests sur Linux et Windows, valide le lanceur disponible et
construit une wheel et une archive source. Les tests utilisent des répertoires
temporaires, pas vos réglages personnels. Les tests hors ligne n'appellent aucun
modèle. PowerShell est testé par la CI Windows, pas nécessairement sur la machine
de développement Linux.

Après installation, vérifier dans `Chat: Open Customizations` la présence des
sept skills et des neuf profils d'agent, puis lancer un petit workflow.
Les huit reviewers sont cachés du sélecteur principal et disponibles seulement
comme sous-agents. Examiner les outils effectivement exposés : les reviewers
doivent être limités à `read` et `search`. S'ils manquent ou si la délégation
native n'est pas disponible, interrompre la revue plutôt que la simuler.

Un nouveau contexte n'exclut pas les instructions utilisateur/projet et ne
constitue pas un bac à sable de fichiers. L'exclusion de ces instructions et
l'isolation réelle ne sont pas garanties. Un workflow EGM et une revue ne
remplacent ni les tests ni l'approbation humaine.

EGM est distribué en amont sous Apache-2.0 ; sa licence accompagne chaque
runtime installé. Ce projet d'intégration n'est pas un produit officiel Google,
GitHub ou Microsoft. Voir les [instructions VS Code](https://code.visualstudio.com/docs/copilot/customization/custom-agents),
les [skills](https://code.visualstudio.com/docs/copilot/customization/agent-skills)
et les [limites de l'adaptateur amont](https://github.com/google/elephant-goldfish-model/blob/72d06f52a2482885d9a64bd24b291c6e8628942c/docs/copilot.md).