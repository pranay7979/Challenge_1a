import json
import re
import os
from collections import Counter
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTFigure, LTRect, LTLine

def extract_text_and_properties_from_pdf(pdf_path):
    """
    Extracts text blocks with their properties (font size, bold, page number, position)
    from a PDF document.
    """
    text_blocks_with_properties = []
    
    for page_num, page_layout in enumerate(extract_pages(pdf_path)):
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                for text_line in element:
                    line_text = text_line.get_text().strip()
                    if not line_text:
                        continue

                    font_size = None
                    is_bold = False
                    if hasattr(text_line, '_objs') and text_line._objs:
                        for char in text_line._objs:
                            if isinstance(char, LTChar):
                                font_size = round(char.size, 2)
                                if "bold" in char.fontname.lower():
                                    is_bold = True
                                break  
                    
                    text_blocks_with_properties.append({
                        "text": line_text,
                        "page": page_num,
                        "x0": round(text_line.x0, 2),
                        "y0": round(text_line.y0, 2),
                        "x1": round(text_line.x1, 2),
                        "y1": round(text_line.y1, 2),
                        "font_size": font_size,
                        "bold": is_bold,
                        "line_height": round(text_line.height, 2)
                    })
    
    text_blocks_with_properties.sort(key=lambda x: (x['page'], -x['y0']))
    
    return text_blocks_with_properties

def get_document_title(text_blocks):
    """
    Extract the main title from the first page.
    """
    first_page_blocks = [b for b in text_blocks if b['page'] == 0]
    
    title_candidates = []
    for block in first_page_blocks:
        text = block['text'].strip()
        font_size = block.get('font_size', 0)
        
        if (font_size >= 8 and 
            len(text) >= 5 and  # At least 5 characters
            len(text.split()) >= 2):  # At least 2 words
            title_candidates.append(block)
    
    if not title_candidates:
        for block in first_page_blocks:
            text = block['text'].strip()
            if len(text) >= 5:
                return text
        return ""
    
    title_candidates.sort(key=lambda x: (x['font_size'] or 0, -x['y0']), reverse=True)
    
    return title_candidates[0]['text'].strip()

def is_form_document(text_blocks):
    """
    More balanced form detection - only for obvious application forms.
    """
    if not text_blocks:
        return True
    
    first_pages_text = " ".join([b['text'] for b in text_blocks if b['page'] <= 1]).lower()
    
    strong_form_indicators = [
        'application form for grant',  # Very specific
        'ltc advance',                 # Very specific
        'government servant',          # Very specific
        'signature of government servant',
        'particulars furnished above are true'
    ]
    
    strong_form_score = sum(1 for indicator in strong_form_indicators if indicator in first_pages_text)
    
    if strong_form_score >= 2:
        return True
    
    generic_form_indicators = [
        'application form', 'name of the applicant', 'date of birth',
        'father\'s name', 'mother\'s name', 'address'
    ]
    
    generic_form_score = sum(1 for indicator in generic_form_indicators if indicator in first_pages_text)
    
    if generic_form_score >= 4:
        return True
    
    return False

def is_real_heading(text, block):
    """
    Determine if text is a real heading using multiple criteria.
    """
    text = text.strip()
    
    if len(text) < 3:
        return False
    
    form_field_patterns = [
        r'^[A-Z][a-z]*\s*:?\s*$',     # Single word like "Name:"
        r'^\d+\.\s*$',                 # Just number like "1."
        r'^S\.No\.?\s*$',              # Serial number
        r'^Rs\.\s*$',                  # Currency
    ]
    
    for pattern in form_field_patterns:
        if re.match(pattern, text):
            return False
    
    if text.lower().replace(':', '').replace('.', '') in [
        'name', 'age', 'date', 'designation', 'service', 'single', 'amount'
    ]:
        return False
    
    strong_heading_patterns = [
        r'^\d+\.\s+[A-Z][a-z]+',        # "1. Introduction"
        r'^\d+\.\d+\s+[A-Z]',           # "1.1 Subsection"
        r'^Chapter\s+\d+',              # "Chapter 1" 
        r'^Section\s+\d+',              # "Section 1"
        r'^Appendix\s+[A-Z]',           # "Appendix A"
        r'^Table of Contents',          # TOC
        r'^Revision History',           # Common in docs
        r'^Acknowledgements',           # Common in docs
        r'^References',                 # Common in docs
        r'^Abstract',                   # Common in papers
        r'^Introduction',               # Common section
        r'^Conclusion',                 # Common section
        r'^Overview',                   # Common section
        r'^Summary',                    # Common section
        r'^Background',                 # Common section
    ]
    
    for pattern in strong_heading_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return True
    
    font_size = block.get('font_size', 0)
    is_bold = block.get('bold', False)
    
    if (len(text.split()) >= 2 and 
        (font_size > 12 or is_bold) and
        (text.istitle() or text.isupper())):
        return True
    
    return False

def detect_headings_universal(text_blocks, threshold=2):
    """
    Detect H1–H3 headings using formatting and semantic signals.
    Applies only the top 3 heading levels.
    """
    outline = []
    seen = set()

    for block in text_blocks:
        text = block.get("text", "").strip()
        if not text or len(text) < 3 or (text, block["page"]) in seen:
            continue

       
        clean_text = text.strip().replace('\u2013', '-').replace('\u2014', '-')

        
        if not is_real_heading(clean_text, block):
            continue

       
        score = 0
        font_size = block.get("font_size", 0)
        is_bold = block.get("bold", False)

        
        if font_size >= 16:
            score += 3
        elif font_size >= 13:
            score += 2
        elif font_size >= 11:
            score += 1

        
        if is_bold:
            score += 1.5

     
        semantic_patterns = [
            r'^\d+(\.\d+)*\s+',                        # 1., 2.1, 3.2.1
            r'^(Appendix|Phase|Section|Chapter)\b',    # Appendix A, Phase I
            r'^(Summary|Background|Timeline|Milestones|Conclusion|Evaluation|Approach|Overview|References|Training)\b',
            r'^\d+\.\s+[A-Z]',                         # "1. Something"
        ]
        if any(re.match(p, clean_text, re.IGNORECASE) for p in semantic_patterns):
            score += 1.5


        if score >= threshold:
            if score >= 5:
                level = "H1"
            elif score >= 4:
                level = "H2"
            else:
                level = "H3"

            seen.add((text, block["page"]))
            outline.append({
                "level": level,
                "text": text,
                "page": block["page"] + 1
            })

    return outline

def process_pdf_for_outline(pdf_path):
    """Main function to process a PDF and extract title and outline."""
    try:
        text_blocks = extract_text_and_properties_from_pdf(pdf_path)
        title = get_document_title(text_blocks)
        
       
        if is_form_document(text_blocks):
            outline = []
        else:
            outline = detect_headings_universal(text_blocks, threshold=3)
        
        return {"title": title.strip(), "outline": outline}
    
    except Exception as e:
        print(f"Error processing {pdf_path}: {str(e)}")
        return {"title": "", "outline": []}

def process_all_pdfs(input_dir="/app/input", output_dir="/app/output"):
    """Process all PDFs in the input directory."""
    if not os.path.exists(input_dir):
        print(f"Input directory {input_dir} does not exist!")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process")
    
    processed_count = 0
    for filename in pdf_files:
        pdf_path = os.path.join(input_dir, filename)
        output_filename = filename.rsplit('.', 1)[0] + '.json'
        output_path = os.path.join(output_dir, output_filename)
        
        print(f"Processing: {filename}")
        result = process_pdf_for_outline(pdf_path)
        
       
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        processed_count += 1
        print(f"✓ Processed {filename} - Title: '{result['title'][:50]}...', Headings: {len(result['outline'])}")
    
    print(f"\nSuccessfully processed {processed_count}/{len(pdf_files)} PDFs")
    print(f"Output files saved to: {output_dir}")

if __name__ == "__main__":
    input_directory = "/app/input"
    output_directory = "/app/output"
    
    # For local development, uncomment and modify these paths:
    #input_directory = "input"
    #output_directory = "output"
    
    process_all_pdfs(input_directory, output_directory)
