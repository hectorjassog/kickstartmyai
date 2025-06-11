"""Embedding service for generating text embeddings."""

import logging
from typing import Any, Dict, List, Optional
import numpy as np
from uuid import uuid4

from app.ai.providers.factory import get_ai_provider

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and managing text embeddings."""
    
    def __init__(self, provider: str = "openai", model: str = "text-embedding-ada-002"):
        """
        Initialize the embedding service.
        
        Args:
            provider: AI provider to use for embeddings
            model: Embedding model to use
        """
        self.provider = provider
        self.model = model
        self._ai_provider = None
        self.cache: Dict[str, List[float]] = {}  # Simple in-memory cache
    
    async def get_ai_provider(self):
        """Get the AI provider instance."""
        if self._ai_provider is None:
            self._ai_provider = get_ai_provider(self.provider, model=self.model)
        return self._ai_provider
    
    async def generate_embedding(
        self,
        text: str,
        use_cache: bool = True
    ) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            use_cache: Whether to use caching
            
        Returns:
            Embedding vector
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Check cache first
        cache_key = f"{self.provider}:{self.model}:{hash(text)}"
        if use_cache and cache_key in self.cache:
            logger.debug(f"Using cached embedding for text: {text[:50]}...")
            return self.cache[cache_key]
        
        try:
            provider = await self.get_ai_provider()
            
            # Generate embedding
            embedding = await provider.create_embedding(
                text=text,
                model=self.model
            )
            
            # Cache the result
            if use_cache:
                self.cache[cache_key] = embedding
            
            logger.debug(f"Generated embedding for text: {text[:50]}... (dimension: {len(embedding)})")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding for text: {text[:50]}... Error: {e}")
            raise
    
    async def generate_embeddings(
        self,
        texts: List[str],
        use_cache: bool = True,
        batch_size: int = 100
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            use_cache: Whether to use caching
            batch_size: Number of texts to process in each batch
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        embeddings = []
        
        # Process in batches to avoid API limits
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = []
            
            for text in batch:
                try:
                    embedding = await self.generate_embedding(text, use_cache=use_cache)
                    batch_embeddings.append(embedding)
                except Exception as e:
                    logger.error(f"Failed to generate embedding for text in batch: {text[:50]}... Error: {e}")
                    # Use zero vector as fallback
                    batch_embeddings.append([0.0] * 1536)  # Default dimension for ada-002
            
            embeddings.extend(batch_embeddings)
            
            logger.info(f"Generated {len(batch_embeddings)} embeddings (batch {i//batch_size + 1})")
        
        return embeddings
    
    async def calculate_similarity(
        self,
        text1: str,
        text2: str,
        similarity_metric: str = "cosine"
    ) -> float:
        """
        Calculate similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            similarity_metric: Similarity metric to use ("cosine", "euclidean", "dot")
            
        Returns:
            Similarity score
        """
        # Generate embeddings
        embedding1 = await self.generate_embedding(text1)
        embedding2 = await self.generate_embedding(text2)
        
        return self._calculate_vector_similarity(embedding1, embedding2, similarity_metric)
    
    def _calculate_vector_similarity(
        self,
        vec1: List[float],
        vec2: List[float],
        metric: str = "cosine"
    ) -> float:
        """
        Calculate similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            metric: Similarity metric
            
        Returns:
            Similarity score
        """
        if len(vec1) != len(vec2):
            raise ValueError("Vectors must have the same dimension")
        
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        if metric == "cosine":
            # Cosine similarity
            dot_product = np.dot(v1, v2)
            norm_v1 = np.linalg.norm(v1)
            norm_v2 = np.linalg.norm(v2)
            
            if norm_v1 == 0 or norm_v2 == 0:
                return 0.0
            
            return float(dot_product / (norm_v1 * norm_v2))
            
        elif metric == "euclidean":
            # Euclidean distance (inverted and normalized)
            distance = np.linalg.norm(v1 - v2)
            # Convert to similarity (higher is better)
            return float(1 / (1 + distance))
            
        elif metric == "dot":
            # Dot product
            return float(np.dot(v1, v2))
            
        else:
            raise ValueError(f"Unknown similarity metric: {metric}")
    
    async def find_most_similar(
        self,
        query_text: str,
        candidate_texts: List[str],
        top_k: int = 5,
        similarity_metric: str = "cosine"
    ) -> List[Dict[str, Any]]:
        """
        Find most similar texts to a query.
        
        Args:
            query_text: Query text
            candidate_texts: List of candidate texts
            top_k: Number of top results to return
            similarity_metric: Similarity metric to use
            
        Returns:
            List of similarity results with text and scores
        """
        if not candidate_texts:
            return []
        
        # Generate query embedding
        query_embedding = await self.generate_embedding(query_text)
        
        # Generate candidate embeddings
        candidate_embeddings = await self.generate_embeddings(candidate_texts)
        
        # Calculate similarities
        similarities = []
        for i, (text, embedding) in enumerate(zip(candidate_texts, candidate_embeddings)):
            similarity = self._calculate_vector_similarity(
                query_embedding, embedding, similarity_metric
            )
            similarities.append({
                "text": text,
                "similarity": similarity,
                "index": i
            })
        
        # Sort by similarity and return top_k
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        return similarities[:top_k]
    
    async def cluster_texts(
        self,
        texts: List[str],
        num_clusters: int = 5,
        clustering_method: str = "kmeans"
    ) -> Dict[str, Any]:
        """
        Cluster texts based on their embeddings.
        
        Args:
            texts: List of texts to cluster
            num_clusters: Number of clusters
            clustering_method: Clustering method to use
            
        Returns:
            Clustering results
        """
        if len(texts) < num_clusters:
            logger.warning(f"Number of texts ({len(texts)}) is less than number of clusters ({num_clusters})")
            num_clusters = len(texts)
        
        # Generate embeddings
        embeddings = await self.generate_embeddings(texts)
        
        try:
            from sklearn.cluster import KMeans
            from sklearn.cluster import DBSCAN
            
            embeddings_array = np.array(embeddings)
            
            if clustering_method == "kmeans":
                clusterer = KMeans(n_clusters=num_clusters, random_state=42)
                cluster_labels = clusterer.fit_predict(embeddings_array)
                
            elif clustering_method == "dbscan":
                clusterer = DBSCAN(eps=0.5, min_samples=2)
                cluster_labels = clusterer.fit_predict(embeddings_array)
                num_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
                
            else:
                raise ValueError(f"Unknown clustering method: {clustering_method}")
            
            # Organize results
            clusters = {}
            for i, (text, label) in enumerate(zip(texts, cluster_labels)):
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append({
                    "text": text,
                    "index": i,
                    "embedding": embeddings[i]
                })
            
            return {
                "method": clustering_method,
                "num_clusters": num_clusters,
                "clusters": clusters,
                "labels": cluster_labels.tolist()
            }
            
        except ImportError:
            logger.error("scikit-learn not available for clustering")
            # Simple fallback clustering based on similarity
            return self._simple_clustering(texts, embeddings, num_clusters)
    
    def _simple_clustering(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        num_clusters: int
    ) -> Dict[str, Any]:
        """Simple clustering fallback when scikit-learn is not available."""
        # Very basic clustering by dividing texts into equal groups
        cluster_size = len(texts) // num_clusters
        clusters = {}
        
        for i in range(num_clusters):
            start_idx = i * cluster_size
            end_idx = start_idx + cluster_size if i < num_clusters - 1 else len(texts)
            
            clusters[i] = []
            for j in range(start_idx, end_idx):
                clusters[i].append({
                    "text": texts[j],
                    "index": j,
                    "embedding": embeddings[j]
                })
        
        return {
            "method": "simple",
            "num_clusters": len(clusters),
            "clusters": clusters,
            "labels": [i // cluster_size for i in range(len(texts))]
        }
    
    def clear_cache(self):
        """Clear the embedding cache."""
        self.cache.clear()
        logger.info("Embedding cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cache_size": len(self.cache),
            "provider": self.provider,
            "model": self.model
        }


# Global instance
embedding_service = EmbeddingService() 