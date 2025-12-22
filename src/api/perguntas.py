from FastAPI import APIRouter

router = APIRouter(prefix="/perguntas")

@router.get("/", tags=["Perguntas"])
def listar_perguntas():
    return {"message": "Aqui estão todas perguntas"}