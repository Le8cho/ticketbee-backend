# Al inicio del archivo, agrega:
from app.database import Base
from app.models import dispositivo, cliente, pago, ticket_model  # importa todos los modelos

# Reemplaza:
target_metadata = Base.metadata