import typing as t
from datetime import datetime
from googleapiclient.errors import HttpError

from .api_view import GmailApiView
from utils.dc.gmail_response_data import ListMessages, Message
from utils.enums.email_status_enum import StatusTypeEnum

class EmailMessagesView(GmailApiView):
    
    def __init__(self, user_id, creds):
        
        super().__init__(user_id, creds)
        
    @GmailApiView.rule(endpoint = "messages", method = "list")   
    async def list_user_messages(self, 
        q: str | None, 
        labelIds: list | None,
        pageToken: str | None,
        maxResults: int | None
        ) -> ListMessages:
        
        try:
            
            params = {}
            
            if q is not None:
                
                params['q'] = q
                
            if labelIds:
                
                params['labelIds'] = labelIds
                
            if pageToken is not None:
                
                params['pageToken'] = pageToken
                
            if maxResults is not None:
                
                params['maxResults'] = maxResults
            
            result = await self.execute(**params)
            
            parsed_result = self.parse_response(result)
            
            self.log.debug("ListMessages response: count=%s, first_10_ids=%s, nextPageToken=%s" % (
                len(parsed_result.messages),
                [m.id for m in parsed_result.messages[:10]],
                parsed_result.nextPageToken
            ))
            
            return parsed_result
            
        except HttpError as exc:
            
            self.log.error("Gmail response failed: %s" % (str(exc)))
            
            raise
        
    def parse_messages(self, messages_dicts: list[dict]) -> list[Message]:
        
        messages: t.List[Message] = []
        
        for i, message in enumerate(messages_dicts):
            
            if not isinstance(message, dict):
                
                self.log.warning("Message at index %s is not a dict: %s" % (i, str(type(message))))
                
                continue

            msg_id = message.get("id")
            
            if not isinstance(msg_id, str):
                
                self.log.warning("Missing or invalid 'id' at index %s" % i)
                
                continue

            raw_label_ids = message.get("labelIds")
            
            if not isinstance(raw_label_ids, list):
                
                raw_label_ids = []

            label_ids_enum: t.List[StatusTypeEnum] = []
           
            for label in raw_label_ids:
                
                if isinstance(label, str):
                    
                    try:
                        
                        label_enum = StatusTypeEnum(label)
                        
                        label_ids_enum.append(label_enum)
                        
                    except ValueError:
                        
                        self.log.warning("Unknown label id '%s' at index %s, skipping" % (label, i))
            
            history_id_val = message.get("historyId")
            
            history_id: int | None = None
            
            if isinstance(history_id_val, str) and history_id_val.isdigit():
                
                history_id = int(history_id_val)

            internal_date_val = message.get("internalDate")
            
            internal_date: datetime | None = None
            
            if isinstance(internal_date_val, str) and internal_date_val.isdigit():
                
                try:
                   
                    internal_date = datetime.fromtimestamp(int(internal_date_val) / 1000)
               
                except Exception as e:
                    
                    self.log.warning("Invalid internalDate at index %s: %s (%s)" % (i, internal_date_val, str(e)))

            try:
                
                message_obj = Message(
                    id = msg_id,
                    threadId = message["threadId"] if isinstance(message.get("threadId"), str) else None,
                    labelIds = label_ids_enum if label_ids_enum else None,
                    snippet = message["snippet"] if isinstance(message.get("snippet"), str) else None,
                    historyId = history_id,
                    internalDate = internal_date,
                    payload = None,
                    sizeEstimate = message["sizeEstimate"] if isinstance(message.get("sizeEstimate"), int) else None,
                    raw = message["raw"] if isinstance(message.get("raw"), str) else None,
                )
                
                messages.append(message_obj)
                
            except Exception as e:
                
                self.log.warning("Failed to build Message object at index %s: %s" % (i, str(e)))
                
                continue
            
        return messages
    
    def parse_response(self, raw: dict) -> ListMessages:
        
        if "messages" not in raw or not isinstance(raw["messages"], list):
            
            self.log.warning("No 'messages' list found in Gmail response or invalid format")
            
            messages_dicts = []
       
        else:
           
            messages_dicts = raw["messages"]

        if len(messages_dicts) > 0:
            
            messages = self.parse_messages(messages_dicts)
            
        else:
            
            messages = []

        return ListMessages(
            messages = messages,
            nextPageToken = raw.get("nextPageToken"),
            resultSizeEstimate = raw.get("resultSizeEstimate"),
        )