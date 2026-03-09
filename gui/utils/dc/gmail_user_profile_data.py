from dataclass import DataclassBaseModel

class GmailUserProfileData(DataclassBaseModel):
    emailAddress: str
    messagesTotal: int
    threadsTotal: int
    historyId: int 