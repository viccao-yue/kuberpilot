from adapters.base import BaseAdapter


_ADAPTERS: dict[str, type[BaseAdapter]] = {}


def register_adapter(adapter_class: type[BaseAdapter]) -> type[BaseAdapter]:
    if not adapter_class.PLATFORM:
        raise ValueError("Adapter PLATFORM must not be empty")
    _ADAPTERS[adapter_class.PLATFORM] = adapter_class
    return adapter_class


def get_adapter(name: str) -> type[BaseAdapter]:
    if name not in _ADAPTERS:
        raise KeyError(f"Adapter is not registered: {name}")
    return _ADAPTERS[name]
