"""
Task API
--------
"""

import builtins
import datetime
import json
from types import UnionType
from typing import Annotated, Any, ClassVar, Literal, Union, get_args, get_origin

from dateutil.parser import parse as parse_date
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, PlainSerializer

from bugwarrior.config.schema import Priority as ConfigPriority


def coerce_datetime(value: str | datetime.datetime | None) -> datetime.datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime.datetime):
        return value.replace(microsecond=0)
    parsed = parse_date(value)
    if not parsed.tzinfo:
        parsed = parsed.replace(tzinfo=datetime.UTC)
    return parsed.replace(microsecond=0)


def _coerce_empty_priority(value: object) -> object:
    return None if value == "" else value


def _format_duration(value: datetime.timedelta | None) -> str | None:
    """Render a duration the way Taskwarrior stores one.

    Taskwarrior rewrites a duration when it saves it: give it "PT12600S" and
    it stores "PT3H30M". The next sync would then read back a value which does
    not match what we sent, and update the task again, every time. So write
    days, hours, minutes and seconds, and leave out the ones which are zero.
    """
    if value is None:
        return None
    days, seconds = divmod(max(int(value.total_seconds()), 0), 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    time = "".join(
        f"{amount}{unit}"
        for amount, unit in ((hours, "H"), (minutes, "M"), (seconds, "S"))
        if amount
    )
    if not days and not time:
        return "PT0S"
    return "P" + (f"{days}D" if days else "") + (f"T{time}" if time else "")


IssueDatetime = Annotated[datetime.datetime | None, BeforeValidator(coerce_datetime)]
Priority = Annotated[ConfigPriority | None, BeforeValidator(_coerce_empty_priority)]
Status = Literal["pending", "completed", "deleted", "waiting", "recurring"] | None
Duration = Annotated[datetime.timedelta | None, PlainSerializer(_format_duration)]


def _uda_type(annotation: Any) -> str:
    """Map a pydantic field annotation to a Taskwarrior UDA type.

    Pydantic has already removed Annotated from field.annotation. The only
    thing left to unwrap is an Optional, a union with one type besides None.
    """
    if get_origin(annotation) in (Union, UnionType):
        non_none = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(non_none) == 1:
            annotation = non_none[0]
    match annotation:
        case datetime.datetime | datetime.date:
            return "date"
        case datetime.timedelta:
            return "duration"
        case builtins.int | builtins.float | builtins.bool:
            return "numeric"
        case _:
            return "string"


class Udas(BaseModel):
    """A service's UDA declarations.

    Every field is a UDA. The base class has no fields: it is what a task
    without UDAs uses, and the default for Task. A service subclasses it to
    declare its own UDAs, and the unique key which identifies a task in the
    remote service.

    The field annotation decides the Taskwarrior UDA type. An Optional is
    unwrapped first, so "str | None" declares a string UDA:

    - datetime.datetime and datetime.date -> date
    - datetime.timedelta -> duration
    - int, float and bool -> numeric
    - anything else, str included -> string

    The field title becomes the UDA label, and the field name becomes the
    label when the field has no title.
    """

    model_config = ConfigDict(extra="forbid")

    #: Names of the UDA fields which identify a task in the remote service.
    #: There is no default on purpose: an empty unique key matches every
    #: pending task in the user's database, so a service which forgets it must
    #: fail rather than run.
    UNIQUE_KEY: ClassVar[tuple[str, ...]]

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """Reject a unique key which names something other than a declared UDA."""
        unique_key = getattr(cls, "UNIQUE_KEY", None)
        if unique_key is None:
            return
        undeclared = [name for name in unique_key if name not in cls.model_fields]
        if undeclared:
            raise TypeError(
                f"{cls.__name__}.UNIQUE_KEY names undeclared fields: "
                f"{', '.join(undeclared)}"
            )

    @classmethod
    def serialize(cls) -> dict[str, dict[str, str]]:
        """Return this service's UDA definitions, one per declared field.

        The type comes from the field annotation; the label from the field's
        title, falling back to the field name.
        """
        return {
            name: {"type": _uda_type(field.annotation), "label": field.title or name}
            for name, field in cls.model_fields.items()
        }


class Task(BaseModel):
    """A typed Taskwarrior record.

    The Taskwarrior fields that services currently set are declared here. A
    service adds its own UDAs by subclassing Task and replacing the "udas" field
    with its own Udas model.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    @classmethod
    def get_udas_model(cls) -> type[Udas]:
        return cls.model_fields["udas"].annotation

    @classmethod
    def serialize(cls) -> dict[str, dict[str, str]]:
        return cls.get_udas_model().serialize()

    @classmethod
    def get_unique_key(cls) -> tuple[str, ...]:
        return cls.get_udas_model().UNIQUE_KEY

    def to_task_data(self) -> dict[str, Any]:
        """Return a flat dictionary suitable for Taskwarrior synchronization.

        Standard fields are written only when they were set. Every UDA is
        written. A Taskwarrior record is flat, so the UDAs leave the nested
        model and sit next to the standard fields.
        """
        data = self.model_dump(exclude={"udas"}, exclude_unset=True)
        data.update(self.udas.model_dump())
        return data

    def unique_identifier(self) -> str:
        data = self.to_task_data()
        return json.dumps(
            {key: data[key] for key in self.get_unique_key()}, sort_keys=True
        )

    annotations: list[str] = Field(default_factory=list)
    description: str | None = None
    due: IssueDatetime = None
    end: IssueDatetime = None
    entry: IssueDatetime = None
    modified: IssueDatetime = None
    priority: Priority = None
    project: str | None = None
    scheduled: IssueDatetime = None
    status: Status = None
    tags: list[str] = Field(default_factory=list)
    wait: IssueDatetime = None

    #: The service's :class:`Udas` subclass.
    udas: Udas = Field(default_factory=Udas)
