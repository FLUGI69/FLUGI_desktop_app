from datetime import datetime
from googleapiclient.errors import HttpError

from .api_view import GmailApiView
from utils.dc.google.gmail_response_data import MessagePart, MessagePartBody, Header, Message
from utils.enums.email_status_enum import StatusTypeEnum

class EmailMessageView(GmailApiView):
    
    def __init__(self, user_id, creds):
        
        super().__init__(user_id, creds)
        
    @GmailApiView.rule(endpoint = "messages", method = "get")  
    async def get_message_by_id(self, 
        id: str
        ) -> Message:
        
        try:
            
            result = await self.execute(
                id = id, 
                format = "full"
            )
            
            parsed_result = self.parse_response(result)
            
            self.log.debug("Message response: %s" % parsed_result)
            
            return parsed_result
            
        except HttpError as exc:
            
            self.log.error("Gmail response failed: %s" % (str(exc)))
            
            raise
    
    @GmailApiView.rule(endpoint = "messages", method = "trash")   
    async def move_to_bin(self, message: Message) -> None:
        
        try:
            
            await self.execute(id = message.id)
            
            self.log.info("%s successfully moved to the bin" % message)
            
        except HttpError as e:
            
            self.log.error("Gmail response failed: %s -> %s" % (
                message,
                str(e)    
                )
            )
            
            raise
        
    @GmailApiView.rule(endpoint = "messages", method = "delete")    
    async def permanently_delete_message(self, message: Message) -> None:
        
        try:
            
            await self.execute(message.id)
            
            self.log.debug("Permanent deletion performed on (%s - %s)" % (
                message, 
                message.id
                )
            )
            
        except HttpError as e:
            
            self.log.error("Gmail response failed: %s -> %s" % (
                message,
                str(e)    
                )
            )
            
            raise
        
    @GmailApiView.rule(endpoint = "messages", method = "modify")
    async def modify_as_read(self,
        message: Message
        ):
        
        try:
            
            await self.execute(
                    id = message.id,
                    body = {"removeLabelIds": [StatusTypeEnum.UNREAD.value]}
                )

            self.log.debug("Marked %s as read" % message)

        except HttpError as exc:
            
            self.log.error("Failed to mark %s as read: %s" % (
                message, 
                str(exc)
                )
            )

    @GmailApiView.rule(endpoint = "messages", method = "attachments.get")
    async def get_attachment_data(self, 
        message_id: str, 
        attachment_id: str
        ) -> str | None:
        
        try:
            
            result = await self.execute(
                messageId = message_id, 
                id = attachment_id
            )
            
            data = result.get("data")
            
            if isinstance(data, str):
                
                self.log.debug("Attachment data fetched for message %s, attachment %s (%d chars)" % (
                    message_id, 
                    attachment_id, 
                    len(data)
                ))
                
                return data
            
            self.log.warning("No data field in attachment response for message %s, attachment %s" % (
                message_id, 
                attachment_id
            ))
            
            return None
            
        except HttpError as exc:
            
            self.log.error("Failed to fetch attachment %s from message %s: %s" % (
                attachment_id, 
                message_id, 
                str(exc)
            ))
            
            raise
        
    def parse_message_part(self, data: dict) -> MessagePart | None:
        
        if not isinstance(data, dict):
            
            self.log.error("Invalid message part, expected dict but got: %s" % type(data))
            
            return None

        headers = None
        
        headers_raw = data.get("headers")
        
        if isinstance(headers_raw, list):
            
            headers = []
            
            for i, h in enumerate(headers_raw):
                
                if isinstance(h, dict) and isinstance(h.get("name"), str) and isinstance(h.get("value"), str):
                   
                    headers.append(Header(name = h["name"], value = h["value"]))
                
                else:
                    
                    self.log.warning("Invalid header at index %d: %s" % (i, h))

        body = None
        
        body_raw = data.get("body")
        
        if isinstance(body_raw, dict):
            
            attachment_id = body_raw.get("attachmentId")
            
            size = body_raw.get("size")
            
            raw_data = body_raw.get("data")

            attachment_id_str = attachment_id if isinstance(attachment_id, str) else ""
            
            size_int = int(size) if isinstance(size, int) or (isinstance(size, str) and size.isdigit()) else 0
        
            body = MessagePartBody(
                attachmentId = attachment_id_str,
                size = size_int,
                data = raw_data if isinstance(raw_data, str) else ""
            )

        parts = None
        
        parts_raw = data.get("parts")
        
        if isinstance(parts_raw, list) and parts_raw:
            
            parts = []
            
            for i, part in enumerate(parts_raw):
                
                parsed = self.parse_message_part(part)
                
                if parsed:
                    
                    parts.append(parsed)
                    
                else:
                    
                    self.log.warning("Skipping invalid subpart at index %d" % i)

            if not parts:
                
                parts = None  # ha egyik subpart se volt valid

        part_id = data.get("partId")
        
        mime_type = data.get("mimeType")
        
        filename = data.get("filename")

        return MessagePart(
            part_id = part_id if isinstance(part_id, str) else None,
            mime_type = mime_type if isinstance(mime_type, str) else None,
            filename = filename if isinstance(filename, str) else None,
            headers = headers,
            body = body,
            parts = parts
        )

    def parse_response(self, raw: dict) -> Message:

        msg_id = raw.get('id')
        
        if not isinstance(msg_id, str):
            
            self.log.error("Missing or invalid 'id' field in raw message data")
            
            raise KeyError("Missing or invalid 'id' field")

        label_ids_raw = raw.get('labelIds')
        
        label_ids = None
        
        if isinstance(label_ids_raw, list) and label_ids_raw:
            
            label_ids = []
            
            for label in label_ids_raw:
                
                if not isinstance(label, str):
                    
                    self.log.warning("Label id not string, skipping: %s" % (str(label)))
                    
                    continue
                
                try:
                    
                    label_ids.append(StatusTypeEnum(label))
                    
                except ValueError:
                    
                    self.log.warning("Unknown label id '%s', skipping" % (label))
        
        else:
            
            self.log.debug("No labelIds or empty list found in message id %s" % (msg_id))

        internal_date = None
        
        internal_date_raw = raw.get('internalDate')
        
        if isinstance(internal_date_raw, str) and internal_date_raw.isdigit():
            
            try:
                
                internal_date = datetime.fromtimestamp(int(internal_date_raw) / 1000)
                
            except Exception as e:
                
                self.log.warning("Failed to parse internalDate '%s': %s" % (internal_date_raw, str(e)))
       
        else:
            
            self.log.debug("No valid internalDate found in message id %s" % (msg_id))

        history_id = None
        
        history_id_raw = raw.get('historyId')
        
        if history_id_raw is not None:
            
            try:
                
                history_id = int(history_id_raw)
                
            except Exception as e:
                
                self.log.warning("Failed to parse historyId '%s': %s" % (str(history_id_raw), str(e)))

        payload_raw = raw.get('payload')
        
        payload = None
        
        if isinstance(payload_raw, dict):
            
            payload = self.parse_message_part(payload_raw)

        thread_id = raw.get('threadId')
        
        if not (thread_id is None or isinstance(thread_id, str)):
            
            self.log.warning("Invalid threadId type, expected str or None, got %s" % (type(thread_id)))

        snippet = raw.get('snippet')
        
        if not (snippet is None or isinstance(snippet, str)):
            
            self.log.warning("Invalid snippet type, expected str or None, got %s" % (type(snippet)))

        size_estimate = raw.get('sizeEstimate')
        
        if not (size_estimate is None or isinstance(size_estimate, int)):
            
            self.log.warning("Invalid sizeEstimate type, expected int or None, got %s" % (type(size_estimate)))

        raw_field = raw.get('raw')
        
        if not (raw_field is None or isinstance(raw_field, str)):
            
            self.log.warning("Invalid raw type, expected str or None, got %s" % (type(raw_field)))

        try:
            
            message = Message(
                id = msg_id,
                threadId = thread_id if isinstance(thread_id, str) else None,
                labelIds = label_ids,
                snippet = snippet if isinstance(snippet, str) else None,
                historyId = history_id,
                internalDate = internal_date,
                payload = payload,
                sizeEstimate = size_estimate if isinstance(size_estimate, int) else None,
                raw = raw_field if isinstance(raw_field, str) else None,
            )
            
        except Exception as e:
            
            self.log.error("Failed to build Message object: %s" % (str(e)))
            
            raise

        self.log.debug("Parsed full message object for id %s" % (msg_id))
        
        return message