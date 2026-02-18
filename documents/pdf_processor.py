"""
PDF text extraction and preprocessing utilities for legal documents.
"""

import re
import logging
from typing import List, Tuple, Optional
from io import BytesIO

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text
    from pdfminer.layout import LAParams
    from pdfminer.pdfpage import PDFPage
    from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
    from pdfminer.converter import TextConverter
except ImportError:
    pdfminer_extract_text = None

logger = logging.getLogger('law_school')


class PDFProcessor:
    """
    Handles PDF text extraction and preprocessing for legal documents.
    """
    
    def __init__(self):
        self.min_chunk_length = 50  # Minimum characters per chunk
        self.max_chunk_length = 2000  # Maximum characters per chunk
    
    def extract_text_from_pdf(self, file_path: str) -> List[Tuple[str, int]]:
        """
        Extract text from PDF file with page numbers.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of tuples containing (text, page_number)
            
        Raises:
            ValueError: If PDF extraction fails
        """
        pages_text = []
        
        # Try PyPDF2 first (faster, good for simple PDFs)
        if PyPDF2:
            try:
                pages_text = self._extract_with_pypdf2(file_path)
                if pages_text:
                    logger.info(f"Successfully extracted text using PyPDF2 from {file_path}")
                    return pages_text
            except Exception as e:
                logger.warning(f"PyPDF2 extraction failed: {str(e)}, trying pdfminer...")
        
        # Fallback to pdfminer (more robust, handles complex PDFs better)
        if pdfminer_extract_text:
            try:
                pages_text = self._extract_with_pdfminer(file_path)
                if pages_text:
                    logger.info(f"Successfully extracted text using pdfminer from {file_path}")
                    return pages_text
            except Exception as e:
                logger.error(f"pdfminer extraction failed: {str(e)}")
                raise ValueError(f"Failed to extract text from PDF: {str(e)}")
        
        raise ValueError("No PDF extraction library available. Please install PyPDF2 or pdfminer.six")
    
    def _extract_with_pypdf2(self, file_path: str) -> List[Tuple[str, int]]:
        """
        Extract text using PyPDF2 library.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of tuples containing (text, page_number)
        """
        pages_text = []
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            
            for page_num in range(num_pages):
                try:
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    if text.strip():
                        pages_text.append((text, page_num + 1))
                except Exception as e:
                    logger.warning(f"Error extracting page {page_num + 1}: {str(e)}")
                    continue
        
        return pages_text
    
    def _extract_with_pdfminer(self, file_path: str) -> List[Tuple[str, int]]:
        """
        Extract text using pdfminer library (more robust for complex PDFs).
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of tuples containing (text, page_number)
        """
        pages_text = []
        
        with open(file_path, 'rb') as file:
            # Get PDF pages
            pages = list(PDFPage.get_pages(file))
            
            for page_num, page in enumerate(pages, start=1):
                try:
                    # Create resource manager and text converter
                    resource_manager = PDFResourceManager()
                    output_string = BytesIO()
                    
                    # Configure layout parameters for better text extraction
                    laparams = LAParams(
                        line_margin=0.5,
                        word_margin=0.1,
                        char_margin=2.0,
                        boxes_flow=0.5,
                        all_texts=False
                    )
                    
                    converter = TextConverter(
                        resource_manager,
                        output_string,
                        laparams=laparams
                    )
                    
                    # Extract text from page
                    interpreter = PDFPageInterpreter(resource_manager, converter)
                    interpreter.process_page(page)
                    
                    text = output_string.getvalue().decode('utf-8')
                    converter.close()
                    output_string.close()
                    
                    if text.strip():
                        pages_text.append((text, page_num))
                        
                except Exception as e:
                    logger.warning(f"Error extracting page {page_num} with pdfminer: {str(e)}")
                    continue
        
        return pages_text
    
    def preprocess_text(self, text: str) -> str:
        """
        Clean and preprocess extracted text.
        
        Args:
            text: Raw text from PDF
            
        Returns:
            Cleaned and preprocessed text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep legal symbols
        # Keep: periods, commas, colons, semicolons, parentheses, brackets, quotes, dashes
        text = re.sub(r'[^\w\s\.\,\:\;\(\)\[\]\{\}\'\"\-\—\–]', ' ', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Fix common OCR/text extraction issues
        text = self._fix_common_issues(text)
        
        return text
    
    def _fix_common_issues(self, text: str) -> str:
        """
        Fix common text extraction issues.
        
        Args:
            text: Text to fix
            
        Returns:
            Fixed text
        """
        # Fix broken words (common in PDF extraction)
        text = re.sub(r'(\w+)\s+(\w+)', lambda m: m.group(1) + ' ' + m.group(2) if len(m.group(1)) > 1 and len(m.group(2)) > 1 else m.group(0), text)
        
        # Fix hyphenated words split across lines
        text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', text)
        
        # Normalize multiple spaces
        text = re.sub(r' {2,}', ' ', text)
        
        # Fix common legal document formatting
        # Preserve section numbers (e.g., "Section 1.2.3")
        text = re.sub(r'Section\s+(\d+(?:\.\d+)*)', r'Section \1', text)
        
        # Preserve paragraph numbers (e.g., "(a)", "(1)", "(i)")
        text = re.sub(r'\(([a-z0-9]+)\)', r'(\1)', text)
        
        return text
    
    def extract_sections(self, text: str, page_number: int) -> Optional[str]:
        """
        Extract section identifiers from legal text.
        
        Args:
            text: Text to analyze
            page_number: Page number for context
            
        Returns:
            Section identifier if found, None otherwise
        """
        # Common legal section patterns
        section_patterns = [
            r'Section\s+(\d+(?:\.\d+)*)',
            r'§\s*(\d+(?:\.\d+)*)',
            r'Article\s+(\d+(?:\.\d+)*)',
            r'Chapter\s+(\d+(?:\.\d+)*)',
            r'Part\s+(\d+(?:\.\d+)*)',
        ]
        
        for pattern in section_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def chunk_text(self, text: str, page_number: int, section: Optional[str] = None) -> List[dict]:
        """
        Split text into chunks suitable for embedding.
        
        Args:
            text: Text to chunk
            page_number: Page number
            section: Optional section identifier
            
        Returns:
            List of chunk dictionaries with text, page_number, and section
        """
        if not text or len(text.strip()) < self.min_chunk_length:
            return []
        
        chunks = []
        
        # Split by sentences first (better for legal documents)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current_chunk = ""
        chunk_index = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # If adding this sentence would exceed max length, save current chunk
            if current_chunk and len(current_chunk) + len(sentence) + 1 > self.max_chunk_length:
                if len(current_chunk.strip()) >= self.min_chunk_length:
                    chunks.append({
                        'text': current_chunk.strip(),
                        'page_number': page_number,
                        'section': section,
                        'chunk_index': chunk_index
                    })
                    chunk_index += 1
                current_chunk = sentence
            else:
                # Add sentence to current chunk
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
            
            # If a single sentence exceeds max length, split it
            if len(current_chunk) > self.max_chunk_length:
                # Split by words
                words = current_chunk.split()
                temp_chunk = ""
                
                for word in words:
                    if temp_chunk and len(temp_chunk) + len(word) + 1 > self.max_chunk_length:
                        if len(temp_chunk.strip()) >= self.min_chunk_length:
                            chunks.append({
                                'text': temp_chunk.strip(),
                                'page_number': page_number,
                                'section': section,
                                'chunk_index': chunk_index
                            })
                            chunk_index += 1
                        temp_chunk = word
                    else:
                        temp_chunk += " " + word if temp_chunk else word
                
                current_chunk = temp_chunk
        
        # Add remaining chunk
        if current_chunk and len(current_chunk.strip()) >= self.min_chunk_length:
            chunks.append({
                'text': current_chunk.strip(),
                'page_number': page_number,
                'section': section,
                'chunk_index': chunk_index
            })
        
        return chunks
    
    def process_pdf(self, file_path: str) -> List[dict]:
        """
        Complete PDF processing pipeline: extract, preprocess, and chunk.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of chunk dictionaries ready for embedding
        """
        logger.info(f"Starting PDF processing for: {file_path}")
        
        # Extract text with page numbers
        pages_text = self.extract_text_from_pdf(file_path)
        
        if not pages_text:
            logger.warning(f"No text extracted from PDF: {file_path}")
            return []
        
        all_chunks = []
        global_chunk_index = 0
        
        # Process each page
        for page_text, page_number in pages_text:
            # Preprocess text
            cleaned_text = self.preprocess_text(page_text)
            
            if not cleaned_text or len(cleaned_text.strip()) < self.min_chunk_length:
                continue
            
            # Extract section identifier
            section = self.extract_sections(cleaned_text, page_number)
            
            # Chunk the text
            page_chunks = self.chunk_text(cleaned_text, page_number, section)
            
            # Update global chunk indices
            for chunk in page_chunks:
                chunk['chunk_index'] = global_chunk_index
                global_chunk_index += 1
            
            all_chunks.extend(page_chunks)
        
        logger.info(f"Processed PDF: {len(pages_text)} pages, {len(all_chunks)} chunks created")
        
        return all_chunks
