"""
Guards against drift between the SettingsTypeHints declarations and the members that @settingsclass adds at runtime
"""

# %%
import inspect

import pytest

import src.settingsclass.settingsclass as settingsclass_lib
from src.settingsclass.settingsclass import SettingsTypeHints, settingsclass

# Added by the decorator, but implementation details that should not be declared
UNDECLARED_RUNTIME_MEMBERS = {"original_init"}


def _declared_class() -> type:
    """Returns SettingsTypeHints as type checkers see it, i.e. with TYPE_CHECKING enabled"""
    namespace = dict(vars(settingsclass_lib))
    namespace["TYPE_CHECKING"] = True
    exec(inspect.getsource(SettingsTypeHints), namespace)  # noqa: S102
    return namespace["SettingsTypeHints"]


DECLARED = _declared_class()


@settingsclass
class Decorated:
    class section:
        value: int = 1


def _public_members(cls: type) -> set[str]:
    """Public methods and attributes, excluding the settings sections (inner classes)"""
    return {
        name
        for name, member in vars(cls).items()
        if not name.startswith("_") and not isinstance(member, type)
    }


def _params(func) -> list[inspect.Parameter]:
    params = list(inspect.signature(func).parameters.values())
    return params[1:] if params and params[0].name == "self" else params


def _assert_same_signature(declared_func, runtime_params, runtime_return):
    """Names, kinds and defaults must match exactly.
    Annotations must match wherever the runtime side is annotated.
    The declared side must be fully annotated"""

    declared_params = _params(declared_func)
    declared_return = inspect.signature(declared_func).return_annotation

    assert [(p.name, p.kind, p.default) for p in declared_params] == [
        (p.name, p.kind, p.default) for p in runtime_params
    ]

    for declared, runtime in zip(declared_params, runtime_params):
        assert declared.annotation is not inspect.Parameter.empty, declared.name
        if runtime.annotation is not inspect.Parameter.empty:
            assert declared.annotation == runtime.annotation, declared.name

    assert declared_return is not inspect.Signature.empty
    if runtime_return is not inspect.Signature.empty:
        assert declared_return == runtime_return


# %%
def test_no_runtime_members():
    """SettingsTypeHints only provides hints, it must not affect runtime behaviour"""
    leaked = [
        name
        for name, member in vars(SettingsTypeHints).items()
        if not (name.startswith("__") and name.endswith("__")) or callable(member)
    ]
    assert leaked == []


def test_declared_members_match_runtime():
    """Every member added by the decorator is declared, and nothing else is"""
    runtime = _public_members(Decorated) - UNDECLARED_RUNTIME_MEMBERS
    assert _public_members(DECLARED) == runtime


@pytest.mark.parametrize("name", sorted(_public_members(DECLARED)))
def test_method_signature_matches_runtime(name):
    runtime = getattr(Decorated, name)
    _assert_same_signature(
        getattr(DECLARED, name),
        _params(runtime),
        inspect.signature(runtime).return_annotation,
    )


def test_init_signature_matches_runtime():
    """The generated __init__ handles the keyword-only arguments itself
    and forwards everything else to _load_settings_init"""
    wrapper_params = _params(Decorated.__init__)
    keyword_only = [
        p for p in wrapper_params if p.kind is inspect.Parameter.KEYWORD_ONLY
    ]
    forwarded = [p.kind for p in wrapper_params if p not in keyword_only]
    assert forwarded == [
        inspect.Parameter.VAR_POSITIONAL,
        inspect.Parameter.VAR_KEYWORD,
    ]

    loader = settingsclass_lib._load_settings_init
    _assert_same_signature(
        DECLARED.__init__,
        _params(loader) + keyword_only,
        inspect.signature(loader).return_annotation,
    )


# %%
if __name__ == "__main__":
    pytest.main()  # pragma: no cover
