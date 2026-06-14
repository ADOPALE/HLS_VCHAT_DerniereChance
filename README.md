# OptiFLUX — Optimisation logistique hospitalière

OptiFLUX est une application Python / Streamlit destinée à importer un fichier Excel de paramétrage logistique hospitalier, contrôler la qualité des données, construire des tournées de transport et exporter les résultats sous Excel et PowerPoint.

Cette première version privilégie la fiabilité métier : le moteur ne prétend pas garantir une optimalité mathématique globale. Il produit une solution heuristique, la ré-optimise localement, puis la fait rejouer par un validateur indépendant. Une solution n'est considérée comme conforme que si les contraintes dures sont validées.

## Fonctionnalités incluses

- Import du classeur Excel de paramétrage.
- Normalisation automatique des libellés, avec rapport de correction.
- Contrôle des erreurs bloquantes : onglets, colonnes, sites, contenants, matrices, fenêtres horaires.
- Ignorance volontaire des champs obsolètes : fréquence, plage horaire, cadence de production, urgence.
- Création d'identifiants techniques lisibles pour les flux et unités de transport.
- Éclatement des flux volumineux en unités de transport.
- Bin packing 2D avec rotation à 90°.
- Empilement limité aux contenants dont le nom contient `caisse` ou `caisses`, avec 3 niveaux maximum.
- Respect simultané de la surface occupée et du poids chargé.
- Gestion des compatibilités véhicule / site / contenant.
- Gestion des tournées mutualisées obligatoires.
- Gestion des règles de transport mixte et d'exclusion propre / sale.
- Gestion de la désinfection à HSJ.
- Gestion des postes chauffeurs, pauses et retour au dépôt.
- Gestion des capacités simultanées de quais / emplacements, par défaut 3, avec 7 pour HLS.
- Plusieurs passes de ré-optimisation.
- Solveur exact local sur petits sous-problèmes de réordonnancement.
- Seuil d'acceptabilité de performance : occupation utile moyenne chauffeur par défaut à 80 %.
- Export Excel complet.
- Export PowerPoint de synthèse.
- Sauvegarde JSON des simulations.

## Installation

### 1. Créer un environnement Python

```bash
python -m venv .venv
```

Sous Windows :

```bash
.venv\Scripts\activate
```

Sous macOS / Linux :

```bash
source .venv/bin/activate
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Lancer l'application

```bash
streamlit run app.py
```

## Utilisation

1. Ouvrir l'application Streamlit.
2. Importer le fichier Excel de paramétrage.
3. Lire le rapport d'import.
4. Corriger le fichier source si des erreurs bloquantes sont affichées.
5. Sélectionner les jours, fonctions support et types de véhicules à inclure.
6. Ajuster les paramètres : facteur circulation, durée de poste, pause, taux d'occupation, passes de ré-optimisation.
7. Lancer l'optimisation.
8. Consulter les résultats et les contrôles.
9. Télécharger l'export Excel, l'export PowerPoint ou la sauvegarde JSON.

## Architecture

```text
optiflux/
├── app.py
├── optiflux/
│   ├── config/          # paramètres et noms de colonnes
│   ├── data/            # import, normalisation, validation source, prétraitement
│   ├── domain/          # modèles métier
│   ├── capacity/        # bin packing 2D et capacité
│   ├── optimization/    # recherche flotte, tournées, amélioration, solveur exact local
│   ├── simulation/      # rejeu, quais, métriques
│   ├── validation/      # validateur indépendant
│   ├── export/          # export Excel
│   ├── reporting/       # export PowerPoint
│   ├── storage/         # sauvegarde JSON
│   ├── ui/              # vues Streamlit
│   └── utils/           # temps, matrices, logs
└── tests/               # tests unitaires
```

## Logique algorithmique

Le moteur suit les étapes suivantes :

1. **Prétraitement des flux** : sélection des flux actifs par jour, création d'unités de transport, éclatement des gros volumes.
2. **Recherche de flotte** : création progressive de véhicules et de postes chauffeurs, avec priorité aux postes standards 6h00–13h30 et 13h30–21h00.
3. **Construction des tournées** : affectation des unités aux véhicules, groupage look-forward de flux compatibles, respect des fenêtres horaires.
4. **Ré-optimisation** : plusieurs passes tentent de fusionner des tournées, absorber les tournées peu utiles, réduire la taille des véhicules et optimiser localement l'ordre des opérations.
5. **Solveur exact local** : pour les petites tournées, énumération des permutations d'ordre afin de réduire les kilomètres dans ce sous-problème local.
6. **Validation indépendante** : rejeu événement par événement pour contrôler le service complet, les horaires, capacités, compatibilités, pauses, quais, retours dépôt et performance.

## Interprétation des statuts

| Statut | Signification |
|---|---|
| Solution non conforme | Au moins une contrainte dure est violée |
| Solution techniquement faisable | Toutes les contraintes dures sont respectées |
| Solution acceptable | Contraintes dures respectées et occupation chauffeur ≥ seuil paramétré |

Par défaut, le seuil d'occupation utile chauffeur est de 80 %. Une solution en dessous de ce seuil n'est pas considérée comme acceptable, même si elle est techniquement faisable.

## Limites connues

- Le moteur est heuristique : il ne garantit pas une optimalité globale.
- Le bin packing 2D est conservative et heuristique : il évite les solutions irréalistes mais ne prouve pas toujours l'impossibilité géométrique.
- Le solveur exact local ne s'applique qu'aux petites tournées.
- Les tournées mutualisées obligatoires peuvent créer des impossibilités si leur volume dépasse les capacités réalistes.
- Les horaires décalés sont testés, mais une modélisation exacte globale des postes reste une piste d'amélioration.
- L'export PowerPoint est une synthèse automatique simple, modifiable ensuite.

## Débogage simple

1. Si l'optimisation ne se lance pas : lire l'onglet `Erreurs données source` ou le rapport d'import.
2. Si une solution est non conforme : lire `Contrôles contraintes` dans l'export Excel.
3. Si l'occupation chauffeur est trop faible : augmenter les passes de ré-optimisation, élargir les fenêtres horaires ou vérifier les contraintes de mutualisation.
4. Si beaucoup de flux ne sont pas servis : vérifier les compatibilités véhicule / site / contenant et les fenêtres horaires.
5. Si les temps semblent trop longs : contrôler le facteur circulation et les matrices durée.

## Tests

```bash
pytest
```

