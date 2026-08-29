# J’ai cartographié tous les marchés Hyperliquid avec Python — sans wallet ni clé privée

![Écrans affichant des graphiques de marché](../assets/medium-cover.jpg)

*Photo de couverture : [Jakub Żerdzicki](https://unsplash.com/@jakubzerdzicki),
[Unsplash](https://unsplash.com/photos/vKNRKjSNbTo). Détails de licence dans le dépôt.*

Hyperliquid évolue vite. Aux perpetuals crypto natifs se sont ajoutés les marchés HIP-3, plusieurs
DEX spécialisés, des actifs spot et une exposition croissante à des sous-jacents traditionnels :
actions, indices, matières premières, devises ou encore actifs pré-IPO.

Pour un développeur ou un analyste, cette richesse crée un problème très concret : **comment obtenir
une vue unique, normalisée et vérifiable de tout ce qui est réellement disponible ?**

C’est la raison d’être de
[Hyperliquid Asset Catalog](https://github.com/Hug0x0/hyperliquid-asset-catalog), un outil Python en
lecture seule qui découvre les marchés depuis l’Info API publique, les normalise, les classe et
produit des exports ainsi que des analyses de risque et de liquidité.

> Les chiffres de marché cités dans cet article proviennent d’un instantané du 22 juillet 2026. Ils
> illustrent le fonctionnement du projet et ne constituent ni des données temps réel ni un conseil
> financier.

## Le problème : un ticker n’est pas un catalogue

Récupérer une liste de symboles est facile. Construire un catalogue exploitable l’est beaucoup
moins.

Un même sous-jacent peut exister sur plusieurs DEX. Les identifiants HIP-3 dépendent de la position
du DEX et de l’actif dans les métadonnées. Certains marchés sont suspendus, d’autres manquent de
profondeur, et un symbole seul ne dit pas s’il représente une crypto, une action ou un indice.

Il faut aussi préserver la précision des prix, tolérer une panne partielle de l’API, documenter la
fraîcheur des données et éviter de confondre disponibilité technique et investissabilité.

Le projet transforme donc une API mouvante en pipeline déterministe :

1. découverte dynamique des DEX ;
2. récupération concurrente des métadonnées et contextes ;
3. normalisation des perpetuals natifs, HIP-3 et marchés spot ;
4. classification explicite par règles YAML ;
5. validation, déduplication et exports JSON/CSV ;
6. analyse optionnelle des bougies et carnets d’ordres.

## Un outil volontairement en lecture seule

Le choix d’architecture le plus important est aussi le plus simple : le dépôt ne contient aucun
chemin d’exécution d’ordre.

Pas de wallet. Pas de clé privée. Pas de signature. Pas de logique de trading.

Le client interroge uniquement l’Info API publique. Cette séparation réduit fortement la surface de
risque et rend l’outil adapté à la recherche, à la veille de marché, à la construction d’univers et
aux pipelines de données.

Une première exploration tient en quelques commandes :

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

hl-catalog list-dexes
hl-catalog fetch --pretty
hl-catalog validate
hl-catalog export --format csv
```

Le résultat est un catalogue complet, accompagné de sous-ensembles dédiés aux marchés natifs,
HIP-3, XYZ, spot, crypto et non-crypto. Les erreurs partielles sont conservées dans un rapport de
run au lieu d’être silencieusement ignorées.

## Pourquoi la normalisation compte

Les montants restent en `Decimal` dans le pipeline et sont sérialisés sous forme de chaînes en JSON.
Ce détail évite les pertes de précision discrètes qui apparaissent facilement avec les nombres à
virgule flottante.

La classification est elle aussi volontairement explicite. Les règles vivent dans un fichier YAML
versionné : elles peuvent être relues, testées et corrigées par pull request. Aucun LLM ne décide en
production qu’un ticker est une action ou une matière première.

Cette approche est moins spectaculaire qu’une classification opaque, mais elle offre ce dont un
catalogue financier a réellement besoin : de l’auditabilité.

## Passer du catalogue aux benchmarks

Une fois les marchés normalisés, le projet peut tester la faisabilité de paniers thématiques. Avant
de construire un benchmark, il déduplique les sous-jacents présents sur plusieurs DEX en retenant le
marché au volume 24 heures le plus élevé, puis l’open interest comme second critère.

L’instantané suivi dans le dépôt comptait **196 contrats non-crypto**. Parmi 17 thèmes étudiés, cinq
avaient au moins cinq constituants uniques, six restaient concentrés et six étaient insuffisants.
Big Tech, intelligence artificielle et semi-conducteurs ressortaient comme les univers les plus
naturels à cette date.

Ces résultats montrent surtout qu’un grand nombre de contrats ne garantit pas un benchmark solide.
Il faut distinguer quatre dimensions :

- la largeur de l’univers ;
- la couverture de la définition cible ;
- la liquidité des constituants ;
- la qualité et la complétude des données.

Le score de qualité du projet combine ces dimensions, tout en pénalisant les benchmarks pour
lesquels seule une partie des constituants dispose d’une analyse détaillée.

## Mesurer ce qu’un volume brut ne montre pas

La commande suivante enrichit les marchés non-crypto les plus liquides avec 90 jours de bougies
quotidiennes et un instantané du carnet L2 :

```bash
hl-catalog analyze-markets --lookback-days 90 --max-assets 40
```

Elle calcule notamment les rendements sur 1, 7 et 30 jours, la volatilité annualisée, le drawdown
maximum, la VaR historique à 95 %, le spread, la profondeur à 10 points de base et le slippage
estimé d’un ordre de 10 000 dollars.

C’est une différence essentielle : un marché peut afficher un volume impressionnant et offrir une
exécution médiocre au moment précis où l’on souhaite intervenir. À l’inverse, un carnet dense et un
spread serré ne prouvent pas que cette qualité persistera demain.

Les mesures du projet restent donc descriptives. Le slippage est calculé sur un carnet statique ; il
n’intègre ni latence, ni impact dynamique, ni liquidité cachée, ni sélection adverse.

## Une base technique simple à auditer

Le projet s’appuie sur une stack Python compacte : HTTPX pour l’API asynchrone, Pydantic pour les
modèles, Typer pour la CLI et Pytest pour les tests. Les appels concurrents sont limités par un
sémaphore, les erreurs réseau sont retentées avec backoff aléatoire et un cache court réduit la
pression sur l’API.

Au moment de la publication de cet article, les contrôles locaux passent : lint, formatage, typage
strict et 18 tests unitaires.

Le dépôt reste néanmoins un projet de recherche en évolution. Parmi les prochaines améliorations
importantes : aligner les corrélations sur les dates exactes des bougies, ajouter un manifeste de
reproductibilité à chaque analyse, automatiser l’audit des dépendances et surveiller les changements
de schéma de l’API.

## Ce que l’on peut construire avec ce catalogue

Le catalogue peut servir de fondation à plusieurs produits :

- un explorateur de marchés HIP-3 ;
- un historique quotidien des nouveaux listings et suspensions ;
- des alertes de variation de liquidité ou de spread ;
- un moteur de présélection pour des paniers thématiques ;
- un dataset de recherche sur l’émergence des marchés TradFi on-chain ;
- un dashboard comparant la qualité d’exécution entre DEX.

Sa valeur n’est pas de donner un signal d’achat. Elle est de rendre l’univers observable,
comparable et reproductible.

## Conclusion

L’expansion d’Hyperliquid au-delà des perpetuals crypto rend nécessaire une couche de données
ouverte et auditée. Hyperliquid Asset Catalog propose cette couche sous la forme d’une CLI lisible,
sans accès privé et sans automatisation de trading.

Le projet est disponible sur GitHub :
[github.com/Hug0x0/hyperliquid-asset-catalog](https://github.com/Hug0x0/hyperliquid-asset-catalog).

Si vous travaillez sur les données de marché, les benchmarks thématiques ou l’écosystème HIP-3, les
retours les plus utiles concernent les règles de classification, les cas limites d’API et les
méthodes de mesure de liquidité.

*Avertissement : ce projet et cet article sont fournis à titre informatif et expérimental. Ils ne
constituent pas un conseil financier. Les marchés dérivés comportent des risques importants.*

---

**Suggestions de publication Medium**

- Sous-titre : *Une CLI Python en lecture seule pour découvrir, normaliser et analyser les marchés
  natifs, HIP-3, XYZ et spot.*
- Tags : `Hyperliquid`, `Python`, `DeFi`, `Data Engineering`, `Open Source`
- Canonical URL : à renseigner uniquement si l’article est d’abord publié ailleurs.

