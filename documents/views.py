from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
from .models import Document
from .serializers import DocumentSerializer
from .tasks import process_document_task


class DocumentUploadView(APIView):
    """
    API endpoint for document upload.
    POST /api/v1/documents/upload/
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        """
        Upload a PDF document for processing.
        
        Expected request:
        - file: PDF file
        """
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        uploaded_file = request.FILES['file']
        
        # Validate file type
        if not uploaded_file.name.endswith('.pdf'):
            return Response(
                {'error': 'Only PDF files are allowed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size
        if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
            return Response(
                {'error': f'File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE} bytes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create document record
        document = Document.objects.create(
            name=uploaded_file.name,
            file=uploaded_file,
            file_size=uploaded_file.size,
            status='pending'
        )
        
        # Trigger background processing task
        process_document_task.delay(str(document.id))
        
        serializer = DocumentSerializer(document)
        return Response({
            'status': 'success',
            'document_id': str(document.id),
            'chunks_indexed': 0,  # Will be updated after processing
            'document': serializer.data
        }, status=status.HTTP_201_CREATED)


class DocumentListView(APIView):
    """
    API endpoint to list all documents.
    GET /api/v1/documents/
    """
    
    def get(self, request):
        documents = Document.objects.all()
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DocumentDetailView(APIView):
    """
    API endpoint to get document details.
    GET /api/v1/documents/<document_id>/
    """
    
    def get(self, request, document_id):
        try:
            document = Document.objects.get(id=document_id)
            serializer = DocumentSerializer(document)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Document.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )
