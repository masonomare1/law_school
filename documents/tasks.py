from celery import shared_task
from django.conf import settings
from django.utils import timezone
from .models import Document
import logging

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
        
        # TODO: Implement document processing logic
        # 1. Extract text from PDF
        # 2. Chunk the text
        # 3. Generate embeddings
        # 4. Store in FAISS index
        # 5. Save chunks to database
        
        # Placeholder implementation
        document.status = 'completed'
        document.chunks_indexed = 0  # Will be updated with actual count
        document.processed_at = timezone.now()
        document.save()
        
        logger.info(f"Completed processing for document: {document.name}")
        
        return {
            'document_id': str(document_id),
            'status': 'completed',
            'chunks_indexed': document.chunks_indexed
        }
        
    except Document.DoesNotExist:
        logger.error(f"Document not found: {document_id}")
        raise
    except Exception as exc:
        logger.error(f"Error processing document {document_id}: {str(exc)}")
        
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
