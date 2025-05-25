"""Google Document AI processing script for various document types."""


from google.cloud import documentai_v1 as documentai
from google.oauth2 import service_account
from PIL import Image
import io, json, os
from dotenv import load_dotenv
# import fitz
# import argparse
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification #possible import for future use
import re
from google.cloud import documentai_v1 as documentai
from PyPDF2 import PdfReader, PdfWriter
import mimetypes
from io import BytesIO
from langchain_core.tools import tool 

load_dotenv(r"C:\Users\nehaj\OneDrive\Desktop\AI_agent\.env")
SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON")
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")   
PROCESSOR_ID = os.getenv("PROCESSOR_ID")
INVOICE_PROC = os.getenv("INVOICE_PROC") 
RECIEPT_PROC = os.getenv("RECIEPT_PROC")
FORM_PROC = os.getenv("FORM_PROC")
UTILITY_PROC = os.getenv("UTILITY_PROC")
UNKNOWN_PROC= os.getenv("UNKNOWN_PROC")


def get_docai_client():
    '''Initialize the Document AI client with service account credentials.'''

    SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON")   
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_JSON)
    return documentai.DocumentProcessorServiceClient(credentials=creds)

def get_text_from_layout(layout, document_text):
    '''Extract text from a layout object with text anchors.'''
    
    segments = layout.text_anchor.text_segments
    if not segments:
        return ""
    start_index = segments[0].start_index
    end_index = segments[0].end_index
    return document_text.text[start_index:end_index]

def extract_heading_from_page(page, document_text):
    '''Extract the heading from a page to identify type of document.'''

    if page.paragraphs:
        return get_text_from_layout(page.paragraphs[0].layout, document_text).strip()
    if page.blocks:
        return get_text_from_layout(page.blocks[0].layout, document_text).strip()
    return ""

def assign_processor_by_heading(heading):
    '''Assign a processor based on the heading of the document.'''

    heading_lower = heading.lower()
    if "invoice" in heading_lower:
        return INVOICE_PROC
    elif "receipt" in heading_lower:
        return RECIEPT_PROC
    elif "form" in heading_lower:
        return FORM_PROC
    elif "utility" in heading_lower:
        return UTILITY_PROC
    else:
        return UNKNOWN_PROC

def extract_pdf_page_bytes(pdf_path, page_number):
    '''Extract bytes of a page from a PDF file.'''

    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    writer.add_page(reader.pages[page_number - 1])
    output_stream = BytesIO()
    writer.write(output_stream)
    return output_stream.getvalue()

def process_page_with_processor(project_id, location, processor_id, page_bytes, mime_type="application/pdf"):
    '''Process a single page with the specified Document AI processor.'''

    client = get_docai_client()

    name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"

    document = {"content": page_bytes, "mime_type": mime_type}
    request = {
        "name": name,
        "raw_document": document,
    }
    response = client.process_document(request=request)
    return response.document

def extract_data(entities):
    '''Extract structured data from Document AI entities (only for INVOICE/FORM/CONTRACT processors).'''

    extracted = {}
    for entity in entities:
        key = getattr(entity, "type_", None)
        value = getattr(entity.normalized_value, "text", None) if hasattr(entity, "normalized_value") else None
        if not value:
            value = getattr(entity, "mention_text", None)
        confidence = getattr(entity, "confidence", 0)

        if confidence > 0.85:
            extracted[key] = value

    return extracted

def main(file_path, project_id, location, initial_processor_id, service_account_json):
    '''Main function to process a document file and save extracted data into json file.'''

    doc_name = str(os.path.basename(file_path)).replace("temp_", "")
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        raise ValueError("Could not determine MIME type")

    client = get_docai_client()
    name = f"projects/{project_id}/locations/{location}/processors/{initial_processor_id}"

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    if mime_type == "application/pdf":
        document = {"content": file_bytes, "mime_type": mime_type}
        request = {"name": name, "raw_document": document}
        result = client.process_document(request=request)
        doc = result.document

        with open(f"{file_path}_ocr.json", "w", encoding="utf-8") as f:
            full_doc = {}
            for page in doc.pages:
                heading = extract_heading_from_page(page, doc)
                processor_id = assign_processor_by_heading(heading)
                page_num = page.page_number
                print(f"Page {page_num} heading: '{heading}' -> Processor: {processor_id}")
                page_bytes = extract_pdf_page_bytes(file_path, page_num)
                processed_page_doc = process_page_with_processor(project_id, location, processor_id, page_bytes, mime_type)
                if processed_page_doc.entities:
                    fin_processed_page_doc = extract_data(processed_page_doc.entities)
                else:
                    fin_processed_page_doc = documentai.Document.to_dict(processed_page_doc)
                full_doc[page_num] = fin_processed_page_doc
    
            json.dump({doc_name: full_doc}, f, indent=2, ensure_ascii=False)
            

    elif mime_type.startswith("image/"):
        ocr_result = process_page_with_processor(project_id, location, initial_processor_id, file_bytes, mime_type)
        
        if ocr_result.pages:
            heading = extract_heading_from_page(ocr_result.pages[0], ocr_result)
        else:
            heading = ocr_result.text[:100]  
        processor_id = assign_processor_by_heading(heading)
        print(f"OCR heading: '{heading}' -> Processor: {processor_id}")

        if processor_id != initial_processor_id:
            processed_doc = process_page_with_processor(project_id, location, processor_id, file_bytes, mime_type)
        else:
            processed_doc = ocr_result  

        with open(f"{file_path}_ocr.json", "w", encoding="utf-8") as f:
            json.dump(documentai.Document.to_dict(processed_doc), f, indent=2, ensure_ascii=False)
        print(f"Processed image using processor: {processor_id}")

    elif mime_type == "text/plain":
        text = file_bytes.decode("utf-8")
        document = {"content": text.encode("utf-8"), "mime_type": mime_type}
        request = {"name": name, "raw_document": document}
        result = client.process_document(request=request)
        heading = text.strip().splitlines()[0]
        processor_id = assign_processor_by_heading(heading)
        print(f"Text heading: '{heading}' -> Processor: {processor_id}")
        with open(f"{file_path}_ocr.json", "w", encoding="utf-8") as f:
            json.dump(documentai.Document.to_dict(result.document), f, indent=2, ensure_ascii=False)
    else:
        raise ValueError(f"Unsupported file type: {mime_type}")
    return f"{file_path}_ocr.json"
    
@tool  
def doc_parse(files: list[str]) -> dict[str, any]:
    '''Parse documents using Google Document AI and return structured data.'''
    
    service_account_json = os.getenv("SERVICE_ACCOUNT_JSON")
    project_id = os.getenv("PROJECT_ID") 
    location = os.getenv("LOCATION")
    initial_processor_id = os.getenv("PROCESSOR_ID") 
    paths = []
    for file in files:
        paths.append(main(file, project_id, location, initial_processor_id, service_account_json))
    return paths


# if __name__ == "__main__":
#     from io import BytesIO
#     import sys

#     if len(sys.argv) != 2:
#         print("Usage: python process_by_page.py <path_to_pdf>")
#         exit(1)

#     file_path = sys.argv[1]
#     service_account_json = os.getenv("SERVICE_ACCOUNT_JSON")
#     project_id = os.getenv("PROJECT_ID") 
#     location = os.getenv("LOCATION")
#     initial_processor_id = os.getenv("PROCESSOR_ID")  

#     fin_files = main(file_path, project_id, location, initial_processor_id, service_account_json)
#     print(fin_files)

