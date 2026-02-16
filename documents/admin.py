from django.contrib import admin
from .models import Document, DocumentChunk


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'chunks_indexed', 'uploaded_at', 'processed_at']
    list_filter = ['status', 'uploaded_at']
    search_fields = ['name']
    readonly_fields = ['id', 'uploaded_at', 'processed_at']


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ['document', 'chunk_index', 'page_number', 'section']
    list_filter = ['document', 'page_number']
    search_fields = ['chunk_text', 'document__name']
    readonly_fields = ['id', 'created_at']
