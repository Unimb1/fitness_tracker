from app import app, db, User
import os

def migrate_database():
    with app.app_context():
        try:
            # Создаем все таблицы
            db.create_all()
            print("✅ База данных инициализирована")
            
            # Проверяем существование столбца weight
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('user')]
            
            if 'weight' not in columns:
                print("🔄 Добавляем столбец weight...")
                db.engine.execute('ALTER TABLE user ADD COLUMN weight REAL DEFAULT 70.0')
                print("✅ Столбец weight добавлен")
            
        except Exception as e:
            print(f"❌ Ошибка миграции: {e}")

if __name__ == '__main__':
    migrate_database()