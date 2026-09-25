"""Tests for /doga slash commands."""
import pytest
import doga.__init__ as plugin


@pytest.fixture(autouse=True)
def _reset_state():
    plugin._state.enabled = True
    plugin._state.auto_depth = True
    plugin._state.depth = 3
    plugin._state.show_simulation = True
    plugin._state.de_bono_enabled = True
    plugin._state.max_recursion = 3
    plugin._state.memory_enabled = True
    plugin._state.jev_enabled = True
    plugin._state._last_jev_status = "enabled"


def test_help():
    result = plugin._handle_doga("help")
    assert "DOGA" in result
    assert "auto" in result


def test_help_empty():
    result = plugin._handle_doga("")
    assert "DOGA" in result


def test_on():
    plugin._state.enabled = False
    result = plugin._handle_doga("on")
    assert plugin._state.enabled is True
    assert "enabled" in result


def test_off():
    plugin._state.enabled = True
    result = plugin._handle_doga("off")
    assert plugin._state.enabled is False
    assert "disabled" in result


def test_status():
    result = plugin._handle_doga("status")
    assert "DOGA status" in result
    assert "Enabled" in result


def test_auto():
    plugin._state.auto_depth = False
    result = plugin._handle_doga("auto")
    assert plugin._state.auto_depth is True
    assert "auto" in result


def test_manual():
    result = plugin._handle_doga("manual high")
    assert plugin._state.auto_depth is False
    assert plugin._state.depth == 5


def test_manual_no_arg():
    result = plugin._handle_doga("manual")
    assert "Usage" in result


def test_manual_invalid():
    result = plugin._handle_doga("manual ultra")
    assert "Level must be" in result


def test_depth():
    result = plugin._handle_doga("depth 4")
    assert plugin._state.depth == 4
    assert plugin._state.auto_depth is False


def test_depth_no_arg():
    result = plugin._handle_doga("depth")
    assert "Current depth" in result


def test_depth_out_of_range():
    result = plugin._handle_doga("depth 6")
    assert "between 1 and 5" in result


def test_depth_invalid_number():
    result = plugin._handle_doga("depth abc")
    assert "Invalid number" in result


def test_show():
    plugin._state.show_simulation = False
    result = plugin._handle_doga("show")
    assert plugin._state.show_simulation is True
    assert "shown" in result


def test_hide():
    plugin._state.show_simulation = True
    result = plugin._handle_doga("hide")
    assert plugin._state.show_simulation is False
    assert "hidden" in result


def test_hats_on():
    plugin._state.de_bono_enabled = False
    result = plugin._handle_doga("hats on")
    assert plugin._state.de_bono_enabled is True


def test_hats_off():
    plugin._state.de_bono_enabled = True
    result = plugin._handle_doga("hats off")
    assert plugin._state.de_bono_enabled is False
    assert plugin._state._active_hats == []


def test_hats_no_arg():
    result = plugin._handle_doga("hats")
    assert "Usage" in result


def test_max_recursion():
    result = plugin._handle_doga("max_recursion 5")
    assert plugin._state.max_recursion == 5


def test_max_recursion_no_arg():
    result = plugin._handle_doga("max_recursion")
    assert "Current max recursion" in result


def test_max_recursion_out_of_range():
    result = plugin._handle_doga("max_recursion 0")
    assert "between 1 and 5" in result


def test_max_recursion_invalid():
    result = plugin._handle_doga("max_recursion abc")
    assert "Invalid number" in result


def test_memory_on():
    plugin._state.memory_enabled = False
    from unittest.mock import patch
    with patch.object(plugin, "MNEMOSYNE_AVAILABLE", True):
        result = plugin._handle_doga("memory on")
    assert plugin._state.memory_enabled is True


def test_memory_off():
    plugin._state.memory_enabled = True
    result = plugin._handle_doga("memory off")
    assert plugin._state.memory_enabled is False


def test_memory_no_arg():
    result = plugin._handle_doga("memory")
    assert "Usage" in result


def test_unknown():
    result = plugin._handle_doga("blahblah")
    assert "Unknown subcommand" in result


def test_status_with_memory_disabled():
    plugin._state.memory_enabled = False
    result = plugin._handle_doga("status")
    assert "Memory: False" in result


def test_jev_is_enabled_by_default():
    state = plugin._PluginState()
    assert state.jev_enabled is True


def test_jev_on_without_api_key_enables(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    plugin._state.jev_enabled = False
    result = plugin._handle_doga("jev on")
    assert result is not None and "enabled" in result
    assert plugin._state.jev_enabled is True


def test_jev_on_and_off(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "router-secret")
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    assert "enabled" in plugin._handle_doga("jev on")
    assert plugin._state.jev_enabled is True
    assert "disabled" in plugin._handle_doga("jev off")
    assert plugin._state.jev_enabled is False


def test_status_includes_jev():
    result = plugin._handle_doga("status")
    assert result is not None and "Jev: enabled" in result
