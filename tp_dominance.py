#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TP Théorie des jeux — Dominance stricte et dominance faible
===========================================================

Élimination itérée des stratégies dominées pour un jeu fini sous forme
normale, avec n joueurs et un nombre quelconque de stratégies par joueur
(stratégies pures uniquement).

Lancement
---------
    python tp_dominance.py                      # menu interactif
    python tp_dominance.py --exemple 1 --mode strict --gui
    python tp_dominance.py --exemple 3 --mode faible --ordre "2 1"
    python tp_dominance.py --fichier mon_jeu.json --mode strict
    python tp_dominance.py --aleatoire --mode faible
    python tp_dominance.py --tests              # vérifie les jeux de test du TP

Visualisation (optionnelle) : pip install pygame

Format JSON d'un jeu
--------------------
{
  "titre": "Mon jeu",
  "strategies": [["H", "B"], ["G", "M", "D"]],
  "gains": [ {"profil": ["H", "G"], "gains": [2, 1]}, ... ]
}
(pour 2 joueurs on peut aussi donner "matrice": [[[u1,u2], ...], ...])
"""

import argparse
import itertools
import json
import math
import os
import random
import sys
from dataclasses import dataclass, field

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
try:
    import pygame
except ImportError:  # la partie graphique est optionnelle
    pygame = None

STRICT, FAIBLE = "strict", "faible"
ADVERBE = {STRICT: "strictement", FAIBLE: "faiblement"}


# ======================================================================
#  1. Modèle du jeu
# ======================================================================

def fmt(x):
    if isinstance(x, float) and x.is_integer():
        return str(int(x))
    return str(x)


def fmt_gains(g):
    return "(" + ", ".join(fmt(x) for x in g) + ")"


class Game:
    """Jeu fini sous forme normale.

    strategies[i] : liste des noms des stratégies du joueur i
    payoffs       : dict  profil (tuple d'indices) -> tuple de n gains
    """

    def __init__(self, strategies, payoffs, title="Jeu"):
        self.strategies = [list(s) for s in strategies]
        self.payoffs = {tuple(k): tuple(v) for k, v in payoffs.items()}
        self.n = len(self.strategies)
        self.title = title
        self.players = [f"Joueur {i + 1}" for i in range(self.n)]
        self._valider()

    def _valider(self):
        if self.n < 2:
            raise ValueError("Il faut au moins 2 joueurs.")
        for i, s in enumerate(self.strategies):
            if not s:
                raise ValueError(f"Le joueur {i + 1} n'a aucune stratégie.")
            if len(set(s)) != len(s):
                raise ValueError(f"Noms de stratégies en double pour le joueur {i + 1}.")
        for p in self.profils():
            if p not in self.payoffs:
                raise ValueError(f"Gains manquants pour le profil {self.nom_profil(p)}.")
            if len(self.payoffs[p]) != self.n:
                raise ValueError(f"Il faut {self.n} gains pour le profil {self.nom_profil(p)}.")

    def profils(self):
        return itertools.product(*[range(len(s)) for s in self.strategies])

    def nom_profil(self, p):
        return "(" + ", ".join(self.strategies[i][x] for i, x in enumerate(p)) + ")"


# ======================================================================
#  2. Dominance et élimination itérée
# ======================================================================

def domine(game, actives, i, b, a, mode):
    """Vrai si la stratégie b du joueur i domine la stratégie a, contre toutes
    les combinaisons de stratégies encore présentes chez les autres joueurs."""
    autres = [actives[j] for j in range(game.n) if j != i]
    une_stricte = False
    for reste in itertools.product(*autres):
        ua = game.payoffs[reste[:i] + (a,) + reste[i:]][i]
        ub = game.payoffs[reste[:i] + (b,) + reste[i:]][i]
        if mode == STRICT:
            if not ub > ua:
                return False
        else:
            if ub < ua:
                return False
            if ub > ua:
                une_stricte = True
    return True if mode == STRICT else une_stricte
    # Deux stratégies aux gains identiques ne se dominent pas (aucune inégalité stricte).


@dataclass
class Etape:
    joueur: int
    supprimee: int
    dominante: int
    genre: str                                   # STRICT ou FAIBLE (nature de la dominance constatée)
    autres: list = field(default_factory=list)   # autres stratégies qui dominent aussi
    alternatives: list = field(default_factory=list)  # autres éliminations possibles à cette étape
    actives: list = field(default_factory=list)  # stratégies restantes après l'étape


@dataclass
class Resultat:
    mode: str
    ordre: list
    etapes: list
    etats: list   # etats[0] = jeu initial, etats[k] = jeu après l'étape k


def candidats(game, actives, mode, ordre):
    """Toutes les éliminations possibles, triées selon la priorité des joueurs."""
    res = []
    for i in ordre:
        for a in actives[i]:
            doms = [b for b in actives[i] if b != a and domine(game, actives, i, b, a, mode)]
            if not doms:
                continue
            stricts = [b for b in doms if domine(game, actives, i, b, a, STRICT)]
            principal = stricts[0] if stricts else doms[0]
            res.append(Etape(i, a, principal, STRICT if stricts else FAIBLE,
                             autres=[b for b in doms if b != principal]))
    return res


def resoudre(game, mode, ordre=None):
    """Élimination itérée, une stratégie à la fois.
    `ordre` = priorité des joueurs (utile en dominance faible, où le résultat
    dépend de l'ordre d'élimination)."""
    ordre = list(ordre) if ordre else list(range(game.n))
    actives = [list(range(len(s))) for s in game.strategies]
    etats = [[list(x) for x in actives]]
    etapes = []
    while True:
        c = candidats(game, actives, mode, ordre)
        if not c:
            break
        e = c[0]
        e.alternatives = [(x.joueur, x.supprimee) for x in c[1:]]
        actives[e.joueur] = [s for s in actives[e.joueur] if s != e.supprimee]
        e.actives = [list(x) for x in actives]
        etapes.append(e)
        etats.append(e.actives)
    return Resultat(mode, ordre, etapes, etats)


# ======================================================================
#  3. Affichage console
# ======================================================================

def texte_matrice(game, actives, extra=()):
    lignes_idx, cols_idx = actives[0], actives[1]
    entete = ["J1\\J2"] + [game.strategies[1][b] for b in cols_idx]
    corps = [[game.strategies[0][a]] + [fmt_gains(game.payoffs[(a, b) + tuple(extra)]) for b in cols_idx]
             for a in lignes_idx]
    larg = [max(len(r[j]) for r in [entete] + corps) for j in range(len(entete))]
    sep = "+" + "+".join("-" * (w + 2) for w in larg) + "+"

    def ligne(r):
        return "| " + " | ".join(x.center(w) for x, w in zip(r, larg)) + " |"

    return "\n".join([sep, ligne(entete), sep] + [ligne(r) for r in corps] + [sep])


def texte_jeu(game, actives):
    """2 joueurs : une matrice. n >= 3 : une matrice par combinaison des joueurs 3..n."""
    if game.n == 2:
        return texte_matrice(game, actives)
    blocs = []
    for extra in itertools.product(*actives[2:]):
        titre = ", ".join(f"J{j + 3} = {game.strategies[j + 2][e]}" for j, e in enumerate(extra))
        blocs.append(f"[{titre}]\n" + texte_matrice(game, actives, extra))
    return "\n\n".join(blocs)


def dimension(actives):
    return " x ".join(str(len(x)) for x in actives)


def conclusion(game, res):
    final = res.etats[-1]
    if all(len(x) == 1 for x in final):
        p = tuple(x[0] for x in final)
        return (f"Un seul profil subsiste : {game.nom_profil(p)} avec les gains "
                f"{fmt_gains(game.payoffs[p])}.")
    restes = "; ".join(f"J{i + 1} : {{{', '.join(game.strategies[i][s] for s in x)}}}"
                       for i, x in enumerate(final))
    return f"Jeu réduit de dimension {dimension(final)} : plusieurs profils subsistent ({restes})."


def afficher_resolution(game, res):
    print("=" * 70)
    print(f"{game.title} — {game.n} joueurs — dimension {dimension(res.etats[0])}")
    print(f"Mode : dominance {res.mode}")
    if res.mode == FAIBLE:
        print("Ordre de priorité des joueurs : " + " > ".join(f"J{i + 1}" for i in res.ordre)
              + "  (en dominance faible, le résultat dépend de cet ordre)")
    print("=" * 70)
    print("\nJeu initial :\n")
    print(texte_jeu(game, res.etats[0]))
    if not res.etapes:
        print(f"\nAucune élimination possible en dominance {res.mode} : le jeu reste inchangé "
              f"({dimension(res.etats[0])}).")
        return
    for k, e in enumerate(res.etapes, 1):
        s, d = game.strategies[e.joueur][e.supprimee], game.strategies[e.joueur][e.dominante]
        print(f"\n--- Étape {k} ---")
        ligne = f"J{e.joueur + 1} : la stratégie {s} est supprimée, {ADVERBE[e.genre]} dominée par {d}"
        if e.autres:
            ligne += " (aussi par " + ", ".join(game.strategies[e.joueur][b] for b in e.autres) + ")"
        print(ligne)
        if res.mode == FAIBLE and e.alternatives:
            alt = ", ".join(f"J{j + 1}:{game.strategies[j][a]}" for j, a in e.alternatives)
            print(f"(autres éliminations possibles à ce stade, non choisies : {alt})")
        print("Jeu après suppression :\n")
        print(texte_jeu(game, e.actives))
    print("\n" + "=" * 70)
    print("RÉSULTAT FINAL")
    print("=" * 70)
    print(texte_jeu(game, res.etats[-1]))
    print("\n" + conclusion(game, res))


# ======================================================================
#  4. Jeux d'exemple (Exemples 1 à 5 du TP + exercice « free rider »)
# ======================================================================

def depuis_matrice(noms_l, noms_c, M, titre):
    payoffs = {(a, b): tuple(M[a][b]) for a in range(len(noms_l)) for b in range(len(noms_c))}
    return Game([noms_l, noms_c], payoffs, titre)


def exemple1():
    return depuis_matrice(["H", "M", "B"], ["G", "C", "D"],
                          [[(3, 1), (2, 3), (0, 0)],
                           [(1, 2), (1, 2), (5, 1)],
                           [(2, 2), (0, 1), (1, 0)]], "Exemple 1")


def exemple2():
    return depuis_matrice(["Pierre", "Feuille", "Ciseaux"], ["Pierre", "Feuille", "Ciseaux"],
                          [[(0, 0), (-1, 1), (1, -1)],
                           [(1, -1), (0, 0), (-1, 1)],
                           [(-1, 1), (1, -1), (0, 0)]], "Exemple 2 (Pierre-Feuille-Ciseaux)")


def exemple3():
    return depuis_matrice(["H", "B"], ["G", "M", "D"],
                          [[(2, 1), (2, 1), (2, 0)],
                           [(2, 1), (1, 0), (2, 0)]], "Exemple 3")


def exemple4():
    payoffs = {}
    for p in itertools.product(range(2), repeat=3):      # 0 = C, 1 = N
        nc = sum(1 for x in p if x == 0)
        payoffs[p] = tuple(2 * nc - 3 if x == 0 else 2 * nc for x in p)
    return Game([["C", "N"]] * 3, payoffs, "Exemple 4 (3 joueurs)")


def exemple5():
    return depuis_matrice(["A1", "A2", "A3"], ["B1", "B2", "B3"],
                          [[(10, 10), (4, 9), (4, 11)],
                           [(5, 6), (8, 3), (3, 4)],
                           [(4, 0), (8, 1), (5, 3)]], "Exemple 5 (Exercice 4, Série 1)")


def free_rider(coef):
    """Produit total coef*(s1+s2), partagé en deux, coût 3 pour travailler."""
    payoffs = {}
    for p in itertools.product(range(2), repeat=2):      # 0 = Travailler (s=1), 1 = Tricher (s=0)
        s = [1 - x for x in p]
        payoffs[p] = tuple(coef * (s[0] + s[1]) / 2 - 3 * s[i] for i in range(2))
    return Game([["Travailler", "Tricher"]] * 2, payoffs, f"Free rider (produit = {coef}(s1+s2))")


EXEMPLES = {1: exemple1, 2: exemple2, 3: exemple3, 4: exemple4, 5: exemple5,
            6: lambda: free_rider(4), 7: lambda: free_rider(8)}


# ======================================================================
#  5. Saisie du jeu : clavier, fichier JSON, génération aléatoire
# ======================================================================

def noms_defaut(i, k):
    return [f"{chr(65 + i % 26)}{j + 1}" for j in range(k)]


def lire_entier(msg, mini=1, defaut=None):
    while True:
        rep = input(msg).strip()
        if not rep and defaut is not None:
            return defaut
        try:
            v = int(rep)
            if v >= mini:
                return v
        except ValueError:
            pass
        print(f"  Entrez un entier >= {mini}.")


def nombre(txt):
    try:
        return int(txt)
    except ValueError:
        return float(txt)


def saisie_clavier():
    n = lire_entier("Nombre de joueurs n (>= 2) : ", 2)
    ks = [lire_entier(f"Nombre de stratégies du joueur {i + 1} : ", 1) for i in range(n)]
    strategies = []
    for i, k in enumerate(ks):
        defaut = noms_defaut(i, k)
        rep = input(f"Noms des stratégies du joueur {i + 1} (séparés par des espaces, "
                    f"vide = {' '.join(defaut)}) : ").split()
        if rep and (len(rep) != k or len(set(rep)) != k):
            print("  Noms invalides (nombre incorrect ou doublons) : noms par défaut utilisés.")
            rep = []
        strategies.append(rep or defaut)
    gains = {}
    print(f"\nSaisissez les {n} gains (séparés par des espaces) de chaque profil.")
    for p in itertools.product(*[range(k) for k in ks]):
        nom = "(" + ", ".join(strategies[i][x] for i, x in enumerate(p)) + ")"
        while True:
            try:
                vals = [nombre(x) for x in input(f"  {nom} : ").replace("(", " ").replace(")", " ")
                        .replace(",", " ").split()]
                if len(vals) == n:
                    break
            except ValueError:
                pass
            print(f"  Entrée invalide : {n} nombres attendus.")
        gains[p] = tuple(vals)
    g = Game(strategies, gains, "Jeu saisi au clavier")
    rep = input("\nSauvegarder ce jeu en JSON ? (nom de fichier, vide = non) : ").strip()
    if rep:
        sauver_json(g, rep)
        print(f"  Jeu sauvegardé dans {rep}")
    return g


def aleatoire(n=None, ks=None, graine=None):
    if n is None:
        n = lire_entier("Nombre de joueurs n (>= 2) : ", 2)
        ks = [lire_entier(f"Nombre de stratégies du joueur {i + 1} : ", 1) for i in range(n)]
        g = input("Graine aléatoire (vide = aucune) : ").strip()
        graine = int(g) if g else None
    rnd = random.Random(graine)
    strategies = [noms_defaut(i, k) for i, k in enumerate(ks)]
    gains = {p: tuple(rnd.randint(-5, 10) for _ in range(n))
             for p in itertools.product(*[range(k) for k in ks])}
    return Game(strategies, gains, "Jeu aléatoire")


def charger_json(chemin):
    with open(chemin, encoding="utf-8") as f:
        d = json.load(f)
    strategies = d["strategies"]
    index = [{nom: j for j, nom in enumerate(s)} for s in strategies]
    gains = {}
    if "matrice" in d:
        for a, ligne in enumerate(d["matrice"]):
            for b, cell in enumerate(ligne):
                gains[(a, b)] = tuple(cell)
    else:
        for e in d["gains"]:
            p = tuple(index[i][nom] for i, nom in enumerate(e["profil"]))
            gains[p] = tuple(e["gains"])
    return Game(strategies, gains, d.get("titre", os.path.basename(chemin)))


def sauver_json(game, chemin):
    d = {"titre": game.title, "strategies": game.strategies,
         "gains": [{"profil": [game.strategies[i][x] for i, x in enumerate(p)],
                    "gains": list(game.payoffs[p])} for p in game.profils()]}
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


# ======================================================================
#  6. Visualisation pygame
# ======================================================================

BG, PANEL, TXT, MUTED = (24, 28, 36), (34, 40, 52), (230, 233, 240), (130, 138, 155)
CELL, CELL_TXT, DEAD, DEAD_TXT = (245, 247, 250), (30, 34, 44), (52, 58, 72), (105, 112, 128)
RED, GREEN, BLUE = (214, 69, 69), (64, 170, 100), (60, 95, 160)
RED_BG, GREEN_BG, FIN_BG, OR_BG = (244, 196, 196), (196, 236, 208), (200, 228, 255), (255, 224, 130)
BTN, BTN_HOVER = (60, 70, 92), (84, 98, 130)


class Visualiseur:
    """Visualisation pas à pas de l'élimination itérée.

    - cases blanches : profils encore dans le jeu ; cases sombres : éliminées
    - rouge : stratégie qui vient d'être supprimée ; vert : celle qui la domine
    - bleu / or : jeu réduit final (or = profil unique)
    """

    def __init__(self, game, mode=STRICT, ordre=None, taille=(1200, 780)):
        if pygame is None:
            raise RuntimeError("pygame n'est pas installé (pip install pygame).")
        pygame.init()
        pygame.display.set_caption(f"Dominance — {game.title}")
        pygame.display.set_mode(taille, pygame.RESIZABLE)
        self.game = game
        self.mode = mode
        self.ordre = list(ordre) if ordre else list(range(game.n))
        self.k = 0
        self.page = 0
        self.auto = False
        self.t_auto = 0
        self.boutons = []
        self._polices = {}
        self.calculer()

    # ---------- état ----------
    def calculer(self):
        self.res = resoudre(self.game, self.mode, self.ordre)
        self.k = 0
        self.page = 0
        self.auto = False

    def N(self):
        return len(self.res.etapes)

    def suiv(self):
        self.k = min(self.k + 1, self.N())

    def prec(self):
        self.k = max(self.k - 1, 0)

    def debut(self):
        self.k = 0

    def fin(self):
        self.k = self.N()

    def basc_auto(self):
        if self.k >= self.N():
            self.k = 0
        self.auto = not self.auto
        self.t_auto = 0

    def mode_strict(self):
        self.mode = STRICT
        self.calculer()

    def mode_faible(self):
        self.mode = FAIBLE
        self.calculer()

    def basc_mode(self):
        self.mode_faible() if self.mode == STRICT else self.mode_strict()

    def rot_ordre(self):
        self.ordre = self.ordre[1:] + self.ordre[:1]
        self.calculer()

    def nb_pages(self):
        return max(1, math.ceil(self.nb_tranches() / 4))

    def nb_tranches(self):
        return int(math.prod(len(s) for s in self.game.strategies[2:]))

    def page_suiv(self):
        self.page = (self.page + 1) % self.nb_pages()

    def page_prec(self):
        self.page = (self.page - 1) % self.nb_pages()

    # ---------- utilitaires de dessin ----------
    def police(self, taille, gras=False):
        cle = (taille, gras)
        if cle not in self._polices:
            self._polices[cle] = pygame.font.SysFont("dejavusans,arial,helvetica,freesans", taille, bold=gras)
        return self._polices[cle]

    def texte(self, surf, s, taille, couleur, pos, ancre="topleft", gras=False):
        img = self.police(taille, gras).render(s, True, couleur)
        r = img.get_rect(**{ancre: pos})
        surf.blit(img, r)
        return r

    @staticmethod
    def statut(p, s, actives, step):
        if step is not None and p == step.joueur:
            if s == step.supprimee:
                return "sup"
            if s == step.dominante:
                return "dom"
        return "vivant" if s in actives[p] else "mort"

    def message(self):
        g, res, k, N = self.game, self.res, self.k, self.N()
        if k == 0:
            if N == 0:
                return (f"Jeu initial. Aucune élimination possible en dominance {self.mode} : "
                        f"le jeu reste inchangé ({dimension(res.etats[0])}).")
            return (f"Jeu initial ({dimension(res.etats[0])}). {N} élimination(s) en dominance "
                    f"{self.mode}. Cliquez sur « Suivant » ou appuyez sur la flèche droite.")
        e = res.etapes[k - 1]
        s, d = g.strategies[e.joueur][e.supprimee], g.strategies[e.joueur][e.dominante]
        txt = (f"Étape {k}/{N} — J{e.joueur + 1} : la stratégie {s} est supprimée "
               f"(rouge), {ADVERBE[e.genre]} dominée par {d} (vert)")
        if e.autres:
            txt += " et aussi par " + ", ".join(g.strategies[e.joueur][b] for b in e.autres)
        txt += "."
        if self.mode == FAIBLE and e.alternatives:
            txt += " D'autres éliminations étaient possibles : l'ordre de priorité compte."
        if k == N:
            txt += "  FIN — " + conclusion(g, res)
        return txt

    # ---------- dessin d'une matrice (une « tranche » pour n >= 3) ----------
    def dessiner_tranche(self, surf, zone, extra, actives, step, teinte_fin):
        g = self.game
        x0, y0, w, h = zone
        st_extra = [self.statut(j + 2, e, actives, step) for j, e in enumerate(extra)]
        if g.n > 2:
            titre = ", ".join(f"J{j + 3} = {g.strategies[j + 2][e]}" for j, e in enumerate(extra))
            col = RED if "sup" in st_extra else MUTED if "mort" in st_extra else GREEN if "dom" in st_extra else TXT
            self.texte(surf, titre, 17, col, (x0 + 4, y0), gras=True)
            y0 += 26
            h -= 26
        noms_l, noms_c = g.strategies[0], g.strategies[1]
        nr, nc = len(noms_l), len(noms_c)
        chaines = [[fmt_gains(g.payoffs[(a, b) + extra]) for b in range(nc)] for a in range(nr)]
        coin = "J1 \\ J2"
        for taille in (22, 20, 18, 16, 14, 12, 10, 8):
            f = self.police(taille)
            wh = max(f.size(s)[0] for s in noms_l + [coin]) + 18
            wc_min = max(max(f.size(s)[0] for lig in chaines for s in lig),
                         max(f.size(s)[0] for s in noms_c)) + 18
            hc_min = f.get_linesize() + 12
            if wh + nc * wc_min <= w and (nr + 1) * hc_min <= h:
                break
        f = self.police(taille)
        wc = max(wc_min, min((w - wh) // nc, 180))
        hc = max(hc_min, min(h // (nr + 1), 64))

        def entete(rect, s, st):
            fond, ct = {"sup": (RED, (255, 255, 255)), "dom": (GREEN, (255, 255, 255)),
                        "vivant": (BLUE, (255, 255, 255)), "mort": (DEAD, DEAD_TXT)}[st]
            pygame.draw.rect(surf, fond, rect)
            pygame.draw.rect(surf, (20, 24, 32), rect, 1)
            img = f.render(s, True, ct)
            surf.blit(img, img.get_rect(center=rect.center))

        pygame.draw.rect(surf, (20, 24, 32), pygame.Rect(x0, y0, wh, hc))
        img = f.render(coin, True, MUTED)
        surf.blit(img, img.get_rect(center=(x0 + wh // 2, y0 + hc // 2)))
        for b in range(nc):
            entete(pygame.Rect(x0 + wh + b * wc, y0, wc, hc), noms_c[b], self.statut(1, b, actives, step))
        for a in range(nr):
            sa = self.statut(0, a, actives, step)
            entete(pygame.Rect(x0, y0 + (a + 1) * hc, wh, hc), noms_l[a], sa)
            for b in range(nc):
                sts = [sa, self.statut(1, b, actives, step)] + st_extra
                if "mort" in sts:
                    fond, ct = DEAD, DEAD_TXT
                elif "sup" in sts:
                    fond, ct = RED_BG, (120, 30, 30)
                elif teinte_fin is not None and all(s in ("vivant", "dom") for s in sts):
                    fond, ct = teinte_fin, CELL_TXT
                elif "dom" in sts:
                    fond, ct = GREEN_BG, (20, 80, 40)
                else:
                    fond, ct = CELL, CELL_TXT
                r = pygame.Rect(x0 + wh + b * wc, y0 + (a + 1) * hc, wc, hc)
                pygame.draw.rect(surf, fond, r)
                pygame.draw.rect(surf, (90, 98, 115), r, 1)
                img = f.render(chaines[a][b], True, ct)
                surf.blit(img, img.get_rect(center=r.center))

    # ---------- dessin complet ----------
    def dessiner(self):
        surf = pygame.display.get_surface()
        W, H = surf.get_size()
        g, res, N = self.game, self.res, self.N()
        surf.fill(BG)
        step = res.etapes[self.k - 1] if self.k > 0 else None
        actives = res.etats[self.k]
        teinte_fin = None
        if self.k == N and N > 0:
            teinte_fin = OR_BG if all(len(x) == 1 for x in actives) else FIN_BG

        # barre du haut
        self.texte(surf, g.title, 22, TXT, (20, 12), gras=True)
        info = (f"Dominance {self.mode.upper()}   |   priorité des joueurs : "
                + " > ".join(f"J{i + 1}" for i in res.ordre) + f"   |   état {self.k}/{N}")
        self.texte(surf, info, 16, MUTED, (20, 44))

        # zone des matrices
        bas = 235
        zone = pygame.Rect(20, 76, W - 40, H - 76 - bas)
        extras = list(itertools.product(*[range(len(s)) for s in g.strategies[2:]]))
        pages = self.nb_pages()
        self.page = min(self.page, pages - 1)
        vis = extras[self.page * 4:(self.page + 1) * 4]
        m = len(vis)
        cn = 1 if m == 1 else 2
        rn = math.ceil(m / cn)
        cw, ch = zone.w // cn, zone.h // rn
        for idx, extra in enumerate(vis):
            r = pygame.Rect(zone.x + (idx % cn) * cw + 6, zone.y + (idx // cn) * ch + 6, cw - 12, ch - 12)
            self.dessiner_tranche(surf, r, extra, actives, step, teinte_fin)

        # panneau du bas
        py = H - bas + 10
        pygame.draw.rect(surf, PANEL, pygame.Rect(0, py, W, bas))
        f = self.police(17)
        y = py + 12
        for ligne in self._wrap(self.message(), f, W - 40)[:4]:
            self.texte(surf, ligne, 17, TXT, (20, y))
            y += 23

        # boutons
        defs = [("|<  Début", self.debut), ("<  Précédent", self.prec), ("Suivant  >", self.suiv),
                (">|  Fin", self.fin), ("Pause" if self.auto else "Auto-play", self.basc_auto),
                (f"Mode : {self.mode}  (S / W)", self.basc_mode),
                (f"Priorité : J{res.ordre[0] + 1} d'abord  (O)", self.rot_ordre)]
        if pages > 1:
            defs.append((f"Page {self.page + 1}/{pages}  (Haut / Bas)", self.page_suiv))
        self.boutons = []
        x, by = 20, H - 112
        souris = pygame.mouse.get_pos()
        fb = self.police(16)
        for label, action in defs:
            wb = fb.size(label)[0] + 28
            if x + wb > W - 20:
                x, by = 20, by + 44
            r = pygame.Rect(x, by, wb, 36)
            pygame.draw.rect(surf, BTN_HOVER if r.collidepoint(souris) else BTN, r, border_radius=6)
            img = fb.render(label, True, TXT)
            surf.blit(img, img.get_rect(center=r.center))
            self.boutons.append((r, action))
            x += wb + 10
        self.texte(surf, "Raccourcis : Droite/Gauche = étape, Espace = auto-play, Début/Fin, "
                         "S = strict, W = faible, O = priorité, Échap = quitter",
                   13, MUTED, (20, H - 24))

    @staticmethod
    def _wrap(s, font, largeur):
        lignes, cur = [], ""
        for mot in s.split():
            test = (cur + " " + mot).strip()
            if font.size(test)[0] <= largeur:
                cur = test
            else:
                lignes.append(cur)
                cur = mot
        lignes.append(cur)
        return lignes

    # ---------- boucle principale ----------
    def boucle(self):
        horloge = pygame.time.Clock()
        touches = {pygame.K_RIGHT: self.suiv, pygame.K_LEFT: self.prec, pygame.K_HOME: self.debut,
                   pygame.K_END: self.fin, pygame.K_SPACE: self.basc_auto, pygame.K_s: self.mode_strict,
                   pygame.K_w: self.mode_faible, pygame.K_o: self.rot_ordre,
                   pygame.K_DOWN: self.page_suiv, pygame.K_UP: self.page_prec}
        actif = True
        while actif:
            dt = horloge.tick(30)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    actif = False
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        actif = False
                    elif ev.key in touches:
                        touches[ev.key]()
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    for r, action in self.boutons:
                        if r.collidepoint(ev.pos):
                            action()
                            break
            if self.auto:
                self.t_auto += dt
                if self.t_auto > 1200:
                    self.t_auto = 0
                    if self.k < self.N():
                        self.k += 1
                    if self.k >= self.N():
                        self.auto = False
            self.dessiner()
            pygame.display.flip()
        pygame.quit()


def lancer_gui(game, mode, ordre):
    if pygame is None:
        print("\n(pygame n'est pas installé : « pip install pygame » pour la visualisation.)")
        return
    Visualiseur(game, mode, ordre).boucle()


# ======================================================================
#  7. Jeux de test du TP
# ======================================================================

def lancer_tests():
    cas = [  # (exemple, mode, ordre, strategies restantes attendues, gains attendus si profil unique)
        (1, STRICT, None, [[0], [1]], (2, 3)),
        (2, STRICT, None, [[0, 1, 2], [0, 1, 2]], None),
        (2, FAIBLE, None, [[0, 1, 2], [0, 1, 2]], None),
        (3, STRICT, None, [[0, 1], [0, 1]], None),
        (3, FAIBLE, [0, 1], [[0], [0, 1]], None),     # H x {G, M}
        (3, FAIBLE, [1, 0], [[0, 1], [0]], None),     # {H, B} x G
        (4, STRICT, None, [[1], [1], [1]], (0, 0, 0)),
        (5, STRICT, None, [[2], [2]], (5, 3)),
        (5, FAIBLE, None, [[2], [2]], (5, 3)),
    ]
    ok = True
    for num, mode, ordre, attendu, gains in cas:
        g = EXEMPLES[num]()
        res = resoudre(g, mode, ordre)
        final = res.etats[-1]
        bon = final == attendu
        if gains is not None and bon:
            bon = g.payoffs[tuple(x[0] for x in final)] == gains
        ok &= bon
        desc = " x ".join("{" + ",".join(g.strategies[i][s] for s in x) + "}" for i, x in enumerate(final))
        print(f"[{'OK' if bon else 'ÉCHEC'}] Exemple {num:<2} {mode:<6} ordre={ordre or 'défaut'} -> {desc}")
    print("\nTous les tests passent." if ok else "\nCertains tests échouent.")
    return ok


# ======================================================================
#  8. Programme principal
# ======================================================================

def choisir_jeu_interactif():
    print("Comment fournir le jeu ?")
    print("  1) Exemples du TP (1 à 5) + exercice free rider (6, 7)")
    print("  2) Charger un fichier JSON")
    print("  3) Génération aléatoire")
    print("  4) Saisie au clavier")
    c = lire_entier("Votre choix : ", 1)
    if c == 1:
        num = lire_entier("Numéro de l'exemple (1-7) : ", 1)
        return EXEMPLES[min(num, 7)]()
    if c == 2:
        return charger_json(input("Chemin du fichier JSON : ").strip())
    if c == 3:
        return aleatoire()
    return saisie_clavier()


def parser_ordre(txt, n):
    if not txt:
        return list(range(n))
    o = [int(x) - 1 for x in txt.replace(",", " ").split()]
    if sorted(o) != list(range(n)):
        raise ValueError(f"L'ordre doit être une permutation des joueurs 1..{n}.")
    return o


def main():
    ap = argparse.ArgumentParser(description="TP : dominance stricte et faible (élimination itérée).")
    ap.add_argument("--exemple", type=int, choices=range(1, 8), help="jeu d'exemple 1..7")
    ap.add_argument("--fichier", help="fichier JSON décrivant le jeu")
    ap.add_argument("--aleatoire", action="store_true", help="génère un jeu aléatoire")
    ap.add_argument("--mode", choices=[STRICT, FAIBLE], help="type de dominance")
    ap.add_argument("--ordre", help='priorité des joueurs en dominance faible, ex. "2 1"')
    ap.add_argument("--gui", action="store_true", help="ouvre la visualisation pygame")
    ap.add_argument("--sans-gui", action="store_true", help="n'ouvre pas la visualisation")
    ap.add_argument("--tests", action="store_true", help="exécute les jeux de test du TP")
    args = ap.parse_args()

    if args.tests:
        sys.exit(0 if lancer_tests() else 1)

    interactif = not (args.exemple or args.fichier or args.aleatoire)
    try:
        if args.exemple:
            game = EXEMPLES[args.exemple]()
        elif args.fichier:
            game = charger_json(args.fichier)
        elif args.aleatoire:
            game = aleatoire()
        else:
            game = choisir_jeu_interactif()

        mode = args.mode
        if mode is None:
            rep = input("Mode de dominance — 1) stricte  2) faible : ").strip()
            mode = FAIBLE if rep == "2" else STRICT
        ordre_txt = args.ordre
        if ordre_txt is None and mode == FAIBLE and interactif:
            ordre_txt = input("Priorité des joueurs (ex. « 2 1 », vide = 1 2 ...) : ").strip()
        ordre = parser_ordre(ordre_txt, game.n)
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        sys.exit(f"Erreur : {exc}")

    res = resoudre(game, mode, ordre)
    afficher_resolution(game, res)

    if args.gui:
        lancer_gui(game, mode, ordre)
    elif not args.sans_gui and interactif:
        if input("\nOuvrir la visualisation pygame ? (O/n) : ").strip().lower() not in ("n", "non"):
            lancer_gui(game, mode, ordre)


if __name__ == "__main__":
    main()
