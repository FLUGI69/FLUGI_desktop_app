from datetime import datetime
from googleapiclient.errors import HttpError

from .api_view import GmailApiView

class EmailPushNotificationView(GmailApiView):
    
    def __init__(self, user_id, creds):
        
        super().__init__(user_id, creds)
    
    @GmailApiView.rule(endpoint = "watch", method = None)
    async def watch_for_new_emails(self, topicName: str, labelIds: list[str]):
        
        try:
            
            body = {
                "topicName": topicName,
                "labelIds": labelIds
            }
            
            result = await self.execute(body = body)
            
            self.log.debug("Watch response: %s" % result)
            
            return result
            
        except HttpError as exc:
            
            self.log.error("Gmail response failed: %s" % (str(exc)))
            
            raise