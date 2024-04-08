import json

from fastapi import Depends
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session, SQLModel, create_engine

from .config import settings


def json_serializer(*args, **kwargs) -> str:
    """

    :param *args:
    :param **kwargs:

    """
    return json.dumps(*args, default=jsonable_encoder, **kwargs)


engine = create_engine(
    settings.db.uri,
    echo=settings.db.echo,
    connect_args=settings.db.connect_args,
    json_serializer=json_serializer,
)


def create_db_and_tables(engine) -> None:
    """

    :param engine:

    """
    SQLModel.metadata.create_all(engine)


def get_session():
    """ """
    with Session(engine) as session:
        yield session


ActiveSession = Depends(get_session)
