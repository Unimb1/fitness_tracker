from app import app, db
import os

def migrate_database():
    with app.app_context():
        try:
            print("🔄 Создание таблиц в базе данных...")
            db.create_all()
            print("✅ Таблицы созданы успешно")
            
            # Проверяем существование таблицы user
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"✅ Существующие таблицы: {tables}")
            
        except Exception as e:
            print(f"❌ Ошибка при создании таблиц: {e}")

if __name__ == '__main__':
    migrate_database()
