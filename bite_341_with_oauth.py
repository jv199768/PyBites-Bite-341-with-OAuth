from datetime import datetime, timedelta, timezone
from typing import Annotated
import tracemalloc
import jwt
from fastapi import Depends, FastAPI, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from pydantic import BaseModel, PositiveInt

HTML_TEMPLATE = """<!doctype html>

<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Food log for {username}</title>
</head>

<body>
    <table>
        <thead>
            <th>Food</th>
            <th>Added</th>
            <th>Servings</th>
            <th>Calories (kcal)</th>
        </thead>
        <tbody>
            {table_rows}
        </tbody>
    </table>

</body>
</html>"""
TABLE_ROW = """<tr>
    <td>{food_name}</td>
    <td>{date_added}</td>
    <td>{number_servings} x {serving_size}</td>
    <td>{total_calories}</td>
</tr>"""

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

external_data = {
    'id': 123,
    'name': 'banana',
    'serving_size': '1 banana',
    'kcal_per_serving' : 90,
    'protein_grams' : 1.3,
    'fibre_grams': 3.1,
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

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "disabled": False,
    }
}


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    hashed_password: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)


def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@app.post("/")
async def create_food(food:Food):
    foods[food.id] = food
    return food
print(create_food(EXPECTED_FOOD1))

@app.get('/', response_model=list[Food])
async def get_root():
    return foods.values()
print(get_root())


@app.get('/{item}')
async def get_item(item:int):
    return(foods[item])
print(get_item(2))
print(get_item(1))

#Create the update and delete endpoints here

@app.put('/{food_id}')
async def update_food(food_id:int, food:Food):
    if food_id not in foods:
        raise HTTPException(status_code=404, detail='Food not found')
    foods[food_id] = food
    return food

@app.delete('/{food_id}')
async def delete_food(food_id:int):
    if food_id not in foods:
        raise HTTPException(status_code=404, detail='Food not found')
    del foods[food_id]
    return {'OK': True}


@app.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@app.get("/users/me/", response_model=User)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return current_user


@app.get("/users/me/items/")
async def read_own_items(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return [{"item_id": "Foo", "owner": current_user.username}]


@app.get("/{username}", response_class=HTMLResponse)
async def show_foods_for_user(request: Request, username: str):
    # 1. extract foods for user using the food_log dict
    # 2. build up the embedded html string
    # 3. return an HTMLResponse (with the html content and status code 200)
    table_rows = '\n'.join([
        TABLE_ROW.format(food_name=row.food.name,
                         date_added=row.date_added,
                         number_servings=row.number_servings,
                         serving_size=row.food.serving_size,
                         total_calories=row.total_calories)
        for row in food_log.items() if row.user.username == username
    ])
    html = HTML_TEMPLATE.format(username=username, table_rows=table_rows)
    return HTMLResponse(status_code=200, content=html)


food = Food(**external_data)

print(food.id)
#> 123
print(food.model_dump())
