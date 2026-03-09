import os

class File:

    def checkIsFile(path):
        
        return True if os.path.isfile(path) and os.access(path, os.R_OK) else False

    def checkIsExists(path):
        
        return True if os.path.exists(path) and os.access(path, os.R_OK) else False

    def getFolderSize(folder):
        
        total_size = os.path.getsize(folder)
        
        for item in os.listdir(folder):
            
            itempath = os.path.join(folder, item)
            
            if os.path.isfile(itempath):
                
                total_size += os.path.getsize(itempath)
                
            elif os.path.isdir(itempath):
                
                total_size += File.getFolderSize(itempath)
                
        return total_size