"""The contract every speech engine implements. Adding a new model (or a new
language) means adding one file that subclasses Engine and registering it."""
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Voice:
    id: str
    name: str
    language: str       # BCP-47 style, e.g. "en-us"
    language_name: str
    gender: str
    description: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class ModelFile:
    name: str
    url: str
    size: int           # approximate bytes, for progress and integrity checks
    sha256: str = None  # checked after download when given


class Engine(ABC):
    id = ""
    name = ""
    license = ""
    loaded = False

    @abstractmethod
    def files(self):
        """Model files this engine needs (list of ModelFile)."""

    @abstractmethod
    def load(self, models_dir):
        """Load the model into memory. Called once, after files are present."""

    @abstractmethod
    def voices(self):
        """All voices this engine can speak (list of Voice)."""

    @abstractmethod
    def synthesize(self, text, voice_id, speed):
        """Return (mono float32 numpy array, sample_rate) for one passage of text."""

    def voice(self, voice_id):
        for v in self.voices():
            if v.id == voice_id:
                return v
        return None
