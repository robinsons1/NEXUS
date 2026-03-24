import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import os

load_dotenv()

def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(os.getenv("FIREBASE_CREDENTIALS"))
        firebase_admin.initialize_app(cred)
    return firestore.client()

def save_data(df, collection="sensor_data"):
    db = init_firebase()
    batch = db.batch()
    count = 0

    for _, row in df.iterrows():
        # Usamos created_at como ID único para evitar duplicados
        doc_id = row["created_at"].strftime("%Y%m%d%H%M%S")
        doc_ref = db.collection(collection).document(doc_id)
        batch.set(doc_ref, row.to_dict())
        count += 1

        # Firestore permite máximo 500 operaciones por batch
        if count % 500 == 0:
            batch.commit()
            batch = db.batch()
            print(f"{count} documentos guardados...")

    batch.commit()
    print(f"✅ Total guardado: {count} documentos")

if __name__ == "__main__":
    # Prueba rápida de conexión
    db = init_firebase()
    db.collection("test").document("ping").set({"status": "connected"})
    print("✅ Conexión con Firestore exitosa")
