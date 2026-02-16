from rest_framework import serializers
from .models import Document, DocumentChunk


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            'id',
            'name',
            'file',
            'file_size',
            'uploaded_at',
            'processed_at',
            'status',
            'chunks_indexed',
            'error_message',
        ]
        read_only_fields = [
            'id',
            'file_size',
            'uploaded_at',
            'processed_at',
            'status',
            'chunks_indexed',
            'error_message',
        ]


class DocumentChunkSerializer(serializers.ModelSerializer):
    document_name = serializers.CharField(source='document.name', read_only=True)
    
    class Meta:
        model = DocumentChunk
        fields = [
            'id',
            'document',
            'document_name',
            'chunk_text',
            'chunk_index',
            'page_number',
            'section',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']
