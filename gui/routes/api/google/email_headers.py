import typing as t
from datetime import datetime
from email.utils import parsedate_to_datetime
from googleapiclient.errors import HttpError

from utils.dc.batch_request import BatchRequestData
from utils.dc.gmail_response_data import Message, EmailHeaders, Header, MessagePartBody, MessagePart
from .api_view import GmailApiView
from utils.enums.email_status_enum import StatusTypeEnum
from config import Config

class EmailHeadersView(GmailApiView):
    
    endpoint = "messages"
    
    def __init__(self, user_id, creds):
        
        super().__init__(user_id, creds)

    @GmailApiView.rule(endpoint = "messages", method = "modify")
    async def modify_important_label(self, message: Message, body: dict):
        
        try:
            
            await self.execute(
                id = message.id,
                body = body
            )
            
            self.log.debug("Modified important label for %s with body %s" % (
                message,
                body
                )
            )
            
        except HttpError as e:
            
            self.log.error("Failed to modify important label for message %s: %s" % (
                message, 
                str(e)
                )
            )
            
    async def list_email_headers_batch(self, messages: list[Message]) -> list[EmailHeaders]:
        
        parsed_results = []

        batch_size = Config.google.batch_size

        for i in range(0, len(messages), batch_size):
            
            chunk = messages[i:i + batch_size]

            requests = [
                BatchRequestData(
                    method_name = "get",
                    params = {
                        "id": msg.id,
                        "format": "metadata",
                        "metadataHeaders": [
                            "From",
                            "Subject",
                            "Date"
                        ]
                    }
                )
                for msg in chunk
            ]

            results = await self.execute_batch(requests)
            
            batch_parsed = self.parse_response(results)
            
            parsed_results.extend(batch_parsed)  # All batches

        self.log.debug("[EmailHeaders] response: %s" % parsed_results)
        
        return parsed_results
    
    def parse_message_part(self, part_data: dict) -> MessagePart:

        raw_headers = part_data.get("headers")
        
        headers: t.List[Header] = []
        
        if isinstance(raw_headers, list):
            
            for h in raw_headers:
                
                if (isinstance(h, dict) and isinstance(h.get("name"), str)
                    and isinstance(h.get("value"), str)
                    ):
                    
                    headers.append(Header(name = h["name"], value = h["value"]))

        body_data = part_data.get("body")
        
        message_body = None

        if isinstance(body_data, dict):
            
            if "size" in body_data and "data" in body_data:
                
                size = body_data.get("size")
                
                data = body_data.get("data")
                
                attachmentId = body_data.get("attachmentId", "")
                
                if isinstance(size, int) and isinstance(data, str) and isinstance(attachmentId, str):
                    
                    message_body = MessagePartBody(
                        size = size,
                        data = data,
                        attachmentId = attachmentId,
                    )

        parts_list = []
        
        raw_parts = part_data.get("parts")
        
        if isinstance(raw_parts, list):
            
            for sub_part in raw_parts:
                
                if isinstance(sub_part, dict):
                    
                    parts_list.append(self.parse_message_part(sub_part))

        return MessagePart(
            part_id = part_data.get("partId") if isinstance(part_data.get("partId"), str) else None,
            mime_type = part_data.get("mimeType") if isinstance(part_data.get("mimeType"), str) else None,
            filename = part_data.get("filename") if isinstance(part_data.get("filename"), str) else None,
            headers = headers if headers else None,
            body = message_body,
            parts = parts_list if parts_list else None,
        )

    def parse_response(self, raw: t.List[dict]) -> t.List[EmailHeaders]:
        
        parsed: t.List[EmailHeaders] = []

        for i, msg in enumerate(raw):
            
            if not isinstance(msg, dict):
                
                self.log.warning("Item at index %s is not a dict: %s" % (i, type(msg)))
                
                continue

            msg_id = msg.get("id")
            
            if not isinstance(msg_id, str):
                
                self.log.warning("Missing or invalid 'id' at index %s" % i)
                
                continue

            payload = msg.get("payload")
            
            if isinstance(payload, dict):
                
                message_part = self.parse_message_part(payload)
                
            else:
                
                self.log.warning("Invalid or missing 'payload' at index %s" % i)
                
                message_part = None

            raw_headers = payload.get("headers") if isinstance(payload, dict) else None
            
            header_dict: t.Dict[str, str] = {}

            if isinstance(raw_headers, list):
                
                for h in raw_headers:
                    
                    if (isinstance(h, dict) and isinstance(h.get("name"), str)
                        and isinstance(h.get("value"), str)):
                        
                        header_dict[h["name"]] = h["value"]

            date_obj: t.Optional[datetime] = None
            
            date_str = header_dict.get("Date")
            
            if isinstance(date_str, str):
                
                try:
                    
                    date_obj = parsedate_to_datetime(date_str)
                    
                except Exception as e:
                    
                    self.log.warning("Invalid date format at index %s: %s (%s)" % (i, date_str, str(e)))

            raw_label_ids = msg.get("labelIds")
            
            if not isinstance(raw_label_ids, list):
                
                raw_label_ids = []

            ui_label_map = {
                "YELLOW_STAR": "STARRED",
                "RED_STAR": "STARRED",
                "BLUE_STAR": "STARRED",
                "GREEN_STAR": "STARRED",
                "PURPLE_STAR": "STARRED",
                "ORANGE_STAR": "STARRED"
            }
            
            raw_label_ids = [ui_label_map.get(label, label) for label in raw_label_ids]

            label_ids_enum: t.List[StatusTypeEnum] = []

            for label in raw_label_ids:
                
                if isinstance(label, str):
                    
                    try:
                        
                        label_enum = StatusTypeEnum(label)
                        label_ids_enum.append(label_enum)
                        
                    except ValueError:
                        
                        self.log.warning("Unknown label id '%s' at index %s, skipping" % (label, i))
    
            label_set = set(label_ids_enum)
  
            is_read = StatusTypeEnum.UNREAD not in label_set
            
            is_important = StatusTypeEnum.IMPORTANT in label_set

            history_id_val = msg.get("historyId")
            
            history_id: int | None = None
            
            if isinstance(history_id_val, str) and history_id_val.isdigit():
                
                history_id = int(history_id_val)

            internal_date_val = msg.get("internalDate")
            
            internal_date: datetime | None = None
            
            if isinstance(internal_date_val, str) and internal_date_val.isdigit():
                
                try:
                    
                    internal_date = datetime.fromtimestamp(int(internal_date_val) / 1000)
                    
                except Exception as e:
                    
                    self.log.warning("Invalid internalDate at index %s: %s (%s)" % (i, internal_date_val, str(e)))

            parsed.append(
                EmailHeaders(
                    id = msg_id,
                    threadId = msg["threadId"] if isinstance(msg.get("threadId"), str) else None,
                    labelIds = label_ids_enum if label_ids_enum else None,
                    snippet = msg["snippet"] if isinstance(msg.get("snippet"), str) else None,
                    historyId = history_id,
                    internalDate = internal_date,
                    payload = message_part,
                    sizeEstimate = msg["sizeEstimate"] if isinstance(msg.get("sizeEstimate"), int) else None,
                    raw = msg["raw"] if isinstance(msg.get("raw"), str) else None,
                    sender = header_dict.get("From"),
                    subject = header_dict.get("Subject"),
                    date = date_obj,
                    is_read = is_read,
                    is_important = is_important,
                )
            )

        return parsed