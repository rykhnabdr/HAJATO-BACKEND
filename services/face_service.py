import cv2
import numpy as np
from insightface.app import FaceAnalysis


# =========================
# LOAD MODEL INSIGHTFACE
# =========================
face_app = FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"]
)

face_app.prepare(
    ctx_id=-1,
    det_size=(640, 640)
)


# =========================
# HELPER: BACA IMAGE DARI FILE FLASK
# =========================
def read_image_from_file(file_storage):
    file_bytes = file_storage.read()

    np_arr = np.frombuffer(file_bytes, np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError("Gambar tidak valid atau tidak bisa dibaca")

    return image


# =========================
# HELPER: PILIH WAJAH TERBESAR
# =========================
def get_largest_face(faces):
    if not faces:
        return None

    largest_face = max(
        faces,
        key=lambda face: (face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1])
    )

    return largest_face


# =========================
# GENERATE EMBEDDING DARI IMAGE FILE
# =========================
def generate_embedding_from_file(file_storage):
    image = read_image_from_file(file_storage)

    faces = face_app.get(image)

    if len(faces) == 0:
        raise ValueError("Wajah tidak terdeteksi")

    face = get_largest_face(faces)

    embedding = face.embedding.astype(np.float32)

    # Normalisasi embedding
    norm = np.linalg.norm(embedding)

    if norm == 0:
        raise ValueError("Embedding wajah tidak valid")

    embedding = embedding / norm

    return embedding.tolist()


# =========================
# COSINE SIMILARITY
# =========================
def cosine_similarity(embedding_1, embedding_2):
    emb1 = np.array(embedding_1, dtype=np.float32)
    emb2 = np.array(embedding_2, dtype=np.float32)

    norm1 = np.linalg.norm(emb1)
    norm2 = np.linalg.norm(emb2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    similarity = np.dot(emb1, emb2) / (norm1 * norm2)

    return float(similarity)