from pydantic import BaseModel


def dump(model: BaseModel) -> dict:
    return model.model_dump(mode="json", by_alias=True, exclude_none=True)
