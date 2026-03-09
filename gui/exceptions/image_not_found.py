class ImageNotFound(Exception):
    
    def __init__(self, file_path: str):
        
        self.file_path = file_path
        
        self.message = f"Image file not found at the specified path: '{file_path}'"
        
        super().__init__(self.message)