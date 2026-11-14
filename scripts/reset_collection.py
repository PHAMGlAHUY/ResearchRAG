from vectorstore.qdrant import get_qdrant_client, VECTOR_DB_COLLECTION

if __name__ == "__main__":
    if input(f"Xóa collection '{VECTOR_DB_COLLECTION}'? (yes/no): ").strip().lower() == "yes":
        get_qdrant_client().delete_collection(VECTOR_DB_COLLECTION)
        print("Đã xóa.")