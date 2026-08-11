import datetime
from types import UnionType
from typing import Annotated, Any, ClassVar, Literal, Union, get_args, get_origin

from dateutil.parser import parse as parse_date
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from bugwarrior.config.schema import Priority as ConfigPriority, parse_config_list


def _coerce_datetime(value: Any) -> datetime.datetime | None:
    """Parse a date string or passthrough an existing datetime.

    Ensures every stored datetime is timezone-aware (UTC when absent) and has
    no sub-second precision.
    """
    if not value:
        return None
    if isinstance(value, datetime.datetime):
        return value.replace(microsecond=0)
    parsed = parse_date(value)
    if not parsed.tzinfo:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed.replace(microsecond=0)


def _coerce_priority(value: Any) -> Any:
    if value == '':
        return None
    if isinstance(value, str):
        return value.upper()
    return value


def _coerce_status(value: Any) -> Any:
    if isinstance(value, str):
        return value.lower()
    return value


def _coerce_optional_config_list(value: Any) -> Any:
    if value is None:
        return None
    return parse_config_list(value)


IssueDatetime = Annotated[datetime.datetime | None, BeforeValidator(_coerce_datetime)]
Priority = Annotated[ConfigPriority | None, BeforeValidator(_coerce_priority)]
Status = Annotated[
    Literal['pending', 'completed', 'deleted', 'waiting', 'recurring'] | None,
    BeforeValidator(_coerce_status),
]
Depends = Annotated[list[str] | None, BeforeValidator(_coerce_optional_config_list)]


def _uda_type(annotation: Any) -> str:
    """Map a pydantic field annotation to a Taskwarrior UDA type.

    Pydantic exposes ``field.annotation`` with ``Annotated`` already stripped,
    so only an Optional (a lone non-None Union member) needs unwrapping.
    """
    if get_origin(annotation) in (Union, UnionType):
        non_none = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(non_none) == 1:
            annotation = non_none[0]
    if annotation in (datetime.datetime, datetime.date):
        return 'date'
    if annotation in (int, float, bool):
        return 'numeric'
    return 'string'


class Udas(BaseModel):
    """A service's UDA declarations.

    Every field is a UDA. The base class declares no fields (a task with no
    UDAs, and the Task default); a service subclasses it to declare its UDA
    fields and the unique key identifying a task in the foreign system.
    """

    model_config = ConfigDict(extra='forbid')

    #: Field names (UDA or generic) that uniquely identify a task externally.
    UNIQUE_KEY: ClassVar[tuple[str, ...]] = ()

    @classmethod
    def get_udas(cls) -> dict[str, dict[str, str]]:
        """Return this service's UDA definitions, one per declared field.

        The type comes from the field annotation; the label from the field's
        title, falling back to the field name.
        """
        return {
            name: {'type': _uda_type(field.annotation), 'label': field.title or name}
            for name, field in cls.model_fields.items()
        }

    @classmethod
    def get_unique_key(cls) -> tuple[str, ...]:
        """Return field names that uniquely identify a task externally."""
        return cls.UNIQUE_KEY


class Task(BaseModel):
    """A typed Taskwarrior record.

    Generic Taskwarrior fields are declared here. Service-specific UDAs are
    composed in via the "udas" field: a service subclasses Task and overrides
    "udas" with its own Udas model.
    """

    model_config = ConfigDict(extra='forbid')

    def to_taskwarrior_data(self) -> dict[str, Any]:
        """Return a flat dictionary suitable for Taskwarrior synchronization.

        Standard fields are emitted only when explicitly set, except tags which
        is always present (a task always has a, possibly empty, tag list). Every
        UDA is emitted (Taskwarrior records are flat, so the nested udas model
        is merged up into the top level).
        """
        data = self.model_dump(exclude={'udas'}, exclude_unset=True)
        data.setdefault('tags', self.tags)
        data.update(self.udas.model_dump())
        return data

    annotations: list[str] = Field(default_factory=list)
    depends: Depends = None
    description: str | None = None
    due: IssueDatetime = None
    end: IssueDatetime = None
    entry: IssueDatetime = None
    id: int | float | None = None
    imask: int | float | None = None
    mask: str | None = None
    modified: IssueDatetime = None
    parent: str | None = None
    priority: Priority = None
    project: str | None = None
    recur: str | datetime.timedelta | None = None
    scheduled: IssueDatetime = None
    start: IssueDatetime = None
    status: Status = None
    tags: list[str] = Field(default_factory=list)
    until: IssueDatetime = None
    urgency: int | float | None = None
    uuid: str | None = None
    wait: IssueDatetime = None

    udas: Udas = Field(default_factory=Udas)
