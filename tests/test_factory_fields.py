import random
from datetime import datetime, timedelta
from typing import Any, Optional

import pytest
from pydantic import BaseModel

from polyfactory.exceptions import MissingBuildKwargException
from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.fields import Ignore, PostGenerated, Require, Use


def test_use() -> None:
    class MyClass:
        name: str

        @classmethod
        def builder(cls, name: str) -> "MyClass":
            instance = MyClass()
            instance.name = name
            return instance

    default_name = "Moishe Zuchmir"

    class MyModel(BaseModel):
        my_class: MyClass

        class Config:
            arbitrary_types_allowed = True

    class MyFactory(ModelFactory):
        __model__ = MyModel
        my_class = Use(fn=MyClass.builder, name=default_name)

    result = MyFactory.build()
    assert result.my_class.name == default_name


def test_sub_factory() -> None:
    default_name = "Moishe Zuchmir"

    class FirstModel(BaseModel):
        name: str

    class SecondModel(BaseModel):
        first_model: FirstModel

    class MyFactory(ModelFactory):
        __model__ = SecondModel
        first_model = Use(fn=ModelFactory.create_factory(FirstModel).build, name=default_name)

    result = MyFactory.build()
    assert result.first_model.name == default_name


def test_build_kwarg() -> None:
    class MyModel(BaseModel):
        name: str

    class MyFactory(ModelFactory):
        __model__ = MyModel
        name = Require()

    with pytest.raises(MissingBuildKwargException):
        MyFactory.build()

    assert MyFactory.build(name="moishe").name == "moishe"


def test_ignored() -> None:
    class MyModel(BaseModel):
        name: Optional[str]

    class MyFactory(ModelFactory):
        __model__ = MyModel
        name = Ignore()

    assert MyFactory.build().name is None


def test_post_generation() -> None:
    random_delta = timedelta(days=random.randint(0, 12), seconds=random.randint(13, 13000))

    def add_timedelta(name: str, values: Any, **kwargs: Any) -> datetime:
        assert name == "to_dt"
        assert "from_dt" in values
        assert isinstance(values["from_dt"], datetime)
        return values["from_dt"] + random_delta

    def decide_long(name: str, values: Any, **kwargs: Any) -> bool:
        assert name == "is_long"
        assert "from_dt" in values
        assert "to_dt" in values
        assert "threshold" in kwargs
        assert isinstance(values["from_dt"], datetime)
        assert isinstance(values["to_dt"], datetime)
        difference = values["to_dt"] - values["from_dt"]
        return difference.days > kwargs["threshold"]  # type: ignore

    def make_caption(name: str, values: Any, **kwargs: Any) -> str:
        assert name == "caption"
        assert "is_long" in values
        return "this was really long for me" if values["is_long"] else "just this"

    class MyModel(BaseModel):
        from_dt: datetime
        to_dt: datetime
        is_long: bool
        caption: str

    class MyFactory(ModelFactory):
        __model__ = MyModel
        to_dt = PostGenerated(add_timedelta)
        is_long = PostGenerated(decide_long, threshold=1)
        caption = PostGenerated(make_caption)

    result = MyFactory.build()
    assert result.to_dt - result.from_dt == random_delta
    assert result.is_long == (random_delta.days > 1)
    if result.is_long:
        assert result.caption == "this was really long for me"
    else:
        assert result.caption == "just this"
