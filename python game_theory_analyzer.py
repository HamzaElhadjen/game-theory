import itertools
import json
import random
import pygame
import sys

# ============================================================
# GAME THEORY ANALYZER
# Dominance stricte et dominance faible
# ============================================================


# ============================================================
# 1. REPRESENTATION DU JEU
# ============================================================

class Game:

    def __init__(self, players, strategies, payoffs):
        self.players = players
        self.strategies = strategies
        self.payoffs = payoffs
        self.validate()

    def validate(self):

        n = len(self.players)

        if n < 2:
            raise ValueError("Un jeu doit avoir au moins deux joueurs.")

        if len(self.strategies) != n:
            raise ValueError("Nombre de strategies incorrect.")

        if len(set(self.players)) != n:
            raise ValueError("Les noms des joueurs doivent etre uniques.")

        for player_strategies in self.strategies:

            if not player_strategies:
                raise ValueError("Chaque joueur doit avoir une strategie.")

            if len(set(player_strategies)) != len(player_strategies):
                raise ValueError("Les strategies doivent etre uniques.")

        expected = set(itertools.product(*self.strategies))

        if set(self.payoffs.keys()) != expected:
            raise ValueError("Les profils ou les gains sont incomplets.")

        for profile, gains in self.payoffs.items():

            if len(gains) != n:
                raise ValueError(
                    f"Le profil {profile} doit contenir {n} gains."
                )

            if not all(
                isinstance(gain, (int, float)) and not isinstance(gain, bool)
                for gain in gains
            ):
                raise ValueError("Les gains doivent etre numeriques.")

    def clone(self):

        return Game(
            self.players[:],
            [strategies[:] for strategies in self.strategies],
            self.payoffs.copy()
        )

    def reduce_strategy(self, player_index, strategy):

        self.strategies[player_index].remove(strategy)

        self.payoffs = {
            profile: gains
            for profile, gains in self.payoffs.items()
            if profile[player_index] != strategy
        }


# ============================================================
# 2. AFFICHAGE DU JEU
# ============================================================

def display_matrix(game, fixed_players=None):

    print(
        f"\n{game.players[0]} / {game.players[1]}",
        end="\t"
    )

    for strategy in game.strategies[1]:
        print(strategy, end="\t")

    print()

    for strategy1 in game.strategies[0]:

        print(strategy1, end="\t")

        for strategy2 in game.strategies[1]:

            profile = [None] * len(game.players)

            profile[0] = strategy1
            profile[1] = strategy2

            if fixed_players:

                for index, strategy in fixed_players.items():
                    profile[index] = strategy

            gains = game.payoffs[tuple(profile)]

            print(gains, end="\t")

        print()


def display_game(game):

    print("\n" + "=" * 75)
    print("REPRESENTATION DU JEU")
    print("=" * 75)

    print("Joueurs :", ", ".join(game.players))

    if len(game.players) == 2:

        display_matrix(game)

    else:

        other_strategies = game.strategies[2:]

        combinations = itertools.product(*other_strategies)

        for combination in combinations:

            fixed_players = {
                index + 2: strategy
                for index, strategy in enumerate(combination)
            }

            print("\nCombinaison :")

            for index, strategy in fixed_players.items():

                print(
                    game.players[index],
                    "=",
                    strategy
                )

            display_matrix(game, fixed_players)

    print("=" * 75)


# ============================================================
# 3. COMPARAISON DE DEUX STRATEGIES
# ============================================================

def dominates(game, player, strategy_a, strategy_b, mode):

    """
    Verifie si strategy_b domine strategy_a
    pour le joueur indique.

    STRICT :
    B doit rapporter strictement plus dans tous les cas.

    WEAK :
    B doit rapporter au moins autant dans tous les cas
    et strictement plus dans au moins un cas.
    """

    other_players = [
        i for i in range(len(game.players))
        if i != player
    ]

    combinations = itertools.product(
        *[game.strategies[i] for i in other_players]
    )

    strict_improvement = False

    for combination in combinations:

        profile_a = [None] * len(game.players)
        profile_b = [None] * len(game.players)

        profile_a[player] = strategy_a
        profile_b[player] = strategy_b

        for index, opponent_strategy in zip(
            other_players, combination
        ):

            profile_a[index] = opponent_strategy
            profile_b[index] = opponent_strategy

        gain_a = game.payoffs[tuple(profile_a)][player]
        gain_b = game.payoffs[tuple(profile_b)][player]

        if mode == "strict":

            if gain_b <= gain_a:
                return False

        elif mode == "weak":

            if gain_b < gain_a:
                return False

            if gain_b > gain_a:
                strict_improvement = True

    if mode == "weak":
        return strict_improvement

    return True


# ============================================================
# 4. RECHERCHE DES STRATEGIES DOMINEES
# ============================================================

def find_dominated_strategy(game, mode):

    for player in range(len(game.players)):

        strategies = game.strategies[player]

        for strategy_a in strategies:

            for strategy_b in strategies:

                if strategy_a == strategy_b:
                    continue

                if dominates(
                    game,
                    player,
                    strategy_a,
                    strategy_b,
                    mode
                ):

                    return {
                        "player": player,
                        "dominated": strategy_a,
                        "dominating": strategy_b
                    }

    return None


# ============================================================
# 5. ELIMINATION ITERATIVE
# ============================================================

def eliminate_strategies(game, mode):

    current_game = game.clone()
    history = []

    print("\n" + "#" * 75)
    print("DEBUT DE L'ANALYSE")
    print(
        "MODE :",
        "DOMINANCE STRICTE"
        if mode == "strict"
        else "DOMINANCE FAIBLE"
    )
    print("#" * 75)

    turn = 1

    while True:

        result = find_dominated_strategy(current_game, mode)

        if result is None:
            break

        player = result["player"]
        dominated = result["dominated"]
        dominating = result["dominating"]

        print("\n" + "-" * 60)
        print(f"TOUR {turn}")
        print("-" * 60)

        print("Joueur :", current_game.players[player])

        print("Strategie supprimee :", dominated)

        print("Strategie dominante :", dominating)

        print(
            "Type :",
            "Dominance stricte"
            if mode == "strict"
            else "Dominance faible"
        )

        history.append({
            "turn": turn,
            "player": current_game.players[player],
            "dominated": dominated,
            "dominating": dominating
        })

        current_game.reduce_strategy(player, dominated)

        print("\nJeu apres elimination :")
        display_game(current_game)
        turn += 1

    print("\n" + "=" * 75)
    print("RESULTAT FINAL")
    print("=" * 75)
    display_game(current_game)
    print("\nHISTORIQUE DES ELIMINATIONS")

    if history:
        for operation in history:
            print(
                f"Tour {operation['turn']} : "
                f"{operation['player']} : "
                f"{operation['dominated']} supprimee "
                f"par {operation['dominating']}"
            )
    else:
        print("Aucune elimination effectuee.")

    print("\nSTRATEGIES RESTANTES")
    for index, strategies in enumerate(current_game.strategies):
        print(current_game.players[index], ":", strategies)

    print("\nNOMBRE D'ELIMINATIONS :", len(history))

    if all(len(strategies) == 1 for strategies in current_game.strategies):
        profile = tuple(strategies[0] for strategies in current_game.strategies)
        print("\nUN SEUL PROFIL RESTANT :", profile)
        print("GAINS :", current_game.payoffs[profile])
    else:
        print("\nPlusieurs strategies restent disponibles.")

    return current_game, history


# ============================================================
# 6. CREATION MANUELLE D'UN JEU
# ============================================================

def create_manual_game():

    n = int(input("\nNombre de joueurs : "))

    if n < 2:
        raise ValueError("Il faut au moins deux joueurs.")

    players = []
    strategies = []

    for i in range(n):

        name = input(f"\nNom du joueur {i + 1} : ").strip()

        if not name:
            raise ValueError("Nom de joueur invalide.")

        players.append(name)

        k = int(
            input(f"Nombre de strategies de {name} : ")
        )

        if k < 1:
            raise ValueError("Nombre de strategies invalide.")

        player_strategies = []

        for j in range(k):

            strategy = input(
                f"Nom de la strategie {j + 1} : "
            ).strip()

            if not strategy:
                raise ValueError("Nom de strategie invalide.")

            player_strategies.append(strategy)

        if len(set(player_strategies)) != len(player_strategies):

            raise ValueError("Les strategies doivent etre uniques.")

        strategies.append(player_strategies)

    payoffs = {}

    profiles = list(itertools.product(*strategies))

    print("\n" + "=" * 60)
    print("SAISIE DES GAINS")
    print("=" * 60)

    for profile in profiles:

        print("\nProfil :", profile)

        gains = []

        for player in players:

            gain = float(
                input(f"Gain de {player} : ")
            )

            gains.append(gain)

        payoffs[profile] = tuple(gains)

    return Game(players, strategies, payoffs)


# ============================================================
# 7. GENERATION ALEATOIRE
# ============================================================

def create_random_game():

    n = int(input("\nNombre de joueurs : "))

    if n < 2:
        raise ValueError("Il faut au moins deux joueurs.")

    players = []
    strategies = []

    for i in range(n):

        players.append(f"J{i + 1}")

        k = int(
            input(f"Nombre de strategies pour J{i + 1} : ")
        )

        if k < 1:
            raise ValueError("Nombre de strategies invalide.")

        strategies.append([
            f"S{j + 1}" for j in range(k)
        ])

    minimum = int(input("Gain minimum : "))
    maximum = int(input("Gain maximum : "))

    if minimum > maximum:
        raise ValueError("Intervalle de gains invalide.")

    payoffs = {}

    for profile in itertools.product(*strategies):

        payoffs[profile] = tuple(
            random.randint(minimum, maximum)
            for _ in range(n)
        )

    return Game(players, strategies, payoffs)


# ============================================================
# 8. IMPORTATION D'UN JEU DEPUIS JSON
# ============================================================

def load_game_json():

    filename = input("\nNom du fichier JSON : ")

    with open(filename, "r", encoding="utf-8") as file:

        data = json.load(file)

    players = data["players"]
    strategies = data["strategies"]

    payoffs = {}

    for item in data["payoffs"]:

        profile = tuple(item["profile"])
        gains = tuple(item["gains"])

        payoffs[profile] = gains

    return Game(players, strategies, payoffs)


# ============================================================
# 9. EXEMPLES DU TP
# ============================================================

def get_tp_example(number):

    if number == 1:

        players = ["J1", "J2"]
        strategies = [["H", "M", "B"], ["G", "C", "D"]]
        matrix = [[(3, 1), (2, 3), (0, 0)], [(1, 2), (1, 2), (5, 1)], [(2, 2), (0, 1), (1, 0)]]

    elif number == 2:

        players = ["J1", "J2"]
        strategies = [["Pierre", "Feuille", "Ciseaux"], ["Pierre", "Feuille", "Ciseaux"]]
        matrix = [[(0, 0), (-1, 1), (1, -1)], [(1, -1), (0, 0), (-1, 1)], [(-1, 1), (1, -1), (0, 0)]]

    elif number == 3:

        players = ["J1", "J2"]
        strategies = [["H", "B"], ["G", "M", "D"]]
        matrix = [[(2, 1), (2, 1), (2, 0)], [(2, 1), (1, 0), (2, 0)]]

    elif number == 4:

        players = ["J1", "J2", "J3"]
        strategies = [["C", "N"], ["C", "N"], ["C", "N"]]
        payoffs = {
            ("C", "C", "C"): (3, 3, 3),
            ("C", "C", "N"): (1, 1, 4),
            ("C", "N", "C"): (1, 4, 1),
            ("N", "C", "C"): (4, 1, 1),
            ("C", "N", "N"): (-1, 2, 2),
            ("N", "C", "N"): (2, -1, 2),
            ("N", "N", "C"): (2, 2, -1),
            ("N", "N", "N"): (0, 0, 0)
        }
        return Game(players, strategies, payoffs)

    elif number == 5:

        players = ["J1", "J2"]
        strategies = [["A1", "A2", "A3"], ["B1", "B2", "B3"]]
        matrix = [[(10, 10), (4, 9), (4, 11)], [(5, 6), (8, 3), (3, 4)], [(4, 0), (8, 1), (5, 3)]]

    else:
        raise ValueError("Numero d'exemple invalide.")

    payoffs = {}
    for i, strategy1 in enumerate(strategies[0]):
        for j, strategy2 in enumerate(strategies[1]):
            payoffs[(strategy1, strategy2)] = matrix[i][j]

    return Game(players, strategies, payoffs)


# ============================================================
# 10. INTERFACE GRAPHIQUE PYGAME (Multi-joueurs)
# ============================================================

def run_pygame_visualization(initial_game, history):
    """
    Lance une interface Pygame pour visualiser l'élimination itérative.
    Supporte les jeux à N joueurs en affichant des sous-matrices.
    """
    pygame.init()
    WIDTH, HEIGHT = 1100, 750
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Visualisation : Élimination des Stratégies Dominées")

    # Polices
    font_title = pygame.font.SysFont("Arial", 28, bold=True)
    font_info = pygame.font.SysFont("Arial", 16, italic=True)
    font_matrix = pygame.font.SysFont("Arial", 18)
    font_step = pygame.font.SysFont("Arial", 22, bold=True)
    font_combo = pygame.font.SysFont("Arial", 18, bold=True)

    # Couleurs
    WHITE, BLACK = (250, 250, 250), (30, 30, 30)
    RED, BLUE = (220, 50, 50), (50, 100, 220)
    GRAY, LIGHT_GRAY = (180, 180, 180), (235, 235, 235)

    # État local pour l'animation
    n_players = len(initial_game.players)
    active_strats = [strats.copy() for strats in initial_game.strategies]
    current_step = 0

    running = True
    while running:
        screen.fill(WHITE)

        # --- GESTION DES ÉVÉNEMENTS ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                # Avancer
                if event.key in (pygame.K_SPACE, pygame.K_RIGHT):
                    if current_step < len(history):
                        op = history[current_step]
                        p_idx = initial_game.players.index(op['player'])
                        active_strats[p_idx].remove(op['dominated'])
                        current_step += 1
                # Reculer
                elif event.key == pygame.K_LEFT:
                    if current_step > 0:
                        current_step -= 1
                        active_strats = [strats.copy() for strats in initial_game.strategies]
                        for i in range(current_step):
                            op = history[i]
                            p_idx = initial_game.players.index(op['player'])
                            active_strats[p_idx].remove(op['dominated'])

        # --- TEXTES D'EN-TÊTE ---
        title_surf = font_title.render("Visualisation : Théorie des Jeux", True, BLACK)
        screen.blit(title_surf, (WIDTH//2 - title_surf.get_width()//2, 20))

        info_surf = font_info.render("Appuyez sur [ESPACE] / [DROITE] pour avancer | [GAUCHE] pour reculer", True, GRAY)
        screen.blit(info_surf, (WIDTH//2 - info_surf.get_width()//2, 60))

        if current_step == 0:
            step_msg = "Étape 0 : État initial du jeu"
            color_msg = BLUE
        elif current_step <= len(history):
            op = history[current_step - 1]
            step_msg = f"Tour {current_step} : {op['player']} supprime '{op['dominated']}' (dominée par '{op['dominating']}')"
            color_msg = RED
        else:
            step_msg = f"Fin : {len(history)} éliminations effectuées. Équilibre trouvé."
            color_msg = (50, 180, 50)

        msg_surf = font_step.render(step_msg, True, color_msg)
        screen.blit(msg_surf, (WIDTH//2 - msg_surf.get_width()//2, 100))

        # --- DESSIN DES MATRICES ---
        if any(not strats for strats in active_strats):
            # Si un joueur n'a plus de stratégie (ne devrait pas arriver dans un jeu valide)
            pygame.display.flip()
            continue

        active_s1 = active_strats[0]
        active_s2 = active_strats[1]

        # Calculer les combinaisons des autres joueurs (J3, J4...)
        if n_players == 2:
            combinations = [()]
        else:
            combinations = list(itertools.product(*active_strats[2:]))

        # Dimensions dynamiques
        cell_w = max(90, 400 // max(1, len(active_s2))) if n_players == 2 else 110
        cell_h = 60
        margin_x = 100
        margin_y = 120

        # Position de départ centrale ou décalée pour grille
        start_x = WIDTH // 2 - ((len(active_s2) * cell_w) // 2) if n_players == 2 else 120
        start_y = HEIGHT // 2 - ((len(active_s1) * cell_h) // 2) if n_players == 2 else 200

        for combo_idx, combo in enumerate(combinations):
            # Organisation en grille si N > 2 (Max 2 matrices par ligne pour lisibilité)
            if n_players > 2:
                col = combo_idx % 2
                row = combo_idx // 2
                offset_x = start_x + col * (len(active_s2) * cell_w + margin_x + 100)
                offset_y = start_y + row * (len(active_s1) * cell_h + margin_y)
                
                # Titre de la combinaison
                combo_text = " | ".join([f"{initial_game.players[i+2]}={combo[i]}" for i in range(len(combo))])
                combo_surf = font_combo.render(f"Sous-matrice : {combo_text}", True, BLUE)
                screen.blit(combo_surf, (offset_x, offset_y - 65))
            else:
                offset_x, offset_y = start_x, start_y

            # Nom des Joueurs 1 et 2
            p1_name = font_title.render(initial_game.players[0], True, BLACK)
            p2_name = font_title.render(initial_game.players[1], True, BLACK)
            screen.blit(p1_name, (offset_x - 100, offset_y + (len(active_s1)*cell_h)//2 - p1_name.get_height()//2))
            screen.blit(p2_name, (offset_x + (len(active_s2)*cell_w)//2 - p2_name.get_width()//2, offset_y - 45 + (15 if n_players>2 else 0)))

            # En-têtes Colonnes (J2)
            for j, s2 in enumerate(active_s2):
                text = font_matrix.render(s2, True, BLACK)
                screen.blit(text, (offset_x + j*cell_w + cell_w//2 - text.get_width()//2, offset_y - 25))

            # En-têtes Lignes (J1)
            for i, s1 in enumerate(active_s1):
                text = font_matrix.render(s1, True, BLACK)
                screen.blit(text, (offset_x - 45, offset_y + i*cell_h + cell_h//2 - text.get_height()//2))

            # Grille et Gains
            for i, s1 in enumerate(active_s1):
                for j, s2 in enumerate(active_s2):
                    rect = pygame.Rect(offset_x + j*cell_w, offset_y + i*cell_h, cell_w, cell_h)
                    pygame.draw.rect(screen, LIGHT_GRAY, rect)
                    pygame.draw.rect(screen, BLACK, rect, 2)

                    # Reconstruire le profil complet
                    profile = [s1, s2] + list(combo)
                    gains = initial_game.payoffs[tuple(profile)]
                    
                    # Formatage des gains
                    gain_str = ", ".join(map(str, gains))
                    gain_text = font_matrix.render(gain_str, True, BLACK)
                    screen.blit(gain_text, (rect.x + cell_w//2 - gain_text.get_width()//2, 
                                            rect.y + cell_h//2 - gain_text.get_height()//2))

        pygame.display.flip()

    pygame.quit()


# ============================================================
# 11. MENU PRINCIPAL
# ============================================================

def main():

    print("\n")
    print("=" * 75)
    print("                  GAME THEORY ANALYZER")
    print("           DOMINANCE STRICTE ET FAIBLE")
    print("=" * 75)

    print("\nCREATION DU JEU")
    print("1. Creer un jeu manuellement")
    print("2. Generer un jeu aleatoire")
    print("3. Importer un jeu JSON")
    print("4. Utiliser un exemple du TP")

    choice = input("\nVotre choix : ")

    try:

        if choice == "1":
            game = create_manual_game()
        elif choice == "2":
            game = create_random_game()
        elif choice == "3":
            game = load_game_json()
        elif choice == "4":
            number = int(input("Numero de l'exemple (1 a 5) : "))
            game = get_tp_example(number)
        else:
            print("Choix invalide.")
            return

        print("\nJEU INITIAL :")
        display_game(game)

        print("\nCHOIX DU TYPE DE DOMINANCE")
        print("1. Dominance stricte")
        print("2. Dominance faible")

        mode_choice = input("\nVotre choix : ")
        if mode_choice == "1":
            mode = "strict"
        elif mode_choice == "2":
            mode = "weak"
        else:
            print("Mode invalide.")
            return

        # Lancement de l'algorithme
        final_game, history = eliminate_strategies(game, mode)

        # Option Pygame Multi-joueurs
        print("\n" + "=" * 75)
        visuel = input("Voulez-vous visualiser l'algorithme pas-à-pas avec Pygame ? (o/n) : ")
        if visuel.strip().lower() in ['o', 'oui', 'y', 'yes']:
            run_pygame_visualization(game, history)

    except (ValueError, KeyError, OSError, TypeError, json.JSONDecodeError) as error:
        print("\nERREUR :", error)


if __name__ == "__main__":
    main()