from app.repositories.base_repository import GameRepository

class GameRepositoryImpl(GameRepository):
    def __init__(self):
        # Aquí puedes inicializar la conexión a base de datos si es necesario
        pass

    async def get_by_id(self, game_id: str):
        # Lógica para obtener un juego por ID
        return {"id": game_id, "status": "dummy game"}

    async def get_all_active(self):
        # Lógica para obtener todos los juegos activos
        return []

    async def save(self, game):
        # Lógica para guardar un juego
        print(f"Juego guardado: {game}")
        return game

    async def delete(self, game_id: str):
        # Lógica para eliminar un juego
        print(f"Juego eliminado: {game_id}")