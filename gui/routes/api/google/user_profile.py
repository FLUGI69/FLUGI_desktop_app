import re
import asyncio
from email.mime.text import MIMEText
import base64  
from googleapiclient.errors import HttpError

from .api_view import GmailApiView
from utils.dc.gmail_user_profile_data import GmailUserProfileData

class UserProfileView(GmailApiView):
    
    def __init__(self, user_id, creds):
        
        super().__init__(user_id, creds)
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        
        if email is not None:

            pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
            
            return re.match(pattern, email) is not None
        
        return False
    
    @GmailApiView.rule(endpoint = "getProfile", method = None)
    async def get_user_profile_data(self):
        
        try:
            
            result = await self.execute()
            
            parsed_result = self.parse_response(result)
            
            self.log.debug("GmailUserProfileData response: %s" % parsed_result)
            
            return parsed_result
        
        except HttpError as exc:
            
            self.log.error("Gmail response failed: %s" % (str(exc)))
            
            raise
        
    @GmailApiView.rule(endpoint = "messages", method = "send")
    async def send_message(self,
        from_email: str,
        to_email: str, 
        subject: str, 
        body_text: str, 
        is_html: bool = False
        ):

        if self.is_valid_email(to_email) == False:
            
            raise ValueError("Invalid email address provided: %s" % to_email)

        if subject is None:
            
            raise ValueError("Subject cannot be empty")

        if body_text is None:
            
            raise ValueError("Body cannot be empty")

        from_email = from_email
        
        try:

            message = MIMEText(
                _text = body_text, 
                _subtype = "html" if is_html == True else "plain" if is_html == False else None
            )
            
            message['to'] = to_email
            message['from'] = from_email
            message['subject'] = subject

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            sent = await asyncio.to_thread(lambda: self.execute(body = {'raw': raw_message}))
            
            self.log.info("Email sent to %s with subject '%s'")
            
            return sent
        
        except Exception as e:
            
            self.log.exception("Failed to send email to %s: %s" % (
                to_email,
                str(e)
                )
            )
    
    def parse_response(self, raw: dict) -> GmailUserProfileData:
        
        if not isinstance(raw, dict):
            
            self.log.error("Expected dict in parse_response, got: %s" % type(raw))
            
            raise TypeError("Invalid response type")

        try:
            
            email_address = raw.get("emailAddress")
            
            if not isinstance(email_address, str):
                
                self.log.warning("Invalid or missing 'emailAddress': %s" % email_address)
                
                email_address = None

            messages_total_val = raw.get("messagesTotal")
            
            messages_total = messages_total_val if isinstance(messages_total_val, int) else None
           
            if messages_total is None:
               
                self.log.warning("Invalid or missing 'messagesTotal': %s" % messages_total_val)

            threads_total_val = raw.get("threadsTotal")
            
            threads_total = threads_total_val if isinstance(threads_total_val, int) else None
           
            if threads_total is None:
                
                self.log.warning("Invalid or missing 'threadsTotal': %s" % threads_total_val)

            history_id_val = raw.get("historyId")
            
            history_id = int(history_id_val) if isinstance(history_id_val, str) and history_id_val.isdigit() else None
            
            if history_id is None:
                
                self.log.warning("Invalid or missing 'historyId': %s" % history_id_val)

            profile_data = GmailUserProfileData(
                emailAddress = email_address,
                messagesTotal = messages_total,
                threadsTotal = threads_total,
                historyId = history_id
            )

            return profile_data

        except Exception as e:
            
            self.log.error("Failed to parse GmailUserProfileData: %s" % str(e))
            
            raise