from abc import ABC, abstractmethod
from typing import Optional, List, Any # Any será reemplazado por GameAggregate
import uuid

# Para evitar importación circular en tiempo de ejecución, usamos un forward reference
# como string o el bloque TYPE_CHECKING
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.domain.game import GameAggregate


class GameRepository(ABC):
    """
    Interfaz abstracta para el repositorio de partidas de Parqués.
    Define los métodos que cualquier implementación de repositorio debe tener.
    """

    @abstractmethod
    async def get_by_id(self, game_id: uuid.UUID) -> Optional[GameAggregate]:
        """
        Obtiene una partida por su ID.
        Retorna la partida o None si no se encuentra.
        """
        pass

    @abstractmethod
    async def save(self, game: GameAggregate) -> None:
        """
        Guarda (crea o actualiza) una partida en el repositorio.
        """
        pass

    @abstractmethod
    async def delete(self, game_id: uuid.UUID) -> bool:
        """
        Elimina una partida del repositorio.
        Retorna True si se eliminó, False si no se encontró.
        """
        pass

    @abstractmethod
    async def get_all_active(self) -> List[GameAggregate]:
        """
        Obtiene todas las partidas activas o en espera.
        (Podría ser útil para un lobby o para limpieza).
        """
        pass