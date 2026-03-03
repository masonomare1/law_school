from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, throttling
from rest_framework.parsers import JSONParser

from documents.embedding_utils import embed_texts
from documents.faiss_indexer import search_across_documents
from documents.serializers import DocumentChunkSerializer

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class QueryView(APIView):
    """
    API endpoint for legal query processing.
    POST /api/v1/query/
    """

    parser_classes = [JSONParser]
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [throttling.UserRateThrottle, throttling.AnonRateThrottle]

    def _call_llm(self, query: str, context: str) -> str:
        if not settings.OPENAI_API_KEY or OpenAI is None:
            # Fallback behaviour when LLM is not configured.
            return (
                "LLM backend is not configured. "
                "Please configure OPENAI_API_KEY to enable AI-powered answers.\n\n"
                f"Query: {query}\n\nContext:\n{context[:1000]}"
            )

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        system_prompt = (
            "You are a legal research assistant. Answer the user's question "
            "using ONLY the provided context from legal documents. "
            "If the context is insufficient, say you are unsure. "
            "Do not fabricate citations."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Question:\n{query}\n\nContext:\n{context}",
            },
        ]

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            temperature=0.1,
        )

        return response.choices[0].message.content.strip()

    def post(self, request):
        """
        Process a legal query and return answer with citations.

        Expected request body:
        {
            "query": "What is the penalty for..."
        }
        """
        query = request.data.get("query")

        if not query:
            return Response(
                {"error": "Query is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Step 1: Embed the query
        query_embedding = embed_texts([query])
        if query_embedding.shape[0] == 0:
            return Response(
                {"error": "Failed to generate embedding for query."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Step 2: Retrieve similar chunks from FAISS
        retrieved = search_across_documents(query_embedding[0], top_k=5)
        if not retrieved:
            return Response(
                {
                    "answer": "No relevant content found in the indexed documents for this query.",
                    "citations": [],
                    "confidence_score": 0.0,
                    "query": query,
                },
                status=status.HTTP_200_OK,
            )

        chunks, distances = zip(*retrieved)

        # Build context from top chunks
        context_parts = []
        for chunk in chunks:
            header = f"[{chunk.document.name} - page {chunk.page_number or 'N/A'} - section {chunk.section or 'N/A'}]"
            context_parts.append(f"{header}\n{chunk.chunk_text}")

        context = "\n\n---\n\n".join(context_parts)

        # Step 3: Call LLM to generate answer
        try:
            answer = self._call_llm(query, context)
        except Exception as exc:
            return Response(
                {
                    "error": f"Failed to generate answer from LLM: {str(exc)}",
                    "query": query,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Prepare citations payload
        serializer = DocumentChunkSerializer(chunks, many=True)
        citations = []
        for item in serializer.data:
            citations.append(
                {
                    "document_name": item.get("document_name"),
                    "document_id": item.get("document"),
                    "section": item.get("section"),
                    "page": item.get("page_number"),
                    "chunk_index": item.get("chunk_index"),
                }
            )

        # Simple confidence heuristic based on distances (smaller distance -> higher confidence)
        max_dist = max(distances) if distances else 0.0
        min_dist = min(distances) if distances else 0.0
        if max_dist == min_dist:
            confidence_score = 0.8
        else:
            # Normalize the best (smallest) distance into [0, 1] and invert.
            best = min_dist
            normalized = (best - min_dist) / (max_dist - min_dist + 1e-9)
            confidence_score = float(max(0.0, min(1.0, 1.0 - normalized)))

        return Response(
            {
                "answer": answer,
                "citations": citations,
                "confidence_score": confidence_score,
                "query": query,
            },
            status=status.HTTP_200_OK,
        )
