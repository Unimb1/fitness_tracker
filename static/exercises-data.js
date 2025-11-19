/**
 * Данные об упражнениях с группировкой по мышцам и MET значениями
 */

const EXERCISES_DATA = {
    'Грудь': [
        { name: 'Жим лежа', met: 6.0 },
        { name: 'Сведение рук в кроссовере на грудь', met: 5.0 }
    ],
    'Руки': [
        { name: 'Разгибания на трицепс с канатной рукоятью в кроссовере', met: 4.0 },
        { name: 'Сгибания на бицепс в рычажном тренажере', met: 4.0 }
    ],
    'Плечи': [
        { name: 'Махи на плечи со свободным весом', met: 4.5 },
        { name: 'Отведение плеча в блочном тренажере "reverse fly"', met: 4.0 }
    ],
    'Ноги': [
        { name: 'Ягодичный мост в рычажном тренажере', met: 5.5 },
        { name: 'Разгибание бедра стоя в кроссовере / рычажном тренажере', met: 5.0 },
        { name: 'Болгарские выпады со свободным весом / в смите', met: 6.0 },
        { name: 'Отведение бедра сидя в сдвоенном блочном тренажере (большая ягодичная)', met: 4.5 },
        { name: 'Отведение с наклоном вперед бедра сидя в сдвоенном блочном тренажере (малая и средняя ягодичные)', met: 4.5 },
        { name: 'Приседание в Смите', met: 6.5 }
    ],
    'Спина': [
        { name: 'Вертикальная тяга сидя', met: 6.0 },
        { name: 'Горизонтальная тяга троссовая в блочном тренажере', met: 6.0 },
        { name: 'Экстензия на наклонной скамье', met: 5.5 }
    ],
    'Кардио': [
        { name: 'Ходьба на дорожке с наклоном 13-14', met: 8.0 }
    ]
};

// Плоский список всех упражнений для обратной совместимости
const ALL_EXERCISES = [];
Object.values(EXERCISES_DATA).forEach(group => {
    group.forEach(exercise => {
        ALL_EXERCISES.push(exercise.name);
    });
});

// Функция для получения MET значения упражнения
function getExerciseMET(exerciseName) {
    for (const group of Object.values(EXERCISES_DATA)) {
        const exercise = group.find(e => e.name === exerciseName);
        if (exercise) {
            return exercise.met;
        }
    }
    return 5.0; // Значение по умолчанию
}

// Функция для создания опций выпадающего списка с группировкой
function createGroupedExerciseSelect(selectElement, includeEmpty = true) {
    // Очищаем существующие опции
    selectElement.innerHTML = '';
    
    // Добавляем пустую опцию если нужно
    if (includeEmpty) {
        const emptyOption = document.createElement('option');
        emptyOption.value = '';
        emptyOption.textContent = 'Выберите упражнение';
        selectElement.appendChild(emptyOption);
    }
    
    // Создаем оптгруппы для каждой группы мышц
    Object.keys(EXERCISES_DATA).forEach(muscleGroup => {
        const optgroup = document.createElement('optgroup');
        optgroup.label = muscleGroup;
        
        EXERCISES_DATA[muscleGroup].forEach(exercise => {
            const option = document.createElement('option');
            option.value = exercise.name;
            option.textContent = exercise.name;
            optgroup.appendChild(option);
        });
        
        selectElement.appendChild(optgroup);
    });
}

// Экспорт для использования в других скриптах
if (typeof window !== 'undefined') {
    window.EXERCISES_DATA = EXERCISES_DATA;
    window.ALL_EXERCISES = ALL_EXERCISES;
    window.getExerciseMET = getExerciseMET;
    window.createGroupedExerciseSelect = createGroupedExerciseSelect;
}

