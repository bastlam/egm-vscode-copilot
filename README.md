# EGM pour GitHub Copilot dans VS Code

Package d'installation de [Elephant-Goldfish Model (EGM)](https://github.com/google/elephant-goldfish-model)
pour GitHub Copilot dans VS Code, sous Linux et Windows. Pas de serveur MCP,
d'extension VSIX ni de cle API supplementaire.

EGM aide a explorer une idee, rediger une specification et la faire relire
par des sous-agents disposant de nouveaux contextes. Ce package installe les
workflows officiels, un agent `egm` et huit profils de revue en lecture seule.
Il ne contient pas de modele d'IA.

**Statut : adaptateur VS Code experimental.** Les tests de ce depot valident
l'installation et les fichiers generes, pas l'execution des workflows par un
modele ni l'isolation effective des reviewers. L'adaptateur Copilot amont vise
principalement la CLI et ne constitue pas une validation VS Code.

## Prerequis

- Python 3.10 ou plus recent ; Git pour telecharger EGM.
- VS Code recent avec GitHub Copilot connecte et un acces aux fonctionnalites agents.
- Une session prenant en charge les skills, agents personnalises et sous-agents.
- Acces HTTPS a GitHub pour l'installation en ligne ; aucune elevation requise.

Les scripts ne telechargent pas Python ou Git et ne modifient pas les reglages
de securite du systeme. Ils utilisent seulement la bibliotheque standard Python.
Les dependances propres a certains workflows EGM restent celles de l'amont.

## Installation Rapide

Depuis une copie locale de ce depot, choisir **une** des deux portees.
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

Sans `--project`, la portee projet utilise le repertoire courant, pas le dossier
du script. `EGM_PYTHON` permet de choisir l'executable Python des installateurs.

## Dans VS Code

1. Ouvrir le projet cible, executer `Developer: Reload Window` puis ouvrir un nouveau chat avec le harness Copilot.
2. Selectionner l'agent **egm** dans le selecteur d'agents.
3. Invoquer un workflow et fournir ses arguments :

```text
/egm-brainstorm Ajouter des webhooks avec reprise sur erreur.
/egm-draft
/egm-review docs/designs/webhooks.md
```

Autres commandes disponibles : `/egm-review-loop`, `/egm-resolve`,
`/egm-bootstrap` et `/egm-drift-report`. La disponibilite d'une commande ne
garantit pas que tous les outils requis par son workflow sont disponibles.
Les workers de bootstrap demandant plus que la lecture/recherche ne sont pas
couverts par cet adaptateur : l'agent doit alors s'arreter et signaler la limite.

Les skills sont invoques explicitement, pas charges automatiquement. Les
validations humaines d'EGM restent obligatoires. Les echanges, drafts,
specifications et rapports suivent la langue demandee explicitement ; sinon,
ils suivent celle de la conversation. Le francais est accepte sans traduction
prealable. L'adaptateur remplace les exigences d'anglais de l'amont par cette
regle : "Plain-English" signifie ici un langage clair et direct. Les fichiers
officiels restent inchanges ; les noms de fichiers, identifiants et marqueurs
techniques requis par les workflows sont conserves.

```text
/egm-draft Redige la specification en francais a partir du brief existant.
```

Apres une mise a jour de ce package, relancer l'installation avec la meme
portee et le meme projet, recharger VS Code puis ouvrir un nouveau chat pour
eviter de conserver les anciennes consignes d'anglais dans le contexte.
Pour choisir un dossier de travail des livrables, ajouter au message :

```text
EGM artifact directory: .dev/docs
```

L'agent `egm` sert a la conception et a la revue, pas a executer des commandes
terminal. Revenir a l'agent general pour implementer la specification approuvee.

## Fichiers Installes

| Portee | Contenu EGM | Skills | Agents VS Code |
| --- | --- | --- | --- |
| Projet | `.github/egm-copilot/runtime/` | `.github/skills/egm-*/` | `.github/agents/egm*.agent.md` |
| Utilisateur | `~/.copilot/egm-copilot/runtime/` | `~/.copilot/skills/egm-*/` | `~/.copilot/agents/egm*.agent.md` |

`~` designe votre dossier personnel (`%USERPROFILE%` sous Windows).
Le harness Copilot de VS Code utilise ces dossiers natifs sans configuration.
L'ancien harness Local de VS Code utilise un stockage de profil different et
est annonce comme obsolete. Pour ce mode uniquement, un dossier d'agents
personnalise peut etre indique, par exemple son dossier de prompts :

```bash
bash ./install.sh --scope user --vscode-prompts-dir "/chemin/profil/prompts"
```

L'option `--vscode-prompts-dir` est aussi acceptee par le script PowerShell.
Exemples historiques de profils Local : `~/.config/Code/User/prompts` sous Linux
et `%APPDATA%\Code\User\prompts` sous Windows. Preferer les dossiers natifs
et le harness Copilot pour les versions recentes de VS Code.
En SSH, WSL ou conteneur, preferer la portee projet et executer l'installation
dans l'environnement du workspace. Aucune modification de `settings.json`,
`AGENTS.md` ou des instructions Copilot existantes n'est effectuee.
Eviter d'installer les memes noms a la fois au niveau projet et utilisateur.

Le runtime conserve `skills/`, `agents/`, `resources/`, `docs/`, `assets/`,
les profils Copilot amont, `plugin.json`, `README.md` et `LICENSE`.
Les skills visibles dans VS Code sont de petits points d'entree vers ce runtime,
pas une reecriture des workflows. Les liens projet restent valides apres un
deplacement du projet. Ne pas ignorer le runtime si l'installation projet doit
etre partagee par Git ; le partager integralement avec les agents et skills.

## Version, Mise A Jour Et Suppression

Le telechargement est fixe au commit EGM
`72d06f52a2482885d9a64bd24b291c6e8628942c`, et non a la branche `main`.
Git verifie le commit obtenu ; le manifeste local enregistre la revision et
les empreintes SHA-256 des fichiers. Le SHA choisi n'est pas une signature de
l'editeur. Examiner une nouvelle revision avant de l'utiliser :

```bash
python3 -m egm_copilot install --scope project --project "/chemin/mon-projet" --revision <SHA_COMPLET_40_CARACTERES>
python3 -m egm_copilot status --scope project --project "/chemin/mon-projet"
python3 -m egm_copilot uninstall --scope project --project "/chemin/mon-projet"
```

Ces commandes s'executent depuis ce depot ; sous Windows, remplacer `python3`
par `py -3`. Pour la portee globale, remplacer `--scope project --project ...`
par `--scope user` et reutiliser `--vscode-prompts-dir` si personnalise.

Relancer l'installation met a jour les fichiers geres, sans les autres fichiers.
Un fichier preexistant non gere ou un fichier gere modifie provoque un refus
avant toute ecriture/suppression. Sauvegarder puis deplacer le fichier en conflit
ou restaurer consciemment sa version installee avant de recommencer. Il n'y a
pas d'option d'ecrasement force. Ne pas lancer deux installations simultanees.
`status` verifie les fichiers geres et sort avec le code 1 s'ils sont modifies
ou manquants. Relancer l'installation restaure les fichiers geres manquants.

Pour installer hors ligne depuis une copie complete et de confiance d'EGM :

```bash
bash ./install.sh --project "/chemin/mon-projet" --source "/chemin/elephant-goldfish-model"
```

Cette copie est marquee `local-unverified` : le package ne pretend pas verifier
son commit ou son origine. Les scripts ne sont pas executes lors de l'installation.

## Distribution Python

Les scripts fonctionnent sans installation pip. Le projet est aussi un package
Python installable dans un environnement virtuel et distribuable en wheel :

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/egm-copilot install --scope user
```

Sous Windows, les executables du venv sont dans `.venv\Scripts\`.
Pour construire les distributions : `python -m pip install build` puis
`python -m build`. Aucun paquet n'est publie automatiquement sur PyPI.
La wheel contient l'installateur, pas EGM : utiliser le reseau ou `--source`.

## Verification Et Limites

```bash
python3 -m unittest discover -s tests -v
bash -n install.sh
```

La CI execute les tests sur Linux et Windows, valide le lanceur disponible et
construit une wheel et une archive source. Les tests utilisent des repertoires
temporaires, pas vos reglages personnels. Les tests hors ligne n'appellent aucun
modele. PowerShell est teste par la CI Windows, pas necessairement sur la machine
de developpement Linux.

Apres installation, verifier dans `Chat: Open Customizations` la presence des
sept skills et des neuf profils d'agent, puis lancer un petit workflow.
Les huit reviewers sont caches du selecteur principal et disponibles seulement
comme sous-agents. Examiner les outils effectivement exposes : les reviewers
doivent etre limites a `read` et `search`. S'ils manquent ou si la delegation
native n'est pas disponible, interrompre la revue plutot que la simuler.

Un nouveau contexte n'exclut pas les instructions utilisateur/projet et ne
constitue pas un bac a sable de fichiers. L'exclusion de ces instructions et
l'isolation reelle ne sont pas garanties. Un workflow EGM et une revue ne
remplacent ni les tests ni l'approbation humaine.

EGM est distribue en amont sous Apache-2.0 ; sa licence accompagne chaque
runtime installe. Ce projet d'integration n'est pas un produit officiel Google,
GitHub ou Microsoft. Voir les [instructions VS Code](https://code.visualstudio.com/docs/copilot/customization/custom-agents),
les [skills](https://code.visualstudio.com/docs/copilot/customization/agent-skills)
et les [limites de l'adaptateur amont](https://github.com/google/elephant-goldfish-model/blob/72d06f52a2482885d9a64bd24b291c6e8628942c/docs/copilot.md).