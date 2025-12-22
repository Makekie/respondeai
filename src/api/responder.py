from FastAPI import APIRouter

router = APIRouter(prefix="/responder")

@router.get("/", tags=["Responder"])
def listar_perguntas():
    return {"message": "Aqui estão todas respostas"}