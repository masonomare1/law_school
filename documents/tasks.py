from celery import shared_task
from django.utils import timezone
from .models import Document, DocumentChunk
from .pdf_processor import PDFProcessor
from .faiss_indexer import build_index_for_document
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

        logger.info("Starting processing for document %s (%s)", document.name, document_id)

        file_path = document.file.path

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found at: {file_path}")

        processor = PDFProcessor()

        # Process PDF: extract, preprocess, and chunk text
        chunks_data = processor.process_pdf(file_path)

        if not chunks_data:
            raise ValueError("No text could be extracted from the PDF")

        # Remove existing chunks for idempotency in case of re-processing
        DocumentChunk.objects.filter(document=document).delete()

        chunks_created = 0
        for chunk_data in chunks_data:
            DocumentChunk.objects.create(
                document=document,
                chunk_text=chunk_data["text"],
                chunk_index=chunk_data["chunk_index"],
                page_number=chunk_data.get("page_number"),
                section=chunk_data.get("section"),
            )
            chunks_created += 1

        # Build / rebuild FAISS index for this document
        try:
            indexed = build_index_for_document(document)
            logger.info(
                "Built FAISS index for document %s (%s) with %s vectors",
                document.name,
                document_id,
                indexed,
            )
        except Exception as exc:
            logger.error("Failed to build FAISS index for document %s: %s", document_id, exc, exc_info=True)
            raise

        document.status = "completed"
        document.chunks_indexed = chunks_created
        document.processed_at = timezone.now()
        document.save()

        logger.info(
            "Completed processing for document %s. Created %s chunks.",
            document.name,
            chunks_created,
        )

        return {
            "document_id": str(document_id),
            "status": "completed",
            "chunks_indexed": chunks_created,
        }

    except Document.DoesNotExist:
        logger.error("Document not found: %s", document_id)
        raise
    except Exception as exc:
        logger.error("Error processing document %s: %s", document_id, exc, exc_info=True)

        try:
            document = Document.objects.get(id=document_id)
            document.status = "failed"
            document.error_message = str(exc)
            document.save()
        except Exception:
            # If we cannot update the document, swallow to avoid masking original error.
            pass

        raise self.retry(exc=exc, countdown=60)
