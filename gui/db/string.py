from typing import Union
import re
from math import ceil

class String:
    
    def containsAlphanumeric(s):
        
        return not re.search(r'[^a-zA-ZáéiíoóöőuúüűÁÉIÍOÓÖŐUÚÜŰä]', s)

    def replaceAlphanumeric(s, to = " "):
        
        return re.sub("[^a-zA-ZáéiíoóöőuúüűÁÉIÍOÓÖŐUÚÜŰä]+", to, s)
        
    def containsAlphanumericWithNum(s):
        
        return not re.search(r'[^a-zA-Z0-9áéiíoóöőuúüűÁÉIÍOÓÖŐUÚÜŰä]', s)

    def maskString(s, perc: Union[int, float] = 0.6, maskChar: str = "*"):
        
        mask_chars = ceil(len(s) * perc)
        
        return f'{maskChar * mask_chars}{s[mask_chars:]}'