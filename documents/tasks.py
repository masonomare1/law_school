from celery import shared_task
from django.conf import settings
from django.utils import timezone
from .models import Document, DocumentChunk
from .pdf_processor import PDFProcessor
import logging
import os

logger = logging.getLogger('law_school')


@shared_task(bind=True, max_retries=3)
def process_document_task(self, document_id):
    """
    Background task to process uploaded document.
    This will extract text, chunk it, generate embeddings, and store in FAISS.
    """
    try:
        document = Document.objects.get(id=document_id)
        document.status = 'processing'
        document.save()
        
        logger.info(f"Starting processing for document: {document.name} (ID: {document_id})")
        
        # Get the file path
        file_path = document.file.path
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found at: {file_path}")
        
        # Initialize PDF processor
        processor = PDFProcessor()
        
        # Process PDF: extract, preprocess, and chunk text
        chunks_data = processor.process_pdf(file_path)
        
        if not chunks_data:
            raise ValueError("No text could be extracted from the PDF")
        
        # Save chunks to database
        chunks_created = 0
        for chunk_data in chunks_data:
            DocumentChunk.objects.create(
                document=document,
                chunk_text=chunk_data['text'],
                chunk_index=chunk_data['chunk_index'],
                page_number=chunk_data.get('page_number'),
                section=chunk_data.get('section')
            )
            chunks_created += 1
        
        # Update document status
        document.status = 'completed'
        document.chunks_indexed = chunks_created
        document.processed_at = timezone.now()
        document.save()
        
        logger.info(
            f"Completed processing for document: {document.name}. "
            f"Created {chunks_created} chunks."
        )
        
        return {
            'document_id': str(document_id),
            'status': 'completed',
            'chunks_indexed': chunks_created
        }
        
    except Document.DoesNotExist:
        logger.error(f"Document not found: {document_id}")
        raise
    except Exception as exc:
        logger.error(f"Error processing document {document_id}: {str(exc)}", exc_info=True)
        
        # Update document status to failed
        try:
            document = Document.objects.get(id=document_id)
            document.status = 'failed'
            document.error_message = str(exc)
            document.save()
        except:
            pass
        
        # Retry the task
        raise self.retry(exc=exc, countdown=60)
