import sys
import json
from pathlib import Path

def determine_version_phase(version_tuple):
    
    major, minor, patch, build = (version_tuple + (0, 0, 0, 0))[:4]

    if major == 0:
        
        if minor == 0 and patch == 0:
            
            phase = "alpha"
            
        elif patch > 0 and build == 0:
            
            phase = f"beta{patch}"
            
        elif build > 0:
            
            phase = f"rc{build}"
            
        else:
            
            phase = "beta"
    
    else:
    
        if patch == 0 and build == 0:
            
            phase = "stable"
            
        elif patch > 0 and build == 0:
            
            phase = f"hotfix{patch}"
            
        elif build > 0:
            
            phase = f"stable-build{build}"
            
        else:
            
            phase = "stable"

    if major == 0 and minor == 0 and patch == 0 and build > 0:
        
        phase = f"nightly{build}"
        
    elif major == 0 and minor == 0 and patch > 0 and build > 0:
        
        phase = f"experimental{patch}-{build}"
    
    return phase

def load_version_file():
    
    try:
        
        version_path = Path(sys.executable).parent / "_internal" / "gui" / "version.json"

        with version_path.open("r", encoding = "utf-8") as f:
            
            data = json.load(f)
            
            version_str = data.get("version", "0.0.0.0")
            
            version_tuple = tuple(int(part) for part in version_str.split("."))
            
            version_phase = determine_version_phase(version_tuple)
            
            return version_tuple, version_phase

    except Exception as e:
        
        print(f"[VERSION LOADER ERROR] {e}")
        
        return (0, 0, 0, 0), "alpha"  # fallback

if getattr(sys, "frozen", False):
    
    VERSION, VERSION_STR = load_version_file()
    
else:
    
    VERSION = (0, 1, 12, 0)
    VERSION_STR = "dev"

COMPANY           = "Example Company Ltd."
EMAIL             = "tamas.jerzsabek@gmail.com"
URL               = "https://github.com/FLUGI69/FLUGI_desktop_app"
DESCRIPTION       = "Company management application built with Python and PyQt6, featuring database connectivity, web scraping, and PDF generation capabilities."
INTERNAL_NAME     = "ExampleApp"
LEGAL_COPYRIGHT   = f"Copyright © Example Company Ltd. 2025. All rights reserved."
ORIGINAL_FILENAME = "example_app.exe" if getattr(sys, "frozen", False) else "__main__.py"
PRODUCT_NAME      = "Example App - Company Management Application"

def get_version_info(as_str: bool = False) -> dict:
    
    version = ".".join(map(str, VERSION))

    info = {
        "version": version,
        "version_str": VERSION_STR,
        "company": COMPANY,
        "email": EMAIL,
        "url": URL,
        "description": DESCRIPTION,
        "internal_name": INTERNAL_NAME,
        "legal_copyright": LEGAL_COPYRIGHT,
        "original_filename": ORIGINAL_FILENAME,
        "product_name": PRODUCT_NAME,
    }

    if as_str:
        
        info["version_full"] = f"{version} ({VERSION_STR})"

    return info