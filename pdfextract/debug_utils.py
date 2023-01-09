
import typing
import pdfminer, pdfminer.layout


class Test:
  prop1: int = 2
  def __init__(self) -> None:
    self.prop1 = 5
    self.__hidden = []
  def as_dict(self):
    out: typing.Dict[str, typing.Any] = dict()
    for key in self.__dict__.keys():
      if not key.startswith("_Test__"):
        out[key] = self.__dict__[key]
    return out

if __name__ == "__main__":
  import json
  t = Test()
  print(t.__dict__)
  print(json.dumps(t.__dict__))
  print(t.as_dict(), t.__class__.__name__ )