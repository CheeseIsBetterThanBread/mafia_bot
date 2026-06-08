import pytest
from unittest.mock import patch

from utils.user_confirmation import confirm


class TestConfirm:
    @pytest.mark.parametrize(
        "user_input,expected",
        [
            ("y", True),
            ("yes", True),
            ("Y", True),
            ("YES", True),
            ("n", False),
            ("no", False),
            ("N", False),
            ("NO", False),
            ("  y  ", True),
            ("  yes  ", True),
            ("  n  ", False),
            ("  no  ", False),
            ("YeS", True),
            ("No", False),
        ],
    )
    def test_various_inputs(self, user_input, expected):
        with patch("builtins.input", return_value=user_input):
            assert confirm("Test?") == expected

    @pytest.mark.parametrize(
        "default,empty_input_result",
        [
            (True, True),
            (False, False),
        ],
    )
    def test_empty_input_with_default(self, default, empty_input_result):
        with patch("builtins.input", return_value=""):
            assert confirm("Test?", default_answer=default) == empty_input_result

    def test_empty_input_without_default(self):
        with patch("builtins.input", side_effect=["", "y"]):
            with patch("builtins.print"):
                assert confirm("Test?", default_answer=None) is True

    @pytest.mark.parametrize(
        "invalid_inputs",
        [
            ["invalid"],
            ["bad", "wrong"],
            ["", "invalid"],
            ["invalid1", "invalid2", "invalid3"],
        ],
    )
    def test_invalid_inputs_retry(self, invalid_inputs):
        inputs = invalid_inputs + ["n"]
        with patch("builtins.input", side_effect=inputs):
            with patch("builtins.print") as mock_print:
                result = confirm("Test?")
                assert result is False
                assert mock_print.call_count == len(invalid_inputs)
