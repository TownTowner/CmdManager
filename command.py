from typing import override


class Command:

    def __init__(self, name="", command="", notes=None, id=None):
        self.id = id
        self.name = name
        self.command = command
        self.notes = notes

    @override
    def __repr__(self) -> str:
        return f"Command(id={self.id}, name={self.name}, command={self.command}, notes={self.notes})"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "command": self.command,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("id"),
            name=data.get("name", ""),
            command=data.get("command", ""),
            notes=data.get("notes", ""),
        )
