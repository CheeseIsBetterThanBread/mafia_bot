import pytest
from unittest.mock import Mock, patch

from engine.services.role_balancer import (
    Player,
    PlayerRoleStats,
    RoleBalancer,
    PLAIN_ASSIGNMENT,
    BALANCE_ASSIGNMENT,
    SIMULATION_ASSIGNMENT,
    BALANCE_CUT_OFF,
)


class TestRoleBalancerConstants:
    def test_max_balance(self):
        assert RoleBalancer._max_balance == BALANCE_CUT_OFF

    def test_precision_threshold(self):
        assert RoleBalancer._RoleBalancer__precision_threshold == 0.01


class TestAssignRoles:
    @pytest.fixture
    def players(self):
        return [
            Mock(spec=Player, user_id=1, role=None),
            Mock(spec=Player, user_id=2, role=None),
            Mock(spec=Player, user_id=3, role=None),
        ]

    @pytest.fixture
    def roles(self):
        return ["Мафия", "Комиссар", "Мирный житель"]

    @pytest.fixture
    def mock_stats(self):
        stats = {
            1: PlayerRoleStats(),
            2: PlayerRoleStats(),
            3: PlayerRoleStats(),
        }
        return stats

    def test_assign_roles_plain_when_allowed(self, players, roles, mock_stats):
        with patch.object(RoleBalancer, "_assign_roles_plain") as mock_plain:
            with patch.object(RoleBalancer, "_assign_roles_balance") as mock_balance:
                with patch.object(RoleBalancer, "_assign_roles_simulation") as mock_sim:
                    with patch(
                        "engine.services.role_balancer.roles_database.load_player_stats",
                        return_value=mock_stats,
                    ):
                        with patch(
                            "engine.services.role_balancer.CURRENT_ASSIGNMENT",
                            PLAIN_ASSIGNMENT,
                        ):
                            mock_plain.return_value = False

                            result = RoleBalancer.assign_roles(players, roles)

                            mock_plain.assert_called_once_with(
                                players, roles, mock_stats
                            )
                            mock_balance.assert_not_called()
                            mock_sim.assert_not_called()
                            assert result is False

    def test_assign_roles_balance_when_allowed(self, players, roles, mock_stats):
        with patch.object(RoleBalancer, "_assign_roles_plain") as mock_plain:
            with patch.object(RoleBalancer, "_assign_roles_balance") as mock_balance:
                with patch.object(RoleBalancer, "_assign_roles_simulation") as mock_sim:
                    with patch(
                        "engine.services.role_balancer.roles_database.load_player_stats",
                        return_value=mock_stats,
                    ):
                        with patch(
                            "engine.services.role_balancer.CURRENT_ASSIGNMENT",
                            BALANCE_ASSIGNMENT,
                        ):
                            mock_balance.return_value = False

                            result = RoleBalancer.assign_roles(players, roles)

                            mock_plain.assert_not_called()
                            mock_balance.assert_called_once_with(
                                players, roles, mock_stats
                            )
                            mock_sim.assert_not_called()
                            assert result is False

    def test_assign_roles_simulation_when_threshold_met(self, players, roles):
        with patch.object(RoleBalancer, "_assign_roles_plain") as mock_plain:
            with patch.object(RoleBalancer, "_assign_roles_balance") as mock_balance:
                with patch.object(RoleBalancer, "_assign_roles_simulation") as mock_sim:
                    with patch(
                        "engine.services.role_balancer.roles_database.load_player_stats"
                    ) as mock_load:
                        with patch(
                            "engine.services.role_balancer.CURRENT_ASSIGNMENT",
                            SIMULATION_ASSIGNMENT,
                        ):
                            with patch(
                                "engine.services.role_balancer.random.random",
                                return_value=0.001,
                            ):
                                mock_sim.return_value = True

                                result = RoleBalancer.assign_roles(players, roles)

                                mock_sim.assert_called_once_with(players)
                                mock_plain.assert_not_called()
                                mock_balance.assert_not_called()
                                mock_load.assert_not_called()
                                assert result is True

    def test_assign_roles_balance_takes_precedence_over_plain(
        self, players, roles, mock_stats
    ):
        with patch.object(RoleBalancer, "_assign_roles_plain") as mock_plain:
            with patch.object(RoleBalancer, "_assign_roles_balance") as mock_balance:
                with patch(
                    "engine.services.role_balancer.roles_database.load_player_stats",
                    return_value=mock_stats,
                ):
                    with patch(
                        "engine.services.role_balancer.CURRENT_ASSIGNMENT",
                        PLAIN_ASSIGNMENT | BALANCE_ASSIGNMENT,
                    ):
                        RoleBalancer.assign_roles(players, roles)

                        mock_balance.assert_called_once()
                        mock_plain.assert_not_called()

    def test_assign_roles_loads_stats_correctly(self, players, roles, mock_stats):
        with patch(
            "engine.services.role_balancer.roles_database.load_player_stats"
        ) as mock_load:
            mock_load.return_value = mock_stats
            with patch.object(RoleBalancer, "_assign_roles_plain"):
                with patch(
                    "engine.services.role_balancer.CURRENT_ASSIGNMENT", PLAIN_ASSIGNMENT
                ):
                    RoleBalancer.assign_roles(players, roles)

                    player_ids = [1, 2, 3]
                    mock_load.assert_called_once_with(player_ids)


class TestAssignRolesPlain:
    @pytest.fixture
    def players(self):
        return [
            Player(user_id=1, name="Player1", number=1),
            Player(user_id=2, name="Player2", number=2),
            Player(user_id=3, name="Player3", number=3),
        ]

    @pytest.fixture
    def roles(self):
        return ["Мафия", "Комиссар", "Мирный житель"]

    @pytest.fixture
    def mock_stats(self):
        return {
            1: PlayerRoleStats(),
            2: PlayerRoleStats(),
            3: PlayerRoleStats(),
        }

    def test_assign_roles_plain_shuffles_roles(self, players, roles, mock_stats):
        with patch("engine.services.role_balancer.roles_database.save_player_stats"):
            with patch("engine.services.role_balancer.random.shuffle") as mock_shuffle:
                RoleBalancer._assign_roles_plain(players, roles, mock_stats)
                mock_shuffle.assert_called_once_with(roles)

    def test_assign_roles_plain_assigns_correctly(self, players, roles, mock_stats):
        with patch("engine.services.role_balancer.roles_database.save_player_stats"):
            with patch(
                "engine.services.role_balancer.random.shuffle",
                side_effect=lambda x: None,
            ):
                RoleBalancer._assign_roles_plain(players, roles, mock_stats)

                for i, player in enumerate(players):
                    assert player.role == roles[i]

    def test_assign_roles_plain_updates_balances(self, players, roles, mock_stats):
        with patch.object(RoleBalancer, "_update_balances") as mock_update:
            RoleBalancer._assign_roles_plain(players, roles, mock_stats)

            expected_assignments = {player.user_id: player.role for player in players}
            mock_update.assert_called_once_with(mock_stats, expected_assignments)

    def test_assign_roles_plain_returns_false(self, players, roles, mock_stats):
        with patch.object(RoleBalancer, "_update_balances"):
            result = RoleBalancer._assign_roles_plain(players, roles, mock_stats)
        assert result is False


class TestAssignRolesBalance:
    @pytest.fixture
    def players(self):
        return [
            Player(user_id=1, name="Player1", number=1),
            Player(user_id=2, name="Player2", number=2),
            Player(user_id=3, name="Player3", number=3),
        ]

    @pytest.fixture
    def roles(self):
        return ["Мафия", "Комиссар", "Мирный житель"]

    @pytest.fixture
    def mock_stats(self):
        stats = {
            1: PlayerRoleStats(),
            2: PlayerRoleStats(),
            3: PlayerRoleStats(),
        }
        stats[1].role_balance = {"Мафия": 0.5, "Комиссар": 0.2, "Мирный житель": -0.3}
        stats[2].role_balance = {"Мафия": -0.2, "Комиссар": 0.8, "Мирный житель": 0.1}
        stats[3].role_balance = {"Мафия": 0.1, "Комиссар": -0.1, "Мирный житель": 0.4}
        return stats

    def test_assign_roles_balance_selects_players_for_each_role(
        self, players, roles, mock_stats
    ):

        with patch("engine.services.role_balancer.roles_database.save_player_stats"):
            with patch.object(RoleBalancer, "_select_player") as mock_select:
                mock_select.side_effect = [1, 2, 3]

                RoleBalancer._assign_roles_balance(players, roles, mock_stats)

                assert mock_select.call_count == 3

                calls = [call[0] for call in mock_select.call_args_list]
                assert calls[0][0] == "Мафия"
                assert calls[1][0] == "Комиссар"
                assert calls[2][0] == "Мирный житель"

    def test_assign_roles_balance_removes_selected_players(
        self, players, roles, mock_stats
    ):
        selected_players = []

        def mock_select(_, candidates, unused):
            selected = min(candidates)
            selected_players.append(selected)
            return selected

        with patch("engine.services.role_balancer.roles_database.save_player_stats"):
            with patch.object(RoleBalancer, "_select_player", side_effect=mock_select):
                RoleBalancer._assign_roles_balance(players, roles, mock_stats)

                assert len(set(selected_players)) == 3

    def test_assign_roles_balance_assigns_roles_to_players(
        self, players, roles, mock_stats
    ):

        with patch("engine.services.role_balancer.roles_database.save_player_stats"):
            with patch.object(RoleBalancer, "_select_player") as mock_select:
                mock_select.side_effect = [2, 1, 3]

                RoleBalancer._assign_roles_balance(players, roles, mock_stats)

                player_roles = {player.user_id: player.role for player in players}
                assert player_roles[2] == "Мафия"
                assert player_roles[1] == "Комиссар"
                assert player_roles[3] == "Мирный житель"

    def test_assign_roles_balance_updates_balances(self, players, roles, mock_stats):
        with patch.object(RoleBalancer, "_select_player") as mock_select:
            mock_select.side_effect = [1, 2, 3]
            with patch.object(RoleBalancer, "_update_balances") as mock_update:
                RoleBalancer._assign_roles_balance(players, roles, mock_stats)

                expected_assignments = {
                    player.user_id: player.role for player in players
                }
                mock_update.assert_called_once_with(mock_stats, expected_assignments)

    def test_assign_roles_balance_returns_false(self, players, roles, mock_stats):
        with patch("engine.services.role_balancer.roles_database.save_player_stats"):
            with patch.object(RoleBalancer, "_select_player") as mock_select:
                mock_select.side_effect = [1, 2, 3]
                result = RoleBalancer._assign_roles_balance(players, roles, mock_stats)
                assert result is False


class TestAssignRolesSimulation:
    def test_assign_roles_simulation_sets_all_to_peaceful(self):
        players = [
            Player(user_id=1, name="Player1", number=1),
            Player(user_id=2, name="Player2", number=2),
            Player(user_id=3, name="Player3", number=3),
        ]

        result = RoleBalancer._assign_roles_simulation(players)

        for player in players:
            assert player.role == "Мирный житель"

        assert result is True


class TestSelectPlayer:
    @pytest.fixture
    def mock_stats(self):
        stats = {
            1: PlayerRoleStats(),
            2: PlayerRoleStats(),
            3: PlayerRoleStats(),
            4: PlayerRoleStats(),
        }
        stats[1].role_balance = {"Мафия": 0.9, "Комиссар": 0.1}
        stats[2].role_balance = {"Мафия": 0.8, "Комиссар": 0.2}
        stats[3].role_balance = {"Мафия": 0.7, "Комиссар": 0.3}
        stats[4].role_balance = {"Мафия": 0.85, "Комиссар": 0.15}
        return stats

    def test_select_player_returns_player_with_highest_score(self, mock_stats):
        candidates = {1, 2, 3}
        selected = RoleBalancer._select_player("Мафия", candidates, mock_stats)

        assert selected == 1

    def test_select_player_handles_missing_stats(self):
        stats = {}
        candidates = {1, 2}

        selected = RoleBalancer._select_player("Мафия", candidates, stats)

        assert selected in candidates

    def test_select_player_random_among_eligible(self):
        stats = {
            1: PlayerRoleStats(),
            2: PlayerRoleStats(),
            3: PlayerRoleStats(),
        }
        stats[1].role_balance = {"Мафия": 0.9}
        stats[2].role_balance = {"Мафия": 0.89}
        stats[3].role_balance = {"Мафия": 0.5}

        candidates = {1, 2, 3}

        with patch("random.choice") as mock_choice:
            mock_choice.return_value = 1

            _ = RoleBalancer._select_player("Мафия", candidates, stats)

            call_args = mock_choice.call_args[0][0]
            assert set(call_args) == {1, 2}

    def test_select_player_respects_precision_threshold(self):
        stats = {
            1: PlayerRoleStats(),
            2: PlayerRoleStats(),
        }
        stats[1].role_balance = {"Мафия": 0.9}
        stats[2].role_balance = {
            "Мафия": 0.9 - RoleBalancer._RoleBalancer__precision_threshold + 0.001
        }

        candidates = {1, 2}

        with patch("random.choice") as mock_choice:
            RoleBalancer._select_player("Мафия", candidates, stats)

            call_args = mock_choice.call_args[0][0]
            assert len(call_args) == 2

    def test_select_player_excludes_below_threshold(self):
        stats = {
            1: PlayerRoleStats(),
            2: PlayerRoleStats(),
        }
        stats[1].role_balance = {"Мафия": 0.9}
        stats[2].role_balance = {
            "Мафия": 0.9 - RoleBalancer._RoleBalancer__precision_threshold - 0.001
        }

        candidates = {1, 2}

        with patch("random.choice") as mock_choice:
            RoleBalancer._select_player("Мафия", candidates, stats)

            call_args = mock_choice.call_args[0][0]
            assert call_args == [1]


class TestUpdateBalances:
    @pytest.fixture
    def mock_stats(self):
        stats = {
            1: PlayerRoleStats(),
            2: PlayerRoleStats(),
        }
        stats[1].role_balance = {"Мафия": 0.0, "Комиссар": 0.0}
        stats[2].role_balance = {"Мафия": 0.0, "Комиссар": 0.0}
        return stats

    def test_update_balances_alters_balance(self, mock_stats):
        assignments = {1: "Мафия", 2: "Комиссар"}

        with patch("engine.services.role_balancer.roles_database.save_player_stats"):
            with patch.object(RoleBalancer, "_calculate_probabilities") as mock_calc:
                mock_calc.return_value = {"Мафия": 0.5, "Комиссар": 0.5}
                with patch(
                    "engine.services.role_balancer.roles_database.save_player_stats"
                ):
                    RoleBalancer._update_balances(mock_stats, assignments)

                    assert mock_stats[1].role_balance["Мафия"] == 0.5 - 1.0
                    assert mock_stats[1].role_balance["Комиссар"] == 0.5
                    assert mock_stats[2].role_balance["Мафия"] == 0.5
                    assert mock_stats[2].role_balance["Комиссар"] == 0.5 - 1.0

    def test_update_balances_clamps_values(self, mock_stats):
        assignments = {1: "Мафия"}

        with patch("engine.services.role_balancer.roles_database.save_player_stats"):
            with patch.object(RoleBalancer, "_calculate_probabilities") as mock_calc:
                mock_calc.return_value = {"Мафия": 100.0}
                with patch(
                    "engine.services.role_balancer.roles_database.save_player_stats"
                ):
                    RoleBalancer._update_balances(mock_stats, assignments)

                    assert (
                        mock_stats[1].role_balance["Мафия"] <= RoleBalancer._max_balance
                    )

    def test_update_balances_saves_stats(self, mock_stats):
        assignments = {1: "Мафия", 2: "Комиссар"}

        with patch("engine.services.role_balancer.roles_database.save_player_stats"):
            with patch.object(RoleBalancer, "_calculate_probabilities") as mock_calc:
                mock_calc.return_value = {"Мафия": 0.5, "Комиссар": 0.5}
                with patch(
                    "engine.services.role_balancer.roles_database.save_player_stats"
                ) as mock_save:
                    RoleBalancer._update_balances(mock_stats, assignments)

                    mock_save.assert_called_once_with(mock_stats)

    def test_update_balances_handles_missing_keys(self):
        stats = {
            1: PlayerRoleStats(),
            2: PlayerRoleStats(),
        }
        stats[1].role_balance = {}
        stats[2].role_balance = {}

        assignments = {1: "Мафия", 2: "Комиссар"}

        with patch("engine.services.role_balancer.roles_database.save_player_stats"):
            with patch.object(RoleBalancer, "_calculate_probabilities") as mock_calc:
                mock_calc.return_value = {"Мафия": 0.5, "Комиссар": 0.5}
                with patch(
                    "engine.services.role_balancer.roles_database.save_player_stats"
                ):
                    RoleBalancer._update_balances(stats, assignments)

                    assert "Мафия" in stats[1].role_balance
                    assert "Комиссар" in stats[2].role_balance


class TestCalculateProbabilities:
    def test_calculate_probabilities_with_unique_roles(self):
        roles = ["Мафия", "Комиссар", "Мирный житель"]

        probabilities = RoleBalancer._calculate_probabilities(roles)

        assert probabilities == {
            "Мафия": 1 / 3,
            "Комиссар": 1 / 3,
            "Мирный житель": 1 / 3,
        }

    def test_calculate_probabilities_with_duplicates(self):
        roles = ["Мафия", "Мафия", "Комиссар", "Мирный житель", "Мирный житель"]

        probabilities = RoleBalancer._calculate_probabilities(roles)

        assert probabilities == {
            "Мафия": 2 / 5,
            "Комиссар": 1 / 5,
            "Мирный житель": 2 / 5,
        }

    def test_calculate_probabilities_single_role(self):
        roles = ["Мафия", "Мафия", "Мафия"]

        probabilities = RoleBalancer._calculate_probabilities(roles)

        assert probabilities == {"Мафия": 1.0}

    def test_calculate_probabilities_empty_list(self):
        roles = []

        probabilities = RoleBalancer._calculate_probabilities(roles)

        assert probabilities == {}


class TestClamp:
    def test_clamp_within_bounds(self):
        assert RoleBalancer._clamp(0.5) == 0.5
        assert RoleBalancer._clamp(-0.5) == -0.5
        assert RoleBalancer._clamp(0.0) == 0.0

    def test_clamp_upper_bound(self):
        max_val = RoleBalancer._max_balance
        assert RoleBalancer._clamp(max_val + 10) == max_val
        assert RoleBalancer._clamp(max_val) == max_val

    def test_clamp_lower_bound(self):
        max_val = RoleBalancer._max_balance
        assert RoleBalancer._clamp(-max_val - 10) == -max_val
        assert RoleBalancer._clamp(-max_val) == -max_val
