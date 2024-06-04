from pydantic import BaseModel, PositiveInt
from fastapi import FastAPI
import tracemalloc
#from main import app

EXPECTED_FOOD1 = {
    "id": 1,
    "name": "egg",
    "serving_size": "piece",
    "kcal_per_serving": 78,
    "protein_grams": 6.2,
    "fibre_grams": 0,
}
EXPECTED_FOOD2 = {
    "id": 2,
    "name": "oatmeal",
    "serving_size": "100 grams",
    "kcal_per_serving": 336,
    "protein_grams": 13.2,
    "fibre_grams": 10.1,
}

class Food (BaseModel):
    id: int
    name: str
    serving_size: str
    kcal_per_serving: int
    protein_grams: float
    fibre_grams: float

app = FastAPI()
foods: dict[int, Food] = {}

@app.post("/")
async def create_food(food:Food):
    Food[food] = food
    return food

@app.get('/', response_model=list[Food])
async def get_root():
    return Food.values()

@app.get('/{item}', response_model=Food)
async def get_item(item:int):
    return Foods[item]

print(create_food(EXPECTED_FOOD1))
print(get_item(2))
print(get_item(1))
print(get_root())



external_data = {
    'id': 123,
    'name': 'banana',
    'serving_size': '1 banana',
    'kcal_per_serving' : 90,
    'protein_grams' : 1.3,
    'fibre_grams': 3.1,
}

food = Food(**external_data)

print(food.id)
#> 123
print(food.model_dump())
