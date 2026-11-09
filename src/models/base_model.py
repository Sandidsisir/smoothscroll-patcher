class BaseModel:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def dict(self) -> dict:
        return self.__dict__

    def to_str(self) -> str:
        return str(self.__dict__)
