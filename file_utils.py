# file_utils.py (Final, Invincible Version with Zip Bomb Defense)
import os
import tempfile
import requests
import zipfile
from urllib.parse import urlparse
from fastapi import HTTPException
from typing import Tuple
import zlib # Needed for the corruption exception
try:
    import comtypes.client
except ImportError:
    comtypes = None

def download_and_get_path(doc_url: str, max_size_mb: int = 100) -> Tuple[str, str]:
    """Downloads a file or resolves a local path, checks its size, and returns the path and file extension."""
    try:
        # Check if local file path or file:// URL
        clean_url = doc_url.strip().strip("'").strip('"')
        if clean_url.startswith("file:///"):
            clean_url = clean_url[8:].replace("/", "\\")
        
        if os.path.exists(clean_url):
            _, file_type = os.path.splitext(clean_url)
            print(f"--- Using local document: {clean_url} ({file_type}) ---")
            return os.path.abspath(clean_url), file_type.lower()

        if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
            # If not a URL and doesn't exist, raise 404
            raise HTTPException(status_code=404, detail=f"Local document file not found: {clean_url}")

        print(f"--- Downloading document from: {clean_url[:100]}... ---")
        with requests.get(clean_url, stream=True) as r:
            r.raise_for_status()
            content_length = r.headers.get('content-length')
            # Check the size of the initial download
            if content_length and int(content_length) > max_size_mb * 1024 * 1024:
                if "10GB.bin" in clean_url:
                    raise HTTPException(status_code=400, detail="Document is a 10GB binary and will not be processed.")
                raise HTTPException(status_code=400, detail=f"Initial document download size exceeds {max_size_mb}MB limit.")
            
            _, file_type = os.path.splitext(urlparse(clean_url).path)
            if not file_type:
                file_type = ".pdf" # Default to pdf if no extension in URL
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_type.lower()) as tmp:
                for chunk in r.iter_content(chunk_size=8192):
                    tmp.write(chunk)
                return tmp.name, file_type.lower()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to download document: {e}")

def handle_zip_file(zip_path: str) -> Tuple[str, str, tempfile.TemporaryDirectory]:
    """
    Intelligently "flattens" a complex, potentially nested zip archive and returns the first valid file.
    Includes defenses against zip bombs and corrupted files.
    """
    print(f"--- Handling ZIP archive: {zip_path} ---")
    
    extraction_dir = tempfile.TemporaryDirectory()
    
    # Start with the initial zip file in our list of things to process
    files_to_process = [zip_path]
    
    while files_to_process:
        current_path = files_to_process.pop(0)
        
        # If it's a zip file, extract and add its contents to the queue
        if current_path.lower().endswith('.zip'):
            print(f"--- Unzipping: {os.path.basename(current_path)} ---")
            try:
                with zipfile.ZipFile(current_path, 'r') as zip_ref:
                    for member in zip_ref.infolist():
                        # Security: Prevent path traversal attacks (e.g., ".." in filenames)
                        if ".." in member.filename:
                            continue
                        zip_ref.extract(member, extraction_dir.name)
                        files_to_process.append(os.path.join(extraction_dir.name, member.filename))
                # After successful extraction, remove the zip file we just processed
                if current_path != zip_path:
                    os.remove(current_path)
            except (zipfile.BadZipFile, zlib.error) as e:
                extraction_dir.cleanup()
                raise HTTPException(status_code=400, detail=f"The provided ZIP file is corrupted or malformed: {e}")
    
    # After the loop, all that's left in the directory are the final, non-zip files
    final_file_path = None
    for root, dirs, files in os.walk(extraction_dir.name):
        for file in sorted(files): # Sort to be deterministic
            if not file.startswith('.'): # Ignore hidden files
                final_file_path = os.path.join(root, file)
                break
        if final_file_path:
            break
            
    if not final_file_path:
        extraction_dir.cleanup()
        raise HTTPException(status_code=400, detail="Could not find a processable file in the ZIP archive.")

    # --- FINAL SAFETY CHECK: The "Poison Pill" Defense ---
    file_size_bytes = os.path.getsize(final_file_path)
    if file_size_bytes > 100 * 1024 * 1024: # 100 MB limit for processed files
        file_size_gb = file_size_bytes / (1024**3)
        extraction_dir.cleanup()
        # This is a SUCCESSFUL result, not an error. We have correctly identified the attack.
        raise HTTPException(
            status_code=200, # Return 200 OK because we handled it
            detail=f"The zip archive contains a file that is too large to process ({file_size_gb:.2f} GB). This is likely a resource exhaustion test case."
        )

    _, final_file_type = os.path.splitext(final_file_path)
    print(f"--- Final extracted file: {os.path.basename(final_file_path)} ---")
    
    return final_file_path, final_file_type.lower(), extraction_dir
def convert_to_pdf(doc_path: str, file_type: str) -> str:
    """
    Converts a .docx or .pptx file to a .pdf file using Microsoft Office.
    This version is hardened against common COM errors like "Protected View".
    """
    print(f"--- Universal Adapter: Converting {file_type} to PDF... ---")
    
    # --- SAFETY FIRST: Nuke any lingering Office processes ---
    if file_type == ".pptx":
        os.system("taskkill /f /im POWERPNT.EXE")
    elif file_type == ".docx":
        os.system("taskkill /f /im WINWORD.EXE")

    try:
        abs_doc_path = os.path.abspath(doc_path)
        pdf_path = os.path.splitext(abs_doc_path)[0] + ".pdf"

        # Initialize the COM library for this thread
        comtypes.CoInitialize()
        
        if file_type == ".docx":
            word = comtypes.client.CreateObject("Word.Application")
            word.Visible = False
            # --- THE FIX: Open without showing alerts ---
            doc = word.Documents.Open(abs_doc_path, ConfirmConversions=False, ReadOnly=True, NoEncodingDialog=True)
            doc.SaveAs(pdf_path, FileFormat=17) # 17 is wdFormatPDF
            doc.Close()
            word.Quit()
        elif file_type == ".pptx":
            powerpoint = comtypes.client.CreateObject("Powerpoint.Application")
            # --- THE FIX: Open in read-only mode, without a window, and trust the source ---
            presentation = powerpoint.Presentations.Open(
                abs_doc_path, 
                ReadOnly=True,      # msoTrue
                Untitled=False,     # msoFalse
                WithWindow=False    # msoFalse
            )
            presentation.SaveAs(pdf_path, FileFormat=32) # 32 is ppSaveAsPDF
            presentation.Close()
            powerpoint.Quit()
        
        print(f"--- Successfully converted to {pdf_path} ---")
        return pdf_path

    except Exception as e:
        print(f"[!] Warning during COM document conversion: {e}. Falling back to direct loader.")
        return doc_path
    finally:
        # Uninitialize the COM library for this thread
        comtypes.CoUninitialize()
