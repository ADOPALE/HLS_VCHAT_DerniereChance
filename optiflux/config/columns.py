from __future__ import annotations

FLOW = {
    "origin": "Point de départ",
    "destination": "Point de destination",
    "support_function": "Fonction Support associée",
    "nature": "Nature du Flux (champ libre)",
    "container": "Nature de contenant",
    "full_empty": "Plein / vide",
    "sanitary": "Sale / propre",
    "direction": "Aller/Retour",
    "mixed": "Transport mixte possible (OUI / NON)",
    "exclusions": "Règles d'exclusions si transport mixte",
    "mutualized": "Tournées mutualisées ? (OUI / NON)",
    "mutualized_name": "Nom de la tournée mutualisée le cas échéant",
    "flow_mode": "Nature du flux (les tournées sont elles à prévoir avec une obligation de transport ou une obligation de passage?)",
    "pickup_min": "Heure de mise à disposition min départ",
    "delivery_max": "Heure max de livraison à la destination",
    "comment": "Commentaire",
}

SITE = {
    "name": "Libellé",
    "address": "Adresses",
    "has_quay": "Présence de quai",
}

VEHICLE = {
    "name": "Types",
    "initial_site": "Stationnement initial",
    "length": "dim longueur interne (m)",
    "width": "dim largeur interne (m)",
    "height": "dim hauteur interne (m)",
    "payload": "Poids max chargement",
    "fuel": "Consommation (L/km)",
    "cost_km": "Cout carburant (€/km)",
    "carbon_km": "Cout carbone (kg/km)",
    "has_lift": "Présence hayon",
    "dock_time": "Temps de mise à quai - manœuvre, contact/admin (minutes)",
    "handling_no_quay": "Manutention sans quai (minutes / contenants)",
    "handling_with_quay": "Manutention avec quai (minutes / contenants)",
}

CONTAINER = {
    "name": "libellé",
    "length": "dim longueur (m)",
    "width": "dim largeur (m)",
    "empty_weight": "Poids vide (T)",
    "full_weight": "Poids plein (T)",
}

REQUIRED_SHEETS = [
    "param RH", "param Sites", "param Véhicules", "param Contenants", "matrice Durée", "matrice Dist", "LISTES", "M flux"
]
