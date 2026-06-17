from collections.abc import Sequence
from functools import cache
from typing import Protocol, cast

from django.core.exceptions import ImproperlyConfigured
from strawberry import Info
from strawberry.utils.importer import import_module_symbol

from strawberry_django.fields.types import OperationInfo, OperationMessage
from strawberry_django.settings import strawberry_django_settings


class DjangoErrorConverter(Protocol):
    def __call__(
        self,
        *,
        exc: Exception,
        source: Any,
        info: Info | None,
        args: list[Any],
        kwargs: dict[str, Any],
    ) -> list[OperationMessage] | None: ...


def _load_django_error_converter(import_path: str) -> DjangoErrorConverter:
    converter = import_module_symbol(import_path)
    if not callable(converter):
        raise ImproperlyConfigured(f"{import_path} is not callable")
    return cast("DjangoErrorConverter", converter)


@cache
def _django_error_converters() -> Sequence[DjangoErrorConverter]:
    settings = strawberry_django_settings()
    error_converter_paths = settings["MUTATIONS_ERROR_CONVERTER"]
    if isinstance(error_converter_paths, str):
        error_converter_paths = (error_converter_paths,)
    return tuple(_load_django_error_converter(path) for path in error_converter_paths)


def handle_django_exception(
    exc: Exception,
    source: Any,
    info: Info | None,
    args: list[Any],
    kwargs: dict[str, Any],
) -> OperationInfo:
    for converter in _django_error_converters():
        messages = converter(
            exc=exc, source=source, info=info, args=args, kwargs=kwargs
        )
        if messages is not None:
            return OperationInfo(messages=messages)
    raise exc


def _get_validaton_error_message(error: ValidationError):
    if not error.message:
        return "Unknown error"

    return error.message % error.params if error.params else error.message


def _get_validation_errors(error: Exception):
    if isinstance(error, PermissionDenied):
        kind = OperationMessage.Kind.PERMISSION
    elif isinstance(error, ValidationError):
        kind = OperationMessage.Kind.VALIDATION
    elif isinstance(error, ObjectDoesNotExist):
        kind = OperationMessage.Kind.ERROR
    else:
        kind = OperationMessage.Kind.ERROR

    if isinstance(error, ValidationError) and hasattr(error, "error_dict"):
        # convert field errors
        for field, field_errors in (error.error_dict or {}).items():
            for e in field_errors:
                yield OperationMessage(
                    kind=kind,
                    field=to_camel_case(field) if field != NON_FIELD_ERRORS else None,
                    message=_get_validaton_error_message(e),
                    code=getattr(e, "code", None),
                )
    elif isinstance(error, ValidationError) and hasattr(error, "error_list"):
        # convert non-field errors
        for e in error.error_list or []:
            yield OperationMessage(
                kind=kind,
                message=_get_validaton_error_message(e),
                code=getattr(error, "code", None),
            )
    else:
        msg = getattr(error, "msg", None)
        if msg is None:
            msg = str(error)

        yield OperationMessage(
            kind=kind,
            message=msg,
            code=getattr(error, "code", None),
        )


def default_django_error_converter(
    *,
    exc: Exception,
    source: Any,
    info: Info | None,
    args: list[Any],
    kwargs: dict[str, Any],
) -> list[OperationMessage] | None:
    if isinstance(error, (ValidationError, PermissionDenied, ObjectDoesNotExist)):
        return list(_get_validation_errors(exc))
    return None
