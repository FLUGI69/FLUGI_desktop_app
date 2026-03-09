import base64
import json
import logging
import typing as t
from html import escape

from utils.logger import LoggerMixin
from utils.dc.gmail_response_data import MessagePart

class EmailContentHandler(LoggerMixin):

    log: logging.Logger

    def __init__(self):
        
        self.bodies: dict[str, str] = {}
        
        self.cid_images: dict[str, str] = {}
        
        self.attachments: list[dict] = []

    def get_body_to_show(self, payload: MessagePart) -> str:
        
        self.bodies.clear()
        self.cid_images.clear()
        self.attachments.clear()

        if payload is None:
            
            self.log.warning("get_body_to_show: payload is None")
            
            return "<pre><i>(No content)</i></pre>"

        self._extract_part(payload)

        html_body = self.bodies.get("text/html")
        
        plain_body = self.bodies.get("text/plain")

        content = ""

        if html_body is not None and self._has_meaningful_html(html_body):
            
            content = html_body

        elif plain_body is not None:
            
            content = "<pre>%s</pre>" % escape(plain_body)

        else:
            
            try:
                
                json_payload = json.dumps(payload, indent = 2)
                
            except Exception as e:
                
                self.log.warning("get_body_to_show: failed to json.dumps payload: %s" % str(e))
                
                json_payload = "(unable to serialize payload)"
            
            content = "<pre>%s</pre>" % escape(json_payload)

        for cid, img_tag in self.cid_images.items():
            
            content = content.replace("cid:%s" % cid, img_tag)

        if len(self.attachments) > 0:
            
            attachments_html = "<div style='padding:10px; border-bottom: 1px solid #ccc;'>"
            attachments_html += "<b>Attachments:</b> "
            
            for idx, attachment in enumerate(self.attachments):
                
                fname = escape(attachment.get("filename", "unnamed"))
                mtype = escape(attachment.get("mime_type", "application/octet-stream"))
                
                base64data = attachment.get("data", None)
                
                if base64data is not None and base64data != "":
                    
                    attachments_html += (
                        f'<a href="data:{mtype};base64,{base64data}" target="_blank" style="margin-right:10px;">'
                        f'{fname}</a>'
                    )
                    
                else:
            
                    attachments_html += f'<span style="margin-right:10px;">{fname}</span>'
                    
            attachments_html += "</div>"
       
            content += attachments_html

        return content

    def _extract_part(self, part: t.Any) -> None:
        
        if part is None:
            
            self.log.warning("_extract_part: part is None, skipping")
            
            return

        mime_type = self._get_attr(part, "mime_type", "mimeType")

        if mime_type is None or not isinstance(mime_type, str) or mime_type.strip() == "":
            
            mime_type = self._get_content_type_from_headers(part)
            
        if not isinstance(mime_type, str) or mime_type.strip() == "":
            
            mime_type = ""

        mime_type = mime_type.lower()

        body = self._get_attr(part, "body")
        
        data = None
        
        if body is not None and (hasattr(body, "data") or isinstance(body, dict)):
            
            data = self._get_attr(body, "data")
        
        content_id = self._get_header_value(part, "content-id")
        
        filename = self._get_attr(part, "filename")
        
        is_attachment = False
        
        if filename is not None and isinstance(filename, str) and filename.strip() != "":
            
            is_attachment = True

        if mime_type.startswith("image/") and data is not None and content_id is not None:
            
            try:
                
                padded_data = data + '=' * ((4 - len(data) % 4) % 4)
                
                raw = base64.urlsafe_b64decode(padded_data)
  
                b64 = base64.b64encode(raw).decode("ascii")
  
                cid = content_id.strip("<>")

                img_tag = "data:%s;base64,%s" % (mime_type, b64)

                self.cid_images[cid] = img_tag
                
                self.log.debug("Extracted inline image cid: %s" % cid)
                
            except Exception as e:
                
                self.log.exception("Failed to decode inline image: %s" % str(e))

        elif is_attachment == True:
            print("1")

        elif mime_type in ("text/plain", "text/html") and data is not None:
            
            try:
                
                if isinstance(data, str) and data.strip().startswith("<!DOCTYPE"):

                    self.bodies[mime_type] = data
                    
                    self.log.debug("Body already decoded (%s), skipping base64 decode." % mime_type)
                    
                else:
  
                    padded_data = data + '=' * ((4 - len(data) % 4) % 4)
                    
                    decoded = base64.urlsafe_b64decode(padded_data.encode("ascii", errors = "ignore")).decode("utf-8", errors="replace")
                    
                    self.bodies[mime_type] = decoded
                    
                    self.log.debug("Decoded body: %s (%d chars)" % (mime_type, len(decoded)))
           
            except Exception as e:
                
                self.log.exception("Error decoding body (%s): %s" % (mime_type, str(e)))

        parts = self._get_attr(part, "parts")

        if isinstance(parts, list):
            
            for subpart in parts:
                
                self._extract_part(subpart)

    def _get_content_type_from_headers(self, part: t.Any) -> str:
        
        headers = self._get_attr(part, "headers", default = [])
    
        if not isinstance(headers, list):
            
            return ""

        for header in headers:
            
            name = self._get_attr(header, "name")
            
            value = self._get_attr(header, "value")
        
            if isinstance(name, str) and name.lower() == "content-type" and isinstance(value, str):
                
                if value.lower().startswith("text/plain"):
                    
                    return "text/plain"
                
                elif value.lower().startswith("text/html"):
                    
                    return "text/html"
                
        return ""

    def _get_header_value(self, part: t.Any, target: str) -> t.Optional[str]:
        
        headers = self._get_attr(part, "headers", default = [])

        if not isinstance(headers, list):
            
            return None

        for header in headers:
            
            name = self._get_attr(header, "name")
            
            value = self._get_attr(header, "value")
            
            if isinstance(name, str) and name.lower() == target.lower() and isinstance(value, str):
                
                return value
            
        return None

    def _has_meaningful_html(self, html: str) -> bool:
        
        cleaned = html.replace('<div dir="ltr"><br></div>', "").strip()
    
        return len(cleaned) > 0

    def _get_attr(self, obj: t.Any, *names: str, default = None) -> t.Any:
        
        for name in names:
            
            if hasattr(obj, name):
                
                return getattr(obj, name)
            
            if isinstance(obj, dict) and name in obj:
                
                return obj[name]
            
        return default
