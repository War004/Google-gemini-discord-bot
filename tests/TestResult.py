from tests.Level import Level
class Failed:
    instance: str
    method: str
    reason: str
    message: str
    level: int

    def __init__(self, method: object, reason: str, message: str, level: Level):
        self.instance = method.__self__.__class__.__name__
        self.method = method.__name__
        self.reason = reason
        self.message = message
        self.level = level
    
    def __str__(self):
        level_label = "WARNING" if self.level == 1 else "ERROR"
        return (
            f"[{level_label}] {self.instance}.{self.method}\n"
            f"Reason: {self.reason}\n"
            f"Message: {self.message}"
        )

    def __repr__(self):
        return f"Failed(instance={self.instance}, method={self.method}, level={self.level}, reason={self.reason})"

class Passed:
    instance: str
    method: str

    def __init__(self, method: object):
        self.instance = method.__self__.__class__.__name__
        self.method = method.__name__
    
    def __str__(self):
        return f"[PASSED] {self.instance}.{self.method}"

    def __repr__(self):
        return f"Passed(instance={self.instance}, method={self.method})"