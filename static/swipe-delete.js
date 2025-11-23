/**
 * Функционал свайпа для удаления тренировок и целей
 * С вибрацией на iOS
 */

(function() {
    'use strict';

    // Функция вибрации
    function vibrate(pattern) {
        if ('vibrate' in navigator) {
            navigator.vibrate(pattern);
        }
    }

    // Класс для управления свайпом
    class SwipeDelete {
        constructor(element, deleteUrl, itemType) {
            this.element = element;
            this.deleteUrl = deleteUrl;
            this.itemType = itemType;
            this.startX = 0;
            this.currentX = 0;
            this.isSwiping = false;
            this.swipeState = 0; // 0 - нет свайпа, 1 - показан крестик, 2 - готов к удалению
            this.threshold1 = 60; // Порог для показа крестика
            this.threshold2 = 150; // Порог для готовности к удалению
            
            this.init();
        }

        init() {
            // Находим или создаем обертку
            let wrapper = this.element.parentElement;
            if (!wrapper.classList.contains(`${this.itemType}-wrapper`)) {
                wrapper = document.createElement('div');
                wrapper.className = `${this.itemType}-wrapper`;
                this.element.parentElement.insertBefore(wrapper, this.element);
                wrapper.appendChild(this.element);
            }
            this.wrapper = wrapper;

            // Создаем элемент действия удаления если его нет
            let deleteAction = wrapper.querySelector(`.${this.itemType}-delete-action`);
            if (!deleteAction) {
                deleteAction = document.createElement('div');
                deleteAction.className = `${this.itemType}-delete-action`;
                deleteAction.innerHTML = '✕';
                wrapper.appendChild(deleteAction);
            }
            this.deleteAction = deleteAction;

            // Touch события
            this.element.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: true });
            this.element.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
            this.element.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: true });

            // Предотвращаем скролл при свайпе
            this.element.addEventListener('touchmove', (e) => {
                if (this.isSwiping) {
                    e.preventDefault();
                }
            }, { passive: false });
        }

        handleTouchStart(e) {
            this.startX = e.touches[0].clientX;
            this.isSwiping = false;
        }

        handleTouchMove(e) {
            if (!this.startX) return;

            this.currentX = e.touches[0].clientX;
            const diffX = this.startX - this.currentX; // Положительный = движение влево

            // Свайп только влево (положительный diffX означает движение влево)
            if (diffX > 10) {
                this.isSwiping = true;
                e.preventDefault();

                const swipeDistance = diffX;

                if (swipeDistance >= this.threshold2) {
                    // Второй порог - готовность к удалению
                    if (this.swipeState !== 2) {
                        this.swipeState = 2;
                        this.deleteAction.classList.add('delete-ready');
                        this.deleteAction.innerHTML = '🗑️ Удалить';
                        this.element.classList.add('swiping');
                        vibrate([50, 30, 50]); // Двойная вибрация
                    }
                    this.element.style.transform = `translateX(-${swipeDistance}px)`;
                } else if (swipeDistance >= this.threshold1) {
                    // Первый порог - показать крестик
                    if (this.swipeState !== 1) {
                        this.swipeState = 1;
                        this.deleteAction.classList.add('show');
                        this.deleteAction.innerHTML = '✕';
                        vibrate(30); // Короткая вибрация
                    }
                    this.element.style.transform = `translateX(-${swipeDistance}px)`;
                } else {
                    // Меньше первого порога - просто двигаем
                    this.element.style.transform = `translateX(-${swipeDistance}px)`;
                }
            } else if (diffX < -10) {
                // Свайп вправо - сброс
                this.reset();
            }
        }

        handleTouchEnd(e) {
            if (!this.isSwiping) {
                this.startX = 0;
                return;
            }

            const diffX = this.startX - this.currentX; // Положительный = движение влево

            if (this.swipeState === 2 && diffX >= this.threshold2) {
                // Показываем подтверждение перед удалением
                this.showDeleteConfirmation();
            } else if (this.swipeState === 1 && diffX >= this.threshold1) {
                // Оставляем крестик видимым
                this.element.style.transform = `translateX(-${this.threshold1}px)`;
            } else {
                // Сброс
                this.reset();
            }

            this.startX = 0;
            this.currentX = 0;
            this.isSwiping = false;
        }

        reset() {
            this.swipeState = 0;
            this.element.style.transform = '';
            this.element.style.transition = 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
            setTimeout(() => {
                this.element.style.transition = '';
            }, 300);
            this.element.classList.remove('swiping');
            this.deleteAction.classList.remove('show', 'delete-ready');
            this.deleteAction.innerHTML = '✕';
        }

        showDeleteConfirmation() {
            // Создаем модальное окно подтверждения
            const modal = document.createElement('div');
            modal.className = 'delete-confirmation-modal';
            modal.innerHTML = `
                <div class="delete-confirmation-content">
                    <h3>Удалить тренировку?</h3>
                    <div class="delete-confirmation-buttons">
                        <button class="btn-confirm-delete">Да</button>
                        <button class="btn-cancel-delete">Отмена</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            
            // Показываем модальное окно
            setTimeout(() => {
                modal.classList.add('show');
            }, 10);
            
            // Обработчики кнопок
            modal.querySelector('.btn-confirm-delete').addEventListener('click', () => {
                this.delete();
                document.body.removeChild(modal);
            });
            
            modal.querySelector('.btn-cancel-delete').addEventListener('click', () => {
                this.reset();
                document.body.removeChild(modal);
            });
            
            // Закрытие при клике вне модального окна
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.reset();
                    document.body.removeChild(modal);
                }
            });
        }
        
        delete() {
            // Анимация удаления
            this.element.style.transition = 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease';
            this.element.classList.add('swiping-delete');
            vibrate([100, 50, 100]); // Длинная вибрация при удалении

            setTimeout(() => {
                // Переход на страницу удаления
                if (this.deleteUrl) {
                    // Создаем форму для удаления
                    const form = document.createElement('form');
                    form.method = 'GET';
                    form.action = this.deleteUrl;
                    document.body.appendChild(form);
                    form.submit();
                }
            }, 300);
        }
    }

    // Инициализация для тренировок
    function initWorkoutSwipe() {
        const workoutSessions = document.querySelectorAll('.workout-session:not([data-swipe-initialized])');
        workoutSessions.forEach(session => {
            const deleteBtn = session.querySelector('.delete-session-btn');
            if (deleteBtn && deleteBtn.href) {
                session.setAttribute('data-swipe-initialized', 'true');
                new SwipeDelete(session, deleteBtn.href, 'workout-session');
            }
        });
    }

    // Инициализация для целей
    function initGoalSwipe() {
        const goalCards = document.querySelectorAll('.goal-card:not([data-swipe-initialized])');
        goalCards.forEach(card => {
            const deleteBtn = card.querySelector('.delete-goal-btn');
            if (deleteBtn && deleteBtn.href) {
                card.setAttribute('data-swipe-initialized', 'true');
                new SwipeDelete(card, deleteBtn.href, 'goal-card');
            }
        });
    }

    // Инициализация при загрузке
    function init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
            return;
        }

        initWorkoutSwipe();
        initGoalSwipe();

        // Переинициализация при динамическом добавлении элементов
        const observer = new MutationObserver(() => {
            initWorkoutSwipe();
            initGoalSwipe();
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    init();

    // Экспорт для использования в других скриптах
    if (typeof window !== 'undefined') {
        window.SwipeDelete = SwipeDelete;
    }

})();

