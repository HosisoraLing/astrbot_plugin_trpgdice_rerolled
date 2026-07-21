from __future__ import annotations

try:
    from astrbot.api.event import filter as _astrbot_filter, AstrMessageEvent as _AstrMessageEvent
except Exception:
    _astrbot_filter = None
    _AstrMessageEvent = object


class _CompatEnum:
    def __init__(self, **values):
        self.__dict__.update(values)


class _CompatFilter:
    def __init__(self):
        self._filter = _astrbot_filter
        self.PlatformAdapterType = getattr(
            _astrbot_filter,
            "PlatformAdapterType",
            _CompatEnum(AIOCQHTTP="AIOCQHTTP"),
        )
        self.EventMessageType = getattr(
            _astrbot_filter,
            "EventMessageType",
            _CompatEnum(ALL="ALL", GROUP_MESSAGE="GROUP_MESSAGE"),
        )

    def __getattr__(self, name):
        if name in {"PlatformAdapterType", "EventMessageType"}:
            return getattr(self, name)

        if self._filter is None:
            return self._identity_decorator

        attr = getattr(self._filter, name, None)
        if callable(attr):
            return self._make_decorator(attr)
        return self._identity_decorator

    def _make_decorator(self, attr):
        def decorator(*args, **kwargs):
            def wrap(func):
                try:
                    return attr(*args, **kwargs)(func)
                except TypeError:
                    try:
                        return attr(func)
                    except TypeError:
                        return func

            return wrap

        return decorator

    @staticmethod
    def _identity_decorator(func=None, *args, **kwargs):
        if func is None:
            return lambda wrapped: wrapped
        return func


filter = _CompatFilter()
AstrMessageEvent = _AstrMessageEvent


def _compat_decorator(name):
    def decorator(*args, **kwargs):
        if _astrbot_filter is None:
            return lambda func: func

        attr = getattr(_astrbot_filter, name, None)
        if not callable(attr):
            return lambda func: func

        try:
            return attr(*args, **kwargs)
        except TypeError:
            try:
                return attr(args[0]) if args and callable(args[0]) and len(args) == 1 and not kwargs else None
            except TypeError:
                return lambda func: func

    return decorator


def command_group(*args, **kwargs):
    return _compat_decorator("command_group")(*args, **kwargs)


def event_message_type(*args, **kwargs):
    return _compat_decorator("event_message_type")(*args, **kwargs)


def llm_tool(*args, **kwargs):
    return _compat_decorator("llm_tool")(*args, **kwargs)


EventMessageType = filter.EventMessageType
