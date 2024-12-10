from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi.staticfiles import StaticFiles
from passlib.context import CryptContext
from jose import jwt
from pydantic import BaseModel
from app.models import News, User
from app.database import get_db
from dependencies import get_current_user, require_admin
from fastapi.security import OAuth2PasswordRequestForm
import requests
import asyncio
import httpx
from collections import deque
import feedparser
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.database import engine
from datetime import datetime

SECRET_KEY = "1337" 
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()

RSS_LINK = 'https://rssexport.rbc.ru/rbcnews/news/20/full.rss'
async_session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)


async def rss_parser(db_session: AsyncSession):
    """Фоновый парсер RSS-лент."""
    posted_q = deque(maxlen=20)
    n_test_chars = 90

    async with httpx.AsyncClient() as client:
        while True:
            try:
                response = await client.get(RSS_LINK)
                feed = feedparser.parse(response.text)

                for entry in reversed(feed.entries):
                    summary = entry.get('summary', '')
                    title = entry.get('title', '')
                    published_at = entry.get('published', None)
                    category = entry.get('category', 'Без категории')

                    if published_at:
                        try:
                            published_at = datetime.strptime(
                                published_at, "%a, %d %b %Y %H:%M:%S %z"
                            ).astimezone(None).replace(tzinfo=None)
                        except ValueError:
                            print(f"Ошибка преобразования даты: {published_at}")
                            published_at = None

                    news_text = f'{title}\n{summary}'
                    head = news_text[:n_test_chars].strip()

                    if head in posted_q:
                        continue

                    existing_news = await db_session.execute(
                        select(News).filter(News.title == title)
                    )
                    if existing_news.scalar_one_or_none():
                        continue

                    new_news = News(
                        title=title,
                        content=summary,
                        category=category,
                        published_at=published_at,
                    )
                    db_session.add(new_news)
                    await db_session.commit()
                    posted_q.appendleft(head)

                await asyncio.sleep(600)
            except Exception as e:
                print(f"Ошибка в RSS-парсере: {e}")
                await asyncio.sleep(10)


@app.on_event("startup")
async def startup_event():
    """Запуск фонового парсера при старте приложения."""
    async with async_session_factory() as db_session:
        asyncio.create_task(rss_parser(db_session))

@app.get("/exchange-rates/")
async def get_exchange_rates():
    url = "https://www.cbr.ru/scripts/XML_daily.asp"
    response = requests.get(url)

    if response.status_code == 200:
        from xml.etree import ElementTree as ET
        tree = ET.fromstring(response.content)

        usd = tree.find(".//Valute[CharCode='USD']/Value").text
        eur = tree.find(".//Valute[CharCode='EUR']/Value").text

        return {"USD": usd, "EUR": eur}
    else:
        return {"error": "Unable to fetch exchange rates"}

app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")

@app.post("/register/")
async def register_user(username: str, password: str, is_admin: bool = False, db: AsyncSession = Depends(get_db)):
    hashed_password = pwd_context.hash(password)
    new_user = User(username=username, hashed_password=hashed_password, is_admin=is_admin)
    db.add(new_user)
    await db.commit()
    return {"message": "User created successfully"}

@app.post("/token/")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.username == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = jwt.encode({"sub": user.username}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/me/")
async def read_current_user(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "is_admin": current_user.is_admin}

class NewsCreate(BaseModel):
    title: str
    content: str
    category: str | None = None

class NewsResponse(BaseModel):
    id: int
    title: str
    content: str
    category: str | None
    published_at: str

    class Config:
        orm_mode = True

def convert_news_to_response(news: News) -> NewsResponse:
    return NewsResponse(
        id=news.id,
        title=news.title,
        content=news.content,
        category=news.category,
        published_at=news.published_at.isoformat() if news.published_at else None,
    )


@app.get("/news/", response_model=list[NewsResponse])
async def get_news(
    title: str | None = None,
    category: str | None = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(News)
    
    if title:
        query = query.filter(News.title.ilike(f"%{title}%"))
    if category:
        query = query.filter(News.category == category)
    query = query.order_by(News.published_at.desc())
    
    result = await db.execute(query)
    news_list = result.scalars().all()
    return [convert_news_to_response(news) for news in news_list]

@app.get("/news/{news_id}", response_model=NewsResponse)
async def get_news_by_id(news_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(News).filter(News.id == news_id))
    news = result.scalar_one_or_none()
    if news is None:
        raise HTTPException(status_code=404, detail="News not found")
    return convert_news_to_response(news)

@app.post("/news/", response_model=NewsResponse)
async def create_news(news: NewsCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_admin)):
    db_news = News(title=news.title, content=news.content, category=news.category)
    db.add(db_news)
    await db.commit()
    await db.refresh(db_news)
    return convert_news_to_response(db_news)


@app.delete("/news/{news_id}")
async def delete(news_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_admin)):
    result = await db.execute(select(News).filter(News.id == news_id))
    news = result.scalar_one_or_none()
    if news is None:
        raise HTTPException(status_code=404, detail="News not found")
    await db.delete(news)
    await db.commit()
    return {"message": "News deleted successfully"}


@app.put("/news/{news_id}", response_model=NewsResponse)
async def update_news(
    news_id: int,
    news: NewsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(select(News).filter(News.id == news_id))
    db_news = result.scalar_one_or_none()
    if db_news is None:
        raise HTTPException(status_code=404, detail="News not found")

    db_news.title = news.title
    db_news.content = news.content
    db_news.category = news.category
    await db.commit()
    await db.refresh(db_news)
    return convert_news_to_response(db_news)