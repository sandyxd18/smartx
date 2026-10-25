"""What job kinds may use besides their run folder and params."""

from dataclasses import dataclass

from app.config import Settings
from app.content import ExerciseCatalog


@dataclass(frozen=True)
class JobContext:
    settings: Settings
    catalog: ExerciseCatalog


class JobInputError(ValueError):
    """The params passed validation but refer to something unusable (e.g. unknown exercise).

    The message is shown to the user, so write it in Indonesian.
    """
