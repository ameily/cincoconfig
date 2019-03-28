from typing import Union


class DomElement:
    def toprettyxml(self, indent: str = None) -> str: ...


def parseString(text: Union[str, bytes]) -> DomElement: ...
