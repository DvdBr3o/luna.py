class NuTag:
    def __repr__(self) -> str:
        return f"<NuTag at {hex(id(self))}>"


def nu() -> NuTag:
    return NuTag()
