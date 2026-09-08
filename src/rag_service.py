import os

# ============================================================
# ENVIRONMENT SAFETY
# ============================================================
# Hindari parallel tokenizer / worker yang tidak diperlukan
# untuk chatbot single-process.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import copy
import glob
import json
import yaml
import numpy as np

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# ============================================================
# SENTENCE TRANSFORMERS
# ============================================================
# Import SentenceTransformer sebelum FAISS.
from sentence_transformers import SentenceTransformer

# ============================================================
# FAISS
# ============================================================
import faiss


# ============================================================
# PATH
# ============================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


# ============================================================
# DOCUMENT
# ============================================================

@dataclass
class Document:
    page_content: str
    metadata: Dict[str, Any]


# ============================================================
# RAG SERVICE
# ============================================================

class RAGService:

    def __init__(
        self,
        index_dir: str = "faiss_index",
        model_name: str = "intfloat/multilingual-e5-small",
        device: str = "cpu",
    ):
        """
        RAG Service menggunakan:

        - SentenceTransformer multilingual-e5-small
        - FAISS IndexFlatIP
        - cosine similarity melalui normalized embeddings
        - CPU sebagai default

        Catatan:
        FAISS index TIDAK dibuat pada __init__.
        Index baru dibuat saat build_index() atau load_index().
        """

        # ----------------------------------------------------
        # Resolve index directory
        # ----------------------------------------------------

        if os.path.isabs(index_dir):
            self.index_dir = index_dir
        else:
            self.index_dir = os.path.join(
                PROJECT_ROOT,
                index_dir
            )

        self.index_dir = os.path.abspath(
            self.index_dir
        )

        # ----------------------------------------------------
        # Configuration
        # ----------------------------------------------------

        self.model_name = model_name
        self.device = device

        # ----------------------------------------------------
        # Create directory
        # ----------------------------------------------------

        os.makedirs(
            self.index_dir,
            exist_ok=True
        )

        # ----------------------------------------------------
        # FAISS initially empty
        # ----------------------------------------------------
        # Penting:
        # Jangan membuat IndexFlatIP di sini.
        # Ini mengurangi kemungkinan konflik native library
        # saat SentenceTransformer melakukan encode().
        self.index = None

        # ----------------------------------------------------
        # Documents
        # ----------------------------------------------------

        self.documents: List[Document] = []

        # ----------------------------------------------------
        # Load embedding model
        # ----------------------------------------------------

        print(
            "\n[RAG] Loading embedding model:"
        )

        print(
            f"      Model : {self.model_name}"
        )

        print(
            f"      Device: {self.device}"
        )

        self.encoder = SentenceTransformer(
            self.model_name,
            device=self.device,
        )

        # ----------------------------------------------------
        # Embedding dimension
        # ----------------------------------------------------

        self.dimension = (
            self.encoder.get_sentence_embedding_dimension()
        )

        if not self.dimension:
            raise RuntimeError(
                "Dimensi embedding tidak dapat ditemukan."
            )

        self.dimension = int(
            self.dimension
        )

        print(
            f"[RAG] Embedding dimension: "
            f"{self.dimension}"
        )

        print(
            "[RAG] Embedding device aktif: "
            f"{self.device}"
        )

    # ========================================================
    # CREATE FAISS INDEX
    # ========================================================

    def _create_empty_index(self):
        """
        Membuat FAISS IndexFlatIP.

        Dipanggil hanya ketika index memang diperlukan.
        """

        self.index = faiss.IndexFlatIP(
            self.dimension
        )

        return self.index

    # ========================================================
    # MARKDOWN PARSER
    # ========================================================

    def _parse_markdown_file(
        self,
        filepath: str,
    ) -> Document:
        """
        Membaca file Markdown.

        Mendukung YAML frontmatter:

        ---
        category: company
        type: profile
        ---

        Isi dokumen...
        """

        with open(
            filepath,
            "r",
            encoding="utf-8",
        ) as f:
            content = f.read()

        content = content.strip()

        metadata: Dict[str, Any] = {}
        page_content = content

        # ----------------------------------------------------
        # YAML frontmatter
        # ----------------------------------------------------

        if content.startswith("---"):

            parts = content.split(
                "---",
                2,
            )

            if len(parts) >= 3:

                try:

                    parsed_metadata = yaml.safe_load(
                        parts[1]
                    )

                    if isinstance(
                        parsed_metadata,
                        dict,
                    ):
                        metadata = parsed_metadata

                except yaml.YAMLError as exc:

                    print(
                        f"[RAG] Warning: YAML error "
                        f"di {filepath}: {exc}"
                    )

                page_content = parts[2].strip()

        # ----------------------------------------------------
        # Metadata tambahan
        # ----------------------------------------------------

        absolute_path = os.path.abspath(
            filepath
        )

        relative_path = os.path.relpath(
            absolute_path,
            PROJECT_ROOT,
        )

        metadata["source"] = os.path.basename(
            filepath
        )

        metadata["source_path"] = relative_path

        # ----------------------------------------------------
        # Empty document
        # ----------------------------------------------------

        if not page_content.strip():

            print(
                f"[RAG] Warning: Dokumen kosong: "
                f"{filepath}"
            )

        return Document(
            page_content=page_content,
            metadata=metadata,
        )

    # ========================================================
    # LOAD KNOWLEDGE BASE
    # ========================================================

    def load_knowledge_base(
        self,
        kb_dir: str = "knowledge_base",
    ) -> List[Document]:
        """
        Load semua file Markdown dari Knowledge Base.
        """

        # ----------------------------------------------------
        # Resolve KB path
        # ----------------------------------------------------

        if os.path.isabs(kb_dir):
            kb_path = kb_dir
        else:
            kb_path = os.path.join(
                PROJECT_ROOT,
                kb_dir,
            )

        kb_path = os.path.abspath(
            kb_path
        )

        print(
            "\n[RAG] Loading Knowledge Base:"
        )

        print(
            f"      {kb_path}"
        )

        # ----------------------------------------------------
        # Validate directory
        # ----------------------------------------------------

        if not os.path.exists(
            kb_path
        ):
            raise FileNotFoundError(
                "Knowledge Base tidak ditemukan:\n"
                f"{kb_path}"
            )

        if not os.path.isdir(
            kb_path
        ):
            raise NotADirectoryError(
                "Path Knowledge Base bukan directory:\n"
                f"{kb_path}"
            )

        # ----------------------------------------------------
        # Find Markdown
        # ----------------------------------------------------

        search_pattern = os.path.join(
            kb_path,
            "**",
            "*.md",
        )

        filepaths = sorted(
            glob.glob(
                search_pattern,
                recursive=True,
            )
        )

        print(
            f"[RAG] Ditemukan "
            f"{len(filepaths)} file Markdown."
        )

        if not filepaths:

            print(
                "[RAG] Warning: Tidak ada file Markdown "
                "di Knowledge Base."
            )

            return []

        # ----------------------------------------------------
        # Parse documents
        # ----------------------------------------------------

        documents: List[Document] = []

        for filepath in filepaths:

            try:

                doc = self._parse_markdown_file(
                    filepath
                )

                if doc.page_content.strip():

                    documents.append(
                        doc
                    )

                    relative_path = os.path.relpath(
                        filepath,
                        PROJECT_ROOT,
                    )

                    print(
                        f"[RAG] Loaded: "
                        f"{relative_path}"
                    )

            except Exception as exc:

                print(
                    f"[RAG] Gagal membaca "
                    f"{filepath}: {exc}"
                )

        print(
            f"[RAG] Total dokumen: "
            f"{len(documents)}"
        )

        return documents

    # ========================================================
    # CHUNK DOCUMENTS
    # ========================================================

    def chunk_documents(
        self,
        documents: List[Document],
        chunk_size: int = 1200,
        overlap: int = 150,
    ) -> List[Document]:
        """
        Memecah dokumen menjadi beberapa chunk.

        Strategi:
        1. Dokumen pendek -> satu chunk.
        2. Pecah berdasarkan paragraph.
        3. Paragraph terlalu besar -> pecah berdasarkan karakter.
        4. Gunakan overlap antar chunk.
        """

        if chunk_size <= 0:
            raise ValueError(
                "chunk_size harus lebih besar dari 0."
            )

        if overlap < 0:
            raise ValueError(
                "overlap tidak boleh negatif."
            )

        if overlap >= chunk_size:
            raise ValueError(
                "overlap harus lebih kecil "
                "dari chunk_size."
            )

        chunked_docs: List[Document] = []

        for doc in documents:

            text = doc.page_content.strip()

            if not text:
                continue

            # ------------------------------------------------
            # Short document
            # ------------------------------------------------

            if len(text) <= chunk_size:

                metadata = copy.deepcopy(
                    doc.metadata
                )

                metadata["chunk_id"] = 0

                chunked_docs.append(
                    Document(
                        page_content=text,
                        metadata=metadata,
                    )
                )

                continue

            # ------------------------------------------------
            # Paragraph split
            # ------------------------------------------------

            paragraphs = [
                p.strip()
                for p in text.split("\n\n")
                if p.strip()
            ]

            current_chunk = ""
            chunk_id = 0

            for paragraph in paragraphs:

                # ------------------------------------------------
                # Large paragraph
                # ------------------------------------------------

                if len(paragraph) > chunk_size:

                    # Save current chunk
                    if current_chunk:

                        metadata = copy.deepcopy(
                            doc.metadata
                        )

                        metadata["chunk_id"] = chunk_id

                        chunked_docs.append(
                            Document(
                                page_content=current_chunk,
                                metadata=metadata,
                            )
                        )

                        chunk_id += 1
                        current_chunk = ""

                    # ------------------------------------------------
                    # Character split
                    # ------------------------------------------------

                    start = 0

                    while start < len(paragraph):

                        end = min(
                            start + chunk_size,
                            len(paragraph),
                        )

                        piece = paragraph[
                            start:end
                        ].strip()

                        if piece:

                            metadata = copy.deepcopy(
                                doc.metadata
                            )

                            metadata["chunk_id"] = chunk_id

                            chunked_docs.append(
                                Document(
                                    page_content=piece,
                                    metadata=metadata,
                                )
                            )

                            chunk_id += 1

                        if end >= len(paragraph):
                            break

                        start = max(
                            end - overlap,
                            start + 1,
                        )

                    continue

                # ------------------------------------------------
                # Normal paragraph
                # ------------------------------------------------

                if not current_chunk:

                    current_chunk = paragraph

                elif (
                    len(current_chunk)
                    + len(paragraph)
                    + 2
                    <= chunk_size
                ):

                    current_chunk += (
                        "\n\n"
                        + paragraph
                    )

                else:

                    # Save current chunk
                    metadata = copy.deepcopy(
                        doc.metadata
                    )

                    metadata["chunk_id"] = chunk_id

                    chunked_docs.append(
                        Document(
                            page_content=current_chunk,
                            metadata=metadata,
                        )
                    )

                    chunk_id += 1

                    # ------------------------------------------------
                    # Overlap
                    # ------------------------------------------------

                    if overlap > 0:

                        overlap_text = (
                            current_chunk[-overlap:]
                        )

                        space_index = (
                            overlap_text.find(" ")
                        )

                        if (
                            space_index != -1
                            and space_index
                            < len(overlap_text) - 1
                        ):

                            overlap_text = (
                                overlap_text[
                                    space_index + 1:
                                ]
                            )

                    else:

                        overlap_text = ""

                    # ------------------------------------------------
                    # New chunk
                    # ------------------------------------------------

                    if overlap_text:

                        current_chunk = (
                            overlap_text
                            + "\n\n"
                            + paragraph
                        )

                    else:

                        current_chunk = paragraph

            # ------------------------------------------------
            # Final chunk
            # ------------------------------------------------

            if current_chunk:

                metadata = copy.deepcopy(
                    doc.metadata
                )

                metadata["chunk_id"] = chunk_id

                chunked_docs.append(
                    Document(
                        page_content=current_chunk,
                        metadata=metadata,
                    )
                )

        print(
            f"[RAG] Total chunks: "
            f"{len(chunked_docs)}"
        )

        return chunked_docs

    # ========================================================
    # BUILD INDEX
    # ========================================================

    def build_index(
        self,
        documents: List[Document],
        batch_size: int = 16,
    ):
        """
        Membuat FAISS index dari documents.
        """

        if batch_size <= 0:
            raise ValueError(
                "batch_size harus lebih besar dari 0."
            )

        # ----------------------------------------------------
        # Create fresh index
        # ----------------------------------------------------

        self._create_empty_index()

        self.documents = []

        # ----------------------------------------------------
        # Validate documents
        # ----------------------------------------------------

        if not documents:

            print(
                "[RAG] Warning: Tidak ada "
                "dokumen untuk di-index."
            )

            return

        # ----------------------------------------------------
        # Remove empty documents
        # ----------------------------------------------------

        valid_documents = [
            doc
            for doc in documents
            if doc.page_content
            and doc.page_content.strip()
        ]

        if not valid_documents:

            print(
                "[RAG] Warning: Semua dokumen kosong."
            )

            return

        self.documents = valid_documents

        total_documents = len(
            valid_documents
        )

        print(
            "\n[RAG] Membuat embedding:"
        )

        print(
            f"      Total chunks : {total_documents}"
        )

        print(
            f"      Batch size   : {batch_size}"
        )

        print(
            f"      Device       : {self.device}"
        )

        print(
            f"      Dimension    : {self.dimension}"
        )

        # ----------------------------------------------------
        # E5 passage
        # ----------------------------------------------------

        texts_to_embed = [
            f"passage: {doc.page_content}"
            for doc in valid_documents
        ]

        all_embeddings = []

        # ----------------------------------------------------
        # Batch embedding
        # ----------------------------------------------------

        for start in range(
            0,
            total_documents,
            batch_size,
        ):

            end = min(
                start + batch_size,
                total_documents,
            )

            batch = texts_to_embed[
                start:end
            ]

            print(
                f"[RAG] Embedding "
                f"{start + 1}-{end} "
                f"/ {total_documents}"
            )

            embeddings = self.encoder.encode(
                batch,
                batch_size=batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
                convert_to_numpy=True,
                num_workers=0,
            )

            embeddings = np.asarray(
                embeddings,
                dtype=np.float32,
            )

            if embeddings.ndim != 2:

                raise ValueError(
                    "Embedding batch memiliki shape "
                    f"tidak valid: {embeddings.shape}"
                )

            if embeddings.shape[1] != self.dimension:

                raise ValueError(
                    "Dimension embedding tidak sesuai.\n"
                    f"Expected: {self.dimension}\n"
                    f"Got     : {embeddings.shape[1]}"
                )

            all_embeddings.append(
                embeddings
            )

            del embeddings

        # ----------------------------------------------------
        # Combine
        # ----------------------------------------------------

        if not all_embeddings:

            raise RuntimeError(
                "Tidak ada embedding yang berhasil dibuat."
            )

        embeddings = np.vstack(
            all_embeddings
        ).astype(
            np.float32,
            copy=False,
        )

        del all_embeddings

        # ----------------------------------------------------
        # Validate
        # ----------------------------------------------------

        if embeddings.shape[0] != len(
            self.documents
        ):

            raise RuntimeError(
                "Jumlah embedding tidak sama "
                "dengan jumlah documents.\n"
                f"Embeddings: {embeddings.shape[0]}\n"
                f"Documents : {len(self.documents)}"
            )

        # ----------------------------------------------------
        # Normalize
        # ----------------------------------------------------

        faiss.normalize_L2(
            embeddings
        )

        # ----------------------------------------------------
        # Add
        # ----------------------------------------------------

        self.index.add(
            embeddings
        )

        # ----------------------------------------------------
        # Release
        # ----------------------------------------------------

        del embeddings
        del texts_to_embed

        # ----------------------------------------------------
        # Validate index
        # ----------------------------------------------------

        print(
            "\n[RAG] Berhasil membuat index FAISS:"
        )

        print(
            f"      Vectors   : {self.index.ntotal}"
        )

        print(
            f"      Documents : {len(self.documents)}"
        )

        if self.index.ntotal != len(
            self.documents
        ):

            raise RuntimeError(
                "Jumlah vector FAISS tidak sama "
                "dengan jumlah documents."
            )

    # ========================================================
    # REBUILD INDEX
    # ========================================================

    def rebuild_index(
        self,
        kb_dir: str = "knowledge_base",
        chunk_size: int = 1200,
        overlap: int = 150,
        batch_size: int = 16,
    ):
        """
        Load KB -> chunk -> embedding -> FAISS -> save.
        """

        print(
            "\n"
            "=================================================="
        )

        print(
            "[RAG] REBUILD KNOWLEDGE BASE"
        )

        print(
            "=================================================="
        )

        print(
            f"[RAG] KB directory : {kb_dir}"
        )

        print(
            f"[RAG] Chunk size   : {chunk_size}"
        )

        print(
            f"[RAG] Overlap      : {overlap}"
        )

        print(
            f"[RAG] Batch size   : {batch_size}"
        )

        print(
            f"[RAG] Device       : {self.device}"
        )

        # ----------------------------------------------------
        # Load
        # ----------------------------------------------------

        documents = self.load_knowledge_base(
            kb_dir
        )

        # ----------------------------------------------------
        # Chunk
        # ----------------------------------------------------

        chunks = self.chunk_documents(
            documents,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        # ----------------------------------------------------
        # Build
        # ----------------------------------------------------

        self.build_index(
            chunks,
            batch_size=batch_size,
        )

        # ----------------------------------------------------
        # Save
        # ----------------------------------------------------

        self.save_index()

        print(
            "[RAG] Rebuild selesai."
        )

        print(
            "==================================================\n"
        )

    # ========================================================
    # SAVE INDEX
    # ========================================================

    def save_index(self):
        """
        Menyimpan:

        faiss_index/
        ├── index.faiss
        └── metadata.json
        """

        if self.index is None:

            raise RuntimeError(
                "FAISS index belum dibuat."
            )

        if self.index.ntotal != len(
            self.documents
        ):

            raise RuntimeError(
                "Tidak dapat menyimpan index.\n"
                "Jumlah vector FAISS dan documents "
                "tidak sama.\n"
                f"FAISS vectors: {self.index.ntotal}\n"
                f"Documents    : {len(self.documents)}"
            )

        # ----------------------------------------------------
        # Paths
        # ----------------------------------------------------

        index_path = os.path.join(
            self.index_dir,
            "index.faiss",
        )

        metadata_path = os.path.join(
            self.index_dir,
            "metadata.json",
        )

        # ----------------------------------------------------
        # Write FAISS
        # ----------------------------------------------------

        faiss.write_index(
            self.index,
            index_path,
        )

        # ----------------------------------------------------
        # Prepare metadata
        # ----------------------------------------------------

        docs_dict = [
            {
                "page_content": doc.page_content,
                "metadata": doc.metadata,
            }
            for doc in self.documents
        ]

        # ----------------------------------------------------
        # Write metadata
        # ----------------------------------------------------

        with open(
            metadata_path,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                docs_dict,
                f,
                ensure_ascii=False,
                indent=2,
            )

        # ----------------------------------------------------
        # Validate
        # ----------------------------------------------------

        if not os.path.exists(
            index_path
        ):
            raise RuntimeError(
                "FAISS index gagal disimpan."
            )

        if not os.path.exists(
            metadata_path
        ):
            raise RuntimeError(
                "Metadata gagal disimpan."
            )

        print(
            "\n[RAG] Index berhasil disimpan:"
        )

        print(
            f"      {index_path}"
        )

        print(
            f"      {metadata_path}"
        )

    # ========================================================
    # LOAD INDEX
    # ========================================================

    def load_index(self):
        """
        Memuat FAISS index dan metadata.

        Penting:
        FAISS index baru dibaca setelah encoder selesai
        dibuat di __init__.
        """

        index_path = os.path.join(
            self.index_dir,
            "index.faiss",
        )

        metadata_path = os.path.join(
            self.index_dir,
            "metadata.json",
        )

        # ----------------------------------------------------
        # Validate files
        # ----------------------------------------------------

        if not os.path.exists(
            index_path
        ):

            raise FileNotFoundError(
                "FAISS index tidak ditemukan:\n"
                f"{index_path}\n"
                "Silakan jalankan rebuild_index()."
            )

        if not os.path.exists(
            metadata_path
        ):

            raise FileNotFoundError(
                "Metadata tidak ditemukan:\n"
                f"{metadata_path}\n"
                "Silakan jalankan rebuild_index()."
            )

        # ----------------------------------------------------
        # Load FAISS
        # ----------------------------------------------------

        print(
            f"[RAG] Loading FAISS index: "
            f"{index_path}"
        )

        loaded_index = faiss.read_index(
            index_path
        )

        # ----------------------------------------------------
        # Validate dimension
        # ----------------------------------------------------

        if loaded_index.d != self.dimension:

            raise ValueError(
                "Dimension FAISS tidak cocok.\n"
                f"Index : {loaded_index.d}\n"
                f"Model : {self.dimension}"
            )

        # ----------------------------------------------------
        # Load metadata
        # ----------------------------------------------------

        print(
            f"[RAG] Loading metadata: "
            f"{metadata_path}"
        )

        with open(
            metadata_path,
            "r",
            encoding="utf-8",
        ) as f:

            docs_dict = json.load(f)

        if not isinstance(
            docs_dict,
            list,
        ):

            raise ValueError(
                "Format metadata.json tidak valid. "
                "Expected list."
            )

        # ----------------------------------------------------
        # Convert metadata
        # ----------------------------------------------------

        documents: List[Document] = []

        for item in docs_dict:

            if not isinstance(
                item,
                dict,
            ):
                continue

            page_content = item.get(
                "page_content",
                "",
            )

            metadata = item.get(
                "metadata",
                {},
            )

            if not isinstance(
                metadata,
                dict,
            ):
                metadata = {}

            if not isinstance(
                page_content,
                str,
            ):
                continue

            if not page_content.strip():
                continue

            documents.append(
                Document(
                    page_content=page_content,
                    metadata=metadata,
                )
            )

        # ----------------------------------------------------
        # Validate count BEFORE assignment
        # ----------------------------------------------------

        if loaded_index.ntotal != len(
            documents
        ):

            raise ValueError(
                "FAISS index dan metadata "
                "tidak sinkron.\n"
                f"FAISS vectors: {loaded_index.ntotal}\n"
                f"Documents    : {len(documents)}\n"
                "Silakan rebuild index."
            )

        # ----------------------------------------------------
        # Assign only after validation
        # ----------------------------------------------------

        self.index = loaded_index
        self.documents = documents

        # ----------------------------------------------------
        # Success
        # ----------------------------------------------------

        print(
            "\n[RAG] Berhasil memuat index:"
        )

        print(
            f"      FAISS vectors: "
            f"{self.index.ntotal}"
        )

        print(
            f"      Documents    : "
            f"{len(self.documents)}"
        )

    # ========================================================
    # METADATA FILTER
    # ========================================================

    def _matches_filters(
        self,
        metadata: Dict[str, Any],
        filters: Dict[str, Any],
    ) -> bool:
        """
        Mengecek metadata terhadap filter.
        """

        for key, value in filters.items():

            if key not in metadata:
                return False

            metadata_value = metadata[key]

            # ------------------------------------------------
            # list vs list
            # ------------------------------------------------

            if (
                isinstance(value, list)
                and isinstance(metadata_value, list)
            ):

                if not set(value).intersection(
                    set(metadata_value)
                ):
                    return False

            # ------------------------------------------------
            # filter list vs scalar
            # ------------------------------------------------

            elif isinstance(value, list):

                if metadata_value not in value:
                    return False

            # ------------------------------------------------
            # scalar vs list
            # ------------------------------------------------

            elif isinstance(metadata_value, list):

                if value not in metadata_value:
                    return False

            # ------------------------------------------------
            # scalar vs scalar
            # ------------------------------------------------

            elif metadata_value != value:

                return False

        return True

    # ========================================================
    # SEARCH
    # ========================================================

    def search(
        self,
        query: str,
        top_k: int = 5,
        metadata_filters: Optional[
            Dict[str, Any]
        ] = None,
    ) -> List[Document]:
        """
        Semantic search menggunakan FAISS.

        E5:

            query: ...
            passage: ...

        Karena embedding dinormalisasi,
        IndexFlatIP menghasilkan cosine similarity.
        """

        # ----------------------------------------------------
        # Validate query
        # ----------------------------------------------------

        if not isinstance(
            query,
            str,
        ):

            return []

        query = query.strip()

        if not query:
            return []

        # ----------------------------------------------------
        # Validate top_k
        # ----------------------------------------------------

        if top_k <= 0:
            return []

        # ----------------------------------------------------
        # Validate index
        # ----------------------------------------------------

        if self.index is None:

            raise RuntimeError(
                "FAISS index belum dimuat. "
                "Jalankan load_index() terlebih dahulu."
            )

        if self.index.ntotal <= 0:

            print(
                "[RAG] Warning: FAISS index kosong."
            )

            return []

        if not self.documents:

            print(
                "[RAG] Warning: documents kosong."
            )

            return []

        if self.index.ntotal != len(
            self.documents
        ):

            raise RuntimeError(
                "FAISS index dan documents "
                "tidak sinkron."
            )

        # ----------------------------------------------------
        # E5 query
        # ----------------------------------------------------

        query_text = (
            f"query: {query}"
        )

        # ----------------------------------------------------
        # Encode
        # ----------------------------------------------------

        query_embedding = self.encoder.encode(
            [query_text],
            batch_size=1,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
            num_workers=0,
        )

        # ----------------------------------------------------
        # Convert NumPy
        # ----------------------------------------------------

        query_embedding = np.asarray(
            query_embedding,
            dtype=np.float32,
        )

        # ----------------------------------------------------
        # Validate
        # ----------------------------------------------------

        if query_embedding.ndim != 2:

            raise ValueError(
                "Query embedding memiliki shape "
                f"tidak valid: "
                f"{query_embedding.shape}"
            )

        if query_embedding.shape != (
            1,
            self.dimension,
        ):

            raise ValueError(
                "Shape query embedding tidak sesuai.\n"
                f"Expected: (1, {self.dimension})\n"
                f"Got     : {query_embedding.shape}"
            )

        # ----------------------------------------------------
        # Normalize
        # ----------------------------------------------------

        faiss.normalize_L2(
            query_embedding
        )

        # ----------------------------------------------------
        # Search candidate
        # ----------------------------------------------------

        if metadata_filters:

            search_k = min(
                max(top_k * 20, 20),
                self.index.ntotal,
            )

        else:

            search_k = min(
                max(top_k, 1),
                self.index.ntotal,
            )

        # ----------------------------------------------------
        # FAISS search
        # ----------------------------------------------------

        distances, indices = self.index.search(
            query_embedding,
            search_k,
        )

        # ----------------------------------------------------
        # Build results
        # ----------------------------------------------------

        results: List[Document] = []

        for rank in range(
            len(indices[0])
        ):

            idx = int(
                indices[0][rank]
            )

            if idx < 0:
                continue

            if idx >= len(
                self.documents
            ):
                continue

            doc = self.documents[idx]

            # ------------------------------------------------
            # Metadata filter
            # ------------------------------------------------

            if (
                metadata_filters
                and not self._matches_filters(
                    doc.metadata,
                    metadata_filters,
                )
            ):
                continue

            score = float(
                distances[0][rank]
            )

            # ------------------------------------------------
            # Copy metadata only
            # ------------------------------------------------

            metadata = dict(
                doc.metadata
            )

            metadata["relevance_score"] = round(
                score,
                4,
            )

            metadata["retrieval_rank"] = (
                len(results) + 1
            )

            # ------------------------------------------------
            # Create result document
            # ------------------------------------------------

            result_doc = Document(
                page_content=doc.page_content,
                metadata=metadata,
            )

            results.append(
                result_doc
            )

            if len(results) >= top_k:
                break

        # ----------------------------------------------------
        # Logging
        # ----------------------------------------------------

        print(
            f"\n[RAG] Query: {query}"
        )

        if not results:

            print(
                "[RAG] Tidak ada hasil retrieval."
            )

        else:

            for i, doc in enumerate(
                results,
                start=1,
            ):

                source = doc.metadata.get(
                    "source",
                    "Unknown",
                )

                score = float(
                    doc.metadata.get(
                        "relevance_score",
                        0.0,
                    )
                )

                preview = (
                    doc.page_content
                    .replace("\n", " ")
                    .strip()
                )

                if len(preview) > 180:

                    preview = (
                        preview[:180]
                        + "..."
                    )

                print(
                    f"[RAG] #{i} "
                    f"score={score:.4f} "
                    f"source={source}"
                )

                print(
                    f"      {preview}"
                )

        print()

        # ----------------------------------------------------
        # Explicit cleanup of temporary NumPy arrays
        # ----------------------------------------------------

        del query_embedding
        del distances
        del indices

        return results

    # ========================================================
    # CONSTRUCT CONTEXT
    # ========================================================

    def construct_context(
        self,
        retrieved_docs: List[Document],
        max_chars: int = 6000,
        min_score: float = 0.0,
    ) -> str:
        """
        Mengubah hasil retrieval menjadi context untuk LLM.
        """

        if not retrieved_docs:
            return ""

        if max_chars <= 0:
            return ""

        context_parts: List[str] = []

        total_chars = 0

        for doc in retrieved_docs:

            score = float(
                doc.metadata.get(
                    "relevance_score",
                    0.0,
                )
            )

            # ------------------------------------------------
            # Minimum score
            # ------------------------------------------------

            if score < min_score:
                continue

            source = doc.metadata.get(
                "source",
                "Unknown source",
            )

            source_path = doc.metadata.get(
                "source_path",
                "",
            )

            content = (
                doc.page_content
                .strip()
            )

            if not content:
                continue

            # ------------------------------------------------
            # Context entry
            # ------------------------------------------------

            entry = (
                f"[SOURCE: {source}]\n"
                f"[SCORE: {score:.4f}]\n"
            )

            if source_path:

                entry += (
                    f"[PATH: {source_path}]\n"
                )

            entry += (
                f"{content}\n"
            )

            # ------------------------------------------------
            # Max chars
            # ------------------------------------------------

            if (
                total_chars
                + len(entry)
                > max_chars
            ):

                if not context_parts:

                    remaining = (
                        max_chars
                        - total_chars
                    )

                    if remaining > 100:

                        context_parts.append(
                            entry[:remaining]
                        )

                break

            context_parts.append(
                entry
            )

            total_chars += len(
                entry
            )

        return "\n".join(
            context_parts
        )

    # ========================================================
    # DEBUG SEARCH
    # ========================================================

    def debug_search(
        self,
        query: str,
        top_k: int = 5,
    ):
        """
        Testing retrieval RAG secara manual.
        """

        print(
            "\n"
            "=================================================="
        )

        print(
            "[RAG DEBUG]"
        )

        print(
            f"Query: {query}"
        )

        print(
            "=================================================="
        )

        # ----------------------------------------------------
        # Search
        # ----------------------------------------------------

        results = self.search(
            query,
            top_k=top_k,
        )

        # ----------------------------------------------------
        # Context
        # ----------------------------------------------------

        context = self.construct_context(
            results,
            max_chars=6000,
            min_score=0.0,
        )

        print(
            "[RAG DEBUG] CONTEXT:"
        )

        if context:

            print(
                context
            )

        else:

            print(
                "(CONTEXT KOSONG)"
            )

        print(
            "==================================================\n"
        )

        return results, context


# ============================================================
# OPTIONAL DIRECT TEST
# ============================================================

if __name__ == "__main__":

    print(
        "\n"
        "=================================================="
    )

    print(
        "RAG SERVICE TEST"
    )

    print(
        "=================================================="
    )

    rag = RAGService(
        device="cpu"
    )

    # --------------------------------------------------------
    # Rebuild
    # --------------------------------------------------------

    rag.rebuild_index(
        kb_dir="knowledge_base",
        chunk_size=1200,
        overlap=150,
        batch_size=16,
    )

    # --------------------------------------------------------
    # Test queries
    # --------------------------------------------------------

    test_queries = [
        "Apa itu KOL?",
        "Apa itu Kerajaan Agency?",
        "Bagaimana cara daftar menjadi KOL?",
    ]

    # --------------------------------------------------------
    # Debug
    # --------------------------------------------------------

    for query in test_queries:

        rag.debug_search(
            query,
            top_k=5,
        )