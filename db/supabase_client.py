"""
Cliente Supabase compartido. Singleton thread-safe para todo el backend.
Reemplaza el cliente inline que vivía en rag/buscar_contexto.py.
"""

import os
from supabase import create_client, Client

_client: Client | None = None


def get_client() -> Client:
    """Devuelve el cliente Supabase singleton. Se inicializa en el primer uso."""
    global _client
    if _client is None:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL y SUPABASE_KEY deben estar en .env")
        _client = create_client(url, key)
    return _client


def get_user_id() -> str:
    """UUID del usuario activo. Single-user ahora; listo para multi-user."""
    uid = os.environ.get("USER_ID", "")
    if not uid:
        raise RuntimeError("USER_ID debe estar en .env")
    return uid
