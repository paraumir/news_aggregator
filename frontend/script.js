const newsContainer = document.getElementById('news-container');
const addNewsForm = document.getElementById('add-news-form');
const editModal = document.getElementById('edit-modal');
const closeEditButton = document.getElementById('close-edit');
const saveEditButton = document.getElementById('save-edit');
const loginForm = document.getElementById('login-form');

let userRole = null;

function isAuthenticated() {
    const token = localStorage.getItem('token');
    return !!token;
}

function authHeaders() {
    const token = localStorage.getItem('token');
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
    };
}

async function fetchUserRole() {
    try {
        const response = await fetch('/me/', { headers: authHeaders() });

        if (response.ok) {
            const user = await response.json();
            userRole = user.is_admin ? 'admin' : 'user';

            const addNewsSection = document.getElementById('add-news-section');
            addNewsSection.style.display = userRole === 'admin' ? 'block' : 'none';

            console.log('Роль пользователя:', userRole);
        } else {
            console.error('Ошибка получения роли пользователя:', await response.json());
        }
    } catch (error) {
        console.error('Ошибка при получении роли пользователя:', error);
    }
}
async function fetchExchangeRates() {
    try {
        const response = await fetch('/exchange-rates/');
        if (response.ok) {
            const rates = await response.json();
            document.getElementById('usd-rate').textContent = rates.USD || 'N/A';
            document.getElementById('eur-rate').textContent = rates.EUR || 'N/A';
        } else {
            console.error('Ошибка загрузки данных о курсах валют');
            document.getElementById('usd-rate').textContent = 'Ошибка';
            document.getElementById('eur-rate').textContent = 'Ошибка';
        }
    } catch (error) {
        console.error('Ошибка подключения к серверу:', error);
        document.getElementById('usd-rate').textContent = 'Ошибка';
        document.getElementById('eur-rate').textContent = 'Ошибка';
    }
}

fetchExchangeRates();

async function loadNews() {
    const title = document.getElementById('search-title').value;
    const category = document.getElementById('search-category').value;

    try {
        const url = new URL('/news/', window.location.origin);
        const params = new URLSearchParams();

        if (title) params.append('title', title);
        if (category) params.append('category', category);
        url.search = params.toString();

        const response = await fetch(url, {
            headers: authHeaders()
        });

        if (response.ok) {
            const news = await response.json();
            newsContainer.innerHTML = '';

            news.forEach(newsItem => {
                const newsDiv = document.createElement('div');
                newsDiv.classList.add('news-item');
                newsDiv.innerHTML = `
                    <h3>${newsItem.title}</h3>
                    <p>${newsItem.content}</p>
                    <p><strong>Категория:</strong> ${newsItem.category || 'Без категории'}</p>
                    <p><small>Опубликовано: ${newsItem.published_at}</small></p>
                `;

                if (userRole === 'admin') {
                    console.log('Пользователь администратор, отображаем кнопки');
                    newsDiv.innerHTML += `
                        <button onclick="editNews(${newsItem.id}, '${newsItem.title}', '${newsItem.content}', '${newsItem.category || ''}')">Редактировать</button>
                        <button onclick="deleteNews(${newsItem.id})">Удалить</button>
                    `;
                }

                newsContainer.appendChild(newsDiv);
            });
        } else if (response.status === 401) {
            alert('Необходимо войти в систему.');
        } else {
            console.error('Ошибка загрузки новостей:', await response.json());
        }
    } catch (error) {
        console.error('Ошибка при загрузке новостей:', error);
    }
}

document.querySelector('button').addEventListener('click', (event) => {
    event.preventDefault();
    loadNews();
});

async function deleteNews(newsId) {
    try {
        const response = await fetch(`/news/${newsId}`, {
            method: 'DELETE',
            headers: authHeaders(),
        });

        if (response.ok) {
            console.log('Новость успешно удалена');
            loadNews();
        } else {
            const error = await response.json();
            alert('Ошибка удаления: ' + (error.detail || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('Ошибка при удалении новости:', error);
    }
}

function editNews(newsId, title, content, category) {
    document.getElementById('edit-title').value = title;
    document.getElementById('edit-content').value = content;
    document.getElementById('edit-category').value = category;

    editModal.style.display = 'block';

    saveEditButton.onclick = async () => {
        const updatedNews = {
            title: document.getElementById('edit-title').value,
            content: document.getElementById('edit-content').value,
            category: document.getElementById('edit-category').value || null,
        };

        try {
            const response = await fetch(`/news/${newsId}`, {
                method: 'PUT',
                headers: authHeaders(),
                body: JSON.stringify(updatedNews),
            });

            if (response.ok) {
                editModal.style.display = 'none';
                loadNews();
            } else {
                alert('Ошибка редактирования: ' + (await response.json()).detail);
            }
        } catch (error) {
            console.error('Ошибка при редактировании новости:', error);
        }
    };
}

closeEditButton.onclick = () => {
    editModal.style.display = 'none';
};

addNewsForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const newsData = {
        title: document.getElementById('title').value,
        content: document.getElementById('content').value,
        category: document.getElementById('category').value || null,
    };

    try {
        const response = await fetch('/news/', {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify(newsData),
        });

        if (response.ok) {
            loadNews();
        } else {
            alert('Ошибка добавления: ' + (await response.json()).detail);
        }
    } catch (error) {
        console.error('Ошибка при добавлении новости:', error);
    }
});

loginForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;

    try {
        const response = await fetch('/token/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ username, password }),
        });

        const data = await response.json();
        if (response.ok) {
            localStorage.setItem('token', data.access_token);
            alert('Вы успешно вошли');
            await fetchUserRole();
            loadNews();
        } else {
            alert('Ошибка входа: ' + (data.detail || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('Ошибка при входе:', error);
    }
});

async function initialize() {
    if (isAuthenticated()) {
        await fetchUserRole();
        loadNews();
    } else {
        alert('Вы не авторизованы!');
    }
}

initialize();
