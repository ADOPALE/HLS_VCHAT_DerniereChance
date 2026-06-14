from __future__ import annotations
from enum import Enum


class Severity(str, Enum):
    BLOCKING = "Erreur bloquante"
    WARNING = "Alerte importante"
    INFO = "Information"


class CheckStatus(str, Enum):
    OK = "OK"
    KO = "KO"
    WARNING = "WARNING"


class EventType(str, Enum):
    START_SHIFT = "Prise de poste"
    END_SHIFT = "Fin de poste"
    TRAVEL = "Trajet"
    DOCK = "Mise à quai"
    LOAD = "Chargement"
    UNLOAD = "Déchargement"
    BREAK = "Pause"
    DISINFECTION = "Désinfection"
    WAIT = "Attente"
    IDLE_BASE = "Temps inoccupé à la base"
