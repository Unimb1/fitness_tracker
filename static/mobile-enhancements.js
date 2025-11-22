/**
 * Мобильные улучшения для фитнес-трекера
 * Оптимизировано для iPhone 13 Pro и iOS 16+
 */

(function() {
    'use strict';

    // ============================================
    // ОПТИМИЗАЦИЯ ДЛЯ iOS
    // ============================================
    
    // Предотвращение зума при фокусе на input
    if (/iPhone|iPad|iPod/.test(navigator.userAgent)) {
        const inputs = document.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            if (input.type !== 'date' && input.type !== 'time') {
                input.addEventListener('focus', function() {
                    if (this.style.fontSize !== '16px') {
                        this.style.fontSize = '16px';
                    }
                });
            }
        });
    }

    // ============================================
    // УЛУЧШЕНИЕ ТАЙМЕРОВ
    // ============================================
    
    // Вибрация для iOS (если доступна)
    function vibrate(pattern) {
        if ('vibrate' in navigator) {
            navigator.vibrate(pattern);
        }
    }

    // Улучшенный таймер тренировки
    function enhanceWorkoutTimer() {
        const timerContainer = document.getElementById('workout-timer-container');
        if (!timerContainer) return;

        const timerDisplay = document.getElementById('workout-timer');
        if (!timerDisplay) return;

        // Добавляем анимацию пульсации каждую секунду
        let lastSecond = -1;
        const interval = setInterval(() => {
            const currentSecond = new Date().getSeconds();
            if (currentSecond !== lastSecond) {
                timerDisplay.style.animation = 'none';
                setTimeout(() => {
                    timerDisplay.style.animation = 'pulseTimer 0.3s ease-out';
                }, 10);
                lastSecond = currentSecond;
            }
        }, 100);

        // Очистка при удалении элемента
        const observer = new MutationObserver(() => {
            if (!document.body.contains(timerContainer)) {
                clearInterval(interval);
                observer.disconnect();
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }

    // Улучшенный таймер перерыва
    function enhanceRestTimer() {
        const restTimers = document.querySelectorAll('.set-rest-timer');
        restTimers.forEach(timer => {
            const timeDisplay = timer.querySelector('.rest-timer-time');
            if (!timeDisplay) return;

            // Добавляем визуальную обратную связь при изменении времени
            let lastTime = timeDisplay.textContent;
            const observer = new MutationObserver(() => {
                if (timeDisplay.textContent !== lastTime) {
                    timeDisplay.style.transform = 'scale(1.1)';
                    setTimeout(() => {
                        timeDisplay.style.transform = 'scale(1)';
                    }, 200);
                    lastTime = timeDisplay.textContent;
                }
            });
            observer.observe(timeDisplay, { childList: true, characterData: true, subtree: true });
        });
    }

    // ============================================
    // УЛУЧШЕНИЕ ГРАФИКОВ ДЛЯ МОБИЛЬНЫХ
    // ============================================
    
    function enhanceCharts() {
        // Находим все контейнеры графиков
        const chartContainers = document.querySelectorAll('.chart-container');
        
        chartContainers.forEach(container => {
            const canvas = container.querySelector('canvas');
            if (!canvas) return;

            // Добавляем обработчик для масштабирования на touch
            let touchStartDistance = 0;
            let initialHeight = container.offsetHeight;

            container.addEventListener('touchstart', function(e) {
                if (e.touches.length === 2) {
                    const touch1 = e.touches[0];
                    const touch2 = e.touches[1];
                    touchStartDistance = Math.hypot(
                        touch2.clientX - touch1.clientX,
                        touch2.clientY - touch1.clientY
                    );
                }
            });

            container.addEventListener('touchmove', function(e) {
                if (e.touches.length === 2) {
                    e.preventDefault();
                    const touch1 = e.touches[0];
                    const touch2 = e.touches[1];
                    const currentDistance = Math.hypot(
                        touch2.clientX - touch1.clientX,
                        touch2.clientY - touch1.clientY
                    );
                    
                    const scale = currentDistance / touchStartDistance;
                    const newHeight = Math.max(200, Math.min(600, initialHeight * scale));
                    container.style.height = newHeight + 'px';
                }
            });

            // Добавляем индикатор возможности масштабирования
            const indicator = document.createElement('div');
            indicator.style.cssText = `
                position: absolute;
                bottom: 10px;
                right: 10px;
                background: rgba(0, 0, 0, 0.5);
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 10px;
                pointer-events: none;
                opacity: 0;
                transition: opacity 0.3s;
            `;
            indicator.textContent = '📌 Два пальца для масштаба';
            container.style.position = 'relative';
            container.appendChild(indicator);

            container.addEventListener('touchstart', () => {
                indicator.style.opacity = '1';
                setTimeout(() => {
                    indicator.style.opacity = '0';
                }, 2000);
            });
        });
    }

    // ============================================
    // УЛУЧШЕНИЕ КНОПОК ДЛЯ TOUCH
    // ============================================
    
    function enhanceButtons() {
        const buttons = document.querySelectorAll('button, .btn-primary, .btn-secondary, a.btn-primary, a.btn-secondary');
        
        buttons.forEach(button => {
            // Добавляем визуальную обратную связь
            button.addEventListener('touchstart', function(e) {
                this.style.transform = 'scale(0.96)';
                vibrate(10); // Короткая вибрация
            }, { passive: true });

            button.addEventListener('touchend', function(e) {
                setTimeout(() => {
                    this.style.transform = '';
                }, 150);
            }, { passive: true });

            // Предотвращаем двойной тап
            let lastTap = 0;
            button.addEventListener('touchend', function(e) {
                const currentTime = new Date().getTime();
                const tapLength = currentTime - lastTap;
                if (tapLength < 300 && tapLength > 0) {
                    e.preventDefault();
                }
                lastTap = currentTime;
            });
        });
    }

    // ============================================
    // УЛУЧШЕНИЕ ФОРМ
    // ============================================
    
    function addNumberButtons(input) {
        // Проверяем, не добавлены ли уже кнопки
        if (input.parentElement && input.parentElement.classList.contains('number-input-wrapper')) {
            return;
        }
        
        // Добавляем кнопки +/- для удобства на мобильных
        const wrapper = document.createElement('div');
        wrapper.className = 'number-input-wrapper';
        wrapper.style.cssText = 'position: relative; display: flex; align-items: center;';
        
        const minusBtn = document.createElement('button');
        minusBtn.type = 'button';
        minusBtn.textContent = '−';
        minusBtn.className = 'number-btn-minus';
        minusBtn.style.cssText = `
            position: absolute;
            left: 8px;
            width: 32px;
            height: 32px;
            border: none;
            background: rgba(0, 0, 0, 0.1);
            border-radius: 6px;
            font-size: 20px;
            font-weight: bold;
            color: var(--text-primary);
            cursor: pointer;
            z-index: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 32px;
        `;
        minusBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const step = parseFloat(input.step) || 1;
            const min = parseFloat(input.min) || 0;
            const current = parseFloat(input.value) || 0;
            input.value = Math.max(min, current - step);
            input.dispatchEvent(new Event('change', { bubbles: true }));
            input.dispatchEvent(new Event('input', { bubbles: true }));
            vibrate(10);
        });

        const plusBtn = document.createElement('button');
        plusBtn.type = 'button';
        plusBtn.textContent = '+';
        plusBtn.className = 'number-btn-plus';
        plusBtn.style.cssText = `
            position: absolute;
            right: 8px;
            width: 32px;
            height: 32px;
            border: none;
            background: rgba(0, 0, 0, 0.1);
            border-radius: 6px;
            font-size: 20px;
            font-weight: bold;
            color: var(--text-primary);
            cursor: pointer;
            z-index: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 32px;
        `;
        plusBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const step = parseFloat(input.step) || 1;
            const max = parseFloat(input.max) || Infinity;
            const current = parseFloat(input.value) || 0;
            input.value = Math.min(max, current + step);
            input.dispatchEvent(new Event('change', { bubbles: true }));
            input.dispatchEvent(new Event('input', { bubbles: true }));
            vibrate(10);
        });

        // Обертываем input
        const parent = input.parentElement;
        parent.insertBefore(wrapper, input);
        wrapper.appendChild(input);
        wrapper.appendChild(minusBtn);
        wrapper.appendChild(plusBtn);
    }
    
    function enhanceForms() {
        const inputs = document.querySelectorAll('input[type="number"]:not(.number-input-wrapper input)');
        
        inputs.forEach(input => {
            addNumberButtons(input);
        });
    }
    
    // Функция для наблюдения за новыми элементами
    function observeNewInputs() {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1) { // Element node
                        // Проверяем сам узел
                        if (node.tagName === 'INPUT' && node.type === 'number') {
                            if (!node.parentElement.classList.contains('number-input-wrapper')) {
                                addNumberButtons(node);
                            }
                        }
                        // Проверяем дочерние элементы
                        const newInputs = node.querySelectorAll && node.querySelectorAll('input[type="number"]:not(.number-input-wrapper input)');
                        if (newInputs) {
                            newInputs.forEach(input => {
                                if (!input.parentElement.classList.contains('number-input-wrapper')) {
                                    addNumberButtons(input);
                                }
                            });
                        }
                    }
                });
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    // ============================================
    // УЛУЧШЕНИЕ ПРОКРУТКИ
    // ============================================
    
    function enhanceScrolling() {
        // Плавная прокрутка для iOS
        if (/iPhone|iPad|iPod/.test(navigator.userAgent)) {
            document.documentElement.style.scrollBehavior = 'smooth';
        }

        // Добавляем индикатор прокрутки
        const scrollIndicator = document.createElement('div');
        scrollIndicator.id = 'scroll-indicator';
        scrollIndicator.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 0%;
            height: 3px;
            background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
            z-index: 10001;
            transition: width 0.1s ease-out;
            pointer-events: none;
        `;
        document.body.appendChild(scrollIndicator);

        window.addEventListener('scroll', () => {
            const windowHeight = window.innerHeight;
            const documentHeight = document.documentElement.scrollHeight;
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            const scrollPercent = (scrollTop / (documentHeight - windowHeight)) * 100;
            scrollIndicator.style.width = scrollPercent + '%';
        }, { passive: true });
    }

    // ============================================
    // УЛУЧШЕНИЕ УВЕДОМЛЕНИЙ
    // ============================================
    
    function enhanceNotifications() {
        // Запрашиваем разрешение на уведомления
        if ('Notification' in window && Notification.permission === 'default') {
            // Не запрашиваем автоматически, только при необходимости
        }

        // Улучшаем toast уведомления
        const toasts = document.querySelectorAll('.toast');
        toasts.forEach(toast => {
            // Добавляем автоматическое скрытие
            setTimeout(() => {
                if (toast && document.body.contains(toast)) {
                    toast.classList.add('toast-hide');
                    setTimeout(() => {
                        if (toast && document.body.contains(toast)) {
                            toast.style.display = 'none';
                        }
                    }, 500);
                }
            }, 5000);
        });
    }

    // ============================================
    // ОПТИМИЗАЦИЯ ПРОИЗВОДИТЕЛЬНОСТИ
    // ============================================
    
    function optimizePerformance() {
        // Lazy loading для изображений
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.removeAttribute('data-src');
                            observer.unobserve(img);
                        }
                    }
                });
            });

            document.querySelectorAll('img[data-src]').forEach(img => {
                imageObserver.observe(img);
            });
        }

        // Дебаунс для событий скролла
        let scrollTimeout;
        const originalScrollHandler = window.onscroll;
        window.onscroll = function() {
            if (scrollTimeout) {
                clearTimeout(scrollTimeout);
            }
            scrollTimeout = setTimeout(() => {
                if (originalScrollHandler) {
                    originalScrollHandler();
                }
            }, 10);
        };
    }

    // ============================================
    // ИНИЦИАЛИЗАЦИЯ
    // ============================================
    
    function init() {
        // Ждем загрузки DOM
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
            return;
        }

        // Запускаем все улучшения
        enhanceWorkoutTimer();
        enhanceRestTimer();
        enhanceCharts();
        enhanceButtons();
        enhanceForms();
        observeNewInputs(); // Наблюдаем за новыми input полями
        enhanceScrolling();
        enhanceNotifications();
        optimizePerformance();

        // Периодически обновляем таймеры перерыва
        setInterval(enhanceRestTimer, 1000);
    }

    // Запускаем инициализацию
    init();

    // Экспортируем функции для использования в других скриптах
    window.MobileEnhancements = {
        vibrate,
        enhanceWorkoutTimer,
        enhanceRestTimer,
        enhanceCharts,
        enhanceButtons,
        enhanceForms
    };

})();







