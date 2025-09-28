from datetime import date
from pydantic import BaseModel, AnyUrl
from typing import List


class Item(BaseModel):
    title: str
    url: AnyUrl
    gist: str
    source: str


class Payload(BaseModel):
    date: date
    tech: List[Item]
    side: List[Item]
    qiita: List[Item]
