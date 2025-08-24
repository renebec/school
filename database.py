import os
from sqlalchemy import create_engine, text
from datetime import datetime
import pytz

db_connection_string = os.environ['DB_CONNECTION_STRING']

engine = create_engine(db_connection_string,
      connect_args={
            "ssl": { 
              "ca": "/etc/ssl/certs/ca-certificates.crt"
                   }
                  }
            )

def load_pg_from_db():
    try:
      with engine.connect() as conn:
          result = conn.execute(text("SELECT * FROM inocAgro"))
          pg = result.mappings().all()
          return pg
    except Exception as e:
      print(f"DB ERROR: {e}")
      return None

      #result_all = result.all()
      #tipo = type(result_all)
      #tipo_2 = type(result_all[0])
      #print(tipo)
      #print(tipo_2)
      #print(result_all)
    #otro comentario

def load_pgn_from_db(id):
  try:
    with engine.connect() as conn:
      result = conn.execute(
        text("SELECT * FROM inocAgro WHERE id = :val"),
        {"val":id}
      )
      row = result.mappings().first()  # <- dict, no tupla
      return dict(row) if row else None
  except Exception as e:
    print(f"DB ERROR: {e}")
    return None
      