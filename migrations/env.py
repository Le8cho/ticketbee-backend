# Al inicio del archivo, agrega:
from app.database import Base
from app.models import ticket, dispositivo, cliente, pago  # importa todos los modelos

# Reemplaza:
target_metadata = Base.metadata